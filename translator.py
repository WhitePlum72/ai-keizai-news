"""
翻訳・記事生成モジュール（DeepSeek公式API対応版）
- platform.deepseek.com のAPIを使用
- thinking無効化でトークン節約
- 429リトライ・指数バックオフ対応
- scorer.py向けのGoogle翻訳（translate_text）は引き続き使用
"""

import sqlite3
import logging
import os
import sys
import re
import time
import requests
from datetime import datetime

try:
    from dotenv import load_dotenv
    load_dotenv(dotenv_path='.env', override=True)
except ImportError:
    pass

DB_PATH = "data/articles.db"
LOG_DIR = "logs"

DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY")
DEEPSEEK_URL     = "https://api.deepseek.com/chat/completions"
DEEPSEEK_MODEL   = "deepseek-v4-pro"

# 記事間の待機秒数（レートリミット対策）
API_INTERVAL = 10

LABEL_PREFIX_RE     = re.compile(r'^\s*(?:[#>*\-]+\s*)?(?:見出し|本文)\s*[:：]\s*')
MARKDOWN_HEADING_RE = re.compile(r'^\s*#+\s*')


# ========================
# ロガー
# ========================
def setup_logger():
    logger = logging.getLogger("translator")
    logger.setLevel(logging.DEBUG)
    if logger.handlers:
        return logger

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    logger.addHandler(console_handler)

    os.makedirs(LOG_DIR, exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")
    file_handler = logging.FileHandler(
        os.path.join(LOG_DIR, f"{today}.log"), encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    logger.addHandler(file_handler)
    return logger


logger = setup_logger()


# ========================
# DB
# ========================
def init_summaries_table():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS summaries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            article_id INTEGER UNIQUE,
            title_ja TEXT,
            summary_ja TEXT,
            tweet_text TEXT,
            category TEXT,
            meta_description TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    try:
        cursor.execute("ALTER TABLE summaries ADD COLUMN meta_description TEXT")
    except Exception:
        pass
    conn.commit()
    conn.close()


def get_articles_to_translate():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT a.id, a.title, a.summary, a.source, a.source_type, a.url
        FROM articles a
        LEFT JOIN summaries s ON a.id = s.article_id
        WHERE a.buzz_score > 0
          AND s.article_id IS NULL
        ORDER BY a.buzz_score DESC
        LIMIT 10
    """)
    rows = cursor.fetchall()
    conn.close()
    return rows


def save_summary(article_id, title_ja, summary_ja, tweet_text, category, meta_description="", article_slug="", category_slug=""):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO summaries
            (article_id, title_ja, summary_ja, tweet_text, category,
             meta_description, article_slug, category_slug, slug_en)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (article_id, title_ja, summary_ja, tweet_text, category,
          meta_description, article_slug, category_slug, article_slug))
    cursor.execute("""
        UPDATE articles
        SET processed = 1,
            article_slug = ?,
            category_slug = ?
        WHERE id = ?
    """, (article_slug, category_slug, article_id))
    conn.commit()
    conn.close()
    return True


# ========================
# テキスト処理
# ========================
def clean_html(text):
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def remove_output_labels(text):
    if not text:
        return ""
    lines = []
    for line in text.split("\n"):
        line = LABEL_PREFIX_RE.sub("", line).strip()
        lines.append(line)
    return "\n".join(lines).strip()


def clean_title_line(text, fallback_title):
    line = remove_output_labels(text).splitlines()[0].strip()
    line = MARKDOWN_HEADING_RE.sub("", line).strip()
    return line or fallback_title


# ========================
# SEO系
# ========================
def make_meta_description(body):
    text = remove_output_labels(clean_html(body))
    sentences = re.split(r'。', text)
    desc = ""
    for s in sentences:
        if len(desc) + len(s) <= 140:
            desc += s + "。"
        else:
            break
    return desc.strip()


def make_lead(body):
    sentences = re.split(r'。', body)
    lead = ""
    for s in sentences:
        if len(lead) + len(s) <= 120:
            lead += s + "。"
        else:
            break
    return lead.strip()


# ========================
# 記事分解
# ========================
def split_generated_article(text, fallback_title):
    text  = remove_output_labels(text)
    lines = text.splitlines()
    title = clean_title_line(lines[0], fallback_title)
    body  = "\n".join(lines[1:]).strip()
    return {
        "title": title,
        "lead":  make_lead(body),
        "body":  body,
        "meta_description": make_meta_description(body),
    }


# ========================
# Google翻訳（scorer.py向けに残存）
# ========================
def translate_text(text):
    try:
        from deep_translator import GoogleTranslator
        return GoogleTranslator(source="en", target="ja").translate(text)
    except Exception:
        return text


# ========================
# DeepSeek API呼び出し（requests直接・thinking無効）
# ========================
def call_deepseek(prompt: str, max_tokens: int = 2500, max_retries: int = 5) -> str:
    """
    DeepSeek公式APIをrequestsで直接呼び出す。
    - thinking無効化でトークン節約
    - 429時は指数バックオフでリトライ
    """
    if not DEEPSEEK_API_KEY:
        raise EnvironmentError(
            "DEEPSEEK_API_KEY が設定されていません。\n"
            "PowerShellで: $env:DEEPSEEK_API_KEY='sk-...' を実行してください。"
        )

    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json",
    }
    body = {
        "model": DEEPSEEK_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "thinking": {"type": "disabled"},  # thinkingを無効化してトークン節約
    }

    for attempt in range(max_retries):
        try:
            res = requests.post(DEEPSEEK_URL, headers=headers, json=body, timeout=60)

            if res.status_code == 429:
                wait = 60 * (attempt + 1)
                logger.warning("429 レートリミット、%d秒待機 (%d/%d)", wait, attempt + 1, max_retries)
                time.sleep(wait)
                continue

            res.raise_for_status()
            data = res.json()
            return data["choices"][0]["message"]["content"].strip()

        except requests.exceptions.Timeout:
            logger.warning("タイムアウト (%d/%d)、リトライします", attempt + 1, max_retries)
            time.sleep(10)
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            logger.warning("APIエラー (%d/%d): %s", attempt + 1, max_retries, e)
            time.sleep(10)

    raise RuntimeError(f"APIリトライ上限({max_retries}回)に達しました")


# ========================
# 記事生成
# ========================
def generate_article(title_en: str, body_en: str) -> tuple[str, str, str, str]:
    """
    Returns: (article_body, meta_description, slug_en, category_slug) のタプル
    """

    # ---- 記事本文生成 ----
    article_prompt = f"""あなたはITmedia・Bloomberg・日経クロステック級の日本人経済記者だ。
以下のニュース情報を元に、高品質な日本語経済ニュース記事を生成せよ。

【元記事情報】
タイトル: {title_en}
内容: {body_en[:3000]}

【絶対ルール】
・1行目: タイトル（32〜42文字）
  - 記事内の最も重要な数字・固有名詞を必ず含める
  - 読者の疑問や利益を示す（「なぜ」「〜の理由」「〜が変わる」等）
  - 【】「」などの記号・括弧は一切使わない
  - 誇張・煽り禁止
  - 重要ワードを前半に配置
・2行目: 空行
・本文1200〜1800文字
・だ・である調
・機械翻訳調禁止
・同じ論点の繰り返し禁止
・3〜4文ごとに改行を入れる

【本文構成】
1. リード文（2〜3文）
   - 結論を最初の1文に凝縮する
   - 「誰が・何を・どれだけ・なぜ重要か」を含める
   - 120文字以内で読者を引き込む
2. ## セクション見出し（記事内容を反映した具体的な見出し）
3. ## セクション見出し
4. ## セクション見出し
5. ## セクション見出し
6. ## セクション見出し

【見出しルール】
・各セクションの冒頭は必ず ## 見出し の形式にする
・見出しは体言止めまたは疑問形
・「## 何が起きたか」のような汎用的な見出しは禁止

【品質基準】
・数字にはソース感を付ける（「〇〇によると」「アナリスト予測では」等）
・「今後の動向に注目です」等の締めは禁止
・日本市場・日本企業への影響を必ず1箇所含める"""

    article_body = call_deepseek(article_prompt, max_tokens=2500)
    time.sleep(API_INTERVAL)

    # ---- meta description生成 ----
    meta_prompt = (
        "以下の記事を120文字以内で要約してください。"
        "文末は「。」で終わること。マークダウン禁止。\n\n"
        f"{article_body[:1000]}"
    )
    meta_description = call_deepseek(meta_prompt, max_tokens=200)[:120]
    time.sleep(API_INTERVAL)

    # ---- slug生成 ----
    slug_prompt = f"""Generate a URL slug for this article.

Title: {title_en}

RULES:
- Output ONLY the slug, nothing else
- 3 to 5 words maximum
- Lowercase letters, numbers, hyphens only
- Include the most important company name or product name
- Include a strong action verb or key topic
- No stop words (a, the, in, of, for, and, to, with)
- Examples: openai-gpt5-reasoning-launch, nvidia-blackwell-datacenter-demand, anthropic-finance-agents-ipo

Slug:"""

    slug_raw = call_deepseek(slug_prompt, max_tokens=30)
    slug_en = re.sub(r'[^a-z0-9-]', '', slug_raw.lower().strip().replace(' ', '-'))[:80]

    return article_body, meta_description, slug_en


# ========================
# X投稿文
# ========================
def make_tweet(title: str, body: str, category: str) -> str:
    prefix = f"【{category}】"
    lead   = make_lead(body)
    suffix = " #AI #LLM"
    text   = f"{prefix}{title}\n{lead}"
    return text[:140 - len(suffix)] + suffix


# ========================
# カテゴリ分類
# ========================
SOURCE_TYPE_TO_CATEGORY = {
    "model":    "AIモデル",
    "business": "ビジネス",
    "research": "研究",
    "stock":    "AI関連株",
    "arxiv":    "研究",
    "hn":       "ビジネス",
}
SOURCE_TYPE_TO_CATEGORY_SLUG = {
    "model":    "model",
    "business": "business",
    "research": "research",
    "stock":    "stock",
    "arxiv":    "research",
    "hn":       "business",
    "official_blog": "model",
    "gov_jp":   "policy",
    "ir_tdnet": "stock",
}

def get_category_slug(source_type: str) -> str:
    return SOURCE_TYPE_TO_CATEGORY_SLUG.get(source_type, "ai")

def get_category(source_type: str) -> str:
    return SOURCE_TYPE_TO_CATEGORY.get(source_type, "AI")


# ========================
# メイン
# ========================
def translate_all():
    init_summaries_table()
    articles = get_articles_to_translate()

    if not articles:
        logger.info("翻訳対象の記事がありません。")
        return

    logger.info("翻訳開始: %d件", len(articles))

    for i, a in enumerate(articles):
        article_id, title, summary, source, source_type, url = a

        try:
            generated, meta_description, slug_en = generate_article(title, summary)
            data = split_generated_article(generated, title)
            data["meta_description"] = meta_description

            category      = get_category(source_type)
            category_slug = get_category_slug(source_type)
            tweet         = make_tweet(data["title"], data["body"], category)

            save_summary(
                article_id,
                data["title"],
                data["body"],
                tweet,
                category,
                data["meta_description"],
                article_slug=slug_en,
                category_slug=category_slug,
            )

            logger.info("完了 [id=%d] slug=%s: %s", article_id, slug_en, data["title"])

            if i < len(articles) - 1:
                time.sleep(API_INTERVAL)

        except Exception as e:
            logger.error("失敗 [id=%d]: %s", article_id, e)
            continue


if __name__ == "__main__":
    translate_all()
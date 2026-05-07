"""
翻訳・記事生成モジュール（DeepSeek V4 Pro対応版）
NVIDIA NIM API経由でDeepSeek V4 Proを使用し、英語原文から直接高品質な日本語記事を生成する。
scorer.py向けのGoogle翻訳（translate_text）は引き続き使用。
"""

import sqlite3
import logging
import os
import sys
import re
import openai
from datetime import datetime

# .envからAPIキーを読み込む（python-dotenv使用）
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # .envが使えない環境でも動作するようフォールバック

DB_PATH = "data/articles.db"
LOG_DIR = "logs"
DELAY_SECONDS = 0.5

NVIDIA_API_KEY  = os.environ.get("NVIDIA_API_KEY")
NVIDIA_BASE_URL = "https://integrate.api.nvidia.com/v1"
DEEPSEEK_MODEL  = "deepseek-ai/deepseek-v4-pro"

LABEL_PREFIX_RE   = re.compile(r'^\s*(?:[#>*\-]+\s*)?(?:見出し|本文)\s*[:：]\s*')
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


def save_summary(article_id, title_ja, summary_ja, tweet_text, category, meta_description=""):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO summaries
            (article_id, title_ja, summary_ja, tweet_text, category, meta_description)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (article_id, title_ja, summary_ja, tweet_text, category, meta_description))
    cursor.execute("UPDATE articles SET processed = 1 WHERE id = ?", (article_id,))
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
    text = remove_output_labels(text)
    lines = text.splitlines()

    title = clean_title_line(lines[0], fallback_title)
    body = "\n".join(lines[1:]).strip()

    return {
        "title": title,
        "lead": make_lead(body),
        "body": body,
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
# DeepSeek V4 Pro 記事生成
# ========================
def generate_article(title_en: str, body_en: str) -> tuple[str, str]:
    """
    英語の元記事情報からDeepSeek V4 Proで高品質な日本語記事を生成する。

    Returns:
        (article_body, meta_description) のタプル
    """
    if not NVIDIA_API_KEY:
        raise EnvironmentError(
            "NVIDIA_API_KEY が設定されていません。.env ファイルを確認してください。"
        )

    client = openai.OpenAI(
        base_url=NVIDIA_BASE_URL,
        api_key=NVIDIA_API_KEY,
    )

    # ---- 記事本文生成 ----
    article_prompt = f"""あなたはITmedia・Bloomberg・日経クロステック級の日本人経済記者だ。
以下のニュース情報を元に、高品質な日本語経済ニュース記事を生成せよ。

【元記事情報】
タイトル: {title_en}
内容: {body_en[:3000]}

【絶対ルール】
・1行目: タイトル（32〜42文字、重要ワードを前半に、誇張禁止）
・2行目: 空行
・本文1200〜1800文字
・だ・である調
・マークダウン禁止
・機械翻訳調禁止
・同じ論点の繰り返し禁止
・3〜4文ごとに改行を入れる

【本文構成】
1. リード文（2〜3文、最重要ポイントを最初に提示）
2. 何が起きたか（具体的な数字・固有名詞を含める）
3. なぜ今重要なのか（業界・市場への影響）
4. 背景と競合状況（他社との比較・業界構造）
5. 投資家・企業戦略視点での考察
6. 今後の展望（抽象論禁止・具体的な予測）

【品質基準】
・数字にはソース感を付ける（「〇〇によると」「アナリスト予測では」等）
・小見出しを追加（■ 見出し の形式）
・「今後の動向に注目です」等の締めは禁止
・日本市場・日本企業への影響を必ず1箇所含める"""

    article_res = client.chat.completions.create(
        model=DEEPSEEK_MODEL,
        messages=[{"role": "user", "content": article_prompt}],
        max_tokens=2500,
    )
    article_body = article_res.choices[0].message.content.strip()

    # ---- meta description生成 ----
    meta_prompt = (
        "以下の記事を120文字以内で要約してください。"
        "文末は「。」で終わること。マークダウン禁止。\n\n"
        f"{article_body[:1000]}"
    )
    meta_res = client.chat.completions.create(
        model=DEEPSEEK_MODEL,
        messages=[{"role": "user", "content": meta_prompt}],
        max_tokens=200,
    )
    meta_description = meta_res.choices[0].message.content.strip()[:120]

    return article_body, meta_description


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

    for a in articles:
        article_id, title, summary, source, source_type, url = a

        try:
            # Google翻訳は廃止 → 英語原文をそのままDeepSeekに渡す
            generated, meta_description = generate_article(title, summary)
            data = split_generated_article(generated, title)
            data["meta_description"] = meta_description

            category = get_category(source_type)
            tweet    = make_tweet(data["title"], data["body"], category)

            save_summary(
                article_id,
                data["title"],
                data["body"],
                tweet,
                category,
                data["meta_description"],
            )

            logger.info(f"完了 [id={article_id}]: {data['title']}")

        except Exception as e:
            logger.error(f"失敗 [id={article_id}]: {e}")
            continue


if __name__ == "__main__":
    translate_all()

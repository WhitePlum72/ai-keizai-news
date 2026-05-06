"""
翻訳・記事生成モジュール（最適化版）
Google翻訳 + QwenでSEO最適化記事＋リード文＋X投稿文を生成
"""

import sqlite3
import logging
import os
import sys
import time
import re
import openai
from datetime import datetime
from deep_translator import GoogleTranslator

DB_PATH = "data/articles.db"
LOG_DIR = "logs"
DELAY_SECONDS = 0.5
QWEN_BASE_URL = "http://localhost:8080/v1"
QWEN_MODEL = "Qwen3.6-27B-UD-Q4_K_XL.gguf"

LABEL_PREFIX_RE = re.compile(r'^\s*(?:[#>*\-]+\s*)?(?:見出し|本文)\s*[:：]\s*')
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
    file_handler = logging.FileHandler(os.path.join(LOG_DIR, f"{today}.log"), encoding="utf-8")
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
    except:
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
        LIMIT 30
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
# 翻訳
# ========================
def translate_text(text):
    try:
        return GoogleTranslator(source="en", target="ja").translate(text)
    except:
        return text


# ========================
# Qwen
# ========================
def generate_article(title_ja, body):
    client = openai.OpenAI(base_url=QWEN_BASE_URL, api_key="dummy")

    prompt = f"""
あなたは日本の新聞記者である。

以下から記事を書け。

{body[:2000]}

条件:
・1行目: 見出し（25文字以内）
・2行目: 空行
・本文500〜700文字
・だ・である調
・マークダウン禁止
"""

    res = client.chat.completions.create(
        model=QWEN_MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=1200,
        extra_body={"chat_template_kwargs": {"enable_thinking": False}},
    )

    article_body = res.choices[0].message.content

    # meta description用の要約を別途生成
    meta_res = client.chat.completions.create(
        model=QWEN_MODEL,
        messages=[{"role": "user", "content": f"以下の記事を120文字以内で要約してください。文末は「。」で終わること。マークダウン禁止。\n\n{article_body[:1000]}"}],
        max_tokens=200,
        extra_body={"chat_template_kwargs": {"enable_thinking": False}},
    )
    meta_description = meta_res.choices[0].message.content.strip()[:120]

    return article_body, meta_description


# ========================
# X投稿
# ========================
def make_tweet(title, body, category):
    prefix = f"【{category}】"
    lead = make_lead(body)
    suffix = " #AI #LLM"

    text = f"{prefix}{title}\n{lead}"
    return text[:140 - len(suffix)] + suffix


# ========================
# メイン
# ========================
def translate_all():
    init_summaries_table()
    articles = get_articles_to_translate()

    for a in articles:
        article_id, title, summary, source, _, url = a

        title_ja = translate_text(title)
        body = translate_text(summary)

        generated, meta_description = generate_article(title_ja, body)
        data = split_generated_article(generated, title_ja)
        data["meta_description"] = meta_description

        category = "AI"

        tweet = make_tweet(data["title"], data["body"], category)

        save_summary(
            article_id,
            data["title"],
            data["body"],
            tweet,
            category,
            data["meta_description"]
        )

        print(f"完了: {data['title']}")


if __name__ == "__main__":
    translate_all()
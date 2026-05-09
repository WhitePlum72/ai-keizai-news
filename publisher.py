"""
記事公開モジュール
翻訳済み記事をMarkdownファイルとして出力しGitにPushする
"""

import sqlite3
import os
import subprocess
import logging
import sys
import re
from datetime import datetime

DB_PATH = "data/articles.db"
LOG_DIR = "logs"
ASTRO_CONTENT_DIR = "astro-site/src/content/articles"

LABEL_PREFIX_RE = re.compile(r'^\s*(?:[#>*\-]+\s*)?(?:見出し|本文)\s*[:：]\s*')
MARKDOWN_HEADING_RE = re.compile(r'^\s*#+\s*')


def setup_logger():
    logger = logging.getLogger("publisher")
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


def get_articles_to_publish():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT a.id, a.url, a.source, a.buzz_score, a.published_at,
               s.title_ja, s.summary_ja, s.category, s.tweet_text,
               COALESCE(a.image_url, '') as image_url,
               COALESCE(s.meta_description, '') as meta_description,
               COALESCE(s.article_slug, '') as article_slug,
               COALESCE(s.category_slug, '') as category_slug
        FROM articles a
        JOIN summaries s ON a.id = s.article_id
        WHERE a.processed = 1
        AND s.created_at >= datetime('now', 'localtime', '-24 hours')
        ORDER BY s.created_at DESC
        LIMIT 30
    """)
    rows = cursor.fetchall()
    conn.close()
    return rows


def slugify(title, article_id, article_slug=""):
    if article_slug and len(article_slug) > 3:
        return article_slug
    return f"article-{article_id}"

def remove_output_labels(text):
    if not text:
        return ""

    text = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    lines = []

    for line in text.split("\n"):
        line = LABEL_PREFIX_RE.sub("", line).strip()
        lines.append(line)

    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()


def clean_title(text, fallback=""):
    cleaned = remove_output_labels(text)
    lines = cleaned.splitlines()

    while lines and not lines[0].strip():
        lines.pop(0)

    if not lines:
        return fallback.strip()

    title = MARKDOWN_HEADING_RE.sub("", lines[0]).strip()
    return title or fallback.strip()


def clean_body(title, body):
    body = remove_output_labels(body)
    lines = body.splitlines()

    while lines and not lines[0].strip():
        lines.pop(0)

    if lines and clean_title(lines[0]) == title.strip():
        lines.pop(0)

    while lines and not lines[0].strip():
        lines.pop(0)

    return "\n".join(lines).strip()


def make_meta_description(body):
    text = re.sub(r"<[^>]+>", " ", body or "")
    text = remove_output_labels(text)
    text = text.replace("#", "")
    text = re.sub(r"\s+", " ", text).strip()
    return text[:120]


def yaml_escape(text):
    return (text or "").replace('"', "").replace("\n", " ").strip()


def generate_markdown(article):
    (article_id, url, source, buzz_score, published_at,
     title_ja, summary_ja, category, tweet_text,
     image_url, meta_description_db,
     article_slug, category_slug) = article

    title = clean_title(title_ja)
    body  = clean_body(title, summary_ja)

    if meta_description_db and len(meta_description_db) > 10:
        meta_desc = meta_description_db
    else:
        meta_desc = make_meta_description(body) or title

    slug      = slugify(title, article_id, article_slug)
    cat_slug  = category_slug if category_slug else "ai"
    today     = datetime.now().strftime("%Y-%m-%d")

    content = f"""---
title: "{yaml_escape(title)}"
source: "{yaml_escape(source)}"
source_url: "{yaml_escape(url)}"
category: "{yaml_escape(category)}"
category_slug: "{yaml_escape(cat_slug)}"
article_slug: "{yaml_escape(slug)}"
published_at: "{today}"
buzz_score: {buzz_score:.1f}
image_url: "{yaml_escape(image_url)}"
meta_description: "{yaml_escape(meta_desc)}"
---

{body}
"""
    return slug, cat_slug, content


def publish_articles():
    logger.info("=" * 60)
    logger.info("記事公開処理を開始しました")
    logger.info("=" * 60)

    articles = get_articles_to_publish()

    if not articles:
        logger.info("公開対象の記事がありません")
        return 0

    count = 0

    for article in articles:
        try:
            slug, cat_slug, content = generate_markdown(article)

            # カテゴリ別サブディレクトリに保存
            category_dir = os.path.join(ASTRO_CONTENT_DIR, cat_slug)
            os.makedirs(category_dir, exist_ok=True)
            filepath = os.path.join(category_dir, f"{slug}.md")

            with open(filepath, "w", encoding="utf-8", newline="\n") as f:
                f.write(content)

            logger.info("生成完了: %s/%s.md", cat_slug, slug)
            count += 1

        except Exception as e:
            logger.error("生成エラー: %s", str(e))

    logger.info("=" * 60)
    logger.info("Markdown生成完了: %d件", count)
    logger.info("=" * 60)

    return count


def git_push():
    try:
        root_dir = "."

        today = datetime.now().strftime("%Y-%m-%d")
        subprocess.run(["git", "add", "."], cwd=root_dir, check=True)
        subprocess.run(["git", "commit", "-m", f"Auto update {today}"], cwd=root_dir, check=True)
        subprocess.run(["git", "push", "origin", "main"], cwd=root_dir, check=True)
        logger.info("Git Push完了")

    except subprocess.CalledProcessError as e:
        logger.error("Git Pushエラー: %s", str(e))


def main():
    count = publish_articles()
    git_push()
    print(f"\n公開完了: {count}件のMarkdownファイルを生成しました")


if __name__ == "__main__":
    main()

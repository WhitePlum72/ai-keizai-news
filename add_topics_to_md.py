"""
既存記事MarkdownにDBのtopics_json / companies_jsonを追記するスクリプト
"""
import sqlite3
import os
import re
import json

DB_PATH = "data/articles.db"
CONTENT_DIR = "astro-site/src/content/articles"

conn = sqlite3.connect(DB_PATH)
rows = conn.execute("""
    SELECT s.article_slug, s.category_slug,
           COALESCE(s.topics_json, '[]'),
           COALESCE(s.companies_json, '[]')
    FROM summaries s
    WHERE s.article_slug IS NOT NULL AND s.article_slug != ''
""").fetchall()
conn.close()

updated = 0
skipped = 0
not_found = 0

for article_slug, category_slug, topics_raw, companies_raw in rows:
    try:
        topics = json.loads(topics_raw)
        companies = json.loads(companies_raw)
    except Exception:
        topics, companies = [], []

    filepath = os.path.join(CONTENT_DIR, category_slug, f"{article_slug}.md")
    if not os.path.exists(filepath):
        not_found += 1
        continue

    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    # すでに追記済みならスキップ
    if "topics_json:" in content:
        skipped += 1
        continue

    # frontmatter末尾（---の直前）に追記
    topics_line = f'topics_json: {json.dumps(topics, ensure_ascii=False)}'
    companies_line = f'companies_json: {json.dumps(companies, ensure_ascii=False)}'
    content = re.sub(
        r'(---\s*)$',
        f'{topics_line}\n{companies_line}\n---',
        content,
        count=1,
        flags=re.MULTILINE
    )

    with open(filepath, "w", encoding="utf-8", newline="\n") as f:
        f.write(content)

    updated += 1

print(f"更新: {updated}件 / スキップ: {skipped}件 / ファイル未発見: {not_found}件")
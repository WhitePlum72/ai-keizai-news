"""
既存のtopics_jsonから不要なtopicを除去し17個に統一するスクリプト
"""
import sqlite3
import json
import os
import re

DB_PATH = "data/articles.db"
CONTENT_DIR = "astro-site/src/content/articles"

VALID_TOPICS = {
    "openai", "nvidia", "anthropic", "google", "microsoft",
    "meta", "amd", "amazon", "llm", "reasoning", "agents",
    "gpu", "datacenter", "semiconductor", "agi", "multimodal", "coding-agent"
}

conn = sqlite3.connect(DB_PATH)
rows = conn.execute("SELECT id, article_slug, topics_json FROM summaries").fetchall()

updated_db = 0
for row_id, article_slug, topics_raw in rows:
    try:
        topics = json.loads(topics_raw or "[]")
    except Exception:
        topics = []

    filtered = [t for t in topics if t in VALID_TOPICS]

    if set(filtered) != set(topics):
        conn.execute(
            "UPDATE summaries SET topics_json = ? WHERE id = ?",
            (json.dumps(filtered, ensure_ascii=False), row_id)
        )
        updated_db += 1

conn.commit()
conn.close()
print(f"DB更新: {updated_db}件")

# Markdownファイルも更新
updated_md = 0
for cat in os.listdir(CONTENT_DIR):
    cat_dir = os.path.join(CONTENT_DIR, cat)
    if not os.path.isdir(cat_dir):
        continue
    for fname in os.listdir(cat_dir):
        if not fname.endswith(".md"):
            continue
        filepath = os.path.join(cat_dir, fname)
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        match = re.search(r'^topics_json: (\[.*?\])$', content, re.MULTILINE)
        if not match:
            continue

        try:
            topics = json.loads(match.group(1))
        except Exception:
            continue

        filtered = [t for t in topics if t in VALID_TOPICS]
        if set(filtered) == set(topics):
            continue

        new_line = f'topics_json: {json.dumps(filtered, ensure_ascii=False)}'
        content = re.sub(
            r'^topics_json: \[.*?\]$',
            new_line,
            content,
            flags=re.MULTILINE
        )
        with open(filepath, "w", encoding="utf-8", newline="\n") as f:
            f.write(content)
        updated_md += 1

print(f"Markdown更新: {updated_md}件")
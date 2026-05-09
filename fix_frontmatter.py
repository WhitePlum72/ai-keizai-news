"""
壊れたfrontmatterを修正するスクリプト
topics_json / companies_json が先頭に来てしまっている記事を修正
"""
import os
import re
import json

CONTENT_DIR = "astro-site/src/content/articles"

fixed = 0
skipped = 0

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

        # 先頭がtopics_jsonで始まっている壊れたファイルを検出
        if not content.startswith("topics_json:"):
            skipped += 1
            continue

        # frontmatter全体を抽出
        # パターン: topics_json/companies_json → --- → 本来のfrontmatter → --- → 本文
        match = re.match(
            r'^(topics_json:[^\n]*\ncompanies_json:[^\n]*\n---\n)(.*?)\n---\n(.*)$',
            content,
            re.DOTALL
        )

        if not match:
            print(f"パターン不一致（スキップ）: {filepath}")
            skipped += 1
            continue

        prefix = match.group(1)       # topics_json + companies_json + ---
        frontmatter_body = match.group(2)  # title, source, ... など
        body = match.group(3)         # 本文

        # topics_json / companies_json の値を取得
        topics_match = re.search(r'^topics_json: (.+)$', prefix, re.MULTILINE)
        companies_match = re.search(r'^companies_json: (.+)$', prefix, re.MULTILINE)
        topics_val = topics_match.group(1) if topics_match else '[]'
        companies_val = companies_match.group(1) if companies_match else '[]'

        # 正しい順序で再構築
        new_content = f"---\n{frontmatter_body}\ntopics_json: {topics_val}\ncompanies_json: {companies_val}\n---\n{body}"

        with open(filepath, "w", encoding="utf-8", newline="\n") as f:
            f.write(new_content)

        fixed += 1

print(f"修正: {fixed}件 / スキップ: {skipped}件")
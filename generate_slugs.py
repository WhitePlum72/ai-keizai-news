"""
slug未設定記事に一括でslugを付与するスクリプト
"""
import sqlite3
import re
import time
import requests
import os

DB_PATH = "data/articles.db"
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY")
DEEPSEEK_URL     = "https://api.deepseek.com/chat/completions"
DEEPSEEK_MODEL   = "deepseek-v4-pro"

SOURCE_TYPE_TO_CATEGORY_SLUG = {
    "model":        "model",
    "business":     "business",
    "research":     "research",
    "stock":        "stock",
    "arxiv":        "research",
    "hn":           "business",
    "official_blog":"model",
    "gov_jp":       "policy",
    "ir_tdnet":     "stock",
}

def get_category_slug(source_type: str) -> str:
    return SOURCE_TYPE_TO_CATEGORY_SLUG.get(source_type or '', 'ai')

def call_deepseek_slug(title_ja: str, title_en: str) -> str:
    if not DEEPSEEK_API_KEY:
        return ""
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json",
    }
    prompt = f"""Generate a URL slug for this article.

Japanese Title: {title_ja}
English Title: {title_en}

RULES:
- Output ONLY the slug, nothing else
- 3 to 5 words maximum
- Lowercase letters, numbers, hyphens only
- Include the most important company name or product name
- No stop words (a, the, in, of, for, and, to, with)
- Examples: openai-gpt5-launch, nvidia-blackwell-demand, anthropic-finance-agents

Slug:"""

    body = {
        "model": DEEPSEEK_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 30,
        "thinking": {"type": "disabled"},
    }
    try:
        res = requests.post(DEEPSEEK_URL, headers=headers, json=body, timeout=30)
        res.raise_for_status()
        slug_raw = res.json()["choices"][0]["message"]["content"].strip()
        slug = re.sub(r'[^a-z0-9-]', '', slug_raw.lower().replace(' ', '-'))[:80]
        return slug
    except Exception as e:
        print(f"APIエラー: {e}")
        return ""

def generate_slugs():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
        SELECT a.id, a.title, a.source_type, s.title_ja
        FROM articles a
        JOIN summaries s ON a.id = s.article_id
        WHERE s.article_slug IS NULL
        AND a.processed = 1
        ORDER BY a.id DESC
    """)
    rows = cur.fetchall()
    conn.close()

    print(f"slug未設定: {len(rows)}件")

    for i, (article_id, title_en, source_type, title_ja) in enumerate(rows):
        slug = call_deepseek_slug(title_ja or '', title_en or '')
        if not slug:
            slug = f"article-{article_id}"

        cat_slug = get_category_slug(source_type)

        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("""
            UPDATE summaries
            SET article_slug = ?, category_slug = ?
            WHERE article_id = ?
        """, (slug, cat_slug, article_id))
        cur.execute("""
            UPDATE articles
            SET article_slug = ?, category_slug = ?
            WHERE id = ?
        """, (slug, cat_slug, article_id))
        conn.commit()
        conn.close()

        print(f"[{i+1}/{len(rows)}] id={article_id} slug={slug} cat={cat_slug}")
        time.sleep(3)

    print("完了")

if __name__ == "__main__":
    generate_slugs()
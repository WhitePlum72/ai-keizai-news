import sqlite3
from datetime import datetime

DB_PATH = "data/articles.db"

SOURCE_WEIGHTS = {
    "techcrunch": 0.8,
    "theverge": 0.8,
    "venturebeat": 0.8,
    "arxiv": 0.6,
    "hn": 0.5,
    "reddit": 0.5,
}

KEYWORDS = [
    "gpt", "claude", "gemini", "release", "open-source",
    "agent", "raises", "breakthrough", "llm", "openai"
]

COMPANY_LIMITS = {
    "openai": 4, "google": 4, "anthropic": 4, "meta": 4
}

def get_source_weight(source_type):
    for key, weight in SOURCE_WEIGHTS.items():
        if key in source_type.lower():
            return weight
    return 0.4

def get_keyword_weight(title):
    title_lower = title.lower()
    return 1.0 if any(kw in title_lower for kw in KEYWORDS) else 0.0

def get_company(title):
    title_lower = title.lower()
    for company in COMPANY_LIMITS:
        if company in title_lower:
            return company
    return None

def calculate_scores():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, title, source_type, score FROM articles WHERE processed = 0")
    articles = cursor.fetchall()

    if not articles:
        print("スコアリング対象の記事がありません")
        conn.close()
        return

    max_score = max(a[3] for a in articles) or 1

    scored = []
    for article_id, title, source_type, score in articles:
        sw = get_source_weight(source_type or "")
        kw = get_keyword_weight(title or "")
        cs = score / max_score
        buzz = sw * 40 + kw * 35 + cs * 25
        scored.append((buzz, article_id, title))

    scored.sort(reverse=True)

    selected = []
    company_counts = {c: 0 for c in COMPANY_LIMITS}

    for buzz, article_id, title in scored:
        if len(selected) >= 30:
            break
        company = get_company(title)
        if company and company_counts[company] >= COMPANY_LIMITS[company]:
            continue
        if company:
            company_counts[company] += 1
        selected.append((buzz, article_id, title))

    for buzz, article_id, title in selected:
        cursor.execute(
            "UPDATE articles SET buzz_score = ? WHERE id = ?",
            (buzz, article_id)
        )

    conn.commit()
    conn.close()

    print(f"スコアリング完了: {len(selected)}件を選出")
    print("\n上位10件:")
    for i, (buzz, article_id, title) in enumerate(selected[:10], 1):
        print(f"{i}. [{buzz:.1f}] {title[:60]}")

if __name__ == "__main__":
    calculate_scores()
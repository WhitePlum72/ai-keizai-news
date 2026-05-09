"""
既存記事を内容ベースで一括再分類するスクリプト
"""
import sqlite3

DB_PATH = "data/articles.db"

CATEGORY_RULES = [
    (["gpu", "半導体", "データセンター", "data center", "chip", "semiconductor",
      "blackwell", "h100", "h200", "cuda", "nvlink", "電力", "inference chip",
      "ai server", "コンピューティング", "computing"], "インフラ"),

    (["株", "決算", "ipo", "投資", "valuation", "earnings", "revenue",
      "stock", "shares", "funding", "raises", "billion", "trillion",
      "市場", "上場", "時価総額", "資金調達"], "マーケット"),

    (["規制", "法律", "政策", "policy", "regulation", "安全", "safety",
      "ai act", "governance", "倫理", "ethics", "government", "官公庁",
      "経産省", "デジタル庁", "congress", "senate"], "政策"),

    (["論文", "arxiv", "research", "benchmark", "ベンチマーク",
      "leaderboard", "evaluation", "学術", "study", "paper",
      "reasoning", "alignment", "fine-tuning"], "研究"),

    (["api", "sdk", "ツール", "tool", "plugin", "extension",
      "開発者", "developer", "platform", "サービス開始", "launch",
      "copilot", "cursor", "agent framework", "workflow"], "プロダクト"),

    (["gpt", "claude", "gemini", "llama", "llm", "language model",
      "モデル", "model", "multimodal", "diffusion", "text to",
      "image generation", "voice ai", "foundation model",
      "open source model", "weights", "release"], "モデル"),
]

CATEGORY_TO_SLUG = {
    "モデル":     "model",
    "ビジネス":   "business",
    "研究":       "research",
    "マーケット": "markets",
    "インフラ":   "infrastructure",
    "政策":       "policy",
    "プロダクト": "products",
}

def classify(title_en: str, title_ja: str, body: str = "") -> str:
    text = f"{title_en} {title_ja} {body[:300]}".lower()
    for keywords, category in CATEGORY_RULES:
        if any(kw in text for kw in keywords):
            return category
    return "ビジネス"

def reclassify_all():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
        SELECT a.id, a.title, s.title_ja, s.summary_ja
        FROM articles a
        JOIN summaries s ON a.id = s.article_id
        WHERE a.processed = 1
    """)
    rows = cur.fetchall()

    counts = {}
    for article_id, title_en, title_ja, summary_ja in rows:
        category = classify(title_en or '', title_ja or '', summary_ja or '')
        cat_slug = CATEGORY_TO_SLUG.get(category, 'business')

        cur.execute("""
            UPDATE summaries
            SET category = ?, category_slug = ?
            WHERE article_id = ?
        """, (category, cat_slug, article_id))
        cur.execute("""
            UPDATE articles
            SET category_slug = ?
            WHERE id = ?
        """, (cat_slug, article_id))

        counts[category] = counts.get(category, 0) + 1

    conn.commit()
    conn.close()

    print("再分類完了:")
    for cat, count in sorted(counts.items(), key=lambda x: -x[1]):
        slug = CATEGORY_TO_SLUG.get(cat, 'business')
        print(f"  {cat} ({slug}): {count}件")

if __name__ == "__main__":
    reclassify_all()
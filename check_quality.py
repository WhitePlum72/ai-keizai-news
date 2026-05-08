import sqlite3
conn = sqlite3.connect("data/articles.db")
cur = conn.cursor()
cur.execute("""
    SELECT a.id, s.title_ja, s.summary_ja, s.created_at
    FROM articles a
    JOIN summaries s ON a.id = s.article_id
    ORDER BY s.created_at DESC
    LIMIT 3
""")
for r in cur.fetchall():
    print(f"\nID:{r[0]}  生成:{r[3]}")
    print(f"タイトル: {r[1]}")
    print(f"文字数: {len(r[1] or '')}")
    print(f"本文冒頭: {(r[2] or '')[:400]}")
    print("-"*60)
conn.close()

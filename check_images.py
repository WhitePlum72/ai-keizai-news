import sqlite3
conn = sqlite3.connect("data/articles.db")
cur = conn.cursor()
cur.execute("""
    SELECT a.id, s.title_ja, a.image_url
    FROM articles a
    JOIN summaries s ON a.id = s.article_id
    WHERE a.processed = 1
    ORDER BY s.created_at DESC
    LIMIT 10
""")
for r in cur.fetchall():
    print(f"ID:{r[0]}  画像:{r[2]}  {(r[1] or '')[:30]}")
conn.close()

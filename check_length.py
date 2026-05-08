import sqlite3
conn = sqlite3.connect("data/articles.db")
cur = conn.cursor()
cur.execute("""
    SELECT a.id, s.title_ja, length(s.summary_ja) as body_len, s.created_at
    FROM articles a
    JOIN summaries s ON a.id = s.article_id
    ORDER BY s.created_at DESC
    LIMIT 7
""")
for r in cur.fetchall():
    print(f"ID:{r[0]}  本文:{r[2]}文字  生成:{r[3]}  {(r[1] or '')[:30]}")
conn.close()

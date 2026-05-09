import sqlite3
from datetime import datetime

conn = sqlite3.connect('data/articles.db')
cur = conn.cursor()
cur.execute("""
    SELECT a.id, a.image_url, s.title_ja
    FROM articles a
    JOIN summaries s ON a.id = s.article_id
    WHERE DATE(s.created_at) = DATE('now', 'localtime')
    ORDER BY a.buzz_score DESC
""")
for row in cur.fetchall():
    og = 'OG' if row[1] and row[1].startswith('http') else 'FLUX'
    title = (row[2] or '')[:30]
    print(f"id={row[0]} [{og}] {title}")
conn.close()

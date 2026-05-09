# check_today.py を更新
import sqlite3
from datetime import datetime, timedelta

conn = sqlite3.connect('data/articles.db')
cur = conn.cursor()

# 昨日と今日の記事を確認
cur.execute("""
    SELECT a.id, a.image_url, s.title_ja, s.created_at
    FROM articles a
    JOIN summaries s ON a.id = s.article_id
    WHERE DATE(s.created_at) >= DATE('now', 'localtime', '-1 day')
    ORDER BY s.created_at DESC
""")
for row in cur.fetchall():
    og = 'OG' if row[1] and row[1].startswith('http') else 'FLUX'
    title = (row[2] or '')[:30]
    print(f"id={row[0]} [{og}] {row[3][:16]} {title}")
conn.close()
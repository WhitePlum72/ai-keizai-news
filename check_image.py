import sqlite3
conn = sqlite3.connect('data/articles.db')
cur = conn.cursor()
cur.execute('SELECT id, title, image_url FROM articles WHERE buzz_score > 0 ORDER BY buzz_score DESC LIMIT 10')
for r in cur.fetchall():
    print(f"ID:{r[0]} | image:{r[2][:50] if r[2] else '未取得'} | {r[1][:30]}")
conn.close()
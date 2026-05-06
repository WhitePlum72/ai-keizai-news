import sqlite3
conn = sqlite3.connect('data/articles.db')
cur = conn.cursor()
cur.execute('SELECT id, title, url, source FROM articles WHERE processed = 0 ORDER BY buzz_score DESC LIMIT 5')
for r in cur.fetchall():
    print(f"ID:{r[0]} | {r[2]}")
    print(f"  タイトル: {r[1][:50]}")
    print(f"  ソース: {r[3]}")
    print()
conn.close()
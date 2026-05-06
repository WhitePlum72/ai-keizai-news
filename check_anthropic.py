import sqlite3
conn = sqlite3.connect('data/articles.db')
cur = conn.cursor()
cur.execute('SELECT title, source FROM articles WHERE source="Anthropic" LIMIT 15')
for r in cur.fetchall():
    print(r[0][:60], r[1])
conn.close()
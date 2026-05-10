import sqlite3
conn = sqlite3.connect('data/articles.db')
c = conn.cursor()
c.execute("SELECT COUNT(*) FROM articles WHERE processed = 0")
print('未処理総数:', c.fetchone()[0])
c.execute("SELECT COUNT(*) FROM articles WHERE processed = 0 AND buzz_score > 0")
print('buzz_score > 0 の未処理:', c.fetchone()[0])
c.execute("SELECT id, title, buzz_score FROM articles WHERE processed = 0 AND buzz_score > 0 ORDER BY buzz_score DESC LIMIT 10")
for row in c.fetchall():
    print(f"  id={row[0]} buzz={row[2]:.1f} {row[1][:60]}")
conn.close()

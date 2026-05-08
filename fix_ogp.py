import sqlite3
conn = sqlite3.connect("data/articles.db")
cur = conn.cursor()
cur.execute("UPDATE articles SET image_url = NULL WHERE id IN (1580, 1651)")
conn.commit()
print(f"リセット: {cur.rowcount}件")
conn.close()

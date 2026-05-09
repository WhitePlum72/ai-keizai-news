# check_images_empty.py を更新
import sqlite3
conn = sqlite3.connect('data/articles.db')
cur = conn.cursor()

cur.execute("SELECT COUNT(*) FROM articles WHERE processed = 1 AND (image_url IS NULL OR image_url = '' OR image_url = '\"\"')")
print('空またはデフォルト:', cur.fetchone()[0])

cur.execute("SELECT id, repr(image_url) FROM articles WHERE processed = 1 AND image_url NOT LIKE '/images/%' AND image_url NOT LIKE 'http%' LIMIT 10")
for row in cur.fetchall():
    print(row)

conn.close()
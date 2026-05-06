import sqlite3
conn = sqlite3.connect('data/articles.db')
try:
    conn.execute('ALTER TABLE articles ADD COLUMN image_url TEXT DEFAULT ""')
    conn.commit()
    print('カラム追加完了')
except Exception as e:
    print('既に存在します:', e)
conn.close()
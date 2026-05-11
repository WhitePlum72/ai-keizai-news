import sqlite3
conn = sqlite3.connect('data/articles.db')
c = conn.cursor()
c.execute("""
    SELECT a.id, s.article_slug, s.category_slug 
    FROM articles a
    JOIN summaries s ON a.id = s.article_id
    WHERE a.id IN (1399, 1387, 1385, 1541, 1439)
""")
for row in c.fetchall():
    print(row)
conn.close()

import sqlite3

conn = sqlite3.connect('data/articles.db')
cur = conn.cursor()

migrations = [
    # フェーズ1
    "ALTER TABLE articles ADD COLUMN article_slug TEXT",
    "ALTER TABLE articles ADD COLUMN category_slug TEXT",
    "ALTER TABLE articles ADD COLUMN primary_source_score INTEGER DEFAULT 0",
    "ALTER TABLE articles ADD COLUMN source_type TEXT DEFAULT 'rss'",
    "ALTER TABLE articles ADD COLUMN source_label TEXT",
    "ALTER TABLE articles ADD COLUMN official_source BOOLEAN DEFAULT 0",
    # フェーズ2（空カラム）
    "ALTER TABLE articles ADD COLUMN topic_slug TEXT",
    "ALTER TABLE articles ADD COLUMN related_company_slugs TEXT",
    "ALTER TABLE articles ADD COLUMN related_person_slugs TEXT",
    "ALTER TABLE articles ADD COLUMN related_article_ids TEXT",
    "ALTER TABLE articles ADD COLUMN faq_json TEXT",
    # フェーズ3（空カラム）
    "ALTER TABLE articles ADD COLUMN entity_json TEXT",
    # summaries
    "ALTER TABLE summaries ADD COLUMN article_slug TEXT",
    "ALTER TABLE summaries ADD COLUMN category_slug TEXT",
    "ALTER TABLE summaries ADD COLUMN slug_en TEXT",
]

for sql in migrations:
    try:
        cur.execute(sql)
        print(f"OK: {sql[:60]}")
    except Exception as e:
        print(f"SKIP: {e}")

conn.commit()

print("\n--- articles ---")
cur.execute("PRAGMA table_info(articles)")
for row in cur.fetchall():
    print(row)

print("\n--- summaries ---")
cur.execute("PRAGMA table_info(summaries)")
for row in cur.fetchall():
    print(row)

conn.close()
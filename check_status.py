import sqlite3
conn = sqlite3.connect("data/articles.db")
cur = conn.cursor()

print("=== 直近2日間の収集状況 ===")
cur.execute("""
    SELECT 
        DATE(a.collected_at) as date,
        COUNT(*) as total,
        SUM(a.processed) as processed,
        SUM(CASE WHEN s.id IS NOT NULL THEN 1 ELSE 0 END) as has_summary,
        SUM(CASE WHEN a.image_url LIKE '/images/%' THEN 1 ELSE 0 END) as has_image
    FROM articles a
    LEFT JOIN summaries s ON a.id = s.article_id
    WHERE DATE(a.collected_at) >= DATE('now', 'localtime', '-2 days')
    GROUP BY DATE(a.collected_at)
    ORDER BY date DESC
""")
for r in cur.fetchall():
    print(f"  日付:{r[0]}  総数:{r[1]}  処理済:{r[2]}  要約あり:{r[3]}  画像あり:{r[4]}")

print()
print("=== 本日の要約済み記事（公開候補） ===")
cur.execute("""
    SELECT a.id, s.title_ja, a.buzz_score, a.image_url, s.created_at
    FROM articles a
    JOIN summaries s ON a.id = s.article_id
    WHERE a.processed = 1
      AND DATE(s.created_at) = DATE('now', 'localtime')
    ORDER BY a.buzz_score DESC
    LIMIT 15
""")
rows = cur.fetchall()
if not rows:
    print("  （本日分の要約済み記事なし）")
for r in rows:
    print(f"  ID:{r[0]}  score:{r[2]}  画像:{r[3]}  {(r[1] or 'タイトルなし')[:45]}")

print()
print("=== 最新3件の本文冒頭（品質確認） ===")
cur.execute("""
    SELECT a.id, s.title_ja, s.summary_ja, s.created_at
    FROM articles a
    JOIN summaries s ON a.id = s.article_id
    ORDER BY s.created_at DESC
    LIMIT 3
""")
for r in cur.fetchall():
    print(f"\n  ID:{r[0]}  生成日時:{r[3]}")
    print(f"  タイトル: {r[1]}")
    body = (r[2] or "")[:300]
    print(f"  本文冒頭: {body}...")

conn.close()

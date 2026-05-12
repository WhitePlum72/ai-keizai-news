import sqlite3
conn = sqlite3.connect('data/articles.db')
c = conn.cursor()
c.execute("""
    SELECT 
        COUNT(*) as total,
        AVG(buzz_score) as avg,
        MAX(buzz_score) as max,
        MIN(buzz_score) as min
    FROM articles 
    WHERE buzz_score > 0
""")
row = c.fetchone()
print(f"総数: {row[0]}, 平均: {row[1]:.1f}, 最大: {row[2]:.1f}, 最小: {row[3]:.1f}")

c.execute("""
    SELECT buzz_score, title 
    FROM articles 
    WHERE buzz_score > 0 
    ORDER BY buzz_score DESC 
    LIMIT 20
""")
print("\n上位20件:")
for row in c.fetchall():
    print(f"  buzz={row[0]:.1f} {row[1][:60]}")
conn.close()

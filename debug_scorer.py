from scorer import *
import sqlite3

conn = sqlite3.connect('data/articles.db')
cur = conn.cursor()
cur.execute("""
    SELECT id, title, summary, source, source_type, published_at, url
    FROM articles WHERE processed = 0 LIMIT 200
""")
articles = cur.fetchall()
conn.close()

for row in articles:
    article_id, title, summary, source, source_type, published_at, url = row
    if 'anthropic.com' not in (url or ''):
        continue
    text = (title or '') + ' ' + (summary or '')
    text_for_company = text + ' ' + (url or '')
    authority  = get_source_authority(source or source_type or '')
    recency    = get_recency_score(published_at)
    economic   = get_economic_score(text)
    ai_topic   = get_ai_topic_score(text)
    comp_score, company = get_company_score(text_for_company)
    buzz = authority*2 + recency*2 + economic + ai_topic + comp_score
    primary_score, stype, label, is_official = get_primary_source_info(url or '')
    recency_mult = RECENCY_MULTIPLIER.get(int(recency), 0.15)
    effective_primary = primary_score * recency_mult
    buzz += effective_primary * 0.5
    print(f"id={article_id} buzz={buzz:.1f} primary={primary_score} recency={recency} company={company} title={title[:40]}")
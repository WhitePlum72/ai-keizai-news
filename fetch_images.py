"""
既存記事のOGP画像を一括取得してDBに保存する
"""
import sqlite3
import requests
from bs4 import BeautifulSoup
import time

DB_PATH = "data/articles.db"

def fetch_ogp_image(url):
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "ja,en-US;q=0.7,en;q=0.3",
            "Referer": "https://www.google.com/",
        }
        res = requests.get(url, headers=headers, timeout=8)
        soup = BeautifulSoup(res.text, 'html.parser')

        og_image = soup.find('meta', property='og:image')
        if og_image and og_image.get('content'):
            return og_image.get('content', '')

        tw_image = soup.find('meta', attrs={'name': 'twitter:image'})
        if tw_image and tw_image.get('content'):
            return tw_image.get('content', '')

    except Exception as e:
        print(f"  エラー: {str(e)[:50]}")
    return ''

def main():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute('''
        SELECT id, url, title FROM articles
        WHERE (image_url IS NULL OR image_url = "")
        AND buzz_score > 0
        ORDER BY buzz_score DESC
    ''')
    articles = cur.fetchall()
    print(f"画像未取得: {len(articles)}件")

    success = 0
    for i, (article_id, url, title) in enumerate(articles, 1):
        print(f"[{i}/{len(articles)}] {title[:40]}")
        try:
            image_url = fetch_ogp_image(url)
            if image_url:
                cur.execute('UPDATE articles SET image_url = ? WHERE id = ?', (image_url, article_id))
                conn.commit()
                print(f"  ✓ 取得: {image_url[:60]}")
                success += 1
            else:
                print(f"  × 未取得")
        except Exception as e:
            print(f"  エラー: {e}")
        time.sleep(0.5)

    conn.close()
    print(f"\n完了: {success}/{len(articles)}件取得")

if __name__ == "__main__":
    main()
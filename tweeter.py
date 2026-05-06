"""
X（Twitter）自動投稿モジュール
buzz_score上位5件を1日5回に分けて投稿する
"""

import sqlite3
import logging
import os
import sys
from datetime import datetime
import tweepy

DB_PATH = "data/articles.db"
LOG_DIR = "logs"

# Twitter API認証情報（後で設定）
CONSUMER_KEY = os.environ.get("TWITTER_CONSUMER_KEY", "")
CONSUMER_SECRET = os.environ.get("TWITTER_CONSUMER_SECRET", "")
ACCESS_TOKEN = os.environ.get("TWITTER_ACCESS_TOKEN", "")
ACCESS_TOKEN_SECRET = os.environ.get("TWITTER_ACCESS_TOKEN_SECRET", "")

def setup_logger():
    logger = logging.getLogger("tweeter")
    logger.setLevel(logging.DEBUG)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    logger.addHandler(console_handler)
    os.makedirs(LOG_DIR, exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")
    file_handler = logging.FileHandler(os.path.join(LOG_DIR, f"{today}.log"), encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    logger.addHandler(file_handler)
    return logger

logger = setup_logger()

def get_tweet_articles(rank):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT a.url, s.tweet_text
        FROM articles a
        JOIN summaries s ON a.id = s.article_id
        WHERE a.processed = 1
        AND DATE(a.collected_at) = DATE('now')
        ORDER BY a.buzz_score DESC
        LIMIT 5
    """)
    rows = cursor.fetchall()
    conn.close()
    if rank < len(rows):
        return rows[rank]
    return None

def post_tweet(rank):
    if not all([CONSUMER_KEY, CONSUMER_SECRET, ACCESS_TOKEN, ACCESS_TOKEN_SECRET]):
        logger.warning("Twitter APIキーが設定されていません")
        logger.warning("環境変数を設定してください:")
        logger.warning("TWITTER_CONSUMER_KEY, TWITTER_CONSUMER_SECRET")
        logger.warning("TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_TOKEN_SECRET")
        return

    article = get_tweet_articles(rank)
    if not article:
        logger.warning("投稿対象の記事がありません (rank=%d)", rank)
        return

    url, tweet_text = article
    full_text = f"{tweet_text}\n{url}"

    try:
        client = tweepy.Client(
            consumer_key=CONSUMER_KEY,
            consumer_secret=CONSUMER_SECRET,
            access_token=ACCESS_TOKEN,
            access_token_secret=ACCESS_TOKEN_SECRET
        )
        client.create_tweet(text=full_text)
        logger.info("ツイート投稿完了 (rank=%d): %s", rank, tweet_text[:50])
    except Exception as e:
        logger.error("ツイート投稿エラー: %s", str(e))

def main():
    now = datetime.now().hour
    schedule = {7: 0, 10: 1, 13: 2, 17: 3, 21: 4}
    rank = schedule.get(now)
    if rank is not None:
        post_tweet(rank)
    else:
        logger.info("投稿時刻ではありません (現在%d時)", now)

if __name__ == "__main__":
    main()
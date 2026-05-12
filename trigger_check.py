import subprocess
import sqlite3
import logging
import os
import sys
from datetime import datetime

DB_PATH = "data/articles.db"
LOG_DIR = "logs"
BUZZ_THRESHOLD = 48

def setup_logger():
    logger = logging.getLogger("trigger")
    logger.setLevel(logging.DEBUG)
    if logger.handlers:
        return logger
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    logger.addHandler(console_handler)
    os.makedirs(LOG_DIR, exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")
    file_handler = logging.FileHandler(
        os.path.join(LOG_DIR, f"{today}.log"), encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    logger.addHandler(file_handler)
    return logger

logger = setup_logger()

def run(script):
    logger.info("実行: %s", script)
    result = subprocess.run(
        ["python", script],
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    if result.stdout:
        for line in result.stdout.strip().splitlines():
            logger.info("  %s", line)
    if result.returncode != 0:
        logger.error("失敗: %s\n%s", script, result.stderr[:500])
        return False
    return True

def has_high_score_articles():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        SELECT COUNT(*) FROM articles a
        LEFT JOIN summaries s ON a.id = s.article_id
        WHERE a.buzz_score >= ?
        AND s.article_id IS NULL
    """, (BUZZ_THRESHOLD,))
    count = c.fetchone()[0]
    conn.close()
    return count > 0

def main():
    logger.info("========================================")
    logger.info("トリガーチェック開始 (閾値: %d)", BUZZ_THRESHOLD)
    logger.info("========================================")

    if not run("collector.py"):
        logger.error("collector.py 失敗・終了")
        return

    if not run("scorer.py"):
        logger.error("scorer.py 失敗・終了")
        return

    if not has_high_score_articles():
        logger.info("高スコア記事なし（buzz_score >= %d）・終了", BUZZ_THRESHOLD)
        return

    logger.info("高スコア記事あり！記事生成・公開を開始します")

    if not run("translator.py"):
        logger.error("translator.py 失敗・終了")
        return

    if not run("publisher.py"):
        logger.error("publisher.py 失敗・終了")
        return

    logger.info("Astroビルド中...")
    result = subprocess.run(
        ["npm", "run", "build"],
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd="astro-site"
    )
    if result.returncode != 0:
        logger.error("Astroビルド失敗: %s", result.stderr[:500])
        return

    logger.info("完了！")

if __name__ == "__main__":
    main()

"""
メインスケジューラ
毎朝4時に全パイプラインを自動実行する
"""

import logging
import sys
import os
from datetime import datetime
from apscheduler.schedulers.blocking import BlockingScheduler

from collector import collect_all
from scorer import calculate_scores
from translator import translate_all
from publisher import publish_articles, git_push

LOG_DIR = "logs"

def setup_logger():
    logger = logging.getLogger("main")
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

def run_pipeline():
    logger.info("=" * 60)
    logger.info("パイプライン開始: %s", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    logger.info("=" * 60)

    try:
        logger.info("[1/4] RSS収集開始")
        collect_all()

        logger.info("[2/4] スコアリング開始")
        calculate_scores()

        logger.info("[3/4] 翻訳開始")
        translate_all()

        logger.info("[4/4] 記事公開開始")
        publish_articles()
        git_push()

        logger.info("パイプライン完了")

    except Exception as e:
        logger.error("パイプラインエラー: %s", str(e))

def main():
    print("スケジューラを起動します")
    print("毎朝4:00に自動実行されます")
    print("Ctrl+Cで停止")

    scheduler = BlockingScheduler()
    scheduler.add_job(run_pipeline, 'cron', hour=4, minute=0)
    logger.info("スケジューラ起動完了")

    try:
        scheduler.start()
    except KeyboardInterrupt:
        logger.info("スケジューラを停止しました")

if __name__ == "__main__":
    main()
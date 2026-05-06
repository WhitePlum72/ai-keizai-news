"""
メインパイプライン
Windowsタスクスケジューラから毎朝4時に直接呼び出す
"""

import logging
import sys
import os
import time
import subprocess
import requests
from datetime import datetime

from collector import collect_all
from scorer import calculate_scores
from translator import translate_all
from publisher import publish_articles, git_push

LOG_DIR = "logs"
LLAMA_SERVER = r"C:\Users\info\Desktop\dev\tools\llama.cpp\build\bin\Release\llama-server.exe"
QWEN_MODEL   = r"C:\Users\info\Desktop\dev\tools\models\qwen3.6-27b\Qwen3.6-27B-UD-Q4_K_XL.gguf"
LLAMA_DIR    = r"C:\Users\info\Desktop\dev\tools\llama.cpp"

def setup_logger():
    logger = logging.getLogger("main")
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

def start_qwen():
    logger.info("Qwen起動中...")
    proc = subprocess.Popen(
        [
            LLAMA_SERVER,
            "-m", QWEN_MODEL,
            "-ngl", "99",
            "-c", "98304",
            "--host", "0.0.0.0",
            "--port", "8080",
            "--temp", "0.6",
            "--top-p", "0.95",
            "--top-k", "20",
        ],
        cwd=LLAMA_DIR,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    for i in range(60):
        time.sleep(2)
        try:
            res = requests.get("http://localhost:8080/health", timeout=3)
            if res.status_code == 200:
                logger.info("Qwen起動完了（%d秒）", (i + 1) * 2)
                return proc
        except Exception:
            pass
        if i % 5 == 0:
            logger.info("Qwen起動待機中... %d秒", (i + 1) * 2)
    logger.warning("Qwen起動確認タイムアウト（続行します）")
    return proc

def stop_qwen(proc):
    logger.info("Qwen停止中...")
    proc.terminate()
    try:
        proc.wait(timeout=15)
    except subprocess.TimeoutExpired:
        proc.kill()
    time.sleep(3)
    logger.info("Qwen停止完了")

def run_pipeline():
    logger.info("=" * 60)
    logger.info("パイプライン開始: %s", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    logger.info("=" * 60)

    qwen_proc = None

    try:
        # Phase1: Qwen起動
        qwen_proc = start_qwen()

        # Phase2: 収集・スコアリング・翻訳
        logger.info("[1/4] RSS収集")
        collect_all()

        logger.info("[2/4] スコアリング（類似記事除外・上位10件）")
        calculate_scores()

        logger.info("[3/4] 翻訳・記事生成（10件）")
        translate_all()

        # Phase3: Qwen停止
        stop_qwen(qwen_proc)
        qwen_proc = None

        # Phase4: 公開・Push
        logger.info("[4/4] 記事公開・Git Push")
        publish_articles()
        git_push()

        logger.info("パイプライン完了")

    except Exception as e:
        logger.error("パイプラインエラー: %s", str(e), exc_info=True)

    finally:
        if qwen_proc:
            stop_qwen(qwen_proc)

    logger.info("=" * 60)
    logger.info("パイプライン終了: %s", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    logger.info("=" * 60)

if __name__ == "__main__":
    run_pipeline()
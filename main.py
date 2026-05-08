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
from image_generator import generate_all_images

# ─────────────────────────────────────────────
# DeepSeek APIキーを.envから強制ロード
# タスクスケジューラではload_dotenvが効かないためここで直接読む
# ─────────────────────────────────────────────
def _load_deepseek_key():
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if not os.path.exists(env_path):
        return
    with open(env_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line.startswith("DEEPSEEK_API_KEY="):
                key = line.split("=", 1)[1].strip()
                if key:
                    os.environ["DEEPSEEK_API_KEY"] = key
                return

_load_deepseek_key()

LOG_DIR     = "logs"
COMFYUI_DIR = r"C:\Users\info\Desktop\dev\tools\ComfyUI"


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


def start_comfyui():
    logger.info("ComfyUI起動中...")
    proc = subprocess.Popen(
        [sys.executable, "main.py", "--listen", "0.0.0.0", "--port", "8188"],
        cwd=COMFYUI_DIR,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    for i in range(30):
        time.sleep(2)
        try:
            res = requests.get("http://localhost:8188", timeout=3)
            if res.status_code == 200:
                logger.info("ComfyUI起動完了（%d秒）", (i + 1) * 2)
                return proc
        except Exception:
            pass
    logger.warning("ComfyUI起動確認タイムアウト（続行します）")
    return proc


def stop_comfyui(proc):
    logger.info("ComfyUI停止中...")
    proc.terminate()
    try:
        proc.wait(timeout=15)
    except subprocess.TimeoutExpired:
        proc.kill()
    logger.info("ComfyUI停止完了")


def run_pipeline():
    logger.info("=" * 60)
    logger.info("パイプライン開始: %s", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    logger.info("=" * 60)

    # APIキーが取れているか確認
    if not os.environ.get("DEEPSEEK_API_KEY"):
        logger.error("DEEPSEEK_API_KEY が設定されていません。.envを確認してください。")
        return

    comfyui_proc = None

    try:
        # Phase1: 収集・スコアリング・記事生成（DeepSeek）
        logger.info("[1/4] RSS収集")
        collect_all()

        logger.info("[2/4] スコアリング（類似記事除外・上位10件）")
        calculate_scores()

        logger.info("[3/4] 記事生成（DeepSeek）")
        translate_all()

        # Phase2: 全記事FLUX画像生成
        logger.info("[4/4] 画像生成（全記事・FLUX.1 Schnell）")
        comfyui_proc = start_comfyui()
        generate_all_images()
        stop_comfyui(comfyui_proc)
        comfyui_proc = None

        # Phase3: 公開・Push
        logger.info("[5/5] 記事公開・Git Push")
        publish_articles()
        git_push()

        logger.info("パイプライン完了")

    except Exception as e:
        logger.error("パイプラインエラー: %s", str(e), exc_info=True)

    finally:
        if comfyui_proc:
            stop_comfyui(comfyui_proc)

    logger.info("=" * 60)
    logger.info("パイプライン終了: %s", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    logger.info("=" * 60)


if __name__ == "__main__":
    run_pipeline()
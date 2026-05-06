"""
画像生成モジュール
Qwenで英語プロンプト生成 → FLUX.1 Schnellで画像生成
"""

import sqlite3
import requests
import json
import time
import os
import logging
import sys
import openai
import urllib.request
from datetime import datetime

DB_PATH = "data/articles.db"
LOG_DIR = "logs"
COMFYUI_URL = "http://localhost:8188"
IMAGE_OUTPUT_DIR = "astro-site/public/images/articles"
QWEN_BASE_URL = "http://localhost:8080/v1"
QWEN_MODEL = "Qwen3.6-27B-UD-Q4_K_XL.gguf"

def setup_logger():
    logger = logging.getLogger("image_generator")
    logger.setLevel(logging.DEBUG)
    if logger.handlers:
        return logger
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(
        logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    )
    logger.addHandler(console_handler)
    os.makedirs(LOG_DIR, exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")
    file_handler = logging.FileHandler(
        os.path.join(LOG_DIR, f"{today}.log"), encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    )
    logger.addHandler(file_handler)
    return logger

logger = setup_logger()

# ========================
# カテゴリ別スタイル設定
# ========================
CATEGORY_STYLE = {
    "AI関連株": (
        "financial data visualization, stock market chart, "
        "professional business photography, dramatic lighting, "
        "Bloomberg terminal aesthetic, dark background"
    ),
    "モデル": (
    "cutting-edge AI technology, neural network visualization, "
    "futuristic blue purple gradient, photorealistic render, "
    "data streams, digital transformation"
),
    "AIモデル": (
        "cutting-edge AI technology, neural network visualization, "
        "futuristic blue purple gradient, photorealistic render, "
        "data streams, digital transformation"
    ),
    "ビジネス": (
        "modern corporate environment, professional business setting, "
        "clean minimal aesthetic, confident atmosphere, "
        "office architecture, strategic planning"
    ),
    "研究": (
        "scientific laboratory, data visualization, "
        "academic research environment, clean minimal aesthetic, "
        "microscope, molecular structure, innovation"
    ),
    "AI": (
        "artificial intelligence concept, technology background, "
        "digital innovation, futuristic aesthetic"
    ),
        "ツール": (          # ← 追加
        "software development tools, productivity application, "
        "modern UI dashboard, clean minimal design, "
        "digital workspace, technology interface"
    ),
}

QUALITY_SUFFIX = (
    "ultra high quality, 4K, sharp focus, "
    "professional photography, award winning, "
    "no text, no watermark, no logo, no letters"
)

GLOBAL_NEGATIVE = (
    "realistic human face, photorealistic person, "
    "celebrity, politician, executive portrait, "
    "recognizable individual, real person likeness, "
    "nsfw, violence, gore, text, watermark, logo, "
    "blurry, low quality, distorted"
)

# 人物キーワード検出
PERSON_KEYWORDS = [
    "ceo", "chief", "executive", "founder", "president",
    "minister", "chairman", "director", "officer",
    "elon", "musk", "altman", "zuckerberg", "pichai",
    "cook", "bezos", "huang", "nadella", "lecun",
]

def needs_illustration_style(text: str) -> bool:
    return any(kw in text.lower() for kw in PERSON_KEYWORDS)

# ========================
# DB操作
# ========================
def get_articles_needing_images():
    """当日処理した全記事を取得（毎回FLUX生成）"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT a.id, s.title_ja, s.category, a.title, a.summary
        FROM articles a
        JOIN summaries s ON a.id = s.article_id
        WHERE a.processed = 1
        AND DATE(a.collected_at) = DATE('now', 'localtime')
        ORDER BY a.buzz_score DESC
    """)
    rows = cursor.fetchall()
    conn.close()
    return rows

def update_image_url(article_id: int, image_path: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE articles SET image_url = ? WHERE id = ?",
        (image_path, article_id)
    )
    conn.commit()
    conn.close()

# ========================
# Qwenでプロンプト生成
# ========================
# 人物名リスト
KNOWN_PERSONS = {
    "altman": ("Sam Altman", "middle-aged man, short dark hair, casual tech style"),
    "musk": ("Elon Musk", "tall man, short hair, intense expression, tech entrepreneur"),
    "zuckerberg": ("Mark Zuckerberg", "young man, curly hair, casual t-shirt"),
    "pichai": ("Sundar Pichai", "South Asian man, glasses, professional suit"),
    "nadella": ("Satya Nadella", "South Asian man, glasses, business suit"),
    "cook": ("Tim Cook", "middle-aged man, glasses, business casual"),
    "bezos": ("Jeff Bezos", "bald man, athletic build, business casual"),
    "huang": ("Jensen Huang", "Asian man, leather jacket, tech style"),
    "lecun": ("Yann LeCun", "older man, beard, academic style"),
    "hassabis": ("Demis Hassabis", "British man, casual smart"),
}

# 企業・モデル名リスト
KNOWN_COMPANIES = {
    "openai": "futuristic AI lab, dark background, glowing neural network, OpenAI aesthetic",
    "anthropic": "clean minimal office, purple tones, AI safety research lab",
    "google": "colorful tech campus, modern architecture, Google colors",
    "microsoft": "corporate blue tones, Windows interface, enterprise technology",
    "nvidia": "green circuit boards, GPU chips, data center, NVIDIA green",
    "apple": "minimalist white design, clean aesthetic, Apple Store atmosphere",
    "meta": "social network visualization, blue tones, VR headset",
    "amazon": "warehouse automation, orange robots, AWS cloud infrastructure",
    "tesla": "electric vehicle, clean energy, Gigafactory",
    "gpt": "language model visualization, text streams, neural network",
    "claude": "purple tones, AI assistant interface, clean design",
    "gemini": "Google colors, multimodal AI, constellation pattern",
    "llama": "Meta purple, open source code, developer environment",
}

def detect_person(text: str) -> tuple[str, str] | None:
    """テキストから人物名を検出して（人物名、外見説明）を返す"""
    text_lower = text.lower()
    for key, (name, appearance) in KNOWN_PERSONS.items():
        if key in text_lower:
            return name, appearance
    return None

def detect_company(text: str) -> str | None:
    """テキストから企業・モデル名を検出してスタイルを返す"""
    text_lower = text.lower()
    for key, style in KNOWN_COMPANIES.items():
        if key in text_lower:
            return style
    return None

def generate_flux_prompt(title_ja: str, category: str, title_en: str) -> str:
    """Qwenで記事タイトルからFLUX用英語プロンプトを生成"""
    text = f"{title_en} {title_ja}"

    # 人物名検出 → イラスト風人物画像
    person = detect_person(text)
    if person:
        name, appearance = person
        return (
            f"digital illustration portrait of {name}, {appearance}, "
            f"flat design style, vector art, professional tech magazine illustration, "
            f"no realistic photo, stylized character art"
        )

    # 企業・モデル名検出 → ブランドイメージ画像
    company_style = detect_company(text)
    if company_style:
        return company_style

    # 該当なし → Qwenでプロンプト生成
    client = openai.OpenAI(base_url=QWEN_BASE_URL, api_key="dummy")

    system = (
        "You are an expert at writing prompts for AI image generation. "
        "Generate a concise English image prompt (under 50 words) "
        "that visually represents the given news article. "
        "Focus on objects, scenes, concepts, and technology — no people or faces. "
        "Output only the prompt, no explanation."
    )

    user = f"Article title: {title_en}\nJapanese title: {title_ja}\nCategory: {category}"

    res = client.chat.completions.create(
        model=QWEN_MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        max_tokens=100,
        extra_body={"chat_template_kwargs": {"enable_thinking": False}},
    )
    return res.choices[0].message.content.strip()

def build_full_prompt(title_ja: str, category: str, title_en: str, summary: str) -> tuple[str, str]:
    """完全なプロンプトとネガティブプロンプトを生成"""
    base = generate_flux_prompt(title_ja, category, title_en)
    style = CATEGORY_STYLE.get(category, CATEGORY_STYLE["AI"])

    is_person = needs_illustration_style(f"{title_en} {summary}")

    if is_person:
        person_style = (
            "flat design illustration, vector art style, "
            "abstract human silhouette only, no realistic face, "
            "minimalist corporate illustration, icon style"
        )
        prompt = f"{base}, {style}, {person_style}, {QUALITY_SUFFIX}"
    else:
        prompt = f"{base}, {style}, {QUALITY_SUFFIX}"

    return prompt, GLOBAL_NEGATIVE

# ========================
# ComfyUI API
# ========================
def generate_image_comfyui(prompt: str, negative: str, article_id: int) -> str | None:
    """ComfyUI APIで画像生成"""

    workflow = {        # ← スペース4つのインデントが必要
        "1": {
            "class_type": "UnetLoaderGGUF",
            "inputs": {"unet_name": "flux1-schnell-Q8_0.gguf"}
        },
        "2": {
            "class_type": "DualCLIPLoader",
            "inputs": {
                "clip_name1": "t5xxl_fp8_e4m3fn.safetensors",
                "clip_name2": "clip_l.safetensors",
                "type": "flux",
                "device": "default"
            }
        },
        "3": {
            "class_type": "VAELoader",
            "inputs": {"vae_name": "ae.safetensors"}
        },
        "4": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": prompt, "clip": ["2", 0]}
        },
        "5": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": negative, "clip": ["2", 0]}
        },
        "6": {
            "class_type": "EmptyLatentImage",
            "inputs": {"width": 1280, "height": 720, "batch_size": 1}
        },
        "7": {
            "class_type": "KSampler",
            "inputs": {
                "model": ["1", 0],
                "positive": ["4", 0],
                "negative": ["5", 0],
                "latent_image": ["6", 0],
                "seed": article_id,
                "steps": 4,
                "cfg": 1.0,
                "sampler_name": "euler",
                "scheduler": "simple",
                "denoise": 1.0
            }
        },
        "8": {
            "class_type": "VAEDecode",
            "inputs": {"samples": ["7", 0], "vae": ["3", 0]}
        },
        "9": {
            "class_type": "SaveImage",
            "inputs": {"images": ["8", 0], "filename_prefix": f"article_{article_id}"}
        }
    }

    try:                # ← ここからも正しくインデント        # キュー送信
        res = requests.post(
            f"{COMFYUI_URL}/prompt",
            json={"prompt": workflow},
            timeout=10
        )
        res.raise_for_status()
        prompt_id = res.json()["prompt_id"]
        logger.info("キュー送信完了: prompt_id=%s", prompt_id)

        # 完了待機
        for _ in range(120):  # 最大120秒待機
            time.sleep(1)
            history = requests.get(
                f"{COMFYUI_URL}/history/{prompt_id}",
                timeout=5
            ).json()

            if prompt_id in history:
                outputs = history[prompt_id].get("outputs", {})
                for node_id, node_output in outputs.items():
                    if "images" in node_output:
                        img_info = node_output["images"][0]
                        return img_info["filename"]

        logger.error("画像生成タイムアウト: article_id=%d", article_id)
        return None

    except Exception as e:
        logger.error("ComfyUI APIエラー: %s", str(e))
        return None

def download_image(filename: str, article_id: int) -> str | None:
    """ComfyUIの出力画像をastro-siteのpublicに保存"""
    os.makedirs(IMAGE_OUTPUT_DIR, exist_ok=True)

    save_path = os.path.join(IMAGE_OUTPUT_DIR, f"article_{article_id}.webp")
    url = f"{COMFYUI_URL}/view?filename={filename}&type=output"

    try:
        urllib.request.urlretrieve(url, save_path)
        # Astroサイトからの参照パス
        return f"/images/articles/article_{article_id}.webp"
    except Exception as e:
        logger.error("画像ダウンロードエラー: %s", str(e))
        return None

# ========================
# メイン処理
# ========================
def generate_all_images():
    os.makedirs(IMAGE_OUTPUT_DIR, exist_ok=True)
    articles = get_articles_needing_images()

    if not articles:
        logger.info("画像生成対象の記事がありません")
        return

    logger.info("画像生成開始: %d件", len(articles))

    success = 0
    failed = 0

    for article_id, title_ja, category, title_en, summary in articles:
        logger.info("生成中 [%d]: %s", article_id, title_ja[:40])

        try:
            # プロンプト生成
            prompt, negative = build_full_prompt(
                title_ja, category or "AI", title_en, summary or ""
            )
            logger.debug("プロンプト: %s", prompt[:80])

            # 画像生成
            filename = generate_image_comfyui(prompt, negative, article_id)
            if not filename:
                failed += 1
                continue

            # 保存
            image_path = download_image(filename, article_id)
            if not image_path:
                failed += 1
                continue

            # DB更新
            update_image_url(article_id, image_path)
            logger.info("✅ 生成完了: %s", title_ja[:40])
            success += 1

        except Exception as e:
            logger.error("生成エラー [%d]: %s", article_id, str(e))
            failed += 1

    logger.info("画像生成完了: 成功%d件 失敗%d件", success, failed)

if __name__ == "__main__":
    generate_all_images()
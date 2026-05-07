"""
画像生成モジュール
DeepSeek V4 ProでFLUX用プロンプト生成 → FLUX.1 Schnellで画像生成
"""

import sqlite3
import requests
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

NVIDIA_BASE_URL = "https://integrate.api.nvidia.com/v1"
DEEPSEEK_MODEL = "deepseek-ai/deepseek-v4-pro"


# ========================
# Logger
# ========================
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
        os.path.join(LOG_DIR, f"{today}.log"),
        encoding="utf-8"
    )

    file_handler.setLevel(logging.DEBUG)

    file_handler.setFormatter(
        logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    )

    logger.addHandler(file_handler)

    return logger


logger = setup_logger()


# ========================
# カテゴリ別スタイル
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
        "innovation atmosphere"
    ),

    "ツール": (
        "software development tools, productivity application, "
        "modern UI dashboard, clean minimal design, "
        "digital workspace"
    ),

    "AI": (
        "artificial intelligence concept, technology background, "
        "digital innovation, futuristic aesthetic"
    ),
}


QUALITY_SUFFIX = (
    "ultra high quality, 4K, sharp focus, "
    "cinematic lighting, professional editorial illustration, "
    "award winning composition, no text, no watermark"
)


GLOBAL_NEGATIVE = (
    "text, watermark, logo, letters, blurry, low quality, "
    "distorted face, duplicate, extra fingers, bad anatomy, "
    "nsfw, gore, violence"
)


# ========================
# 人物判定
# ========================
KNOWN_PERSONS = {
    "altman": (
        "Sam Altman",
        "middle-aged man, short dark hair, casual tech style"
    ),

    "musk": (
        "Elon Musk",
        "tall man, short hair, intense expression, tech entrepreneur"
    ),

    "zuckerberg": (
        "Mark Zuckerberg",
        "young man, curly hair, casual t-shirt"
    ),

    "pichai": (
        "Sundar Pichai",
        "South Asian man, glasses, professional suit"
    ),

    "nadella": (
        "Satya Nadella",
        "South Asian man, glasses, business suit"
    ),

    "cook": (
        "Tim Cook",
        "middle-aged man, glasses, business casual"
    ),

    "bezos": (
        "Jeff Bezos",
        "bald man, athletic build, business casual"
    ),

    "huang": (
        "Jensen Huang",
        "Asian man, leather jacket, tech style"
    ),

    "lecun": (
        "Yann LeCun",
        "older man, beard, academic style"
    ),

    "hassabis": (
        "Demis Hassabis",
        "British man, casual smart"
    ),
}


# ========================
# 企業判定
# ========================
KNOWN_COMPANIES = {
    "openai": (
        "futuristic AI laboratory, glowing neural networks, "
        "dark cinematic atmosphere, advanced artificial intelligence"
    ),

    "anthropic": (
        "clean minimal AI safety laboratory, purple tones, "
        "modern research environment"
    ),

    "google": (
        "colorful technology campus, futuristic data systems, "
        "modern architecture"
    ),

    "microsoft": (
        "corporate enterprise technology, blue tones, "
        "cloud infrastructure"
    ),

    "nvidia": (
        "advanced GPU chips, green glowing circuits, "
        "AI data center, semiconductor technology"
    ),

    "apple": (
        "minimalist white futuristic design, "
        "premium technology atmosphere"
    ),

    "meta": (
        "social network visualization, virtual reality environment, "
        "blue futuristic aesthetic"
    ),

    "amazon": (
        "warehouse automation, cloud computing infrastructure, "
        "industrial robotics"
    ),

    "tesla": (
        "electric vehicles, futuristic factory, clean energy technology"
    ),

    "gpt": (
        "AI language model visualization, neural networks, "
        "floating digital text streams"
    ),

    "claude": (
        "purple AI assistant interface, clean minimal design"
    ),

    "gemini": (
        "multimodal AI visualization, constellation patterns, "
        "Google-inspired futuristic design"
    ),

    "llama": (
        "open source AI development environment, "
        "developer workspace, purple technology aesthetic"
    ),
}


# ========================
# DB
# ========================
def get_articles_needing_images():

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            a.id,
            s.title_ja,
            s.summary_ja,
            s.category,
            a.title,
            a.summary
        FROM articles a
        JOIN summaries s
            ON a.id = s.article_id
        WHERE a.processed = 1
        AND s.summary_ja IS NOT NULL
        AND (
            a.image_url IS NULL
            OR a.image_url NOT LIKE '/images/%'
        )
        ORDER BY a.buzz_score DESC
    """)

    rows = cursor.fetchall()

    conn.close()

    return rows


def update_image_url(article_id: int, image_path: str, flux_prompt: str):

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE articles
        SET image_url = ?,
            flux_prompt = ?
        WHERE id = ?
    """, (
        image_path,
        flux_prompt,
        article_id
    ))

    conn.commit()
    conn.close()


# ========================
# 判定
# ========================
def detect_person(text: str):

    text_lower = text.lower()

    for key, value in KNOWN_PERSONS.items():
        if key in text_lower:
            return value

    return None


def detect_company(text: str):

    text_lower = text.lower()

    for key, style in KNOWN_COMPANIES.items():
        if key in text_lower:
            return style

    return None


# ========================
# DeepSeek Prompt生成
# ========================
def generate_flux_prompt(
    title_ja: str,
    summary_ja: str,
    category: str,
    title_en: str,
    summary_en: str
) -> str:

    text = f"{title_en} {title_ja} {summary_en}"

    # 人物優先
    person = detect_person(text)

    if person:

        name, appearance = person

        return (
            f"editorial illustration of {name}, "
            f"{appearance}, "
            f"futuristic AI technology background, "
            f"cinematic lighting, "
            f"digital art, "
            f"professional magazine illustration, "
            f"highly detailed, "
            f"no text"
        )

    # 企業・モデル優先
    company_style = detect_company(text)

    if company_style:

        return (
            f"{company_style}, "
            f"cinematic lighting, "
            f"editorial illustration, "
            f"ultra detailed, "
            f"professional business magazine style"
        )

    # DeepSeek生成
    client = openai.OpenAI(
        base_url=NVIDIA_BASE_URL,
        api_key=os.environ.get("NVIDIA_API_KEY")
    )

    prompt = f"""
You are a world-class editorial illustrator.

Create ONE cinematic FLUX image prompt.

ARTICLE:

Japanese Title:
{title_ja}

Japanese Summary:
{summary_ja[:1500]}

English Title:
{title_en}

English Summary:
{summary_en[:1500]}

RULES:
- Output ONLY the image prompt
- Under 80 words
- No text
- No watermark
- No UI screenshots
- Cinematic lighting
- Editorial illustration
- Modern AI business aesthetic
- Highly detailed
- Professional magazine quality
- Visual storytelling
- Avoid generic abstract art
"""

    for attempt in range(3):

        try:

            res = client.chat.completions.create(
                model=DEEPSEEK_MODEL,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=120,
                temperature=0.7,
                top_p=0.9,
            )

            return res.choices[0].message.content.strip()

        except Exception as e:

            logger.error(
                "DeepSeek APIエラー (%d/3): %s",
                attempt + 1,
                str(e)
            )

            time.sleep(5)

    return (
        "futuristic AI technology background, "
        "digital network, cinematic lighting, "
        "editorial illustration, ultra detailed"
    )


# ========================
# 完全プロンプト
# ========================
def build_full_prompt(
    title_ja: str,
    summary_ja: str,
    category: str,
    title_en: str,
    summary_en: str
):

    base = generate_flux_prompt(
        title_ja,
        summary_ja,
        category,
        title_en,
        summary_en
    )

    style = CATEGORY_STYLE.get(
        category,
        CATEGORY_STYLE["AI"]
    )

    prompt = f"{base}, {style}, {QUALITY_SUFFIX}"

    return prompt, GLOBAL_NEGATIVE


# ========================
# ComfyUI
# ========================
def generate_image_comfyui(
    prompt: str,
    negative: str,
    article_id: int
):

    workflow = {
        "1": {
            "class_type": "UnetLoaderGGUF",
            "inputs": {
                "unet_name": "flux1-schnell-Q8_0.gguf"
            }
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
            "inputs": {
                "vae_name": "ae.safetensors"
            }
        },

        "4": {
            "class_type": "CLIPTextEncode",
            "inputs": {
                "text": prompt,
                "clip": ["2", 0]
            }
        },

        "5": {
            "class_type": "CLIPTextEncode",
            "inputs": {
                "text": negative,
                "clip": ["2", 0]
            }
        },

        "6": {
            "class_type": "EmptyLatentImage",
            "inputs": {
                "width": 1280,
                "height": 720,
                "batch_size": 1
            }
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
            "inputs": {
                "samples": ["7", 0],
                "vae": ["3", 0]
            }
        },

        "9": {
            "class_type": "SaveImage",
            "inputs": {
                "images": ["8", 0],
                "filename_prefix": f"article_{article_id}"
            }
        }
    }

    try:

        res = requests.post(
            f"{COMFYUI_URL}/prompt",
            json={"prompt": workflow},
            timeout=10
        )

        res.raise_for_status()

        prompt_id = res.json()["prompt_id"]

        logger.info(
            "ComfyUIキュー送信完了: %s",
            prompt_id
        )

        for _ in range(120):

            time.sleep(1)

            history = requests.get(
                f"{COMFYUI_URL}/history/{prompt_id}",
                timeout=5
            ).json()

            if prompt_id in history:

                outputs = history[prompt_id].get("outputs", {})

                for _, node_output in outputs.items():

                    if "images" in node_output:

                        img_info = node_output["images"][0]

                        return img_info["filename"]

        logger.error(
            "画像生成タイムアウト: article_id=%d",
            article_id
        )

        return None

    except Exception as e:

        logger.error(
            "ComfyUI APIエラー: %s",
            str(e)
        )

        return None


# ========================
# ダウンロード
# ========================
def download_image(filename: str, article_id: int):

    os.makedirs(IMAGE_OUTPUT_DIR, exist_ok=True)

    save_path = os.path.join(
        IMAGE_OUTPUT_DIR,
        f"article_{article_id}.webp"
    )

    url = (
        f"{COMFYUI_URL}/view"
        f"?filename={filename}&type=output"
    )

    try:

        urllib.request.urlretrieve(url, save_path)

        return f"/images/articles/article_{article_id}.webp"

    except Exception as e:

        logger.error(
            "画像ダウンロードエラー: %s",
            str(e)
        )

        return None


# ========================
# Main
# ========================
def generate_all_images():

    os.makedirs(IMAGE_OUTPUT_DIR, exist_ok=True)

    articles = get_articles_needing_images()

    if not articles:

        logger.info("画像生成対象の記事がありません")

        return

    logger.info(
        "画像生成開始: %d件",
        len(articles)
    )

    success = 0
    failed = 0

    for (
        article_id,
        title_ja,
        summary_ja,
        category,
        title_en,
        summary_en
    ) in articles:

        logger.info(
            "生成中 [%d]: %s",
            article_id,
            title_ja[:40]
        )

        try:

            prompt, negative = build_full_prompt(
                title_ja,
                summary_ja or "",
                category or "AI",
                title_en,
                summary_en or ""
            )

            logger.debug(
                "FLUX Prompt: %s",
                prompt[:200]
            )

            filename = generate_image_comfyui(
                prompt,
                negative,
                article_id
            )

            if not filename:
                failed += 1
                continue

            image_path = download_image(
                filename,
                article_id
            )

            if not image_path:
                failed += 1
                continue

            update_image_url(
                article_id,
                image_path,
                prompt
            )

            logger.info(
                "✅ 生成完了 [%d]",
                article_id
            )

            success += 1

        except Exception as e:

            logger.error(
                "生成エラー [%d]: %s",
                article_id,
                str(e)
            )

            failed += 1

    logger.info(
        "画像生成完了: 成功%d件 / 失敗%d件",
        success,
        failed
    )


if __name__ == "__main__":
    generate_all_images()
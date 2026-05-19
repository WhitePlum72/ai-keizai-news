"""
画像生成モジュール（DeepSeek公式API対応版）
- platform.deepseek.com のAPIでFLUX用プロンプト生成
- FLUX.1 Schnellで画像生成
- Pillowで企業名・モデル名を中央オーバーレイ合成
- 人物記事はオーバーレイなし
"""

import sqlite3
import requests
import time
import os
import logging
import sys
import urllib.request

from datetime import datetime
from PIL import Image, ImageDraw, ImageFont

try:
    from dotenv import load_dotenv
    load_dotenv(dotenv_path='.env', override=True)
except ImportError:
    pass

DB_PATH = "data/articles.db"
LOG_DIR = "logs"

COMFYUI_URL    = "http://localhost:8188"
IMAGE_OUTPUT_DIR = "astro-site/public/images/articles"

DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY")
DEEPSEEK_URL     = "https://api.deepseek.com/chat/completions"
DEEPSEEK_MODEL   = "deepseek-v4-pro"

# フォント（Windows優先、なければNotoSansCJK）
FONT_PATH_WIN = "C:/Windows/Fonts/NotoSansJP-ExtraBold.ttf"
FONT_PATH_LINUX = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"
FONT_PATH = FONT_PATH_WIN if os.path.exists(FONT_PATH_WIN) else FONT_PATH_LINUX

BADGE_PAD    = 20
BADGE_RADIUS = 16
BADGE_ALPHA  = 180
FONT_SIZE_PRIMARY   = 72
FONT_SIZE_SECONDARY = 48
BADGE_SPACING = 100


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


# ========================
# カテゴリ別スタイル
# ========================
CATEGORY_STYLE = {
    "AI関連株": "financial data visualization, stock market chart, professional business photography, dramatic lighting, Bloomberg terminal aesthetic, dark background",
    "モデル":   "cutting-edge AI technology, neural network visualization, futuristic blue purple gradient, photorealistic render, data streams, digital transformation",
    "AIモデル": "cutting-edge AI technology, neural network visualization, futuristic blue purple gradient, photorealistic render, data streams, digital transformation",
    "ビジネス": "modern corporate environment, professional business setting, clean minimal aesthetic, confident atmosphere, office architecture, strategic planning",
    "研究":     "scientific laboratory, data visualization, academic research environment, clean minimal aesthetic, innovation atmosphere",
    "ツール":   "software development tools, productivity application, modern UI dashboard, clean minimal design, digital workspace",
    "AI":       "artificial intelligence concept, technology background, digital innovation, futuristic aesthetic",
}

QUALITY_SUFFIX  = "ultra high quality, 4K, sharp focus, cinematic lighting, professional editorial illustration, award winning composition, no text, no watermark"
GLOBAL_NEGATIVE = "text, watermark, logo, letters, blurry, low quality, distorted face, duplicate, extra fingers, bad anatomy, nsfw, gore, violence"


# ========================
# 人物・企業判定
# ========================
KNOWN_PERSONS = {
    "altman":     ("Sam Altman",     "40s american male, round face, short dark brown hair, clean shaven, warm brown eyes, casual style, slight smile"),
    "musk":       ("Elon Musk",      "50s american male, tall, square jaw, short dark hair, intense blue eyes, black casual jacket, serious expression"),
    "zuckerberg": ("Mark Zuckerberg","40s american male, curly dark hair, neutral expression, pale skin, dark eyes, grey t-shirt, youthful appearance"),
    "pichai":     ("Sundar Pichai",  "50s indian male, black hair with grey temples, warm brown skin, glasses, gentle smile, business suit"),
    "nadella":    ("Satya Nadella",  "50s indian male, short black hair, brown skin, slim glasses, confident expression, dark business suit"),
    "cook":       ("Tim Cook",       "60s american male, short silver hair, blue eyes, silver rimmed glasses, business casual, calm expression"),
    "bezos":      ("Jeff Bezos",     "60s american male, bald head, athletic build, wide smile, strong jaw, business casual shirt"),
    "huang":      ("Jensen Huang",   "60s taiwanese american male, short black hair with grey, confident smile, signature black leather jacket"),
    "lecun":      ("Yann LeCun",     "60s french male, grey beard, grey hair, academic style, glasses, thoughtful expression"),
    "hassabis":   ("Demis Hassabis", "40s british male, dark hair, olive skin, slim build, casual smart, intelligent expression"),
}

KNOWN_COMPANIES = {
    "openai":     ("OpenAI",     "futuristic AI laboratory, glowing neural networks, dark cinematic atmosphere"),
    "anthropic":  ("Anthropic",  "clean minimal AI safety laboratory, purple tones, modern research environment"),
    "google":     ("Google",     "colorful technology campus, futuristic data systems, modern architecture"),
    "microsoft":  ("Microsoft",  "corporate enterprise technology, blue tones, cloud infrastructure"),
    "nvidia":     ("NVIDIA",     "advanced GPU chips, green glowing circuits, AI data center, semiconductor technology"),
    "apple":      ("Apple",      "minimalist white futuristic design, premium technology atmosphere"),
    "meta":       ("Meta",       "social network visualization, virtual reality environment, blue futuristic aesthetic"),
    "amazon":     ("Amazon",     "warehouse automation, cloud computing infrastructure, industrial robotics"),
    "tesla":      ("Tesla",      "electric vehicles, futuristic factory, clean energy technology"),
    "gpt":        ("GPT",        "AI language model visualization, neural networks, floating digital text streams"),
    "claude":     ("Claude",     "purple AI assistant interface, clean minimal design"),
    "gemini":     ("Gemini",     "multimodal AI visualization, constellation patterns, Google-inspired futuristic design"),
    "llama":      ("Llama",      "open source AI development environment, developer workspace, purple technology aesthetic"),
    "deepseek":   ("DeepSeek",   "deep sea inspired AI visualization, dark blue tones, advanced language model"),
    "mistral":    ("Mistral",    "European AI research, clean modern design, wind-inspired visualization"),
    "qwen":       ("Qwen",       "Alibaba AI, futuristic Asian tech aesthetic, modern digital interface"),
    "grok":       ("Grok",       "xAI visualization, dark futuristic aesthetic, neural network"),
    "perplexity": ("Perplexity", "search AI visualization, clean minimal design, information flow"),
}
# KNOWN_COMPANIES の直下に追加
PERSON_QUALITY = (
    "2D digital illustration, anime-inspired art style, "
    "clean line art, flat color with shading, "
    "professional editorial illustration, "
    "vibrant colors, sharp details, "
    "character portrait, centered composition"
)

# ========================
# DB
# ========================
def update_image_url(article_id: int, image_path: str, flux_prompt: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE articles SET image_url = ?, flux_prompt = ? WHERE id = ?",
        (image_path, flux_prompt, article_id)
    )
    conn.commit()
    conn.close()


# ========================
# 人物・企業検出
# ========================
def detect_person(text: str):
    text_lower = text.lower()
    for key, value in KNOWN_PERSONS.items():
        if key in text_lower:
            return value
    return None


def detect_companies(text: str) -> list[tuple[str, str]]:
    text_lower = text.lower()
    return [(name, style) for key, (name, style) in KNOWN_COMPANIES.items() if key in text_lower]


# ========================
# Pillowオーバーレイ
# ========================
def add_text_overlay(image_path: str, labels: list[str]) -> None:
    if not labels:
        return

    img = Image.open(image_path).convert("RGBA")
    W, H = img.size

    target_w = int(W * 2 / 3)
    MIN_SIZE = 80

    def fit_font(text: str, max_width: int) -> ImageFont.FreeTypeFont:
        for size in range(300, MIN_SIZE - 1, -4):
            try:
                f = ImageFont.truetype(FONT_PATH, size)
            except Exception:
                return ImageFont.load_default()
            dummy = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
            bb = dummy.textbbox((0, 0), text, font=f)
            if (bb[2] - bb[0]) <= max_width:
                return f
        try:
            return ImageFont.truetype(FONT_PATH, MIN_SIZE)
        except Exception:
            return ImageFont.load_default()

    GAP = 40

    fonts = []
    for i, label in enumerate(labels):
        max_w = target_w if i == 0 else int(target_w * 0.80)
        fonts.append(fit_font(label, max_w))

    # ストローク幅を先に確定してレイアウト計算に含める
    def get_stroke_w(font):
        return max(3, int(font.size * 0.04))

    sizes = []
    for label, font in zip(labels, fonts):
        stroke_w = get_stroke_w(font)
        dummy = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
        bb = dummy.textbbox((0, 0), label, font=font, stroke_width=stroke_w)
        sizes.append((bb[2] - bb[0], bb[3] - bb[1]))

    total_h = sum(h for _, h in sizes) + GAP * (len(labels) - 1)
    cy = H // 2 - total_h // 2

    draw = ImageDraw.Draw(img)

    for label, font, (tw, th) in zip(labels, fonts, sizes):
        stroke_w = get_stroke_w(font)
        # ストローク込みのbboxで中央揃え
        dummy = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
        bb = dummy.textbbox((0, 0), label, font=font, stroke_width=stroke_w)
        tx = W // 2 - (bb[2] - bb[0]) // 2 - bb[0]
        ty = cy - bb[1]

        draw.text(
            (tx, ty), label,
            font=font,
            fill=(255, 255, 255, 255),
            stroke_width=stroke_w,
            stroke_fill=(0, 0, 0, 255),
        )

        cy += th + GAP

    img.convert("RGB").save(image_path, "WEBP", quality=82, method=6)
    logger.debug("オーバーレイ完了: %s %s", image_path, labels)

# ========================
# DeepSeek APIでFLUXプロンプト生成
# ========================
def call_deepseek(prompt: str, max_tokens: int = 120) -> str:
    if not DEEPSEEK_API_KEY:
        raise EnvironmentError("DEEPSEEK_API_KEY が設定されていません。")

    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json",
    }
    body = {
        "model": DEEPSEEK_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "thinking": {"type": "disabled"},
    }

    for attempt in range(3):
        try:
            res = requests.post(DEEPSEEK_URL, headers=headers, json=body, timeout=30)
            if res.status_code == 429:
                time.sleep(60 * (attempt + 1))
                continue
            res.raise_for_status()
            return res.json()["choices"][0]["message"]["content"].strip()
        except Exception as e:
            logger.error("DeepSeek APIエラー (%d/3): %s", attempt + 1, e)
            time.sleep(5)

    return "futuristic AI technology background, digital network, cinematic lighting, editorial illustration, ultra detailed"


def generate_flux_prompt(title_ja, summary_ja, category, title_en, summary_en) -> str:
    text = f"{title_en} {title_ja} {summary_en}"

    # 人物（2Dイラスト）
    person = detect_person(text)
    if person:
        name, appearance = person
        return (
            f"2D digital illustration portrait of {name}, "
            f"{appearance}, "
            f"futuristic AI technology background, "
            f"anime-inspired editorial illustration style, "
            f"clean line art, flat colors with cel shading, "
            f"{PERSON_QUALITY}, "
            f"no photo, no watermark, no text"
        )

    # 企業・モデル検出（プロンプトに企業名を含める）
    companies = detect_companies(text)
    if companies:
        company_names = ", ".join([name for name, _ in companies[:2]])
        _, style = companies[0]
        return (
            f"{style}, "
            f"with subtle {company_names} branding elements, "
            f"cinematic lighting, editorial illustration, "
            f"ultra detailed, professional business magazine style, "
            f"no text overlay, no watermark"
        )

    # DeepSeekで生成
    prompt = f"""You are a world-class editorial illustrator.
Create ONE cinematic FLUX image prompt.

ARTICLE:
Japanese Title: {title_ja}
English Title: {title_en}
English Summary: {summary_en[:1000]}

RULES:
- Output ONLY the image prompt (under 80 words)
- No text, no watermark, no UI screenshots
- Cinematic lighting, editorial illustration
- Modern AI business aesthetic, highly detailed
- Professional magazine quality"""

    return call_deepseek(prompt, max_tokens=120)


def build_full_prompt(title_ja, summary_ja, category, title_en, summary_en):
    base  = generate_flux_prompt(title_ja, summary_ja, category, title_en, summary_en)
    style = CATEGORY_STYLE.get(category, CATEGORY_STYLE["AI"])
    return f"{base}, {style}, {QUALITY_SUFFIX}", GLOBAL_NEGATIVE


# ========================
# ComfyUI
# ========================
def generate_image_comfyui(prompt: str, negative: str, article_id: int):
    workflow = {
        "1": {"class_type": "UnetLoaderGGUF",  "inputs": {"unet_name": "flux1-schnell-Q8_0.gguf"}},
        "2": {"class_type": "DualCLIPLoader",   "inputs": {"clip_name1": "t5xxl_fp8_e4m3fn.safetensors", "clip_name2": "clip_l.safetensors", "type": "flux", "device": "default"}},
        "3": {"class_type": "VAELoader",        "inputs": {"vae_name": "ae.safetensors"}},
        "4": {"class_type": "CLIPTextEncode",   "inputs": {"text": prompt,   "clip": ["2", 0]}},
        "5": {"class_type": "CLIPTextEncode",   "inputs": {"text": negative, "clip": ["2", 0]}},
        "6": {"class_type": "EmptyLatentImage", "inputs": {"width": 1280, "height": 720, "batch_size": 1}},
        "7": {"class_type": "KSampler", "inputs": {
            "model": ["1", 0], "positive": ["4", 0], "negative": ["5", 0],
            "latent_image": ["6", 0], "seed": article_id,
            "steps": 4, "cfg": 1.0, "sampler_name": "euler",
            "scheduler": "simple", "denoise": 1.0,
        }},
        "8": {"class_type": "VAEDecode",  "inputs": {"samples": ["7", 0], "vae": ["3", 0]}},
        "9": {"class_type": "SaveImage",  "inputs": {"images": ["8", 0], "filename_prefix": f"article_{article_id}"}},
    }

    try:
        res = requests.post(f"{COMFYUI_URL}/prompt", json={"prompt": workflow}, timeout=10)
        res.raise_for_status()
        prompt_id = res.json()["prompt_id"]
        logger.info("ComfyUIキュー送信完了: %s", prompt_id)

        for _ in range(120):
            time.sleep(1)
            history = requests.get(f"{COMFYUI_URL}/history/{prompt_id}", timeout=5).json()
            if prompt_id in history:
                for _, node_output in history[prompt_id].get("outputs", {}).items():
                    if "images" in node_output:
                        return node_output["images"][0]["filename"]

        logger.error("画像生成タイムアウト: article_id=%d", article_id)
        return None
    except Exception as e:
        logger.error("ComfyUI APIエラー: %s", e)
        return None


def download_image(filename: str, article_id: int) -> str | None:
    os.makedirs(IMAGE_OUTPUT_DIR, exist_ok=True)
    save_path = os.path.join(IMAGE_OUTPUT_DIR, f"article_{article_id}.webp")
    try:
        urllib.request.urlretrieve(
            f"{COMFYUI_URL}/view?filename={filename}&type=output", save_path
        )
        return save_path
    except Exception as e:
        logger.error("画像ダウンロードエラー: %s", e)
        return None


# ========================
# Main
# ========================
def get_articles_needing_images():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT a.id, s.title_ja, s.summary_ja, s.category, a.title, a.summary,
               a.image_url, a.url
        FROM articles a
        JOIN summaries s ON a.id = s.article_id
        WHERE a.processed = 1
          AND s.summary_ja IS NOT NULL
          AND (
              a.image_url IS NULL
              OR a.image_url = ''
              OR a.image_url = '""'
          )
        ORDER BY a.buzz_score DESC
    """)
    rows = cursor.fetchall()
    conn.close()
    return rows


def generate_all_images():
    os.makedirs(IMAGE_OUTPUT_DIR, exist_ok=True)
    articles = get_articles_needing_images()

    if not articles:
        logger.info("画像生成対象の記事がありません")
        return

    logger.info("画像生成開始: %d件", len(articles))
    success = failed = 0

    for row in articles:
        article_id, title_ja, summary_ja, category, title_en, summary_en, og_image_url, source_url = row
        logger.info("処理中 [%d]: %s", article_id, (title_ja or title_en)[:40])

        try:
            # OG画像がある場合はそのまま使用
            if og_image_url and og_image_url.startswith("http"):
                web_path = og_image_url  # 外部URLをそのまま使用
                update_image_url(article_id, web_path, "og_image")
                logger.info("✅ OG画像使用 [%d]: %s", article_id, og_image_url[:60])
                success += 1
                continue

            # OG画像なし → FLUX生成
            prompt, negative = build_full_prompt(
                title_ja or "", summary_ja or "", category or "AI",
                title_en or "", summary_en or ""
            )
            logger.debug("FLUX Prompt: %s", prompt[:200])

            filename = generate_image_comfyui(prompt, negative, article_id)
            if not filename:
                failed += 1
                continue

            local_path = download_image(filename, article_id)
            if not local_path:
                failed += 1
                continue

            web_path = f"/images/articles/article_{article_id}.webp"
            update_image_url(article_id, web_path, prompt)
            logger.info("✅ FLUX生成完了 [%d]", article_id)
            success += 1

        except Exception as e:
            logger.error("生成エラー [%d]: %s", article_id, e)
            failed += 1

    logger.info("画像処理完了: 成功%d件 / 失敗%d件", success, failed)


if __name__ == "__main__":
    generate_all_images()

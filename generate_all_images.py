# generate_all_images.py
import sqlite3
import sys
sys.path.insert(0, ".")
from image_generator import build_full_prompt, generate_image_comfyui, download_image, update_image_url
import logging

logging.basicConfig(level=logging.INFO)
DB_PATH = "data/articles.db"

def get_all_articles():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT a.id, s.title_ja, s.category, a.title, a.summary
        FROM articles a
        JOIN summaries s ON a.id = s.article_id
        WHERE a.processed = 1
        ORDER BY a.buzz_score DESC
    """)
    rows = cursor.fetchall()
    conn.close()
    return rows

articles = get_all_articles()
total = len(articles)
print(f"対象記事: {total}件\n")

# Step1: Qwenでプロンプト全件生成
print("=" * 50)
print("Step1: プロンプト生成中（Qwen使用）")
print("=" * 50)

prompts = []
for i, (article_id, title_ja, category, title_en, summary) in enumerate(articles):
    print(f"[{i+1}/{total}] {title_ja[:40]}")
    try:
        prompt, negative = build_full_prompt(
            title_ja, category or "AI", title_en, summary or ""
        )
        prompts.append((article_id, title_ja, prompt, negative))
        print(f"       ✅ 完了")
    except Exception as e:
        print(f"       ❌ スキップ: {e}")

print(f"\nプロンプト生成完了: {len(prompts)}/{total}件")

# Step2: Qwen停止待ち
print("\n" + "=" * 50)
print("Qwenを停止してください（Ctrl+C）")
print("停止後、Enterキーを押してください")
print("=" * 50)
input("Enterキーで画像生成を開始します...")

# Step3: FLUX.1で全件生成
print("\n" + "=" * 50)
print("Step2: 画像生成中（FLUX.1 Schnell）")
print("=" * 50)

success = 0
for i, (article_id, title_ja, prompt, negative) in enumerate(prompts):
    print(f"[{i+1}/{len(prompts)}] {title_ja[:40]}")

    filename = generate_image_comfyui(prompt, negative, article_id)
    if not filename:
        print(f"       ❌ 失敗")
        continue

    image_path = download_image(filename, article_id)
    if not image_path:
        print(f"       ❌ 保存失敗")
        continue

    update_image_url(article_id, image_path)
    print(f"       ✅ {image_path}")
    success += 1

print(f"\n全件生成完了: {success}/{len(prompts)}件成功")
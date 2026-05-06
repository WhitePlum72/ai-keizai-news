# sample_image_gen.py
import sqlite3
import sys
sys.path.insert(0, ".")
from image_generator import build_full_prompt, generate_image_comfyui, download_image, update_image_url
import logging

logging.basicConfig(level=logging.INFO)
DB_PATH = "data/articles.db"

def get_sample_articles(limit=10):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT a.id, s.title_ja, s.category, a.title, a.summary
        FROM articles a
        JOIN summaries s ON a.id = s.article_id
        ORDER BY a.buzz_score DESC
        LIMIT ?
    """, (limit,))
    rows = cursor.fetchall()
    conn.close()
    return rows

articles = get_sample_articles(10)
print(f"対象記事: {len(articles)}件\n")

# ========================
# Step1: Qwenでプロンプト生成（全記事分）
# ========================
print("=" * 50)
print("Step1: プロンプト生成中（Qwen使用）")
print("=" * 50)

prompts = []
for i, (article_id, title_ja, category, title_en, summary) in enumerate(articles):
    print(f"[{i+1}/10] {title_ja[:40]}")
    prompt, negative = build_full_prompt(
        title_ja, category or "AI", title_en, summary or ""
    )
    prompts.append((article_id, title_ja, prompt, negative))
    print(f"       ✅ プロンプト生成完了")

# ========================
# Step2: Qwen停止を待つ
# ========================
print("\n" + "=" * 50)
print("Step2: Qwenを停止してください")
print("llama-server.exeのウィンドウでCtrl+Cを押す")
print("停止後、Enterキーを押してください")
print("=" * 50)
input("Enterキーで画像生成を開始します...")

# ========================
# Step3: FLUX.1で画像生成
# ========================
print("\n" + "=" * 50)
print("Step3: 画像生成中（FLUX.1 Schnell）")
print("=" * 50)

success = 0
for i, (article_id, title_ja, prompt, negative) in enumerate(prompts):
    print(f"[{i+1}/10] 生成中: {title_ja[:40]}")

    filename = generate_image_comfyui(prompt, negative, article_id)
    if not filename:
        print(f"       ❌ 失敗")
        continue

    image_path = download_image(filename, article_id)
    if not image_path:
        print(f"       ❌ 保存失敗")
        continue

    update_image_url(article_id, image_path)
    print(f"       ✅ 完了: {image_path}")
    success += 1

print(f"\n生成完了: {success}/10件成功")
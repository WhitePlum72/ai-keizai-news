import sqlite3
import sys
sys.path.insert(0, ".")
from image_generator import build_full_prompt, generate_image_comfyui, download_image, update_image_url

DB_PATH = "data/articles.db"

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()
cursor.execute("""
    SELECT a.id, s.title_ja, s.category, a.title, a.summary
    FROM articles a
    JOIN summaries s ON a.id = s.article_id
    WHERE (a.image_url IS NULL OR a.image_url = '')
    AND a.processed = 1
    ORDER BY a.buzz_score DESC
""")
articles = cursor.fetchall()
conn.close()

print(f"画像なし記事: {len(articles)}件")
for a in articles:
    print(f"  - {a[1][:50]}")

# Step1: Qwen起動中にプロンプト生成
print("\nStep1: プロンプト生成中（Qwen使用）...")
prompts = []
for article_id, title_ja, category, title_en, summary in articles:
    try:
        prompt, negative = build_full_prompt(
            title_ja, category or "AI", title_en, summary or ""
        )
        prompts.append((article_id, title_ja, prompt, negative))
        print(f"✅ {title_ja[:40]}")
    except Exception as e:
        print(f"❌ {title_ja[:40]}: {e}")

print(f"\nプロンプト生成完了: {len(prompts)}件")

# Step2: Qwen停止待ち
input("\nQwenを停止してからEnterを押してください（VRAM解放）...")

# Step3: FLUX画像生成
print("\nStep3: 画像生成中（FLUX.1 Schnell）...")
success = 0
for article_id, title_ja, prompt, negative in prompts:
    print(f"生成中: {title_ja[:40]}")
    filename = generate_image_comfyui(prompt, negative, article_id)
    if not filename:
        print("❌ 失敗")
        continue
    image_path = download_image(filename, article_id)
    if not image_path:
        print("❌ 保存失敗")
        continue
    update_image_url(article_id, image_path)
    print(f"✅ {image_path}")
    success += 1

print(f"\n完了: {success}/{len(prompts)}件成功")
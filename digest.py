"""
日次まとめ記事生成モジュール
その日の上位記事をまとめた「今日のAIニュースまとめ」記事を自動生成
"""

import sqlite3
import logging
import os
import sys
import openai
from datetime import datetime
import re

DB_PATH = "data/articles.db"
LOG_DIR = "logs"
QWEN_BASE_URL = "http://localhost:8080/v1"
QWEN_MODEL = "Qwen3.6-27B-UD-Q4_K_XL.gguf"
OUTPUT_DIR = "astro-site/src/content/articles"


# ========================
# ロガー
# ========================
def setup_logger():
    logger = logging.getLogger("digest")
    logger.setLevel(logging.DEBUG)

    if logger.handlers:
        return logger

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


# ========================
# DB
# ========================
def get_top_articles(limit=10):
    """summariesの上位記事を取得"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT a.id, s.title_ja, s.summary_ja, s.category, a.buzz_score, a.source
        FROM articles a
        JOIN summaries s ON a.id = s.article_id
        ORDER BY a.buzz_score DESC
        LIMIT ?
    """, (limit,))
    rows = cursor.fetchall()
    conn.close()
    return rows


# ========================
# Qwen
# ========================
def generate_digest(articles):
    """上位記事からまとめ記事を生成"""
    client = openai.OpenAI(base_url=QWEN_BASE_URL, api_key="dummy")

    article_list = ""
    for i, (aid, title, body, category, score, source) in enumerate(articles, 1):
        article_list += f"{i}. 【{category}】{title}\n{(body or '')[:300]}\n\n"

    today_str = datetime.now().strftime("%Y年%m月%d日")

    prompt = f"""
あなたはSEOに精通した日本のAI専門メディアの編集者である。

以下は{today_str}のAIニュース上位{len(articles)}件である。

{article_list}

これらをまとめた記事を書け。

条件:
・1行目: 見出し（例：{today_str}のAIニュースまとめ｜注目トピックを解説）
・2行目: 空行
・文体: です・ます調
・本文800〜1000文字
・冒頭の第1段落: その日のAIニュース全体の概要を2〜3文で要約する（読者がすぐ内容を把握できるようにする）
・各トピックを段落ごとに分けて解説する
・検索ユーザーが知りたい情報（何が・なぜ重要か）を意識して書く
・「AI」「人工知能」「最新ニュース」「{today_str}」などのキーワードを自然に含める
・マークダウン記法一切禁止
・最後の段落: 「今後のAI動向にも引き続き注目していきましょう。」で締める
"""

    res = client.chat.completions.create(
        model=QWEN_MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=1800,
        extra_body={"chat_template_kwargs": {"enable_thinking": False}},
    )

    body = res.choices[0].message.content

    # meta description用の要約を別途生成
    meta_res = client.chat.completions.create(
        model=QWEN_MODEL,
        messages=[{"role": "user", "content": f"以下の記事を120文字以内で要約してください。文末は「。」で終わること。マークダウン禁止。\n\n{body[:1000]}"}],
        max_tokens=200,
        extra_body={"chat_template_kwargs": {"enable_thinking": False}},
    )
    meta_description = meta_res.choices[0].message.content.strip()[:120]

    return body, meta_description


# ========================
# Markdown生成
# ========================
def save_digest_markdown(content, meta_description):
    today = datetime.now().strftime("%Y-%m-%d")
    lines = content.strip().splitlines()

    title = lines[0].strip().lstrip("#").strip()
    body = "\n".join(lines[1:]).strip()

    slug = f"{today}-digest"
    filepath = os.path.join(OUTPUT_DIR, f"{slug}.md")

    frontmatter = f"""---
title: "{title}"
source: "AI経済新聞"
source_url: "https://aikeizai.jp"
category: "その他"
published_at: "{today}"
buzz_score: 999
image_url: ""
meta_description: "{meta_description}"
is_digest: true
---

{body}
"""

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(frontmatter)

    logger.info(f"まとめ記事を生成しました: {filepath}")
    return filepath


# ========================
# メイン
# ========================
def generate_daily_digest():
    logger.info("日次まとめ記事生成を開始します")

    articles = get_top_articles(limit=10)

    if not articles:
        logger.warning("本日の記事が見つかりません。まとめ記事をスキップします。")
        return

    logger.info(f"{len(articles)}件の記事を取得しました")

    content, meta_description = generate_digest(articles)
    filepath = save_digest_markdown(content, meta_description)

    logger.info(f"完了: {filepath}")
    return filepath


if __name__ == "__main__":
    generate_daily_digest()
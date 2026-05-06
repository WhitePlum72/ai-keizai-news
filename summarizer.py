"""
要約生成モジュール
Qwen3.6-27Bを使って記事の日本語要約・Xツイート文・カテゴリ分類を生成し、summariesテーブルに保存する。
"""

import sqlite3
import openai
import logging
import os
import sys
from datetime import datetime
from typing import Dict, Optional, Tuple


# ==================== 設定 ====================

# DBファイルパス
DB_PATH = "data/articles.db"

# LLM接続設定
LLM_ENDPOINT = "http://localhost:8080/v1"
LLM_API_KEY = "dummy"
LLM_MODEL = "qwen3.6-27b"

# ログディレクトリ
LOG_DIR = "logs"

# カテゴリ一覧
CATEGORIES = ["モデル", "ビジネス", "ツール", "研究", "その他"]


# ==================== ログ設定 ====================

def setup_logger() -> logging.Logger:
    """ロガーを設定する"""
    logger = logging.getLogger("summarizer")
    logger.setLevel(logging.DEBUG)

    # コンソール出力
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_format = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    console_handler.setFormatter(console_format)
    logger.addHandler(console_handler)

    # ファイル出力
    os.makedirs(LOG_DIR, exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")
    log_file = os.path.join(LOG_DIR, f"{today}.log")

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_format = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    file_handler.setFormatter(file_format)
    logger.addHandler(file_handler)

    return logger


logger = setup_logger()


# ==================== DB操作 ====================

def init_db():
    """summariesテーブルが存在しない場合は作成する"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS summaries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            article_id INTEGER NOT NULL UNIQUE,
            summary TEXT,
            tweet_text TEXT,
            category TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (article_id) REFERENCES articles(id)
        )
    """)

    conn.commit()
    conn.close()
    logger.info("summariesテーブルを確認しました")


def get_pending_articles() -> list:
    """
    buzz_score > 0 かつ processed = 0 の記事をbuzz_score降順で取得する
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, title, summary, source, source_type
        FROM articles
        WHERE buzz_score > 0 AND processed = 0
        ORDER BY buzz_score DESC
    """)

    articles = cursor.fetchall()
    conn.close()

    logger.info("要約対象記事: %d件", len(articles))
    return articles


def save_summary(article_id: int, summary: str, tweet_text: str, category: str):
    """要約結果をsummariesテーブルに保存する"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO summaries (article_id, summary, tweet_text, category)
        VALUES (?, ?, ?, ?)
    """, (article_id, summary, tweet_text, category))

    conn.commit()
    conn.close()
    logger.info("要約を保存: article_id=%d, category=%s", article_id, category)


def mark_processed(article_id: int):
    """記事を処理済みに更新する"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(
        "UPDATE articles SET processed = 1 WHERE id = ?",
        (article_id,)
    )

    conn.commit()
    conn.close()


# ==================== LLM連携 ====================

def build_prompt(title: str, summary: str) -> str:
    """LLMへ送信するプロンプトを構築する"""
    return f"""あなたはAIニュースのキュレーターです。以下の英語AIニュース記事を分析してください。

【記事タイトル】
{title}

【記事概要】
{summary}

以下の3つをJSON形式で出力してください。他の説明は一切含めないでください。

{{
  "summary": "日本語要約（3〜5文・事実のみ・誇張なし）",
  "tweet": "Xツイート文（140字以内・冒頭に【カテゴリ】・末尾に#AI #LLM・URLなし）",
  "category": "{'/'.join(CATEGORIES)}のいずれか"
}}

ルール:
- summary: 3〜5文の日本語要約。事実のみを記述し、誇張表現は使わない。
- tweet: 140字以内のX用ツイート。冒頭に【カテゴリ】を付けて、末尾に「#AI #LLM」を付ける。URLは含めない。
- category: 「モデル」「ビジネス」「ツール」「研究」「その他」のいずれか1つを指定。
  - モデル: 新モデルの発表・比較ベンチマークなど
  - ビジネス: 資金調達・企業動向・市場分析など
  - ツール: 開発ツール・アプリ・プラットフォームなど
  - 研究: 論文・学術研究・技術調査など
  - その他: 上記に当てはまらないもの"""


def call_llm(prompt: str) -> Optional[Dict]:
    """
    Qwenにリクエストを送信してJSONレスポンスを返す
    """
    client = openai.OpenAI(
        api_key=LLM_API_KEY,
        base_url=LLM_ENDPOINT
    )

    response = client.chat.completions.create(
        model=LLM_MODEL,
        messages=[
            {"role": "system", "content": "あなたはAIニュースの専門キュレーターです。JSON形式で正確に回答してください。"},
            {"role": "user", "content": prompt}
        ],
        temperature=0.3,
        max_tokens=1024
    )

    content = response.choices[0].message.content.strip()

    # JSON部分の抽出（```json ... ```等形式に対応）
    if "```" in content:
        # ```json ... ``` の形式からJSON部分を抽出
        start = content.find("{")
        end = content.rfind("}") + 1
        if start != -1 and end != 0:
            content = content[start:end]

    import json
    result = json.loads(content)
    return result


def generate_summary(title: str, summary: str) -> Tuple[str, str, str]:
    """
    1記事に対して要約・ツイート文・カテゴリを生成する
    戻り値: (summary, tweet_text, category)
    """
    prompt = build_prompt(title, summary)

    try:
        result = call_llm(prompt)

        if result is None:
            raise ValueError("LLMレスポンスがNone")

        generated_summary = result.get("summary", "")
        tweet_text = result.get("tweet", "")
        category = result.get("category", "その他")

        # カテゴリのバリデーション
        if category not in CATEGORIES:
            logger.warning("無効なカテゴリ '%s' を 'その他' に置換", category)
            category = "その他"

        # ツイート文字数チェック（140字超えの場合は切り詰め）
        if len(tweet_text) > 140:
            logger.warning("ツイートが140字を超えるため切り詰め: %d字", len(tweet_text))
            tweet_text = tweet_text[:135] + "..."

        return generated_summary, tweet_text, category

    except Exception as e:
        logger.error("LLM呼び出しエラー: %s", str(e))
        raise


# ==================== メイン処理 ====================

def run_summarization():
    """要約処理を全記事に対して実行する"""
    logger.info("=" * 60)
    logger.info("要約処理を開始しました")
    logger.info("=" * 60)

    init_db()

    articles = get_pending_articles()

    if not articles:
        logger.info("要約対象の記事がありません")
        print("\n要約対象の記事がありません")
        return

    success_count = 0
    error_count = 0

    for i, article in enumerate(articles, 1):
        article_id = article["id"]
        title = article["title"] or ""
        summary = article["summary"] or ""

        logger.info("[%d/%d] 処理中: %s", i, len(articles), title[:60])

        try:
            generated_summary, tweet_text, category = generate_summary(title, summary)

            save_summary(article_id, generated_summary, tweet_text, category)
            mark_processed(article_id)

            success_count += 1
            logger.info("完了: category=%s, tweet=%s", category, tweet_text[:50])

        except Exception as e:
            error_count += 1
            logger.error("記事処理エラー (id=%d): %s", article_id, str(e))
            # エラーが出ても次の記事に進む

    logger.info("=" * 60)
    logger.info("要約処理が完了しました")
    logger.info("成功: %d件, エラー: %d件", success_count, error_count)
    logger.info("=" * 60)

    print(f"\n要約完了: 成功{success_count}件, エラー{error_count}件")


def main():
    """メイン関数"""
    try:
        run_summarization()
    except Exception as e:
        logger.error("要約処理で致命的なエラーが発生しました: %s", str(e))
        raise


if __name__ == "__main__":
    main()
# AI Daily JP - プロジェクト概要

## 目的
英語AIニュースを自動収集・日本語要約してサイトとXに配信する
完全自動運用のAIキュレーションメディア

## 技術スタック
- Python 3.11
- SQLite（ローカルDB）
- Qwen3.6-27B（llama.cpp・localhost:8080/v1）
- Astro（静的サイトジェネレーター）
- Vercel（デプロイ）
- GitHub Actions（CI/CD）
- APScheduler（スケジューラ）
- Tweepy（X自動投稿）

## ファイル構成
- collector.py   : RSS取得・重複排除・DB保存
- scorer.py      : buzz_score計算・30件選出
- summarizer.py  : Qwenで要約生成
- publisher.py   : Markdown生成・Git Push
- tweeter.py     : X自動投稿
- main.py        : 全体スケジューラ

## コーディング規則
- 関数名はスネークケース
- エラーは必ずtry/exceptで囲む
- ログはlogs/YYYY-MM-DD.logに保存
- 各ファイルは単体で実行できること
- コメントは日本語で記述
- 過剰な設計不要・シンプルに動くことを最優先

## LLM接続
- エンドポイント: http://localhost:8080/v1
- APIキー: dummy
- モデル: Qwen3.6-27B-UD-Q4_K_XL.gguf
- 外部LLM API（OpenAI・Anthropic等）は一切使用しない

## DB設計
- articles テーブル: 収集記事
- summaries テーブル: 要約・ツイート文

## 制約
- Qwenへのリクエストは1件ずつ順番に処理
- arXivはキーワードフィルタ必須
- HNはスコア500以上のみ
- Redditはupvote上位10件のみ
- 同一企業は1日最大4件まで
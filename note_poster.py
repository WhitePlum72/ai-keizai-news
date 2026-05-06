"""
note自動投稿モジュール
Playwrightを使ってnoteに記事を自動投稿する
"""

import os
import asyncio
import logging
import sys
import openai
from datetime import datetime
from dotenv import load_dotenv
from playwright.async_api import async_playwright

dotenv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
load_dotenv(dotenv_path)

LOG_DIR = "logs"
NOTE_EMAIL = os.getenv("NOTE_EMAIL")
NOTE_PASSWORD = os.getenv("NOTE_PASSWORD")
ARTICLES_DIR = "astro-site/src/content/articles"
QWEN_BASE_URL = "http://localhost:8080/v1"
QWEN_MODEL = "Qwen3.6-27B-UD-Q4_K_XL.gguf"


def setup_logger():
    logger = logging.getLogger("note_poster")
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


def get_latest_digest():
    """最新のまとめ記事を取得"""
    today = datetime.now().strftime("%Y-%m-%d")
    filepath = os.path.join(ARTICLES_DIR, f"{today}-digest.md")

    if not os.path.exists(filepath):
        logger.warning(f"まとめ記事が見つかりません: {filepath}")
        return None, None

    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    title = ""
    body_lines = []
    in_frontmatter = False
    frontmatter_done = False
    lines = content.splitlines()

    for i, line in enumerate(lines):
        if i == 0 and line == "---":
            in_frontmatter = True
            continue
        if in_frontmatter and line == "---":
            in_frontmatter = False
            frontmatter_done = True
            continue
        if in_frontmatter:
            if line.startswith("title:"):
                title = line.replace("title:", "").strip().strip('"')
        if frontmatter_done:
            body_lines.append(line)

    body = "\n".join(body_lines).strip()
    return title, body


def generate_hashtags(body):
    """記事内容からハッシュタグを生成"""
    try:
        client = openai.OpenAI(base_url=QWEN_BASE_URL, api_key="dummy")
        res = client.chat.completions.create(
            model=QWEN_MODEL,
            messages=[{"role": "user", "content": f"以下の記事に合うハッシュタグを3つ生成してください。出力形式は「#タグ1 #タグ2 #タグ3」のみ。説明不要。\n\n{body[:500]}"}],
            max_tokens=50,
            extra_body={"chat_template_kwargs": {"enable_thinking": False}},
        )
        dynamic_tags = res.choices[0].message.content.strip()
    except Exception as e:
        logger.warning(f"ハッシュタグ生成失敗: {e}")
        dynamic_tags = "#人工知能 #テクノロジー #OpenAI"

    return f"#AI #AI経済新聞 {dynamic_tags}"


async def post_to_note(title, body):
    """Playwrightでnoteに投稿"""
    session_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "note_session")

    async with async_playwright() as p:
        browser = await p.chromium.launch_persistent_context(
            session_path,
            headless=False,
        )
        page = await browser.new_page()

        try:
            # セッション確認
            await page.goto("https://note.com")
            await page.wait_for_load_state("networkidle")
            await page.wait_for_timeout(2000)

            # ログインチェック
            if "login" in page.url or await page.query_selector('a[href="/login"]'):
                logger.info("ログインが必要です。手動でログインしてください...")
                await page.goto("https://note.com/login")
                await page.wait_for_url("https://note.com/", timeout=120000)
                logger.info("ログイン完了")

            # 新規記事作成
            logger.info("新規記事を作成中...")
            await page.goto("https://note.com/notes/new")
            await page.wait_for_load_state("networkidle")
            await page.wait_for_timeout(3000)

            # タイトル入力
            await page.click('.EditorTitle__Input, [placeholder="記事タイトル"], .title-input')
            await page.keyboard.type(title)
            await page.wait_for_timeout(500)

            # 本文入力
            await page.click('.ProseMirror, .editor-body, [contenteditable="true"]')
            await page.wait_for_timeout(500)

            for line in body.splitlines():
                if line.startswith("## "):
                    # h2見出しとして入力
                    heading_text = line.replace("## ", "")
                    await page.keyboard.press("Enter")
                    await page.wait_for_timeout(200)
                    await page.keyboard.press("Control+Alt+2")
                    await page.wait_for_timeout(200)
                    await page.keyboard.type(heading_text)
                    await page.keyboard.press("Enter")
                    await page.keyboard.press("Control+Alt+0")
                    await page.wait_for_timeout(200)
                elif line.strip() == "":
                    await page.keyboard.press("Enter")
                    await page.wait_for_timeout(100)
                else:
                    await page.keyboard.type(line)
                    await page.keyboard.press("Enter")
                    await page.wait_for_timeout(100)

            # ハッシュタグを追加
            await page.keyboard.press("Enter")
            await page.keyboard.press("Enter")
            hashtags = generate_hashtags(body)
            await page.keyboard.type(hashtags)
            logger.info(f"ハッシュタグ追加: {hashtags}")
            await page.wait_for_timeout(1000)

            # 公開ボタン
            logger.info("記事を公開中...")
            await page.click('button:has-text("公開")')
            await page.wait_for_timeout(3000)

            for selector in [
                'button:has-text("公開する")',
                'button:has-text("投稿する")',
                'button:has-text("無料公開")',
                'button:has-text("送信")',
                '.o-notePublishModal button[type="submit"]',
                'button[data-type="publish"]',
            ]:
                try:
                    btn = await page.query_selector(selector)
                    if btn:
                        await btn.click()
                        logger.info(f"公開ボタンをクリック: {selector}")
                        break
                except:
                    continue

            await page.wait_for_load_state("networkidle")
            await page.wait_for_timeout(3000)
            logger.info(f"note投稿完了: {title}")

        except Exception as e:
            logger.error(f"note投稿エラー: {e}")
            await page.screenshot(path="logs/note_error.png")
            raise

        finally:
            await browser.close()


async def main():
    logger.info("note自動投稿を開始します")

    if not NOTE_EMAIL or not NOTE_PASSWORD:
        logger.error(".envにNOTE_EMAILとNOTE_PASSWORDを設定してください")
        return

    title, body = get_latest_digest()

    if not title:
        logger.warning("投稿する記事がありません")
        return

    logger.info(f"投稿記事: {title}")
    await post_to_note(title, body)


if __name__ == "__main__":
    asyncio.run(main())
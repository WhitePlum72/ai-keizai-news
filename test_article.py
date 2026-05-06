"""
記事生成テスト
QwenとGeminiで同じ記事を生成して品質を比較する
"""

import requests
import time
from deep_translator import GoogleTranslator
from bs4 import BeautifulSoup
import openai

# ========== 設定 ==========
QWEN_BASE_URL = "http://localhost:8080/v1"
QWEN_MODEL = "Qwen3.6-27B-UD-Q4_K_XL.gguf"
GEMINI_API_KEY = "AIzaSyBJs39iH7alq8Hwx8NO9qQV4OQnKV5hSmI"  # 後で設定

# テスト対象のURL（OpenAIの最新記事）
TEST_URL = "https://venturebeat.com/technology/the-creator-of-claude-code-just-revealed-his-workflow-and-developers-are"

# ========== 本文取得 ==========
def fetch_body(url):
    headers = {"User-Agent": "Mozilla/5.0"}
    res = requests.get(url, headers=headers, timeout=10)
    soup = BeautifulSoup(res.text, 'html.parser')
    for tag in soup(['script', 'style', 'nav', 'header', 'footer', 'aside']):
        tag.decompose()
    for sel in ['article', '[class*="article-body"]', '[class*="post-body"]', 'main']:
        el = soup.select_one(sel)
        if el:
            text = el.get_text(separator='\n', strip=True)
            if len(text) > 200:
                return text[:10000]  # 10000文字に変更
    paragraphs = soup.find_all('p')
    return '\n'.join(p.get_text(strip=True) for p in paragraphs if len(p.get_text(strip=True)) > 50)[:10000]

# ========== 翻訳 ==========
def translate(text):
    chunks = []
    while text:
        chunk = text[:4500]
        if len(text) > 4500:
            last_nl = chunk.rfind('\n')
            if last_nl > 2000:
                chunk = text[:last_nl]
        chunks.append(chunk)
        text = text[len(chunk):]

    results = []
    for chunk in chunks:
        try:
            r = GoogleTranslator(source='en', target='ja').translate(chunk)
            results.append(r or "")
            time.sleep(0.5)
        except:
            results.append(chunk)
    return '\n'.join(results)

# ========== 記事生成プロンプト ==========
PROMPT_TEMPLATE = """あなたはAI専門のSEOライターです。
以下の情報をもとに、Googleで上位表示されやすい日本語ニュース記事を書いてください。

【元記事の内容】
{content}

【出力形式】
以下の形式で書いてください。

## SEOタイトル
（32文字以内・主要キーワードを含む・クリックしたくなるタイトル）

## メタディスクリプション
（120文字以内・記事の要点を含む・検索結果に表示される説明文）

## リード文
（150文字程度・記事全体の要点を伝える・主要キーワードを自然に含める）

## 背景
### （背景の見出し）
（この出来事の背景・経緯を200文字程度で解説）

## 詳細
### （詳細の見出し）
（具体的な内容・数字・事実を300文字程度で解説）

## 日本への影響
### 日本のAI業界への影響
（日本企業・ユーザーへの影響を150文字程度で解説）

## まとめ
（100文字程度・記事全体を締める・今後の展望を含める）

【SEOルール】
- タイトルに主要キーワードを必ず含める
- 見出し（##・###）を適切に使う
- です・ます調で書く
- 数字・固有名詞は正確に記載する
- 誇張せず事実のみ記載する
- 出力は記事本文のみ（前置き不要）"""

# ========== Qwenで生成 ==========
def generate_with_qwen(content):
    print("\n【Qwen】記事生成中...")
    client = openai.OpenAI(base_url=QWEN_BASE_URL, api_key="dummy")
    response = client.chat.completions.create(
        model=QWEN_MODEL,
        messages=[
            {"role": "user", "content": PROMPT_TEMPLATE.format(content=content)}
        ],
        max_tokens=1000,
        temperature=0.7,
        extra_body={"chat_template_kwargs": {"enable_thinking": False}}
    )
    return response.choices[0].message.content

# ========== Geminiで生成 ==========
def generate_with_gemini(content):
    if not GEMINI_API_KEY:
        return "GeminiのAPIキーが設定されていません"
    print("\n【Gemini】記事生成中...")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"
    payload = {
        "contents": [{"parts": [{"text": PROMPT_TEMPLATE.format(content=content)}]}]
    }
    res = requests.post(url, json=payload, timeout=30)
    data = res.json()
    try:
        return data['candidates'][0]['content']['parts'][0]['text']
    except:
        return f"エラー: {data}"

# ========== メイン ==========
def main():
    print("=" * 60)
    print("記事生成品質比較テスト")
    print("=" * 60)

    print(f"\nURL: {TEST_URL}")
    print("本文を取得中...")
    body = fetch_body(TEST_URL)
    print(f"取得文字数: {len(body)}文字")

    print("翻訳中...")
    translated = translate(body)
    print(f"翻訳文字数: {len(translated)}文字")

    print("\n翻訳結果（冒頭300文字）:")
    print("-" * 40)
    print(translated[:300])
    print("-" * 40)

    # Qwenで生成
    qwen_article = generate_with_qwen(translated)
    print("\n" + "=" * 60)
    print("【Qwen生成記事】")
    print("=" * 60)
    print(qwen_article)

    # Geminiで生成（APIキーがある場合のみ）
    if GEMINI_API_KEY:
        gemini_article = generate_with_gemini(translated)
        print("\n" + "=" * 60)
        print("【Gemini生成記事】")
        print("=" * 60)
        print(gemini_article)

    print("\n完了！")

if __name__ == "__main__":
    main()
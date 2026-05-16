"""
翻訳・記事生成モジュール（DeepSeek公式API対応版）
- platform.deepseek.com のAPIを使用
- thinking無効化でトークン節約
- 429リトライ・指数バックオフ対応
- scorer.py向けのGoogle翻訳（translate_text）は引き続き使用
"""

import sqlite3
import logging
import os
import sys
import re
import time
import requests
import json
from datetime import datetime

try:
    from dotenv import load_dotenv
    load_dotenv(dotenv_path='.env', override=True)
except ImportError:
    pass

DB_PATH = "data/articles.db"
LOG_DIR = "logs"

DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY")
DEEPSEEK_URL     = "https://api.deepseek.com/chat/completions"
DEEPSEEK_MODEL   = "deepseek-v4-pro"

# 記事間の待機秒数（レートリミット対策）
API_INTERVAL = 10

LABEL_PREFIX_RE     = re.compile(r'^\s*(?:[#>*\-]+\s*)?(?:見出し|本文)\s*[:：]\s*')
MARKDOWN_HEADING_RE = re.compile(r'^\s*#+\s*')


# ========================
# ロガー
# ========================
def setup_logger():
    logger = logging.getLogger("translator")
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
# DB
# ========================
def init_summaries_table():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS summaries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            article_id INTEGER UNIQUE,
            title_ja TEXT,
            summary_ja TEXT,
            tweet_text TEXT,
            category TEXT,
            meta_description TEXT,
            summary_points_json TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    for table, column, col_type in [
        ("summaries", "meta_description", "TEXT"),
        ("summaries", "summary_points_json", "TEXT"),
        ("articles", "summary_points_json", "TEXT"),
    ]:
        try:
            cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")
        except Exception:
            pass
    conn.commit()
    conn.close()


def get_articles_to_translate():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT a.id, a.title, a.summary, a.source, a.source_type, a.url
        FROM articles a
        LEFT JOIN summaries s ON a.id = s.article_id
        WHERE s.article_id IS NULL
        ORDER BY a.buzz_score DESC
        LIMIT 10
    """)
    rows = cursor.fetchall()
    conn.close()
    return rows


def save_summary(article_id, title_ja, summary_ja, tweet_text, category,
                 meta_description="", article_slug="", category_slug="",
                 entities: dict = None, summary_points=None):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    entities = entities or {}
    summary_points = normalize_summary_points(summary_points or [], meta_description)
    topics_json   = json.dumps(entities.get("topics",    []), ensure_ascii=False)
    companies_json = json.dumps(entities.get("companies", []), ensure_ascii=False)
    persons_json  = json.dumps(entities.get("persons",   []), ensure_ascii=False)
    tags_json     = json.dumps(entities.get("tags",      []), ensure_ascii=False)
    summary_points_json = json.dumps(summary_points, ensure_ascii=False)

    primary_topic   = entities.get("topics",    [""])[0] if entities.get("topics")    else ""
    primary_company = entities.get("companies", [""])[0] if entities.get("companies") else ""
    primary_person  = entities.get("persons",   [""])[0] if entities.get("persons")   else ""

    cursor.execute("""
        INSERT OR REPLACE INTO summaries
            (article_id, title_ja, summary_ja, tweet_text, category,
             meta_description, summary_points_json, article_slug, category_slug, slug_en,
             topics_json, companies_json, persons_json, tags_json)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (article_id, title_ja, summary_ja, tweet_text, category,
          meta_description, summary_points_json, article_slug, category_slug, article_slug,
          topics_json, companies_json, persons_json, tags_json))

    cursor.execute("""
        UPDATE articles
        SET processed      = 1,
            article_slug   = ?,
            category_slug  = ?,
            topics_json    = ?,
            companies_json = ?,
            summary_points_json = ?
        WHERE id = ?
    """, (article_slug, category_slug,
          topics_json, companies_json,
          summary_points_json,
          article_id))

    conn.commit()
    conn.close()
    return True


# ========================
# テキスト処理
# ========================
def clean_html(text):
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def remove_output_labels(text):
    if not text:
        return ""
    lines = []
    for line in text.split("\n"):
        line = LABEL_PREFIX_RE.sub("", line).strip()
        lines.append(line)
    return "\n".join(lines).strip()


def clean_title_line(text, fallback_title):
    line = remove_output_labels(text).splitlines()[0].strip()
    line = MARKDOWN_HEADING_RE.sub("", line).strip()
    return line or fallback_title


# ========================
# SEO系
# ========================
def make_meta_description(body):
    text = remove_output_labels(clean_html(body))
    sentences = re.split(r'。', text)
    desc = ""
    for s in sentences:
        if len(desc) + len(s) <= 140:
            desc += s + "。"
        else:
            break
    return desc.strip()


def normalize_description(text, fallback=""):
    text = remove_output_labels(clean_html(text or "")).strip()
    text = re.sub(r"\s+", " ", text)
    text = text.replace("。 。", "。")

    if not text and fallback:
        text = make_meta_description(fallback)

    if "。" in text:
        sentences = [s.strip() for s in text.split("。") if s.strip()]
        desc = ""
        for sentence in sentences:
            candidate = f"{desc}{sentence}。"
            if len(candidate) <= 140:
                desc = candidate
            else:
                break
        text = desc or (sentences[0].rstrip("。") + "。")
    else:
        text = text.rstrip("、，,. 　")
        if text and not text.endswith("。"):
            text += "。"

    bad_endings = ("で。", "により。", "として。", "ため。", "こと。")
    if len(text) < 80 or text.endswith(bad_endings):
        fallback_desc = make_meta_description(fallback)
        if fallback_desc and 50 <= len(fallback_desc) <= 160:
            text = fallback_desc

    if len(text) > 140:
        clipped = text[:140]
        if "。" in clipped:
            text = clipped[:clipped.rfind("。") + 1]
        else:
            text = clipped.rstrip("、，,. 　") + "。"

    return text.strip()


def make_lead(body):
    sentences = re.split(r'。', body)
    lead = ""
    for s in sentences:
        if len(lead) + len(s) <= 120:
            lead += s + "。"
        else:
            break
    return lead.strip()


def normalize_summary_points(points, fallback=""):
    cleaned = []
    fallback_text = remove_output_labels(clean_html(fallback or "")).strip()
    fallback_head = fallback_text[:45]
    for point in points or []:
        text = remove_output_labels(clean_html(str(point))).strip()
        text = re.sub(r"\s+", " ", text)
        parts = [p.strip() for p in re.split(r"。|．", text) if p.strip()]
        if len(parts) > 1 and len(text) > 100:
            candidates = parts
        else:
            candidates = [text]
        for candidate in candidates:
            if not candidate:
                continue
            candidate = candidate.rstrip("。") + "。"
            if fallback_head and fallback_head in candidate:
                continue
            if len(candidate) > 110:
                continue
            if candidate not in cleaned:
                cleaned.append(candidate)
            if len(cleaned) == 3:
                break
        if len(cleaned) == 3:
            break

    if len(cleaned) == 3:
        return cleaned

    structural_fallbacks = [
        "このニュースは、AI企業の競争がモデル性能だけでなく基盤確保にも左右されることを示している。",
        "GPU、クラウド、データ、販売網のどこを押さえるかが、今後のAI事業の差になりやすい。",
        "読者は単発の発表ではなく、供給網や提携関係がどう変わるかを見る必要がある。",
    ]
    for point in structural_fallbacks:
        if point not in cleaned:
            cleaned.append(point)
        if len(cleaned) == 3:
            break

    return cleaned[:3]


def parse_json_object(text):
    text = (text or "").strip()
    text = re.sub(r"^```(?:json)?", "", text).strip()
    text = re.sub(r"```$", "", text).strip()
    try:
        return json.loads(text)
    except Exception:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            return json.loads(match.group(0))
    return {}


# ========================
# 記事分解
# ========================
def split_generated_article(text, fallback_title):
    text  = remove_output_labels(text)
    lines = text.splitlines()
    title = clean_title_line(lines[0], fallback_title)
    body  = "\n".join(lines[1:]).strip()
    return {
        "title": title,
        "lead":  make_lead(body),
        "body":  body,
        "meta_description": make_meta_description(body),
    }


# ========================
# Google翻訳（scorer.py向けに残存）
# ========================
def translate_text(text):
    try:
        from deep_translator import GoogleTranslator
        return GoogleTranslator(source="en", target="ja").translate(text)
    except Exception:
        return text


# ========================
# DeepSeek API呼び出し（requests直接・thinking無効）
# ========================
def call_deepseek(prompt: str, max_tokens: int = 2500, max_retries: int = 5) -> str:
    """
    DeepSeek公式APIをrequestsで直接呼び出す。
    - thinking無効化でトークン節約
    - 429時は指数バックオフでリトライ
    """
    if not DEEPSEEK_API_KEY:
        raise EnvironmentError(
            "DEEPSEEK_API_KEY が設定されていません。\n"
            "PowerShellで: $env:DEEPSEEK_API_KEY='sk-...' を実行してください。"
        )

    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json",
    }
    body = {
        "model": DEEPSEEK_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "thinking": {"type": "disabled"},  # thinkingを無効化してトークン節約
    }

    for attempt in range(max_retries):
        try:
            res = requests.post(DEEPSEEK_URL, headers=headers, json=body, timeout=60)

            if res.status_code == 429:
                wait = 60 * (attempt + 1)
                logger.warning("429 レートリミット、%d秒待機 (%d/%d)", wait, attempt + 1, max_retries)
                time.sleep(wait)
                continue

            res.raise_for_status()
            data = res.json()
            return data["choices"][0]["message"]["content"].strip()

        except requests.exceptions.Timeout:
            logger.warning("タイムアウト (%d/%d)、リトライします", attempt + 1, max_retries)
            time.sleep(10)
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            logger.warning("APIエラー (%d/%d): %s", attempt + 1, max_retries, e)
            time.sleep(10)

    raise RuntimeError(f"APIリトライ上限({max_retries}回)に達しました")


# ========================
# 記事生成
# ========================
def generate_summary_points(title_ja: str, body_ja: str, meta_description: str) -> list[str]:
    prompt = f"""あなたはAI経済新聞の編集デスクです。
以下の記事から、記事冒頭に表示する「この記事の要約」を3項目だけ作成してください。
これは本文要約ではなく、読者が先に理解すべき構造的ポイントです。

【記事タイトル】
{title_ja}

【リード文】
{meta_description}

【本文】
{body_ja[:1800]}

【出力ルール】
- JSONのみを返す
- キーは summaryPoints
- summaryPoints は必ず3項目
- 日本語
- 各40〜90文字程度
- 単なる本文圧縮、事実説明、リード文の言い換えにしない
- 読者が「この記事を読む意味」を3秒で理解できる内容にする
- AI業界の供給網、企業関係、競争構造、投資、クラウド、GPU、モデル、エージェントの文脈を意識する
- 誇張しすぎない、断定しすぎない
- SNSで切り出しても意味が通る文にする
- 文末を完結させ、必ず句点「。」で終える
- リード文や本文冒頭と完全一致させない
- 元記事のリード文やdescriptionを貼り付けない
- 1項目だけの長文にしない
- SEO目的のキーワード詰め込みはしない

例:
{{
  "summaryPoints": [
    "この動きは、AI企業の競争がモデル性能だけでなく計算資源の確保に移っていることを示している。",
    "クラウド、GPU、データセンターを誰が押さえるかが、生成AIサービスの成長速度を左右し始めている。",
    "投資や提携のニュースは、資金調達ではなくAI産業の供給網再編として読む必要がある。"
  ]
}}"""
    raw = call_deepseek(prompt, max_tokens=500)
    data = parse_json_object(raw)
    return normalize_summary_points(data.get("summaryPoints", []), meta_description)


def generate_article(title_en: str, body_en: str) -> tuple[str, str, str, list[str]]:
    """
    Returns: (article_body, meta_description, slug_en, summary_points) のタプル
    """

    # ---- 記事本文生成 ----
    article_prompt = f"""あなたはITmedia・Bloomberg・日経クロステック級の日本人経済記者だ。
以下のニュース情報を元に、高品質な日本語経済ニュース記事を生成せよ。

【元記事情報】
タイトル: {title_en}
内容: {body_en[:3000]}

【絶対ルール】
・1行目: タイトル（32〜42文字）
  - 記事内の最も重要な数字・固有名詞を必ず含める
  - 読者の疑問や利益を示す（「なぜ」「〜の理由」「〜が変わる」等）
  - 【】「」などの記号・括弧は一切使わない
  - 誇張・煽り禁止
  - 重要ワードを前半に配置
・2行目: 空行
・本文1200〜1800文字
・だ・である調
・機械翻訳調禁止
・同じ論点の繰り返し禁止
・3〜4文ごとに改行を入れる
・金額は元の通貨のまま表記する（「1億ドル」「10億ドル」等）。日本円への換算は行わない

【本文構成】
1. 導入
    - この記事の意味を一言で説明する
    - 「誰が・何を・どれだけ・なぜ重要か」を含める
    - SEO用リード文と同一文にしない
2. ## 背景
   - なぜ重要なのかを説明する
3. ## 構造
   - 企業・技術・市場の関係性を説明する
4. ## 影響
   - AI業界全体への影響を説明する
5. ## 今後の論点
   - 次に注目すべき点を整理する

【見出しルール】
・各セクションの冒頭は必ず ## 見出し の形式にする
・見出しは体言止めまたは疑問形
・「## 何が起きたか」のような汎用的な見出しは禁止

【品質基準】
・数字にはソース感を付ける（「〇〇によると」「アナリスト予測では」等）
・「今後の動向に注目です」等の締めは禁止
・日本市場・日本企業への影響を必ず1箇所含める
・本文冒頭にdescriptionや短いリード文をそのまま貼り付けない
・AI経済新聞の方向性は、単なるニュース翻訳ではなく「AI業界の構造を日本語で分かりやすく読む」こと"""

    article_body = call_deepseek(article_prompt, max_tokens=2500)
    time.sleep(API_INTERVAL)

    # ---- meta description生成 ----
    meta_prompt = (
        "以下の記事から、SEO、OGP、記事一覧カードで使うdescriptionを1文で作成してください。\n"
        "ルール: 日本語、80〜140字程度、必ず文として完結、句点「。」で終える、"
        "「〜で」「〜により」「〜として」など途中で切れた形にしない、"
        "本文冒頭と完全一致させない、マークダウン禁止。\n\n"
        f"{article_body[:1200]}"
    )
    meta_description = normalize_description(call_deepseek(meta_prompt, max_tokens=220), article_body)
    time.sleep(API_INTERVAL)

    # ---- 記事冒頭の3点要約生成 ----
    parsed = split_generated_article(article_body, title_en)
    summary_points = generate_summary_points(parsed["title"], parsed["body"], meta_description)
    time.sleep(API_INTERVAL)

    # ---- slug生成 ----
    slug_prompt = f"""Generate a URL slug for this article.

Title: {title_en}

RULES:
- Output ONLY the slug, nothing else
- 3 to 5 words maximum
- Lowercase letters, numbers, hyphens only
- Include the most important company name or product name
- Include a strong action verb or key topic
- No stop words (a, the, in, of, for, and, to, with)
- Examples: openai-gpt5-reasoning-launch, nvidia-blackwell-datacenter-demand, anthropic-finance-agents-ipo

Slug:"""

    slug_raw = call_deepseek(slug_prompt, max_tokens=30)
    slug_en = re.sub(r'[^a-z0-9-]', '', slug_raw.lower().strip().replace(' ', '-'))[:80]

    return article_body, meta_description, slug_en, summary_points


# ========================
# X投稿文
# ========================
def make_tweet(title: str, body: str, category: str) -> str:
    prefix = f"【{category}】"
    lead   = make_lead(body)
    suffix = " #AI #LLM"
    text   = f"{prefix}{title}\n{lead}"
    return text[:140 - len(suffix)] + suffix


# ========================
# カテゴリ分類
# ========================
# translator.py の SOURCE_TYPE_TO_CATEGORY を差し替え
SOURCE_TYPE_TO_CATEGORY = {
    "model":         "モデル",
    "business":      "ビジネス",
    "research":      "研究",
    "stock":         "マーケット",
    "arxiv":         "研究",
    "hn":            "ビジネス",
    "official_blog": "モデル",
    "gov_jp":        "政策",
    "ir_tdnet":      "マーケット",
    "rss":           "ビジネス",
    "media":         "ビジネス",
}
CATEGORY_TO_SLUG = {
    "モデル":     "model",
    "ビジネス":   "business",
    "研究":       "research",
    "マーケット": "markets",
    "インフラ":   "infrastructure",
    "政策":       "policy",
    "プロダクト": "products",
    "AI":         "business",
    "AI関連株":   "markets",
    "AIモデル":   "model",
    "ツール":     "products",
}

def get_category(source_type: str) -> str:
    return SOURCE_TYPE_TO_CATEGORY.get(source_type, "ビジネス")

def get_category_slug(source_type: str, category: str = "") -> str:
    if category and category in CATEGORY_TO_SLUG:
        return CATEGORY_TO_SLUG[category]
    cat = SOURCE_TYPE_TO_CATEGORY.get(source_type, "ビジネス")
    return CATEGORY_TO_SLUG.get(cat, "business")

# ========================
# Topic・Company・Tag 抽出用定数
# ========================
KNOWN_COMPANIES = {
    "openai", "anthropic", "google", "deepmind", "microsoft",
    "meta", "apple", "amazon", "nvidia", "amd", "intel",
    "tsmc", "broadcom", "arm", "qualcomm", "xai",
    "mistral", "cohere", "perplexity", "huggingface",
    "databricks", "snowflake", "palantir", "servicenow",
    "salesforce", "oracle", "ibm", "samsung", "softbank",
    "ntt", "kddi", "fujitsu", "nec", "sony", "toyota",
    "preferred networks", "sakura internet",
}

KNOWN_TOPICS = {
    "gpt-5", "gpt-4", "claude", "gemini", "llama",
    "deepseek", "mistral", "qwen", "grok",
    "agents", "ai-agents", "coding-agent",
    "gpu", "blackwell", "hopper", "h100", "h200",
    "datacenter", "semiconductor",
    "reasoning", "multimodal", "rag",
    "agi", "alignment", "safety",
    "llm", "open-source-ai",
}

KNOWN_PERSONS = {
    "sam altman", "elon musk", "jensen huang",
    "sundar pichai", "satya nadella", "mark zuckerberg",
    "demis hassabis", "dario amodei", "yann lecun",
    "greg brockman", "ilya sutskever", "tim cook",
}

TOPIC_KEYWORDS = {
    "openai":        ["openai", "chatgpt", "gpt"],
    "nvidia":        ["nvidia", "blackwell", "h100", "h200", "cuda", "nvlink"],
    "anthropic":     ["anthropic", "claude"],
    "google":        ["google", "gemini", "deepmind"],
    "microsoft":     ["microsoft", "copilot", "azure"],
    "meta":          ["meta", "llama"],
    "amd":           ["amd", "radeon", "instinct"],
    "amazon":        ["amazon", "aws", "bedrock"],
    "llm":           ["llm", "language model", "foundation model"],
    "reasoning":     ["reasoning", "chain of thought", "推論"],
    "agents":        ["agent", "エージェント", "autonomous", "agentic"],
    "gpu":           ["gpu", "グラフィックス", "graphics card"],
    "datacenter":    ["datacenter", "data center", "データセンター"],
    "semiconductor": ["semiconductor", "半導体", "chip", "チップ"],
    "agi":           ["agi", "artificial general intelligence", "汎用人工知能"],
    "multimodal":    ["multimodal", "マルチモーダル"],
    "coding-agent":  ["coding agent", "code generation", "コーディング", "copilot"],
}

CATEGORY_RULES = [
    (["gpu", "半導体", "データセンター", "data center", "chip", "semiconductor",
      "blackwell", "h100", "h200", "cuda", "nvlink", "電力", "inference chip",
      "ai server", "コンピューティング", "computing"], "インフラ"),
    (["株", "決算", "ipo", "投資", "valuation", "earnings", "revenue",
      "stock", "shares", "funding", "raises", "billion", "trillion",
      "市場", "上場", "時価総額", "資金調達"], "マーケット"),
    (["規制", "法律", "政策", "policy", "regulation", "安全", "safety",
      "ai act", "governance", "倫理", "ethics", "government", "官公庁",
      "経産省", "デジタル庁", "congress", "senate"], "政策"),
    (["論文", "arxiv", "research", "benchmark", "ベンチマーク",
      "leaderboard", "evaluation", "学術", "study", "paper",
      "reasoning", "alignment", "fine-tuning"], "研究"),
    (["api", "sdk", "ツール", "tool", "plugin", "extension",
      "開発者", "developer", "platform", "サービス開始", "launch",
      "copilot", "cursor", "agent framework", "workflow"], "プロダクト"),
    (["gpt", "claude", "gemini", "llama", "llm", "language model",
      "モデル", "model", "multimodal", "diffusion", "text to",
      "image generation", "voice ai", "foundation model",
      "open source model", "weights", "release"], "モデル"),
]

def classify_category_by_rules(title_en: str, title_ja: str, body: str = "") -> str:
    text = f"{title_en} {title_ja} {body[:300]}".lower()
    for keywords, category in CATEGORY_RULES:
        if any(kw in text for kw in keywords):
            return category
    return "ビジネス"


def extract_entities(title_en: str, title_ja: str, body: str) -> dict:
    import json
    text = f"{title_en} {title_ja} {body[:1000]}".lower()

    companies = sorted([c for c in KNOWN_COMPANIES if c in text])

    topics = []
    for topic_slug, keywords in TOPIC_KEYWORDS.items():
        if any(kw in text for kw in keywords):
            topics.append(topic_slug)
    topics = sorted(set(topics))

    persons = sorted([p for p in KNOWN_PERSONS if p in text])

    tags = list(topics)
    if "billion" in text or "trillion" in text or "funding" in text:
        tags.append("funding")
    if "ipo" in text or "上場" in text:
        tags.append("ipo")
    if "acquisition" in text or "買収" in text:
        tags.append("acquisition")
    if "regulation" in text or "規制" in text:
        tags.append("regulation")
    tags = sorted(set(tags))

    return {
        "companies": companies,
        "topics":    topics,
        "persons":   persons,
        "tags":      tags,
    }


# ========================
# メイン
# ========================
def translate_all():
    init_summaries_table()
    articles = get_articles_to_translate()

    if not articles:
        logger.info("翻訳対象の記事がありません。")
        return

    logger.info("翻訳開始: %d件", len(articles))

    for i, a in enumerate(articles):
        article_id, title, summary, source, source_type, url = a

        try:
            generated, meta_description, slug_en, summary_points = generate_article(title, summary)
            data = split_generated_article(generated, title)
            data["meta_description"] = meta_description

            # カテゴリをルールベースで判定
            category      = classify_category_by_rules(title, data["title"], data["body"])
            category_slug = get_category_slug("", category)

            # entities抽出
            entities = extract_entities(title, data["title"], data["body"])

            tweet = make_tweet(data["title"], data["body"], category)

            save_summary(
                article_id,
                data["title"],
                data["body"],
                tweet,
                category,
                data["meta_description"],
                article_slug=slug_en,
                category_slug=category_slug,
                entities=entities,
                summary_points=summary_points,
            )

            logger.info(
                "完了 [id=%d] cat=%s topics=%s: %s",
                article_id, category,
                entities.get("topics", [])[:3],
                data["title"]
            )

            if i < len(articles) - 1:
                time.sleep(API_INTERVAL)

        except Exception as e:
            logger.error("失敗 [id=%d]: %s", article_id, e)
            continue


if __name__ == "__main__":
    translate_all()



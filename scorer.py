import sqlite3
from datetime import datetime, timezone
from deep_translator import GoogleTranslator
from difflib import SequenceMatcher

DB_PATH = "data/articles.db"

SOURCE_AUTHORITY = {
    "bloomberg":     10,
    "reuters":       10,
    "wsj":           10,
    "ft.com":         9,
    "marketwatch":    8,
    "yahoofinance":   7,
    "seekingalpha":   6,
    "techcrunch":     7,
    "venturebeat":    7,
    "the-decoder":    7,
    "theverge":       6,
    "wired":          6,
    "technologyreview": 6,
    "artificialintelligence-news": 6,
    "openai":         9,
    "anthropic":      9,
    "googleblog":     8,
    "microsoft":      8,
    "meta":           7,
    "nvidia":         8,
    "aws":            7,
    "arxiv":          5,
    "bair":           4,
    "huggingface":    6,
}

ECONOMIC_KEYWORDS = {
    "billion":        6,
    "trillion":       8,
    "million":        3,
    "billion dollar": 7,
    "acquisition":    6,
    "merger":         6,
    "ipo":            6,
    "funding":        5,
    "raises":         5,
    "investment":     4,
    "valuation":      5,
    "deal":           4,
    "earnings":       5,
    "revenue":        4,
    "profit":         4,
    "quarterly":      3,
    "market share":   4,
    "stock":          3,
    "shares":         3,
    "lawsuit":        6,
    "settlement":     5,
    "fine":           5,
    "ban":            5,
    "antitrust":      6,
    "regulation":     4,
    "penalty":        5,
}

AI_TOPIC_KEYWORDS = {
    "gpt":            5,
    "claude":         5,
    "gemini":         5,
    "llama":          4,
    "grok":           4,
    "release":        3,
    "open-source":    4,
    "llm":            3,
    "agent":          4,
    "agi":            6,
    "breakthrough":   5,
    "multimodal":     4,
    "autonomous":     4,
    "robotics":       4,
    "healthcare":     3,
    "drug":           3,
    "self-driving":   4,
    "copilot":        3,
}

COMPANY_TIER = {
    "nvidia":         15,
    "openai":         13,
    "anthropic":      12,
    "microsoft":      10,
    "google":         10,
    "alphabet":       10,
    "amazon":          9,
    "meta":            9,
    "apple":           9,
    "tesla":           8,
    "tsmc":            8,
    "arm":             7,
    "amd":             7,
    "intel":           6,
    "qualcomm":        6,
    "broadcom":        6,
    "palantir":        7,
    "salesforce":      5,
    "servicenow":      5,
    "snowflake":       5,
    "databricks":      5,
    "xai":             7,
    "mistral":         5,
    "cohere":          4,
    "perplexity":      5,
    "cursor":          4,
}

COMPANY_LIMITS = {
    "openai":     2,
    "google":     2,
    "alphabet":   2,
    "microsoft":  2,
    "anthropic":  2,
    "meta":       2,
    "nvidia":     2,
    "apple":      1,
    "amazon":     1,
    "tesla":      1,
}

PRIMARY_SOURCE_RULES = {
    "openai.com/index":           (40, "official_blog",  "公式発表",       True),
    "openai.com/blog":            (40, "official_blog",  "公式発表",       True),
    "openai.com/research":        (40, "official_blog",  "公式発表",       True),
    "anthropic.com/news":         (40, "official_blog",  "公式発表",       True),
    "anthropic.com/research":     (40, "official_blog",  "公式発表",       True),
    "deepmind.google":            (40, "official_blog",  "公式発表",       True),
    "blog.google":                (38, "official_blog",  "公式発表",       True),
    "nvidia.com/en-us/blog":      (40, "official_blog",  "公式発表",       True),
    "blogs.nvidia.com":           (40, "official_blog",  "公式発表",       True),
    "blogs.microsoft.com":        (38, "official_blog",  "公式発表",       True),
    "ai.meta.com/blog":           (38, "official_blog",  "公式発表",       True),
    "huggingface.co/blog":        (30, "official_blog",  "公式発表",       True),
    "mistral.ai/news":            (35, "official_blog",  "公式発表",       True),
    "xai.com":                    (38, "official_blog",  "公式発表",       True),
    "arxiv.org/abs":              (35, "arxiv",          "論文",           True),
    "arxiv.org/pdf":              (35, "arxiv",          "論文",           True),
    "openreview.net":             (30, "arxiv",          "論文",           True),
    "sec.gov/Archives":           (50, "sec_filing",     "SEC",            True),
    "sec.gov/cgi-bin":            (50, "sec_filing",     "SEC",            True),
    "github.com/releases":        (30, "github_release", "GitHub",         True),
    "github.com/blob/main/CHANGELOG": (28, "github_release", "GitHub",    True),
    "meti.go.jp":                 (50, "gov_jp",         "政府資料",       True),
    "soumu.go.jp":                (50, "gov_jp",         "政府資料",       True),
    "digital.go.jp":              (50, "gov_jp",         "政府資料",       True),
    "cao.go.jp":                  (48, "gov_jp",         "政府資料",       True),
    "nedo.go.jp":                 (48, "gov_jp",         "政府資料",       True),
    "ipa.go.jp":                  (48, "gov_jp",         "政府資料",       True),
    "mof.go.jp":                  (48, "gov_jp",         "政府資料",       True),
    "tdnet.info":                 (48, "ir_tdnet",       "適時開示",       True),
    "release.tdnet.info":         (48, "ir_tdnet",       "適時開示",       True),
    "edinet-fsa.go.jp":           (48, "ir_tdnet",       "EDINET",         True),
    "riken.jp":                   (40, "research_jp",    "研究機関",       True),
    "aist.go.jp":                 (40, "research_jp",    "研究機関",       True),
    "nii.ac.jp":                  (38, "research_jp",    "研究機関",       True),
    "preferred.jp":               (40, "official_jp",    "企業IR",         True),
    "softbank.co.jp/corp":        (45, "official_jp",    "企業IR",         True),
    "ntt.com/about":              (45, "official_jp",    "企業IR",         True),
    "kddi.com/corporate":         (45, "official_jp",    "企業IR",         True),
    "sakura.ad.jp/news":          (40, "official_jp",    "企業IR",         True),
    "prtimes.jp":                 (20, "press_release",  "プレスリリース", False),
    "reuters.com":                (15, "media",          None,             False),
    "bloomberg.com":              (15, "media",          None,             False),
    "nikkei.com":                 (12, "media_jp",       None,             False),
    "techcrunch.com":             (10, "media",          None,             False),
    "theverge.com":               (10, "media",          None,             False),
    "itmedia.co.jp":              (8,  "media_jp",       None,             False),
}

TIER1_COMPANIES = {
    "openai", "nvidia", "anthropic", "google",
    "microsoft", "meta", "amazon", "apple", "xai", "tsmc"
}

def get_recency_multiplier(recency_score: float) -> float:

    if recency_score >= 12:
        return 1.4

    if recency_score >= 10:
        return 1.2

    if recency_score >= 7:
        return 1.0

    if recency_score >= 4:
        return 0.7

    if recency_score >= 2:
        return 0.4

    return 0.15
AI_RELEVANCE_KEYWORDS = {

    # =====================================================
    # Core AI
    # =====================================================
    "artificial intelligence", "machine learning",
    "deep learning", "neural network", "transformer",
    "foundation model", "multimodal", "reasoning",
    "ai inference", "ai training", "fine tuning",
    "rag", "synthetic data", "ai alignment",
    "distillation", "embedding",

    # =====================================================
    # LLM / Models
    # =====================================================
    "llm", "language model", "gpt", "chatgpt",
    "claude", "gemini", "llama", "mistral",
    "deepseek", "qwen", "gemma", "mixtral",
    "command r", "grok",

    # =====================================================
    # Agent / Coding AI
    # =====================================================
    "ai agent", "autonomous agent",
    "coding agent", "code generation",
    "github copilot", "cursor ai", "windsurf",
    "devin", "replit", "lovable",
    "claude code",

    # =====================================================
    # Image / Video / Audio AI
    # =====================================================
    "diffusion model", "stable diffusion",
    "midjourney", "runway ml",
    "sora", "veo", "pika",
    "text to video", "image generation",
    "voice ai", "speech synthesis",
    "text to speech", "audio generation",

    # =====================================================
    # AI Companies
    # =====================================================
    "openai", "anthropic",
    "deepmind", "microsoft",
    "xai", "mistral ai", "cohere",
    "hugging face", "huggingface",
    "perplexity",
    "databricks",
    "palantir",

    # =====================================================
    # Hardware / Infrastructure
    # =====================================================
    "gpu", "ai chip", "semiconductor",
    "ai accelerator", "datacenter",
    "data center", "ai server",
    "blackwell", "hopper", "rubin",
    "h100", "h200", "b200", "gb200",
    "mi300", "cuda", "tensor core",
    "nvlink", "inference chip",
    "ai infrastructure",

    # =====================================================
    # Chip / Infra Companies
    # =====================================================
    "nvidia", "amd",
    "tsmc", "broadcom",
    "arm holdings", "arm chip",
    "qualcomm", "micron",
    "sk hynix", "supermicro",

    # =====================================================
    # Cloud / Platform
    # =====================================================
    "azure ai", "aws ai", "google cloud ai",
    "vertex ai", "amazon bedrock",
    "sagemaker", "oracle cloud",

    # =====================================================
    # Research
    # =====================================================
    "arxiv", "ai research",
    "ai benchmark", "leaderboard",
    "open source ai", "open weights",
    "ai evaluation",

    # =====================================================
    # Business / Finance（AI限定）
    # =====================================================
    "ai investment", "ai funding",
    "ai startup", "ai stock",
    "ai valuation", "ai ipo",
    "ai revenue", "ai earnings",
    "ai deal", "ai acquisition",

    # =====================================================
    # Robotics / Autonomous
    # =====================================================
    "robotics", "humanoid robot",
    "autonomous driving",
    "self driving", "ai robot",
    "tesla bot", "waymo",

    # =====================================================
    # Search / Browser
    # =====================================================
    "ai search", "ai browser",
    "perplexity ai",

    # =====================================================
    # Regulation
    # =====================================================
    "ai regulation", "ai act",
    "ai safety", "ai policy",
    "ai governance",

    # =====================================================
    # Japanese Keywords
    # =====================================================
    "生成ai", "生成 ai",
    "人工知能", "大規模言語モデル",
    "推論ai", "半導体",
    "データセンター",
    "aiエージェント",
    "マルチモーダル",
}
BLACKLIST_DOMAINS = {
    "finance.yahoo.com/markets/stocks",
    "investors.com",
    "seekingalpha.com/article",
    "fool.com",
    "benzinga.com",
    "zacks.com",
    "thestreet.com",
    "barrons.com",
}


def get_primary_source_info(url: str) -> tuple[int, str, str | None, bool]:
    if not url:
        return 5, "rss", None, False
    url_lower = url.lower()
    for domain, (score, stype, label, is_official) in PRIMARY_SOURCE_RULES.items():
        if domain in url_lower:
            return score, stype, label, is_official
    return 5, "rss", None, False


def is_tier1_official(url: str, text: str) -> bool:
    url_lower = (url or "").lower()
    for company in TIER1_COMPANIES:
        if company in url_lower and any(
            kw in url_lower for kw in ("blog", "news", "research", "release")
        ):
            return True
    return False


def get_source_authority(source: str) -> float:
    source_lower = (source or "").lower()
    for key, score in SOURCE_AUTHORITY.items():
        if key in source_lower:
            return score
    return 3


def get_economic_score(text: str) -> float:
    text_lower = text.lower()
    score = 0
    for kw, val in ECONOMIC_KEYWORDS.items():
        if kw in text_lower:
            score += val
    return min(score, 20)


def get_ai_topic_score(text: str) -> float:
    text_lower = text.lower()
    score = 0
    for kw, val in AI_TOPIC_KEYWORDS.items():
        if kw in text_lower:
            score += val
    return min(score, 15)


def get_company_score(text: str) -> tuple[float, str | None]:
    text_lower = text.lower()
    best_score = 0
    best_company = None
    for company, score in COMPANY_TIER.items():
        if company in text_lower and score > best_score:
            best_score = score
            best_company = company
    return min(best_score, 15), best_company


import math

def get_recency_score(published_at: str | None) -> float:

    if not published_at:
        return 2

    try:

        pub = datetime.fromisoformat(
            published_at.replace("Z", "+00:00")
        )

        if pub.tzinfo is None:
            pub = pub.replace(tzinfo=timezone.utc)

        hours_ago = (
            datetime.now(timezone.utc) - pub
        ).total_seconds() / 3600

        # ==========================
        # 超速報ブースト
        # ==========================
        if hours_ago <= 1:
            return 15

        if hours_ago <= 3:
            return 12

        # ==========================
        # 指数減衰
        # ==========================
        score = 10 * math.exp(-hours_ago / 16)

        # 最低値制限
        return max(score, 0)

    except Exception:
        return 2


def translate_title(title: str) -> str:
    try:
        return GoogleTranslator(source="en", target="ja").translate(title)
    except Exception:
        return title


def is_similar(title_ja: str, selected_titles_ja: list, threshold=0.75) -> bool:
    for existing in selected_titles_ja:
        if SequenceMatcher(None, title_ja, existing).ratio() >= threshold:
            return True
    return False


def calculate_scores():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, title, summary, source, source_type, published_at, url
        FROM articles
        WHERE processed = 0
        ORDER BY collected_at DESC
        LIMIT 200
    """)
    articles = cursor.fetchall()

    if not articles:
        print("スコアリング対象の記事がありません")
        conn.close()
        return

    scored = []
    for article_id, title, summary, source, source_type, published_at, url in articles:
        text = (title or '') + ' ' + (summary or '')
        text_lower = text.lower()
        url_lower = (url or '').lower()
        text_for_company = text + ' ' + (url or '')
        
        # ブラックリストドメインチェック
        if any(bl in url_lower for bl in BLACKLIST_DOMAINS):
            continue
# AI関連性フィルター（公式ソースは除外しない）
        primary_score_check, _, _, is_official_check = get_primary_source_info(url or '')
        if not is_official_check:
            title_lower_f   = (title or '').lower()
            summary_lower_f = (summary or '').lower()
            url_lower_f     = (url or '').lower()

            ai_score = 0
            for kw in AI_RELEVANCE_KEYWORDS:
                if kw in title_lower_f:
                    ai_score += 5
                if kw in url_lower_f:
                    ai_score += 3
                if kw in summary_lower_f:
                    ai_score += 1

            economic_score_f = get_economic_score(title_lower_f + ' ' + summary_lower_f)

            if not (
                ai_score >= 5
                or (ai_score >= 3 and economic_score_f >= 5)
            ):
                continue

        authority  = get_source_authority(source or source_type or "")
        recency    = get_recency_score(published_at)
        economic   = get_economic_score(text)
        ai_topic   = get_ai_topic_score(text)
        comp_score, company = get_company_score(text_for_company)

        buzz = (
            authority  * 2.5 +
            recency    * 2.5 +
            economic   * 1.0 +
            ai_topic   * 1.0 +
            comp_score * 1.0
        )

        primary_score, stype, label, is_official = get_primary_source_info(url or "")
        tier1_official = is_tier1_official(url or "", text)

        recency_mult = get_recency_multiplier(recency)
        effective_primary = primary_score * recency_mult
        buzz += effective_primary * 0.5

        scored.append((
            buzz, article_id, title, company,
            primary_score, stype, label, is_official, tier1_official
        ))

    scored.sort(reverse=True)

    selected = []
    selected_titles_ja = []
    company_counts = {c: 0 for c in COMPANY_LIMITS}

    for row in scored:
        buzz, article_id, title, company, \
        primary_score, stype, label, is_official, tier1_official = row

        if len(selected) >= 10:
            break

        limit_bonus = 1 if tier1_official else 0
        if company and company in COMPANY_LIMITS:
            if company_counts[company] >= COMPANY_LIMITS[company] + limit_bonus:
                continue

        title_ja = translate_title(title)
        sim_threshold = 0.85 if is_official else 0.75
        if is_similar(title_ja, selected_titles_ja, threshold=sim_threshold):
            print(f"類似記事スキップ: {title[:50]}")
            continue

        if company and company in COMPANY_LIMITS:
            company_counts[company] += 1

        selected.append(row)
        selected_titles_ja.append(title_ja)

    cursor.execute("UPDATE articles SET buzz_score = 0 WHERE processed = 0")
    for row in selected:
        buzz, article_id, title, company, \
        primary_score, stype, label, is_official, tier1_official = row

        cursor.execute("""
            UPDATE articles
            SET buzz_score           = ?,
                primary_source_score = ?,
                source_type          = ?,
                source_label         = ?,
                official_source      = ?
            WHERE id = ?
        """, (
            round(buzz, 2),
            primary_score,
            stype,
            label,
            1 if is_official else 0,
            article_id,
        ))

    conn.commit()
    conn.close()

    print(f"スコアリング完了: {len(selected)}件を選出")
    print("\n選出記事:")
    for row in selected:
        buzz, article_id, title, company, \
        primary_score, stype, label, is_official, _ = row
        tag = f"[{company}]" if company else ""
        src = f"[{label}]" if label else f"[{stype}]"
        print(f"  buzz={buzz:.1f} primary={primary_score} {src} {tag} {title[:50]}")


if __name__ == "__main__":
    calculate_scores()
import sqlite3
from datetime import datetime, timezone
from deep_translator import GoogleTranslator
from difflib import SequenceMatcher

DB_PATH = "data/articles.db"

# ソース権威性（満点10）
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
    "amazon":         9,
    "meta":           9,
    "apple":          9,
    "tesla":          8,
    "tsmc":           8,
    "arm":            7,
    "amd":            7,
    "intel":          6,
    "qualcomm":       6,
    "broadcom":       6,
    "palantir":       7,
    "salesforce":     5,
    "servicenow":     5,
    "snowflake":      5,
    "databricks":     5,
    "xai":            7,
    "mistral":        5,
    "cohere":         4,
    "perplexity":     5,
    "cursor":         4,
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

def get_recency_score(published_at: str | None) -> float:
    if not published_at:
        return 3
    try:
        pub = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
        if pub.tzinfo is None:
            pub = pub.replace(tzinfo=timezone.utc)
        hours_ago = (datetime.now(timezone.utc) - pub).total_seconds() / 3600
        if hours_ago <= 3:    return 10
        elif hours_ago <= 6:  return 8
        elif hours_ago <= 12: return 6
        elif hours_ago <= 24: return 4
        elif hours_ago <= 48: return 2
        else:                 return 0
    except Exception:
        return 3

def translate_title(title: str) -> str:
    """Google翻訳でタイトルを日本語に変換"""
    try:
        return GoogleTranslator(source="en", target="ja").translate(title)
    except Exception:
        return title

def is_similar(title_ja: str, selected_titles_ja: list, threshold=0.75) -> bool:
    """日本語タイトルの類似度チェック"""
    for existing in selected_titles_ja:
        ratio = SequenceMatcher(None, title_ja, existing).ratio()
        if ratio >= threshold:
            return True
    return False

def calculate_scores():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, title, summary, source, source_type, published_at
        FROM articles
        WHERE processed = 0
        LIMIT 200
    """)
    articles = cursor.fetchall()

    if not articles:
        print("スコアリング対象の記事がありません")
        conn.close()
        return

    # buzz_score計算
    scored = []
    for article_id, title, summary, source, source_type, published_at in articles:
        text = f"{title or ''} {summary or ''}"
        authority  = get_source_authority(source or source_type or "")
        recency    = get_recency_score(published_at)
        economic   = get_economic_score(text)
        ai_topic   = get_ai_topic_score(text)
        comp_score, company = get_company_score(text)
        buzz = (
            authority  * 2.0 +
            recency    * 2.0 +
            economic   * 1.0 +
            ai_topic   * 1.0 +
            comp_score * 1.0
        )
        scored.append((buzz, article_id, title, company))

    scored.sort(reverse=True)

    # 上位10件を選出（企業制限 + 類似記事除外）
    selected = []
    selected_titles_ja = []
    company_counts = {c: 0 for c in COMPANY_LIMITS}

    for buzz, article_id, title, company in scored:
        if len(selected) >= 10:
            break

        # 企業制限チェック
        if company and company in COMPANY_LIMITS:
            if company_counts[company] >= COMPANY_LIMITS[company]:
                continue

        # 類似記事チェック
        title_ja = translate_title(title)
        if is_similar(title_ja, selected_titles_ja):
            print(f"類似記事スキップ: {title[:50]}")
            continue

        # 選出確定
        if company and company in COMPANY_LIMITS:
            company_counts[company] += 1
        selected.append((buzz, article_id, title, company))
        selected_titles_ja.append(title_ja)

    # DB更新
    cursor.execute("UPDATE articles SET buzz_score = 0 WHERE processed = 0")
    for buzz, article_id, title, company in selected:
        cursor.execute(
            "UPDATE articles SET buzz_score = ? WHERE id = ?",
            (round(buzz, 2), article_id)
        )

    conn.commit()
    conn.close()

    print(f"スコアリング完了: {len(selected)}件を選出")
    print("\n選出記事:")
    for i, (buzz, article_id, title, company) in enumerate(selected, 1):
        tag = f"[{company}]" if company else ""
        print(f"{i}. [{buzz:.1f}] {tag} {title[:60]}")

if __name__ == "__main__":
    calculate_scores()
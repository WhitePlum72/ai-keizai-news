"""
RSSフィード収集モジュール
英語AIニュースを各RSSソースから取得し、SQLiteに保存する。
"""

import feedparser
import sqlite3
import logging
import os
import sys
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from difflib import SequenceMatcher
from typing import List, Dict

# ==================== 設定 ====================

RSS_SOURCES = {
    "openai": {
        "url": "https://openai.com/news/rss.xml",
        "type": "rss",
        "description": "OpenAI",
    },
    "huggingface": {
        "url": "https://huggingface.co/blog/feed.xml",
        "type": "rss",
        "description": "Hugging Face",
    },
    "techcrunch": {
        "url": "https://techcrunch.com/feed/",
        "type": "rss",
        "description": "TechCrunch",
    },
    "theverge_ai": {
        "url": "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml",
        "type": "rss",
        "description": "The Verge AI",
    },
    "venturebeat": {
        "url": "https://venturebeat.com/category/ai/feed/",
        "type": "rss",
        "description": "VentureBeat AI",
    },
    "wired_ai": {
        "url": "https://www.wired.com/feed/tag/ai/latest/rss",
        "type": "rss",
        "description": "Wired AI",
    },
    "mit_review": {
        "url": "https://www.technologyreview.com/feed/",
        "type": "rss",
        "description": "MIT Technology Review",
    },
    "bair": {
        "url": "https://bair.berkeley.edu/blog/feed.xml",
        "type": "rss",
        "description": "BAIR Blog",
    },
    "bloomberg": {
        "url": "https://feeds.bloomberg.com/technology/news.rss",
        "type": "rss",
        "description": "Bloomberg Technology",
    },
    "reuters": {
        "url": "https://www.reutersagency.com/feed/?best-topics=tech",
        "type": "rss",
        "description": "Reuters Technology",
    },
    "the_decoder": {
        "url": "https://the-decoder.com/feed/",
        "type": "rss",
        "description": "The Decoder",
    },
    "arxiv_cs_ai": {
        "url": "https://arxiv.org/rss/cs.AI",
        "type": "arxiv",
        "description": "arXiv CS.AI",
    },
    "arxiv_cs_cl": {
        "url": "https://arxiv.org/rss/cs.CL",
        "type": "arxiv",
        "description": "arXiv CS.CL",
    },
    "yahoo_finance_ai": {
        "url": "https://finance.yahoo.com/rss/topstories",
        "type": "rss",
        "description": "Yahoo Finance",
    },
    "seeking_alpha": {
        "url": "https://seekingalpha.com/feed.xml",
        "type": "rss",
        "description": "Seeking Alpha",
    },
    "marketwatch_tech": {
        "url": "https://feeds.marketwatch.com/marketwatch/technology/",
        "type": "rss",
        "description": "MarketWatch Tech",
    },
}

ARXIV_KEYWORDS = [
    "deep learning", "neural network", "transformer", "large language model",
    "llm", "reinforcement learning", "computer vision", "natural language processing",
    "generative ai", "diffusion", "gpt", "bert", "ai alignment", "machine learning",
]

DB_PATH = "data/articles.db"
LOG_DIR = "logs"
DUPLICATE_THRESHOLD = 0.85

# ==================== ログ設定 ====================

def setup_logger() -> logging.Logger:
    logger = logging.getLogger("collector")
    logger.setLevel(logging.DEBUG)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    logger.addHandler(console_handler)
    os.makedirs(LOG_DIR, exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")
    log_file = os.path.join(LOG_DIR, f"{today}.log")
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    logger.addHandler(file_handler)
    return logger

logger = setup_logger()

# ==================== DB操作 ====================

def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT UNIQUE NOT NULL,
            title TEXT NOT NULL,
            summary TEXT,
            source TEXT,
            source_type TEXT,
            author TEXT,
            published_at TEXT,
            score INTEGER DEFAULT 0,
            buzz_score REAL DEFAULT 0,
            collected_at TEXT DEFAULT CURRENT_TIMESTAMP,
            processed INTEGER DEFAULT 0,
            image_url TEXT DEFAULT ''
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_articles_url ON articles(url)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_articles_collected_at ON articles(collected_at)")
    conn.commit()
    conn.close()
    logger.info("データベースを初期化しました: %s", DB_PATH)

def is_duplicate(url: str, title: str) -> bool:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM articles WHERE url = ?", (url,))
    if cursor.fetchone()[0] > 0:
        conn.close()
        return True
    cursor.execute("SELECT title FROM articles WHERE processed = 0")
    rows = cursor.fetchall()
    conn.close()
    for row in rows:
        similarity = SequenceMatcher(None, title.lower(), row[0].lower()).ratio()
        if similarity >= DUPLICATE_THRESHOLD:
            return True
    return False

def fetch_ogp_image(url):
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Referer": "https://www.google.com/",
        }
        res = requests.get(url, headers=headers, timeout=5)
        soup = BeautifulSoup(res.text, 'html.parser')
        og_image = soup.find('meta', property='og:image')
        if og_image and og_image.get('content'):
            return og_image.get('content', '')
        tw_image = soup.find('meta', attrs={'name': 'twitter:image'})
        if tw_image and tw_image.get('content'):
            return tw_image.get('content', '')
    except Exception:
        pass
    return ''

def save_article(article):
    if is_duplicate(article["url"], article["title"]):
        logger.debug("重複記事をスキップ: %s", article["title"][:50])
        return False
    image_url = fetch_ogp_image(article["url"])
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO articles
            (url, title, summary, source, source_type, author, published_at, score, image_url)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            article["url"],
            article["title"],
            article.get("summary", ""),
            article.get("source", ""),
            article.get("source_type", ""),
            article.get("author", ""),
            article.get("published_at", ""),
            article.get("score", 0),
            image_url,
        ))
        conn.commit()
        logger.info("記事を保存: %s", article["title"][:50])
        return True
    except sqlite3.IntegrityError:
        logger.debug("重複URLをスキップ: %s", article["url"])
        return False
    finally:
        conn.close()

# ==================== RSSパース ====================

def fetch_rss_feed(source_key: str, source_info: Dict) -> List[Dict]:
    articles = []
    source_type = source_info["type"]
    url = source_info["url"]
    logger.info("RSS取得開始: %s (%s)", source_info["description"], url)
    try:
        feed = feedparser.parse(url)
        if source_type == "arxiv":
            articles = parse_arxiv_feed(feed, source_info)
        elif source_type == "hn":
            articles = parse_hn_feed(feed, source_info)
        else:
            articles = parse_generic_rss(feed, source_info)
        logger.info("RSS取得完了: %s - 記事数: %d", source_info["description"], len(articles))
    except Exception as e:
        logger.error("RSS取得エラー: %s - エラー: %s", source_info["description"], str(e))
    return articles

def fetch_anthropic_news():
    articles = []
    try:
        from playwright.sync_api import sync_playwright
        import re
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto("https://www.anthropic.com/news", timeout=30000)
            page.wait_for_load_state("networkidle")
            content = page.content()
            browser.close()
        links = re.findall(r'href="(/news/[^"]+)"', content)
        titles = re.findall(r'"heading":"([^"]{10,})"', content)
        seen = set()
        for i, path in enumerate(links[:20]):
            url = f"https://www.anthropic.com{path}"
            if url in seen:
                continue
            seen.add(url)
            title = titles[i] if i < len(titles) else path.split("/")[-1].replace("-", " ").title()
            articles.append({
                "url": url, "title": title, "summary": "",
                "source": "Anthropic", "source_type": "rss",
                "author": "", "published_at": "", "score": 0,
            })
        logger.info("Anthropicスクレイピング完了: %d件", len(articles))
    except Exception as e:
        logger.error("Anthropicスクレイピングエラー: %s", str(e))
    return articles

def parse_generic_rss(feed, source_info: Dict) -> List[Dict]:
    articles = []
    for entry in feed.entries[:30]:
        article = {
            "url": entry.get("link", ""),
            "title": entry.get("title", ""),
            "summary": entry.get("summary", entry.get("description", "")),
            "source": source_info["description"],
            "source_type": "rss",
            "author": entry.get("author", ""),
            "published_at": entry.get("published", ""),
            "score": 0,
        }
        if article["url"] and article["title"]:
            articles.append(article)
    return articles

HN_KEYWORDS = [
    'ai', 'ml', 'llm', 'gpt', 'model', 'language', 'neural', 'learning',
    'openai', 'anthropic', 'llama', 'agent', 'claude', 'gemini'
]

def parse_hn_feed(feed, source_info: Dict) -> List[Dict]:
    articles = []
    for entry in feed.entries:
        title = entry.get("title", "").lower()
        if not any(kw in title for kw in HN_KEYWORDS):
            continue
        article = {
            "url": entry.get("link", ""),
            "title": entry.get("title", ""),
            "summary": entry.get("summary", ""),
            "source": "Hacker News",
            "source_type": "hn",
            "author": entry.get("author", ""),
            "published_at": entry.get("published", ""),
            "score": 0,
        }
        if article["url"] and article["title"]:
            articles.append(article)
    return articles

def parse_arxiv_feed(feed, source_info: Dict) -> List[Dict]:
    articles = []
    for entry in feed.entries[:5]:
        url = ""
        for link in entry.get("links", []):
            if link.get("rel") == "alternate":
                url = link.get("href", "")
                break
        if not url:
            url = entry.get("id", "")
        article = {
            "url": url,
            "title": entry.get("title", ""),
            "summary": entry.get("summary", ""),
            "source": source_info["description"],
            "source_type": "arxiv",
            "author": ", ".join([a.get("name", "") for a in entry.get("authors", [])]),
            "published_at": entry.get("published", ""),
            "score": 0,
        }
        if article["url"] and article["title"]:
            articles.append(article)
    return articles

# ==================== メイン処理 ====================

def collect_all():
    logger.info("=" * 60)
    logger.info("RSS収集を開始しました")
    logger.info("=" * 60)
    init_db()
    total_collected = 0
    total_duplicates = 0

    for article in fetch_anthropic_news():
        if save_article(article):
            total_collected += 1
        else:
            total_duplicates += 1

    for source_key, source_info in RSS_SOURCES.items():
        articles = fetch_rss_feed(source_key, source_info)
        for article in articles:
            if save_article(article):
                total_collected += 1
            else:
                total_duplicates += 1

    logger.info("=" * 60)
    logger.info("RSS収集が完了しました")
    logger.info("新規収集: %d件", total_collected)
    logger.info("重複排除: %d件", total_duplicates)
    logger.info("=" * 60)
    return total_collected, total_duplicates

def main():
    try:
        collected, duplicates = collect_all()
        print(f"\n収集完了: 新規{collected}件, 重複{duplicates}件")
    except Exception as e:
        logger.error("収集処理でエラーが発生しました: %s", str(e))
        raise

if __name__ == "__main__":
    main()
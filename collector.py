"""
RSSフィード収集モジュール
英語AIニュースを各RSSソースから取得し、SQLiteに保存する。
"""

import feedparser
import sqlite3
import logging
import os
import re
import sys
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from difflib import SequenceMatcher
from typing import List, Dict
from urllib.parse import urljoin, urlparse

# ==================== 設定 ====================

# Primary-source-only feed set.
# The collector no longer depends on newspapers, wire services, reposts,
# or AI-news aggregation sites.
RSS_SOURCES = {
    # Official company blogs / newsrooms
    "openai_news": {
        "url": "https://openai.com/news/rss.xml",
        "type": "rss",
        "source_type": "official_blog",
        "description": "OpenAI News",
        "source_authority": 10,
    },
    "anthropic_news": {
        "url": "https://www.anthropic.com/rss.xml",
        "type": "rss",
        "source_type": "official_blog",
        "description": "Anthropic News",
        "source_authority": 10,
    },
    "google_ai_blog": {
        "url": "https://blog.google/technology/ai/rss/",
        "type": "rss",
        "source_type": "official_blog",
        "description": "Google AI Blog",
        "source_authority": 9,
    },
    "deepmind_blog": {
        "url": "https://deepmind.google/blog/rss/",
        "type": "rss",
        "source_type": "official_blog",
        "description": "Google DeepMind Blog",
        "source_authority": 9,
    },
    "meta_ai_blog": {
        "url": "https://ai.meta.com/blog/rss/",
        "type": "rss",
        "source_type": "official_blog",
        "description": "Meta AI Blog",
        "source_authority": 9,
    },
    "nvidia_blog": {
        "url": "https://blogs.nvidia.com/feed/",
        "type": "rss",
        "source_type": "official_blog",
        "description": "NVIDIA Blog",
        "source_authority": 10,
    },
    "nvidia_developer_blog": {
        "url": "https://developer.nvidia.com/blog/feed/",
        "type": "rss",
        "source_type": "developer_blog",
        "description": "NVIDIA Developer Blog",
        "source_authority": 9,
    },
    "microsoft_ai_blog": {
        "url": "https://blogs.microsoft.com/ai/feed/",
        "type": "rss",
        "source_type": "official_blog",
        "description": "Microsoft AI Blog",
        "source_authority": 9,
    },
    "azure_ai_blog": {
        "url": "https://azure.microsoft.com/en-us/blog/topics/ai-machine-learning/feed/",
        "type": "rss",
        "source_type": "developer_blog",
        "description": "Azure AI Blog",
        "source_authority": 8,
    },
    "aws_ml_blog": {
        "url": "https://aws.amazon.com/blogs/machine-learning/feed/",
        "type": "rss",
        "source_type": "developer_blog",
        "description": "AWS Machine Learning Blog",
        "source_authority": 8,
    },
    "huggingface_blog": {
        "url": "https://huggingface.co/blog/feed.xml",
        "type": "rss",
        "source_type": "official_blog",
        "description": "Hugging Face Blog",
        "source_authority": 8,
    },
    "mistral_news": {
        "url": "https://mistral.ai/news/rss.xml",
        "type": "rss",
        "source_type": "official_blog",
        "description": "Mistral AI News",
        "source_authority": 8,
    },
    "cerebras_blog": {
        "url": "https://www.cerebras.ai/blog/rss.xml",
        "type": "rss",
        "source_type": "official_blog",
        "description": "Cerebras Blog",
        "source_authority": 8,
    },
    "coreweave_blog": {
        "url": "https://www.coreweave.com/blog/rss.xml",
        "type": "rss",
        "source_type": "official_blog",
        "description": "CoreWeave Blog",
        "source_authority": 8,
    },

    # GitHub releases / OSS changelogs
    "langchain_releases": {
        "url": "https://github.com/langchain-ai/langchain/releases.atom",
        "type": "rss",
        "source_type": "github_release",
        "description": "LangChain GitHub Releases",
        "source_authority": 8,
    },
    "vllm_releases": {
        "url": "https://github.com/vllm-project/vllm/releases.atom",
        "type": "rss",
        "source_type": "github_release",
        "description": "vLLM GitHub Releases",
        "source_authority": 8,
    },
    "llamacpp_releases": {
        "url": "https://github.com/ggerganov/llama.cpp/releases.atom",
        "type": "rss",
        "source_type": "github_release",
        "description": "llama.cpp GitHub Releases",
        "source_authority": 8,
    },
    "ollama_releases": {
        "url": "https://github.com/ollama/ollama/releases.atom",
        "type": "rss",
        "source_type": "github_release",
        "description": "Ollama GitHub Releases",
        "source_authority": 8,
    },
    "openwebui_releases": {
        "url": "https://github.com/open-webui/open-webui/releases.atom",
        "type": "rss",
        "source_type": "github_release",
        "description": "Open WebUI GitHub Releases",
        "source_authority": 8,
    },
    "comfyui_releases": {
        "url": "https://github.com/comfyanonymous/ComfyUI/releases.atom",
        "type": "rss",
        "source_type": "github_release",
        "description": "ComfyUI GitHub Releases",
        "source_authority": 8,
    },
    "autogen_releases": {
        "url": "https://github.com/microsoft/autogen/releases.atom",
        "type": "rss",
        "source_type": "github_release",
        "description": "AutoGen GitHub Releases",
        "source_authority": 8,
    },
    "crewai_releases": {
        "url": "https://github.com/crewAIInc/crewAI/releases.atom",
        "type": "rss",
        "source_type": "github_release",
        "description": "CrewAI GitHub Releases",
        "source_authority": 8,
    },

    # Research
    "arxiv_cs_ai": {
        "url": "https://arxiv.org/rss/cs.AI",
        "type": "arxiv",
        "source_type": "research_paper",
        "description": "arXiv CS.AI",
        "source_authority": 8,
    },
    "arxiv_cs_lg": {
        "url": "https://arxiv.org/rss/cs.LG",
        "type": "arxiv",
        "source_type": "research_paper",
        "description": "arXiv CS.LG",
        "source_authority": 8,
    },
    "arxiv_cs_cl": {
        "url": "https://arxiv.org/rss/cs.CL",
        "type": "arxiv",
        "source_type": "research_paper",
        "description": "arXiv CS.CL",
        "source_authority": 8,
    },
    "arxiv_stat_ml": {
        "url": "https://arxiv.org/rss/stat.ML",
        "type": "arxiv",
        "source_type": "research_paper",
        "description": "arXiv stat.ML",
        "source_authority": 8,
    },
    "bair_blog": {
        "url": "https://bair.berkeley.edu/blog/feed.xml",
        "type": "rss",
        "source_type": "research_paper",
        "description": "BAIR Blog",
        "source_authority": 7,
    },

    # Government / regulation
    "nist_news": {
        "url": "https://www.nist.gov/news-events/news/rss.xml",
        "type": "rss",
        "source_type": "government",
        "description": "NIST News",
        "source_authority": 9,
    },
    "ftc_press": {
        "url": "https://www.ftc.gov/news-events/news/press-releases/rss.xml",
        "type": "rss",
        "source_type": "government",
        "description": "FTC Press Releases",
        "source_authority": 8,
    },
    "sec_press": {
        "url": "https://www.sec.gov/news/pressreleases.rss",
        "type": "rss",
        "source_type": "government",
        "description": "SEC Press Releases",
        "source_authority": 8,
    },
    "meti": {
        "url": "https://www.meti.go.jp/rss/rss.rdf",
        "type": "rss",
        "source_type": "government",
        "description": "METI",
        "source_authority": 9,
    },
    "digital_agency": {
        "url": "https://www.digital.go.jp/rss.xml",
        "type": "rss",
        "source_type": "government",
        "description": "Digital Agency",
        "source_authority": 8,
    },
    "ipa": {
        "url": "https://www.ipa.go.jp/rss/news.rdf",
        "type": "rss",
        "source_type": "government",
        "description": "IPA",
        "source_authority": 8,
    },
    "nedo": {
        "url": "https://www.nedo.go.jp/rss/index.xml",
        "type": "rss",
        "source_type": "government",
        "description": "NEDO",
        "source_authority": 8,
    },
}

OFFICIAL_PAGE_SOURCES = {
    "xai_news": {
        "url": "https://x.ai/news",
        "source_type": "official_blog",
        "description": "xAI News",
        "source_authority": 9,
    },
    "amd_newsroom": {
        "url": "https://www.amd.com/en/newsroom",
        "source_type": "official_press",
        "description": "AMD Newsroom",
        "source_authority": 8,
    },
    "tsmc_news": {
        "url": "https://pr.tsmc.com/english/news",
        "source_type": "official_press",
        "description": "TSMC News",
        "source_authority": 9,
    },
    "broadcom_news": {
        "url": "https://news.broadcom.com/",
        "source_type": "official_press",
        "description": "Broadcom News",
        "source_authority": 8,
    },
    "groq_news": {
        "url": "https://groq.com/news/",
        "source_type": "official_press",
        "description": "Groq News",
        "source_authority": 8,
    },
    "figure_news": {
        "url": "https://www.figure.ai/news",
        "source_type": "official_press",
        "description": "Figure News",
        "source_authority": 8,
    },
    "tesla_ai": {
        "url": "https://www.tesla.com/AI",
        "source_type": "official_blog",
        "description": "Tesla AI",
        "source_authority": 8,
    },
}

OFFICIAL_LINK_KEYWORDS = (
    "news", "blog", "press", "release", "research", "announcement",
    "model", "api", "ai", "gpu", "chip", "cloud", "robot", "earnings",
    "investor", "datacenter", "data-center", "security", "benchmark",
)

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
            image_url TEXT DEFAULT '',
            is_primary_source INTEGER DEFAULT 0,
            source_authority REAL DEFAULT 0
        )
    """)
    for sql in (
        "ALTER TABLE articles ADD COLUMN is_primary_source INTEGER DEFAULT 0",
        "ALTER TABLE articles ADD COLUMN source_authority REAL DEFAULT 0",
    ):
        try:
            cursor.execute(sql)
        except sqlite3.OperationalError:
            pass
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

def fetch_og_image(url: str) -> str:
    """OG画像URLを取得する（Playwright優先・requestsフォールバック）"""
    # まずrequestsで試みる（高速）
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        res = requests.get(url, timeout=8, headers=headers)
        soup = BeautifulSoup(res.text, "html.parser")
        og = soup.find("meta", property="og:image")
        if og and og.get("content"):
            return og["content"].strip()
        tw = soup.find("meta", attrs={"name": "twitter:image"})
        if tw and tw.get("content"):
            return tw["content"].strip()
    except Exception:
        pass

    # requestsで取得できない場合はPlaywrightで試みる
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, timeout=15000)
            page.wait_for_load_state("domcontentloaded")
            og_url = page.evaluate("""() => {
                const og = document.querySelector('meta[property="og:image"]');
                if (og) return og.getAttribute('content');
                const tw = document.querySelector('meta[name="twitter:image"]');
                if (tw) return tw.getAttribute('content');
                return '';
            }""")
            browser.close()
            if og_url:
                return og_url.strip()
    except Exception:
        pass

    return ""


def save_article(article):
    article["title"] = article.get("title", "").replace('\xa0', ' ').replace('\u200b', '').strip()
    article["summary"] = article.get("summary", "").replace('\xa0', ' ').replace('\u200b', '').strip()
    if is_duplicate(article["url"], article["title"]):
        return False
     # OG画像取得
    og_image = fetch_og_image(article["url"])
    image_url = og_image if og_image else ""

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO articles
            (url, title, summary, source, source_type, author, published_at, score, image_url,
             is_primary_source, source_authority)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            1 if article.get("is_primary_source", True) else 0,
            float(article.get("source_authority", 0) or 0),
        ))
        conn.commit()
        logger.info("記事を保存: %s [OG:%s]", article["title"][:40], "あり" if og_image else "なし")
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
                "source": "Anthropic News", "source_type": "official_blog",
                "author": "", "published_at": "", "score": 0,
                "is_primary_source": 1, "source_authority": 10,
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
            "source_type": source_info.get("source_type", "business"),  # ← ここを修正
            "author": entry.get("author", ""),
            "published_at": entry.get("published", ""),
            "score": 0,
            "is_primary_source": 1,
            "source_authority": source_info.get("source_authority", 0),
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
            "is_primary_source": 0,
            "source_authority": 0,
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
            "source_type": source_info.get("source_type", "research"),  # ← ここを修正
            "author": ", ".join([a.get("name", "") for a in entry.get("authors", [])]),
            "published_at": entry.get("published", ""),
            "score": 0,
            "is_primary_source": 1,
            "source_authority": source_info.get("source_authority", 8),
        }
        if article["url"] and article["title"]:
            articles.append(article)
    return articles


def fetch_official_page(source_key: str, source_info: Dict) -> List[Dict]:
    articles = []
    base_url = source_info["url"]
    base_host = urlparse(base_url).netloc.replace("www.", "")
    logger.info("公式ページ取得開始: %s (%s)", source_info["description"], base_url)

    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; AIKeizaiBot/1.0; +https://aikeizai.jp/)"
        }
        res = requests.get(base_url, timeout=12, headers=headers)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, "html.parser")
        seen = set()

        for link in soup.find_all("a", href=True):
            title = re.sub(r"\s+", " ", link.get_text(" ", strip=True))
            href = urljoin(base_url, link["href"])
            parsed = urlparse(href)
            host = parsed.netloc.replace("www.", "")

            if host != base_host:
                continue
            if href in seen:
                continue
            if len(title) < 8 or len(title) > 160:
                continue

            haystack = f"{href} {title}".lower()
            if not any(keyword in haystack for keyword in OFFICIAL_LINK_KEYWORDS):
                continue

            seen.add(href)
            articles.append({
                "url": href,
                "title": title,
                "summary": "",
                "source": source_info["description"],
                "source_type": source_info.get("source_type", "official_press"),
                "author": "",
                "published_at": "",
                "score": 0,
                "is_primary_source": 1,
                "source_authority": source_info.get("source_authority", 8),
            })

            if len(articles) >= 20:
                break

        logger.info("公式ページ取得完了: %s - 記事数: %d", source_info["description"], len(articles))
    except Exception as e:
        logger.error("公式ページ取得エラー: %s - エラー: %s", source_info["description"], str(e))

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

    for source_key, source_info in OFFICIAL_PAGE_SOURCES.items():
        for article in fetch_official_page(source_key, source_info):
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

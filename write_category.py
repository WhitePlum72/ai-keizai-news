import pathlib

content = """---
import { getCollection } from "astro:content";
import Header from "../components/Header.astro";
import Footer from "../components/Footer.astro";
import Sidebar from "../components/Sidebar.astro";

export async function getStaticPaths() {
  const CATEGORIES = [
    { slug: "model",          label: "モデル",      emoji: "🤖" },
    { slug: "business",       label: "ビジネス",    emoji: "💼" },
    { slug: "markets",        label: "AI関連株",    emoji: "📈" },
    { slug: "infrastructure", label: "インフラ",    emoji: "🖥️" },
    { slug: "research",       label: "研究",        emoji: "🔬" },
    { slug: "policy",         label: "政策",        emoji: "⚖️" },
    { slug: "products",       label: "プロダクト",  emoji: "📦" },
  ];
  return CATEGORIES.map(cat => ({
    params: { category: cat.slug },
    props: { ...cat },
  }));
}

const { category, label, emoji } = Astro.props;
const allArticles = await getCollection("articles");
const articles = allArticles
  .filter(a => a.data.category_slug === category || a.id.startsWith(category + "/"))
  .sort((a, b) => (b.data.buzz_score || 0) - (a.data.buzz_score || 0));

const getArticleUrl = (article) => {
  const cat = article.data.category_slug || "business";
  const slug = article.data.article_slug || article.id;
  return `/article/${cat}/${slug}/`;
};

const formatDate = (str) => {
  if (!str) return "";
  const d = new Date(str);
  if (isNaN(d)) return str;
  return d.toLocaleDateString("ja-JP", { month: "numeric", day: "numeric" });
};

const canonicalUrl = `https://aikeizai.jp/${category}/`;
const pageTitle = `${label}のニュース — AI経済新聞`;
const pageDesc = `AI経済新聞の${label}カテゴリ。AI・テック産業に関する${label}分野の最新情報を配信。`;
---

<html lang="ja">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{pageTitle}</title>
  <meta name="description" content={pageDesc} />
  <link rel="canonical" href={canonicalUrl} />
  <meta property="og:type" content="website" />
  <meta property="og:url" content={canonicalUrl} />
  <meta property="og:title" content={pageTitle} />
  <meta property="og:description" content={pageDesc} />
  <meta property="og:image" content="https://aikeizai.jp/ogp.png" />
  <meta name="twitter:card" content="summary_large_image" />
  <script async src="https://www.googletagmanager.com/gtag/js?id=G-R8C9ET314H"></script>
  <script>
    window.dataLayer = window.dataLayer || [];
    function gtag(){dataLayer.push(arguments);}
    gtag("js", new Date());
    gtag("config", "G-R8C9ET314H");
  </script>
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: "Noto Sans JP", -apple-system, sans-serif; background: #f2f4f7; color: #1a1a1a; font-size: 14px; line-height: 1.6; }
    a { text-decoration: none; color: inherit; }
    img { display: block; width: 100%; }
    .container { max-width: 1200px; margin: 0 auto; padding: 20px 16px; }
    .main-grid { display: grid; grid-template-columns: minmax(0, 1fr) 300px; gap: 24px; }
    .page-header { margin-bottom: 24px; padding-bottom: 16px; border-bottom: 3px solid #003f88; }
    .page-header h1 { font-size: 22px; font-weight: 900; color: #0d1117; }
    .page-header p { font-size: 13px; color: #666; margin-top: 6px; }
    .article-list { background: #fff; border-radius: 4px; border: 1px solid #e8ecf2; overflow: hidden; }
    .l-item { display: flex; gap: 12px; padding: 14px 16px; border-bottom: 1px solid #f0f2f5; align-items: flex-start; text-decoration: none; color: inherit; transition: background 0.1s; }
    .l-item:hover { background: #f7f9fc; }
    .l-item:last-child { border-bottom: none; }
    .l-thumb { width: 100px; height: 70px; object-fit: cover; border-radius: 4px; flex-shrink: 0; }
    .l-placeholder { width: 100px; height: 70px; background: #edf0f7; border-radius: 4px; flex-shrink: 0; display: flex; align-items: center; justify-content: center; font-size: 28px; }
    .l-body { flex: 1; min-width: 0; }
    .l-source-badge { font-size: 9px; font-weight: 700; padding: 1px 5px; border-radius: 2px; background: #fff8e1; color: #7a5800; margin-right: 4px; }
    .l-title { font-size: 14px; font-weight: 700; line-height: 1.55; margin-bottom: 5px; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
    .l-lead { font-size: 12px; color: #666; line-height: 1.6; margin-bottom: 5px; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
    .l-meta { font-size: 11px; color: #aaa; }
    .empty { padding: 40px; text-align: center; color: #999; background: #fff; border-radius: 4px; }
    @media (max-width: 900px) { .main-grid { grid-template-columns: 1fr; } }
    @media (max-width: 600px) { .l-thumb, .l-placeholder { width: 80px; height: 58px; } }
  </style>
</head>
<body>
<Header currentCategory={category} />
<div class="container">
  <div class="main-grid">
    <main>
      <div class="page-header">
        <h1>{emoji} {label}</h1>
        <p>{pageDesc}</p>
      </div>
      {articles.length === 0 ? (
        <div class="empty">記事がありません</div>
      ) : (
        <div class="article-list">
          {articles.map(article => (
            <a class="l-item" href={getArticleUrl(article)}>
              {article.data.image_url
                ? <img class="l-thumb" src={article.data.image_url} alt={article.data.title} loading="lazy" />
                : <div class="l-placeholder" aria-hidden="true">{emoji}</div>
              }
              <div class="l-body">
                <div class="l-title">
                  {article.data.source_label && <span class="l-source-badge">{article.data.source_label}</span>}
                  {article.data.title}
                </div>
                <div class="l-lead">{(article.body || "").replace(/[#*`\\n]/g, " ").trim().slice(0, 120)}…</div>
                <div class="l-meta">{article.data.source} · {formatDate(article.data.published_at)}</div>
              </div>
            </a>
          ))}
        </div>
      )}
    </main>
    <Sidebar />
  </div>
</div>
<Footer />
</body>
</html>
"""

with open("astro-site/src/pages/[category].astro", "w", encoding="utf-8", newline="\n") as f:
    f.write(content)
print("完了")


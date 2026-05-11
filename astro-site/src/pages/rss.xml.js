import rss from '@astrojs/rss';
import { getCollection } from 'astro:content';

export async function GET(context) {
  const articles = await getCollection('articles');
  const sorted = articles
    .sort((a, b) => (b.data.published_at || '').localeCompare(a.data.published_at || ''))
    .slice(0, 50);

  return rss({
    title: 'AI経済新聞',
    description: 'AIと経済の最新ニュースを毎日配信。OpenAI・NVIDIA・Anthropicなど一次情報を日本語で解説。',
    site: context.site,
    items: sorted.map(article => ({
      title: article.data.title,
      pubDate: new Date(article.data.published_at || new Date()),
      description: article.data.meta_description || article.data.title,
      link: `/article/${article.data.category_slug || 'business'}/${article.data.article_slug || article.id}/`,
    })),
    customData: `<language>ja</language>`,
  });
}

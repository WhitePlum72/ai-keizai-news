import { defineConfig } from 'astro/config';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import sitemap from '@astrojs/sitemap';
import react from '@astrojs/react';

import tailwindcss from '@tailwindcss/vite';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const articleRoot = path.join(__dirname, 'src', 'content', 'articles');
const legacyArticleUrls = new Set();

function readFrontmatterValue(frontmatter, key) {
  const match = frontmatter.match(new RegExp(`^${key}:\\s*["']?([^"'\\r\\n]+)["']?\\s*$`, 'm'));
  return match ? match[1].trim() : '';
}

function collectLegacyArticleUrls(dir, category = '') {
  if (!fs.existsSync(dir)) return;

  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const fullPath = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      collectLegacyArticleUrls(fullPath, entry.name);
      continue;
    }
    if (!entry.isFile() || !entry.name.endsWith('.md')) continue;

    const text = fs.readFileSync(fullPath, 'utf8');
    const end = text.indexOf('\n---', 3);
    if (!text.startsWith('---') || end < 0) continue;

    const frontmatter = text.slice(4, end);
    const archived =
      /^noindex:\s*true\s*$/m.test(frontmatter) ||
      /^indexable:\s*false\s*$/m.test(frontmatter) ||
      /legacy_secondary_source/.test(frontmatter);
    if (!archived) continue;

    const cat = readFrontmatterValue(frontmatter, 'category_slug') || category || 'business';
    const slug = readFrontmatterValue(frontmatter, 'article_slug') || entry.name.replace(/\.md$/, '');
    legacyArticleUrls.add(`/article/${cat}/${slug}/`);
  }
}

collectLegacyArticleUrls(articleRoot);

export default defineConfig({
  site: 'https://aikeizai.jp',
  trailingSlash: 'always',

  integrations: [
    sitemap({
      filter: (page) => {
        const url = new URL(page);
        return !legacyArticleUrls.has(url.pathname);
      },
    }),
    react(),
  ],

  legacy: {
    collections: true,
  },

  vite: {
    plugins: [tailwindcss()],
  },
});

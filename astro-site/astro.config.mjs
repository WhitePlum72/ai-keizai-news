import { defineConfig } from 'astro/config';
import sitemap from '@astrojs/sitemap';

export default defineConfig({
  site: 'https://aikeizai.jp',
  trailingSlash: 'always',
  integrations: [sitemap()],
  legacy: {
    collections: true,
  },
});
import { defineConfig } from 'astro/config';
import sitemap from '@astrojs/sitemap';

export default defineConfig({
  site: 'https://aikeizai.jp',
  integrations: [sitemap()],
  legacy: {
    collections: true,
  },
});
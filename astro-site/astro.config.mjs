import { defineConfig } from 'astro/config';
import sitemap from '@astrojs/sitemap';
import react from '@astrojs/react';

import tailwindcss from '@tailwindcss/vite';

export default defineConfig({
  site: 'https://aikeizai.jp',
  trailingSlash: 'always',

  integrations: [
    sitemap(),
    react(),
  ],

  legacy: {
    collections: true,
  },

  vite: {
    plugins: [tailwindcss()],
  },
});
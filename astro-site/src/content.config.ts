import { defineCollection, z } from 'astro:content';
import { glob } from 'astro/loaders';

const articles = defineCollection({
  loader: glob({ pattern: '**/*.md', base: './src/content/articles' }),
  schema: z.object({
    title: z.string(),
    source: z.string(),
    source_url: z.string(),
    category: z.string(),
    published_at: z.string(),
    buzz_score: z.number(),
    image_url: z.string().optional(),
    meta_description: z.string().optional(),
    is_digest: z.boolean().optional(),
  }),
});

export const collections = { articles };
import { defineCollection, z } from 'astro:content';
import { glob } from 'astro/loaders';

const articles = defineCollection({
  loader: glob({ pattern: '**/*.md', base: './src/content/articles' }),
  schema: z.object({
    title: z.string(),
    source: z.string().optional(),
    source_url: z.string().optional(),
    category: z.string().optional(),
    category_slug: z.string().optional(),
    article_slug: z.string().optional(),
    published_at: z.string().optional(),
    buzz_score: z.number().optional(),
    image_url: z.string().optional(),
    description: z.string().optional(),
    meta_description: z.string().optional(),
    summaryPoints: z.array(z.string()).optional(),
    source_label: z.string().optional(),
    is_digest: z.boolean().optional(),
  }),
});

export const collections = { articles };

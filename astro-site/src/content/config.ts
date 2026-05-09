import { defineCollection, z } from 'astro:content';

const articles = defineCollection({
  type: 'content',
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
    meta_description: z.string().optional(),
    source_label: z.string().optional(),
  }),
});

export const collections = { articles };
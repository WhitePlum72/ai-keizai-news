import { defineCollection, z } from 'astro:content';
import { glob } from 'astro/loaders';

const articles = defineCollection({
  loader: glob({ pattern: '**/*.md', base: './src/content/articles' }),
  schema: z.object({
    title: z.string(),
    source: z.string().optional(),
    source_url: z.string().optional(),
    source_type: z.string().optional(),
    source_authority: z.number().optional(),
    category: z.string().optional(),
    category_slug: z.string().optional(),
    article_slug: z.string().optional(),
    published_at: z.string().optional(),
    source_published_at: z.string().optional(),
    buzz_score: z.number().optional(),
    image: z.string().optional(),
    image_url: z.string().optional(),
    description: z.string().optional(),
    meta_description: z.string().optional(),
    summaryPoints: z.array(z.string()).optional(),
    source_label: z.string().optional(),
    is_primary_source: z.boolean().optional(),
    noindex: z.boolean().optional(),
    indexable: z.boolean().optional(),
    source_status: z.string().optional(),
    archive_reason: z.string().optional(),
    is_digest: z.boolean().optional(),
    topics_json: z.array(z.string()).optional(),
    companies_json: z.array(z.string()).optional(),
  }),
});

export const collections = { articles };

import { defineCollection, z } from 'astro:content';
import { glob } from 'astro/loaders';

const letters = defineCollection({
  loader: glob({ pattern: '**/*.md', base: './src/content/letters' }),
  schema: z.object({
    title: z.string(),
    date: z.coerce.date(),
    description: z.string().optional().default(''),
    quote: z.string().optional().default(''),
    attribution: z.string().optional().default(''),
    source: z.literal('tinyletter'),
    originalSlug: z.string(),
  }),
});

export const collections = { letters };

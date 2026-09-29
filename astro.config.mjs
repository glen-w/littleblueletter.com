import { defineConfig } from 'astro/config';

export default defineConfig({
  site: 'https://littleblueletter.com',
  trailingSlash: 'always',
  markdown: {
    syntaxHighlight: false,
  },
});

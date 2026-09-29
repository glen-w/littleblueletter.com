# Little Blue Letter

Public site for **https://littleblueletter.com** — Tiny Letter–style ocean newsletter archive (2017–2023).

Personal site keeps the same letters under glenwright.earth (`/blog/tag/littleblueletter/`) and a project card. The brand home is this domain.

## Local

```sh
npm install
npm run build
npm run dev
```

Letters live in `src/content/letters/` (from the TinyLetter extract + personal-site publish path). Images in `public/images/letters/`.

Optional ingest scripts (Syncthing `content/`, Wayback):

```sh
python3 scripts/extract.py
python3 scripts/fetch_images.py
python3 scripts/publish.py   # writes into glen-w.github.io
```

## Analytics

Umami site id for `littleblueletter.com` (`81f9fc36-…`). Never reuse the glenwright.earth id. Override with `PUBLIC_UMAMI_WEBSITE_ID` / `PUBLIC_UMAMI_SRC` if needed.

## Deploy

GitHub Pages via Actions (`.github/workflows/deploy.yml`) from `main`. Custom domain: `littleblueletter.com` (+ `www`). See [DNS.md](DNS.md).

## Own-TLD pattern

Same shape as Academia Obscura: separate Astro repo + OVH DNS → GitHub Pages + HTTPS. Logged in Untangle `decisions/project-own-tld.md`.

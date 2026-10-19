# Newsletter workflow (ListMonk era)

High-level pipeline for getting an issue from draft to inbox. Automation hooks are marked **(auto)** where scripts exist or are planned.

## 1. Draft

- Work in `drafts/YYYY-MM-DD.md` (issue send date).
- Follow [listmonk-markup.md](./listmonk-markup.md).
- Keep working assets beside the draft if you like (e.g. Desktop `LBL-YYYY-MM-DD/images/`); rename to match upload slugs before publish.

## 2. Lint **(auto)**

```sh
python3 scripts/lint_listmonk_issue.py drafts/2026-10-16.md
# optional: check upload URLs respond
python3 scripts/lint_listmonk_issue.py drafts/2026-10-16.md --check-images
```

Fixes common paste errors (`@TrackLink`, `--` dividers, `##` headings, missing credit styling hints).

## 3. Images

| Local (example) | Upload as |
|-----------------|-----------|
| `images/03-book-cover.jpg` | `261016_how_to_revive_our_ocean.jpg` |
| Wikimedia / stock | Export or download, upload with `261016_{slug}.jpg` |

Upload via ListMonk → Media. Confirm URLs with `--check-images`.

## 4. Send

- Create campaign in ListMonk; paste body HTML/Markdown fragment.
- Subject line and preview text: set in ListMonk (not stored in `drafts/` yet).

## 5. Archive **(planned)**

After send:

1. Save final body to `drafts/` or `src/content/letters/YYYY-MM-DD.md` with Astro front matter.
2. Mirror images into `public/images/letters/` for the public site.
3. Run site build / deploy.

`scripts/publish.py` today targets the historical TinyLetter → Astro path; extend or add `scripts/archive_listmonk_issue.py` when this step is ready.

## Roadmap

| Step | Script / doc |
|------|----------------|
| Markup spec | `docs/listmonk-markup.md` |
| Pre-flight lint | `scripts/lint_listmonk_issue.py` |
| Link cleanup (`@TrackLink`, UTM strip) | extend lint or `scripts/normalize_links.py` |
| Upload rename helper | `scripts/prepare_uploads.py` (date prefix + slug from manifest) |
| Post-send archive | `scripts/archive_listmonk_issue.py` |
| AI drafting assistant | prompt + schema derived from `listmonk-markup.md` |

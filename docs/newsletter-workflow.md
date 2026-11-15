# Newsletter workflow (ListMonk era)

High-level pipeline for getting an issue from draft to inbox. Automation hooks are marked **(auto)** where scripts exist or are planned.

**Working root:** `/Users/89298/Documents/Little Blue Letter/content/`  
Do **not** use the repo `drafts/` folder for new issues.

## 1. Draft

- Create a dedicated send-date folder: `content/YYMMDD/` (e.g. `261113` for 13 Nov 2026).
- Typical files in that folder (see `content/261106/` as a model):
  - `YYMMDD_LBL.md` — campaign body (ListMonk paste)
  - `YYMMDD_author_block.md` — curator portrait + bio fragment
  - Image uploads named `YYMMDD_short_slug.ext`
  - Source doc (`.docx` / Google Doc export) optional
  - For gifs: keep the compressed upload file and optionally `YYMMDD_….gif.orig`
- Follow [listmonk-markup.md](./listmonk-markup.md).

## 2. Lint **(auto)**

```sh
CONTENT="/Users/89298/Documents/Little Blue Letter/content"
python3 scripts/lint_listmonk_issue.py "$CONTENT/261016/261016_LBL.md"
# optional: check upload URLs respond
python3 scripts/lint_listmonk_issue.py "$CONTENT/261016/261016_LBL.md" --check-images
```

Catches common paste errors (`--` dividers, `##` headings, missing credit styling hints, non-400px or uncentered images).

## 3. Images

| Local (example) | Upload as |
|-----------------|-----------|
| `content/261016/261016_how_to_revive_our_ocean.jpg` | same filename → ListMonk Media |
| Wikimedia / stock | Export or download, save into `content/YYMMDD/` with `YYMMDD_{slug}.jpg` |

In the body HTML, use **400px width and centered** (`display:block; margin:0 auto;`) for story photos and gifs (see [listmonk-markup.md](./listmonk-markup.md)). Book covers: 300px; curator portrait: 90px.

Upload via ListMonk → Media. Confirm URLs with `--check-images`.

### Gifs library

Copy every gif used in the issue (compressed upload version and `.orig` if kept) into:

`/Users/89298/Documents/Little Blue Letter/content/gifs/`

Keep the same `YYMMDD_…` filenames so the issue folder and the library stay in sync.

## 4. Add ListMonk `@TrackLink` suffixes

Before creating the campaign, append `@TrackLink` to **every outbound link URL** in the paste body (Markdown `](url)` and HTML `href="url"`). Example: `https://example.com/path@TrackLink`. Skip image `src=` URLs.

```sh
CONTENT="/Users/89298/Documents/Little Blue Letter/content"
# pre-send gate: fail if any outbound link is missing @TrackLink
python3 scripts/lint_listmonk_issue.py "$CONTENT/261016/261016_LBL.md" --require-tracklink
```

Keep a clean-URL copy for the site archive (no `@TrackLink`). See [listmonk-markup.md](./listmonk-markup.md#links).

## 5. Send

- Create campaign in ListMonk; paste the `@TrackLink`-suffixed body from `YYMMDD_LBL.md`.
- Subject line and preview text: set in ListMonk (store alongside the issue folder if useful; not required).

## 6. Archive **(planned)**

After send:

1. Save final body to the Astro site as `src/content/letters/YYYY-MM-DD.md` with front matter (**strip `@TrackLink`** from all URLs for the public site). Source of truth for the campaign remains `content/YYMMDD/`.
2. Mirror images into `public/images/letters/` for the public site.
3. Run site build / deploy.

`scripts/publish.py` today targets the historical TinyLetter → Astro path; extend or add `scripts/archive_listmonk_issue.py` when this step is ready.

## Roadmap

| Step | Script / doc |
|------|----------------|
| Markup spec | `docs/listmonk-markup.md` |
| Pre-flight lint | `scripts/lint_listmonk_issue.py` |
| Add/strip `@TrackLink` for send vs archive | `lint --require-tracklink`; optional `scripts/normalize_links.py` |
| Upload rename helper | `scripts/prepare_uploads.py` (date prefix + slug from manifest) |
| Post-send archive | `scripts/archive_listmonk_issue.py` |
| AI drafting assistant | prompt + schema derived from `listmonk-markup.md` |

# ListMonk campaign body markup

Little Blue Letter sends from **ListMonk**. The campaign body is mostly HTML with light Markdown (bold, links, italics). ListMonk does not need a full HTML document — paste the fragment below the template header/footer.

This spec is the source of truth for humans and for lint/automation scripts (`scripts/lint_listmonk_issue.py`).

## Section structure

1. **Section title** on its own line: `**{emoji} Title text**`  
   Do not use `##` headings; they render as large `<h2>` and break the TinyLetter-style rhythm.

2. One or more paragraphs of prose (Markdown links and emphasis are fine).

3. Optional **hero image** + **credit line** (see Images).

4. **Section break:** a line containing only `---` (three hyphens). Not `--`.

Repeat for each story block. Optional recurring blocks:

| Block | Title pattern |
|-------|----------------|
| Short items | `**Meanwhile...**` then bullet list (`- `) |
| Grants / jobs | `**🎯 Opportunities**` |
| Book | `**📚 Book of the Week — [*Title*](amazon-url), by Author(s)**` |
| Papers | `**📄 In the Literature**` then bullets with bold linked titles |
| Gif | `**🐙 Gif of the Week**` then centered image (200px) |

## Links

- Use clean destination URLs only. Strip mail-client trackers such as `@TrackLink` before paste.
- Amazon / affiliate: `https://link.amazon/...` as used in recent issues.
- Inline link text: `[agreed this week](url)`, `[Details](url)` for opportunities.

## Images

**Host:** `https://lists.littleblueletter.com/uploads/`

**Filename:** `YYMMDD_short_slug.ext` where `YYMMDD` is the send date (e.g. 16 Oct 2026 → `261016`). Use lowercase slugs with underscores.

**Story image (inline HTML):**

```html
<img src="https://lists.littleblueletter.com/uploads/261016_example.jpg" alt="Short description" width="600" style="width:600px;max-width:100%;height:auto;" />
```

**Credit line (always immediately after the image):**

```html
<p style="font-size:12px;line-height:1.4;color:#666666;margin:8px 0 0 0;text-align:center;"><em>Credit: Name or agency</em></p>
```

For artwork with a title, credit line may include the title and artists; keep the same `<p style="...">` wrapper.

**Book cover (300px, linked):**

```html
<p align="center" style="text-align:center;margin:0;">
  <a href="https://link.amazon/XXXXX">
    <img src="https://lists.littleblueletter.com/uploads/261016_book_slug.jpg" alt="Book title cover" width="300" style="width:300px;max-width:100%;height:auto;border:0;" />
  </a>
</p>
```

**Gif of the Week (200px, centered, usually not linked):**

```html
<p align="center" style="text-align:center;margin:0;">
  <img src="https://lists.littleblueletter.com/uploads/261016_octopus.gif" alt="Dumbo octopus" width="200" style="width:200px;max-width:100%;height:auto;" />
</p>
```

Upload files in ListMonk **Media** before send; campaign HTML should reference the final public URL.

## In the Literature

Each item is one bullet:

```markdown
- **[Paper title](https://doi-or-publisher-url)**
  One or two sentences of plain-language summary (indented continuation line is OK).
```

## Typography habits

- Emoji at the start of section titles; space after flag emojis when followed by words (`🇨🇴 A Caribbean…`).
- Curly apostrophes in prose are fine; watch **its** vs **it's**.
- Em dash `—` in book title line; en dash for date ranges where needed.

## What ListMonk supplies separately

Do not duplicate in the body fragment: full-page wrapper, unsubscribe link, subscriber name salutation (unless you intentionally override the template).

## Example reference

See `drafts/2026-10-16.md` for a full issue following this spec. Older archived HTML under `archive/issues/` reflects the TinyLetter era (heavier inline styles); new sends should follow this document.

#!/usr/bin/env python3
"""Write the Astro archive and the personal-site posts from the extracted letters."""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ISSUES = ROOT / "archive" / "issues"
MANIFEST = ROOT / "archive" / "manifest.json"
IMAGE_MAP = ROOT / "ingest" / "out" / "image_map.json"
CACHE = ROOT / "ingest" / "images"
PUBLIC_IMAGES = ROOT / "public" / "images" / "letters"
LETTERS = ROOT / "src" / "content" / "letters"
SITE = Path("/Users/89298/Documents/website/glen-w.github.io")
JEKYLL_POSTS = SITE / "_posts"
JEKYLL_IMAGES = SITE / "assets" / "img" / "little-blue-letter"
DESIGN = Path("/Users/89298/Documents/Little Blue Letter/design")
HOME = "/little-blue-letter/"
MIGRATION = ROOT / "MIGRATION.md"


def yaml_quote(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


# TinyLetter hosted several copies of the banner logo under different UUIDs.
LOGO_URL_MARKERS = (
    "734e28c8-c57b-4330-8dce-b8b42daa5e2b",
    "81bb84db-2a04-4dc4-a6ba-fcc0ee829997",
    "7f376862-3fa1-48ae-abee-928ccdec1bf9",
)
CANON_LOGO = "734e28c8-c57b-4330-8dce-b8b42daa5e2b.png"


def load_map() -> dict[str, dict]:
    if not IMAGE_MAP.exists():
        return {}
    rows = json.loads(IMAGE_MAP.read_text(encoding="utf-8"))
    return {row["url"]: row for row in rows if row.get("file")}


def is_banner_logo(url: str) -> bool:
    return any(marker in url for marker in LOGO_URL_MARKERS)


def resolve_image(url: str, mapping: dict[str, dict]) -> Path | None:
    """Return the local cache/public path for an image URL."""
    if is_banner_logo(url):
        public_logo = PUBLIC_IMAGES / CANON_LOGO
        if public_logo.exists():
            return public_logo
        cached = CACHE / CANON_LOGO
        if cached.exists():
            return cached
    row = mapping.get(url)
    if not row:
        return None
    name = row["file"]
    # Never let a bad inference overwrite the banner logo slot.
    if is_banner_logo(url):
        name = CANON_LOGO
    src = CACHE / name
    return src if src.exists() else None


def rewrite(html: str, mapping: dict[str, dict], dest_prefix: str, copied: set[str]) -> tuple[str, int]:
    missing = 0

    def repl(match: re.Match) -> str:
        nonlocal missing
        tag = match.group(0)
        url_match = re.search(r'src="(https?://[^"]+)"', tag)
        if not url_match:
            return tag
        url = url_match.group(1).replace("&amp;", "&")
        src = resolve_image(url, mapping)
        if not src:
            missing += 1
            return ""
        name = CANON_LOGO if is_banner_logo(url) else src.name
        if name not in copied:
            PUBLIC_IMAGES.mkdir(parents=True, exist_ok=True)
            JEKYLL_IMAGES.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, PUBLIC_IMAGES / name)
            shutil.copy2(src, JEKYLL_IMAGES / name)
            copied.add(name)
        return re.sub(r'src="https?://[^"]+"', f'src="{dest_prefix}{name}"', tag, count=1)

    html = re.sub(r"<img\b[^>]*>", repl, html, flags=re.I)
    return stack_images(html), missing


def stack_images(html: str) -> str:
    """One column, like TinyLetter: each image on its own line, no side text."""

    def repl(match: re.Match) -> str:
        tag = match.group(0)
        tag = re.sub(r"\sheight=\"[^\"]*\"", "", tag, flags=re.I)
        style_match = re.search(r'style="([^"]*)"', tag, flags=re.I)
        style = style_match.group(1) if style_match else ""
        style = re.sub(
            r"(?:float|height|min-width)\s*:[^;\"']*;?",
            "",
            style,
            flags=re.I,
        )
        style = re.sub(r"\s+", " ", style).strip(" ;")
        block = (
            "display:block;float:none;clear:both;height:auto;"
            "max-width:100%;margin:0.75rem auto;"
        )
        style = f"{style};{block}" if style else block
        if style_match:
            tag = re.sub(r'style="[^"]*"', f'style="{style}"', tag, count=1, flags=re.I)
        else:
            tag = tag[:-1] + f' style="{style}">'
        return tag

    return re.sub(r"<img\b[^>]*>", repl, html, flags=re.I)


def write_letter(entry: dict, html: str) -> None:
    slug = entry["slug"]
    path = LETTERS / f"{slug}.md"
    fm = "\n".join(
        [
            "---",
            f"title: {yaml_quote(entry['title'])}",
            f"date: {entry['date']}",
            f"description: {yaml_quote(entry['description'])}",
            f"quote: {yaml_quote(entry['quote'])}",
            f"attribution: {yaml_quote(entry['attribution'])}",
            "source: tinyletter",
            f"originalSlug: {yaml_quote(slug)}",
            "---",
            "",
        ]
    )
    path.write_text(fm + html.strip() + "\n", encoding="utf-8")


def write_post(entry: dict, html: str) -> None:
    slug = entry["slug"]
    filename = f"{entry['date']}-little-blue-letter-{slug}.md"
    intro = (
        f"*Sent {entry['date_label']}. "
        f"Part of [Little Blue Letter]({HOME}).*\n\n"
    )
    fm = "\n".join(
        [
            "---",
            "layout: post",
            f"title: {yaml_quote(entry['title'])}",
            f"date: {entry['created_at']}",
            f"description: {yaml_quote(entry['description'])}",
            'tags: ["LittleBlueLetter"]',
            'categories: ["Little Blue Letter"]',
            "source: tinyletter",
            f"originalSlug: {yaml_quote(slug)}",
            "---",
            "",
        ]
    )
    (JEKYLL_POSTS / filename).write_text(fm + intro + html.strip() + "\n", encoding="utf-8")


def copy_brand() -> None:
    public = ROOT / "public"
    public.mkdir(parents=True, exist_ok=True)
    shutil.copy2(DESIGN / "Little Blue Letter logo small.png", public / "logo.png")
    shutil.copy2(DESIGN / "Little Blue Letter bg.png", public / "bg.png")
    shutil.copy2(DESIGN / "Little Blue Letter logo small.png", SITE / "assets/img/projects/thumbs/little_blue_letter_logo.png")


def main() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    mapping = load_map()
    LETTERS.mkdir(parents=True, exist_ok=True)
    for old in LETTERS.glob("*.md"):
        old.unlink()
    copied: set[str] = set()
    missing_total = 0
    for entry in manifest:
        raw = (ISSUES / f"{entry['slug']}.html").read_text(encoding="utf-8")
        minisite_html, missing_a = rewrite(raw, mapping, "/little-blue-letter/images/letters/", copied)
        jekyll_html, missing_b = rewrite(raw, mapping, "/assets/img/little-blue-letter/", copied)
        # Second rewrite sees files already copied; count once.
        missing_total += missing_a
        write_letter(entry, minisite_html)
        write_post(entry, jekyll_html)
        del missing_b
    copy_brand()
    quotes_blank = sum(1 for entry in manifest if not entry["quote"])
    exact_files = 0
    inferred_map = 0
    if IMAGE_MAP.exists():
        for row in json.loads(IMAGE_MAP.read_text(encoding="utf-8")):
            if not row.get("file"):
                continue
            src = str(row.get("source", ""))
            if src.startswith("inferred:"):
                inferred_map += 1
            else:
                exact_files += 1
    lines = [
        "# Little Blue Letter migration",
        "",
        f"- Issues: **{len(manifest)}**",
        f"- Span: **{manifest[0]['date']} → {manifest[-1]['date']}**",
        f"- Unique image files copied: **{len(copied)}**",
        f"- Map entries (exact): **{exact_files}**",
        f"- Map entries (inferred): **{inferred_map}**",
        f"- Image tags still missing: **{missing_total}**",
        f"- Opening quotes blank: **{quotes_blank}** (the 18 January 2018 cancellation has no quote)",
        "",
        "Subscriber lists, promo mailouts, and the praise corpus stayed out of this tree.",
        "",
    ]
    MIGRATION.write_text("\n".join(lines), encoding="utf-8")
    print(MIGRATION.read_text())


if __name__ == "__main__":
    main()

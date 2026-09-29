#!/usr/bin/env python3
"""Extract TinyLetter issues into cleaned HTML, a manifest, and opening_quotes.csv."""

from __future__ import annotations

import csv
import html
import json
import re
import unicodedata
from datetime import datetime
from pathlib import Path

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = Path(
    "/Users/89298/Documents/Little Blue Letter/tinyletter_sent_messages_2024_01_16.csv"
)
ISSUES = ROOT / "archive" / "issues"
QUOTES = ROOT / "archive" / "opening_quotes.csv"
MANIFEST = ROOT / "archive" / "manifest.json"

SKIP_HEADINGS = {
    "gif of the week",
    "further reading",
    "from the editor",
    "meanwhile on twitter",
    "meanwhile, on land...",
    "meanwhile on land",
    "in case you missed it",
    "#oceanoptimism",
    "oceanoptimism",
    "opportunities",
    "editor's note",
    "editors note",
    "quick note from the editor",
}


def slugify(text: str) -> str:
    text = html.unescape(text or "")
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return text or "letter"


def plain(node) -> str:
    text = node.get_text("\n", strip=True)
    text = html.unescape(text).replace("\xa0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s+", "\n", text)
    return text.strip()


def strip_chrome(soup: BeautifulSoup) -> None:
    for img in list(soup.find_all("img")):
        width = str(img.get("width") or "")
        height = str(img.get("height") or "")
        if width in {"0", "1"} or height in {"0", "1"}:
            img.decompose()
    for tag in soup.find_all(string=re.compile(r"view (this|in).{0,20}browser", re.I)):
        parent = tag.parent
        if parent:
            parent.decompose()
    for tag in soup.find_all(href=re.compile(r"unsubscribe", re.I)):
        parent = tag.find_parent("p") or tag
        parent.decompose()


def quote_from_html(soup: BeautifulSoup) -> tuple[str, str, str]:
    """Return quote, attribution, note."""
    head = plain(soup)[:900]
    if head.lower().startswith("due to a last-minute"):
        return "", "", "no opening quote"
    # Prefer the emphasised line when the letter uses one.
    em = soup.find(["em", "i"])
    em_text = plain(em).strip(" \"“”‘’") if em else ""
    match = re.search(r"[~—―]", head)
    if match and (em_text or head[:1] in "\"“"):
        quote = em_text
        if not quote:
            quote = head[: match.start()].strip(" \"“”‘’\n")
        after = head[match.end() :]
        lines = [re.sub(r"\s+", " ", line).strip(" \"“”") for line in after.split("\n")]
        lines = [line for line in lines if line]
        attr = lines[0] if lines else ""
        if len(attr) > 120:
            attr = attr[:120].rsplit(" ", 1)[0]
        if quote:
            return re.sub(r"\s+", " ", quote)[:500], attr, ""
    if head[:1] in "\"“" or (em_text and len(em_text) < 400):
        quote = em_text or head.split("\n")[0].strip(" \"“”")
        return re.sub(r"\s+", " ", quote)[:500], "", "no attribution on the opening line"
    return "", "", "no opening quote"


def lead_heading(soup: BeautifulSoup, quote: str) -> str:
    for strong in soup.find_all(["strong", "b"]):
        label = re.sub(r"\s+", " ", plain(strong)).strip()
        if not label or len(label) > 80:
            continue
        if label.lower().strip(" .") in SKIP_HEADINGS:
            continue
        if quote and label.lower() in quote.lower():
            continue
        return label
    # First sentence after the quote paragraph.
    seen_quote = False
    for p in soup.find_all("p"):
        text = re.sub(r"\s+", " ", plain(p))
        if not seen_quote:
            if "~" in text or (quote and quote[:24].lower() in text.lower()):
                seen_quote = True
            continue
        if len(text) < 20:
            continue
        sentence = re.split(r"(?<=[.!?])\s", text)[0]
        return sentence[:90].rstrip(" .")
    return ""


def clean_html(raw: str) -> str:
    soup = BeautifulSoup(raw, "html.parser")
    strip_chrome(soup)
    # Drop TinyLetter image class noise but keep src.
    for img in soup.find_all("img"):
        for attr in ("class", "data-id", "style"):
            if attr in img.attrs and attr == "style":
                # Keep width constraints only.
                continue
            img.attrs.pop(attr, None)
    body = soup.decode()
    body = re.sub(r"\n{3,}", "\n\n", body).strip()
    return body


def main() -> None:
    ISSUES.mkdir(parents=True, exist_ok=True)
    with CSV_PATH.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    rows.sort(key=lambda row: row["Created_At"])

    seen_dates: dict[str, int] = {}
    manifest = []
    quote_rows = []
    for index, row in enumerate(rows, start=1):
        created = datetime.strptime(row["Created_At"], "%Y-%m-%d %H:%M:%S")
        day = created.strftime("%Y-%m-%d")
        seen_dates[day] = seen_dates.get(day, 0) + 1
        slug = day if seen_dates[day] == 1 else f"{day}-{seen_dates[day]}"
        raw = row["Content"]
        soup = BeautifulSoup(raw, "html.parser")
        strip_chrome(soup)
        quote, attribution, note = quote_from_html(soup)
        heading = lead_heading(soup, quote)
        date_label = created.strftime("%-d %B %Y")
        if heading:
            title = f"{date_label} — {heading}"
        elif quote:
            title = f"{date_label} — {quote[:70].rstrip()}"
        else:
            title = f"{date_label} — Ocean update"
        description = heading or quote or "Ocean update from Little Blue Letter"
        description = re.sub(r"\s+", " ", description)[:180]
        cleaned = clean_html(raw)
        (ISSUES / f"{slug}.html").write_text(cleaned + "\n", encoding="utf-8")
        manifest.append(
            {
                "number": index,
                "slug": slug,
                "created_at": row["Created_At"],
                "date": day,
                "date_label": date_label,
                "subject": row["Subject"],
                "title": title,
                "description": description,
                "quote": quote,
                "attribution": attribution,
                "quote_note": note,
                "original_slug": slug,
            }
        )
        quote_rows.append(
            {
                "date": day,
                "subject": row["Subject"],
                "quote": quote,
                "attribution": attribution,
                "note": note,
            }
        )

    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with QUOTES.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["date", "subject", "quote", "attribution", "note"])
        writer.writeheader()
        writer.writerows(quote_rows)
    missing = sum(1 for row in quote_rows if not row["quote"])
    print(f"issues {len(manifest)} quotes_blank {missing} -> {QUOTES}")


if __name__ == "__main__":
    main()

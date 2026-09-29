#!/usr/bin/env python3
"""Pull a private corpus of reader praise. Not for the website or git."""

from __future__ import annotations

import re
from email import message_from_bytes
from email.header import decode_header, make_header
from email.policy import default
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "private" / "praise.md"
MAILBOXES = [
    Path("/Users/89298/email/gmail/Projects.sbd/Little Blue Letter"),
    Path("/Users/89298/email/gmail/[Gmail].sbd/Sent Mail"),
]
PRAISE = re.compile(
    r"(great issue|another great|love your ocean|really love|really enjoy|kind words|nice feedback|satisfied reader|made my (day|week)|uplifting)",
    re.I,
)
SKIP = re.compile(r"(automatic reply|undeliverable|out of office|invitation to edit|curator sign)", re.I)


def decode(value: str | None) -> str:
    if not value:
        return ""
    try:
        return str(make_header(decode_header(value)))
    except Exception:
        return str(value)


def plain_part(message) -> str:
    for part in message.walk():
        if part.get_content_type() == "text/plain":
            data = part.get_payload(decode=True) or b""
            return data.decode("utf-8", "replace")
    return ""


def new_text(body: str) -> str:
    return re.split(r"\nOn .+wrote:\n|\n-{5,}\s*Forwarded|\nFrom:", body, maxsplit=1)[0].strip()


def quoted_praise(body: str) -> str:
    match = re.search(
        r"(?:Forwarded message|Forwarded Message).{0,800}?(\n\n|\n)(.{40,600})",
        body,
        re.S,
    )
    if not match:
        return ""
    chunk = match.group(2)
    chunk = re.split(r"\nOn .+wrote:", chunk, maxsplit=1)[0]
    return re.sub(r"\s+", " ", chunk).strip()[:500]


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    rows: list[str] = [
        "# Little Blue Letter — reader praise",
        "",
        "Private. Names and addresses stay in this file. Do not publish.",
        "",
    ]
    seen: set[str] = set()
    for path in MAILBOXES:
        if not path.exists():
            continue
        data = path.read_bytes()
        parts = data.split(b"\nFrom ")
        for index, blob in enumerate(parts):
            if index:
                blob = b"From " + blob
            if b"Ocean update" not in blob and b"Ocean Update" not in blob and b"kind words" not in blob and b"nice feedback" not in blob:
                continue
            message = message_from_bytes(blob, policy=default)
            subject = decode(message.get("subject"))
            if SKIP.search(subject):
                continue
            body = plain_part(message)
            fresh = new_text(body)
            keep = False
            excerpt = ""
            sender = decode(message.get("from"))
            if subject.lower().startswith(("re:", "fw:", "fwd:")) and "ocean update" in subject.lower():
                excerpt = re.sub(r"\s+", " ", fresh)[:400]
            if PRAISE.search(excerpt) and not re.search(r"hyperlink|vacancy|does not work|wrong link", excerpt, re.I):
                keep = True
            if "kind words" in fresh.lower() or "nice feedback" in fresh.lower() or "satisfied reader" in fresh.lower():
                forwarded = quoted_praise(body)
                if forwarded:
                    keep = True
                    excerpt = forwarded
                    sender = "forwarded by Glen Wright"
            if not keep or not excerpt:
                continue
            if sender.lower().startswith("glen wright") or "glen.w.wright@" in sender.lower():
                continue
            key = excerpt[:120]
            if key in seen:
                continue
            seen.add(key)
            date = decode(message.get("date"))[:31]
            rows.append(f"## {date}")
            rows.append("")
            rows.append(f"- From: {sender}")
            rows.append(f"- Subject: {subject}")
            rows.append("")
            rows.append(excerpt)
            rows.append("")
    OUT.write_text("\n".join(rows) + "\n", encoding="utf-8")
    print(f"notes {len(seen)} -> {OUT}")


if __name__ == "__main__":
    main()

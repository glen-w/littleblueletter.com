#!/usr/bin/env python3
"""Pre-flight checks for a ListMonk campaign body draft."""

from __future__ import annotations

import argparse
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

TRACKLINK = re.compile(r"@TrackLink\b")
MARKDOWN_H2 = re.compile(r"^##\s+")
BAD_RULE = re.compile(r"^--\s*$")
IMG_SRC = re.compile(
    r'src="(https://lists\.littleblueletter\.com/uploads/[^"]+)"',
    re.I,
)
CREDIT_STYLE = "font-size:12px;line-height:1.4;color:#666666"


def lint(text: str, path: Path) -> list[str]:
    issues: list[str] = []
    lines = text.splitlines()

    for i, line in enumerate(lines, start=1):
        if TRACKLINK.search(line):
            issues.append(f"{path}:{i}: remove @TrackLink from URL")
        if MARKDOWN_H2.match(line):
            issues.append(
                f"{path}:{i}: use **emoji Title** instead of ## heading (see docs/listmonk-markup.md)"
            )
        if BAD_RULE.match(line):
            issues.append(f"{path}:{i}: section break must be --- not --")

    # After each story <img> (600px), expect a credit <p> within the next few lines.
    for m in re.finditer(r"<img\s[^>]*>", text, re.I):
        tag = m.group(0)
        if 'width="300"' in tag or "width:300px" in tag:
            continue
        start = m.end()
        snippet = text[start : start + 400]
        if "<p" in snippet:
            continue
        if re.match(r"\s*\n\s*---", snippet):
            continue
        line_no = text[: m.start()].count("\n") + 1
        issues.append(f"{path}:{line_no}: story <img> has no credit <p> before next section")

    for m in re.finditer(r"<p[^>]*>", text, re.I):
        tag = m.group(0)
        ctx = text[m.start() : m.start() + 120]
        if "Credit:" in ctx or "credit:" in ctx.lower():
            if CREDIT_STYLE not in tag:
                line_no = text[: m.start()].count("\n") + 1
                issues.append(
                    f"{path}:{line_no}: credit line should use standard grey 12px style (see docs/listmonk-markup.md)"
                )

    return issues


def check_images(text: str, path: Path) -> list[str]:
    issues: list[str] = []
    for url in IMG_SRC.findall(text):
        req = urllib.request.Request(url, method="GET", headers={"Range": "bytes=0-0"})
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                if resp.status >= 400:
                    issues.append(f"{path}: {url} → HTTP {resp.status}")
        except urllib.error.HTTPError as e:
            issues.append(f"{path}: {url} → HTTP {e.code}")
        except OSError as e:
            issues.append(f"{path}: {url} → {e}")
    return issues


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("draft", type=Path, help="Path to draft markdown/HTML fragment")
    parser.add_argument(
        "--check-images",
        action="store_true",
        help="HEAD-request each lists.littleblueletter.com/uploads URL",
    )
    args = parser.parse_args()

    if not args.draft.is_file():
        print(f"Not found: {args.draft}", file=sys.stderr)
        return 2

    text = args.draft.read_text(encoding="utf-8")
    issues = lint(text, args.draft)
    if args.check_images:
        issues.extend(check_images(text, args.draft))

    if issues:
        for item in issues:
            print(item)
        print(f"\n{len(issues)} issue(s).", file=sys.stderr)
        return 1

    print(f"OK: {args.draft}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

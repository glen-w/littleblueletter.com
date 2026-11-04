"""Shared helpers for TinyLetter archive images."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

# Default Word "profile picture" embedded in many curator .docx files — not newsletter art.
DOCX_PROFILE_PLACEHOLDER_SHA256 = (
    "95960f5ae576f9a25f18b468cd617b18b747fba471e3c1c3c21de25d635c44a5"
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def is_docx_profile_placeholder(path: Path) -> bool:
    if not path.is_file():
        return False
    return sha256_file(path) == DOCX_PROFILE_PLACEHOLDER_SHA256


def placeholder_basenames(letters_dir: Path) -> set[str]:
    if not letters_dir.is_dir():
        return set()
    return {
        path.name
        for path in letters_dir.iterdir()
        if path.is_file() and is_docx_profile_placeholder(path)
    }


def strip_docx_profile_placeholders(html: str, placeholder_names: set[str]) -> str:
    """Drop img tags for known docx profile placeholders and paired photo credits."""
    if not placeholder_names:
        return html

    removed = False
    for name in placeholder_names:
        pattern = rf'<img\b[^>]*\bsrc="[^"]*{re.escape(name)}"[^>]*/?>'
        html, n = re.subn(pattern, "", html, flags=re.I)
        removed = removed or n > 0

    if not removed:
        return html

    # Centered © / credit lines tied to a removed inline photo.
    html = re.sub(
        r'<p\b[^>]*text-align:\s*center[^>]*>\s*'
        r'(?:<span[^>]*>\s*)?©[\s\S]*?</p>\s*',
        "",
        html,
        flags=re.I,
    )
    html = re.sub(r"<p\b[^>]*>\s*</p>\s*", "", html, flags=re.I)
    html = re.sub(
        r'<div\b[^>]*text-align:\s*center[^>]*>\s*<em>[\s\S]*?(?:©|\(VNA/|\(Photo)[\s\S]*?</em>[\s\S]*?</div>\s*',
        "",
        html,
        flags=re.I,
    )
    return html

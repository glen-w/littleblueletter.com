#!/usr/bin/env python3
"""Recover TinyLetter images: Wayback, live URLs, and lax local inference."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import time
import zipfile
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from email import message_from_bytes
from email.policy import default
from pathlib import Path
from urllib.parse import unquote, urlparse

import requests

ROOT = Path(__file__).resolve().parents[1]
ISSUES = ROOT / "archive" / "issues"
MANIFEST = ROOT / "archive" / "manifest.json"
CACHE = ROOT / "ingest" / "images"
OUT = ROOT / "ingest" / "out"
MAP_PATH = OUT / "image_map.json"
INFERENCE_PATH = OUT / "image_inference.json"
CONTENT = Path("/Users/89298/Documents/Little Blue Letter/content")
MAIL = Path("/Users/89298/email/gmail/Projects.sbd/Little Blue Letter")
GALLERY_PREFIX = (
    "gallery.tinyletterapp.com/c74940307bb5fd2ea298a5cddfbc83c472da22db/images/"
)
IMAGE_EXT = {".png", ".jpg", ".jpeg", ".gif", ".webp"}
MIN_BYTES = 8_000
TOPIC_WORDS = (
    "whale",
    "shark",
    "plastic",
    "coral",
    "turtle",
    "krill",
    "dolphin",
    "seal",
    "fish",
    "ocean",
    "reef",
    "sargassum",
    "nudi",
    "penguin",
    "octopus",
    "jelly",
    "manta",
    "seabird",
    "trash",
    "pollution",
    "microplastic",
    "bbnj",
    "mpa",
    "fisheries",
    "ice",
    "polar",
    "pirate",
    "submarine",
    "kelp",
    "seagrass",
    "mangrove",
)
SESSION = requests.Session()
SESSION.headers["User-Agent"] = (
    "LittleBlueLetterArchive/1.0 (personal archive; contact glenwright.earth)"
)


@dataclass
class LocalAsset:
    path: Path
    sha256: str
    size: int
    when: date
    name_date: date | None
    is_gif: bool
    is_screenshot: bool
    kind: str  # content | gifs | docx | mail


@dataclass
class MapRow:
    url: str
    file: str = ""
    source: str = "missing"
    bytes: int = 0
    local: str = ""
    slug: str = ""
    canonical_url: str = ""


def normalize_url(url: str) -> str:
    url = url.replace("&amp;", "&").strip()
    if "#" in url and "gallery.tinyletterapp.com" in url:
        tail = url.split("#", 1)[1]
        if tail.startswith("http"):
            return tail
    return url


def canonical_gallery(url: str) -> str:
    url = normalize_url(url)
    if "gallery.tinyletterapp.com" in url:
        return url
    return url


def filename_for(url: str) -> str:
    url = normalize_url(url)
    name = Path(urlparse(url).path).name
    name = unquote(name)
    name = re.sub(r"[^A-Za-z0-9._-]", "", name) or "image"
    return name


def cache_name_for(url: str) -> str:
    url = normalize_url(url)
    if "giphy.com" in url:
        m = re.search(r"/media/([^/]+)/", url)
        if m:
            return f"giphy-{re.sub(r'[^A-Za-z0-9._-]', '', m.group(1))}.gif"
        digest = hashlib.sha256(url.encode()).hexdigest()[:16]
        return f"giphy-{digest}.gif"
    base = filename_for(url)
    if base in {"giphy.gif", "image"} or len(base) < 6:
        digest = hashlib.sha256(url.encode()).hexdigest()[:16]
        ext = Path(urlparse(url).path).suffix.lower() or ".bin"
        if ext not in IMAGE_EXT:
            ext = ".jpg"
        return f"ext-{digest}{ext}"
    return base


def hash_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def file_when(path: Path) -> date:
    st = path.stat()
    ts = getattr(st, "st_birthtime", None) or st.st_mtime
    return datetime.fromtimestamp(ts).date()


def _safe_date(y: int, m: int, d: int) -> date | None:
    try:
        return date(y, m, d)
    except ValueError:
        return None


def parse_filename_date(name: str) -> date | None:
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", name)
    if m:
        return _safe_date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    m = re.search(r"(\d{2})(\d{2})(\d{2})_", name)
    if m:
        yy, mm, dd = int(m.group(1)), int(m.group(2)), int(m.group(3))
        return _safe_date(2000 + yy if yy < 70 else 1900 + yy, mm, dd)
    m = re.search(r"(\d{1,2})\s+(\d{1,2})\s+(\d{4})", name)
    if m:
        return _safe_date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
    m = re.search(r"(\d{2})_(\d{2})_(\d{4})", name)
    if m:
        return _safe_date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
    return None


def all_img_urls() -> list[str]:
    """Every http(s) img src as it appears in issue HTML (publish looks up exact URL)."""
    found: list[str] = []
    seen: set[str] = set()
    for path in sorted(ISSUES.glob("*.html")):
        for url in img_urls_in_html(path.read_text(encoding="utf-8")):
            if not url.startswith("http"):
                continue
            if url not in seen:
                seen.add(url)
                found.append(url)
    return found


def urls_to_fetch(urls: list[str]) -> list[str]:
    """Subset we attempt to download (skip bare googleusercontent hosts)."""
    out: list[str] = []
    seen: set[str] = set()
    for url in urls:
        canon = canonical_gallery(url)
        if "gallery.tinyletterapp.com" in canon:
            key = canon
        elif is_fetchable_external(url):
            key = url
        else:
            continue
        if key not in seen:
            seen.add(key)
            out.append(key)
    return out


def is_fetchable_external(url: str) -> bool:
    if "giphy.com" in url and "/media/" in url:
        return True
    host = urlparse(url).netloc.lower()
    if host in {"giphy.com", "www.giphy.com"}:
        return False
    if host.endswith("googleusercontent.com"):
        return False
    if "tinyletterapp.com" in host:
        return False
    return any(
        host.endswith(suffix)
        for suffix in (
            "bbci.co.uk",
            "tumblr.com",
            "twimg.com",
            "iddri.org",
            "wri.org",
            "nereusprogram.org",
            "cdnsciencepub.com",
            "gifs.com",
            "gif-finder.com",
        )
    ) or host in {"media.giphy.com", "media2.giphy.com"}


def img_urls_in_html(html: str) -> list[str]:
    urls: list[str] = []
    for tag in re.findall(r"<img\b[^>]*>", html, flags=re.I):
        m = re.search(r'src=["\']([^"\']+)["\']', tag, flags=re.I)
        if m:
            urls.append(normalize_url(m.group(1)))
    return urls


def cdx_hits() -> dict[str, str]:
    endpoint = "https://web.archive.org/cdx/search/cdx"
    params = {
        "url": f"{GALLERY_PREFIX}*",
        "fl": "timestamp,original,statuscode",
        "filter": "statuscode:200",
        "collapse": "urlkey",
        "output": "json",
        "limit": "5000",
    }
    try:
        response = SESSION.get(endpoint, params=params, timeout=180)
        response.raise_for_status()
    except requests.RequestException as exc:
        print(f"cdx failed: {exc}", flush=True)
        return {}
    rows = response.json()
    hits: dict[str, str] = {}
    for row in rows[1:]:
        timestamp, original, _status = row
        hits[filename_for(original)] = timestamp
    return hits


def looks_like_image(data: bytes) -> bool:
    if not data or data[:20].lstrip().startswith(b"<"):
        return False
    head = data[:12]
    return (
        head.startswith(b"\x89PNG")
        or head.startswith(b"GIF")
        or head[:3] == b"\xff\xd8\xff"
        or head.startswith(b"RIFF")
        or head.startswith(b"WEBP")
    )


def fetch_bytes(url: str, timestamp: str | None = None) -> tuple[bytes | None, str]:
    if timestamp:
        capture = f"https://web.archive.org/web/{timestamp}id_/{url}"
        label = "wayback"
    else:
        capture = url
        label = "live"
    try:
        response = SESSION.get(capture, timeout=60)
    except requests.RequestException:
        return None, "error"
    if response.status_code == 429:
        return None, "http-429"
    if response.status_code != 200 or not response.content:
        return None, f"http-{response.status_code}"
    if not looks_like_image(response.content):
        return None, "html"
    return response.content, label


def wayback_available(url: str) -> tuple[bytes | None, str]:
    try:
        response = SESSION.get(
            "https://archive.org/wayback/available",
            params={"url": url},
            timeout=40,
        )
    except requests.RequestException:
        return None, "error"
    if response.status_code == 429:
        return None, "http-429"
    if response.status_code != 200:
        return None, f"http-{response.status_code}"
    closest = (response.json().get("archived_snapshots") or {}).get("closest") or {}
    if not closest.get("available"):
        return None, "no-capture"
    snapshot = re.sub(r"/web/(\d+)/", r"/web/\1id_/", closest["url"], count=1)
    try:
        got = SESSION.get(snapshot, timeout=60)
    except requests.RequestException:
        return None, "error"
    if got.status_code == 429:
        return None, "http-429"
    if got.status_code == 200 and looks_like_image(got.content):
        return got.content, "wayback"
    return None, "no-capture"


def recover_url(url: str, cdx: dict[str, str], slow: bool) -> tuple[str, bytes | None, str]:
    url = normalize_url(url)
    name = cache_name_for(url)
    dest = CACHE / name
    if dest.exists() and dest.stat().st_size > 0:
        return name, dest.read_bytes(), "cached"

    if is_fetchable_external(url):
        data, status = fetch_bytes(url)
        if not data:
            data, status = wayback_available(url)
        if data:
            return name, data, status
        return name, None, status

    gallery_name = filename_for(url)
    ts = cdx.get(gallery_name)
    if ts:
        data, status = fetch_bytes(url, ts)
        if data:
            return name, data, status

    data, status = wayback_available(url)
    if data:
        return name, data, status

    if slow and status in {"http-429", "error"}:
        time.sleep(2.5)
        data, status = wayback_available(url)
        if data:
            return name, data, status

    return name, None, status


def local_hashes() -> dict[str, str]:
    found: dict[str, str] = {}
    if CONTENT.exists():
        for path in CONTENT.rglob("*"):
            if path.suffix.lower() not in IMAGE_EXT or not path.is_file():
                continue
            if path.stat().st_size < MIN_BYTES:
                continue
            found.setdefault(hash_file(path), f"content:{path.name}")
        for path in CONTENT.rglob("*.docx"):
            try:
                with zipfile.ZipFile(path) as archive:
                    for name in archive.namelist():
                        if not name.startswith("word/media/"):
                            continue
                        data = archive.read(name)
                        if len(data) < MIN_BYTES:
                            continue
                        found.setdefault(hash_bytes(data), f"docx:{path.name}")
            except zipfile.BadZipFile:
                continue
    if MAIL.exists():
        raw_parts = MAIL.read_bytes().split(b"\nFrom ")
        for blob in raw_parts:
            if b"image/" not in blob:
                continue
            if not blob.startswith(b"From "):
                blob = b"From " + blob
            message = message_from_bytes(blob, policy=default)
            subject = str(message.get("subject") or "")
            if "Little Blue" not in subject and "Ocean" not in subject:
                continue
            for part in message.walk():
                if not (part.get_content_type() or "").startswith("image/"):
                    continue
                data = part.get_payload(decode=True) or b""
                if len(data) < 20_000:
                    continue
                found.setdefault(hash_bytes(data), f"mail:{subject[:60]}")
    return found


def build_local_pool() -> list[LocalAsset]:
    pool: list[LocalAsset] = []
    if not CONTENT.exists():
        return pool

    def add(path: Path, kind: str) -> None:
        if path.suffix.lower() not in IMAGE_EXT or not path.is_file():
            return
        size = path.stat().st_size
        if size < MIN_BYTES:
            return
        name = path.name.lower()
        pool.append(
            LocalAsset(
                path=path,
                sha256=hash_file(path),
                size=size,
                when=file_when(path),
                name_date=parse_filename_date(path.name),
                is_gif=path.suffix.lower() == ".gif",
                is_screenshot="capture" in name,
                kind=kind,
            )
        )

    for path in CONTENT.iterdir():
        if path.is_file():
            add(path, "content")
    gifs_dir = CONTENT / "gifs"
    if gifs_dir.is_dir():
        for path in gifs_dir.rglob("*"):
            add(path, "gifs")

    for path in CONTENT.rglob("*.docx"):
        try:
            with zipfile.ZipFile(path) as archive:
                for name in archive.namelist():
                    if not name.startswith("word/media/"):
                        continue
                    data = archive.read(name)
                    if len(data) < MIN_BYTES:
                        continue
                    ext = Path(name).suffix.lower() or ".png"
                    digest = hash_bytes(data)[:16]
                    cache_path = CACHE / f"docx-{path.stem[:40]}-{digest}{ext}"
                    if not cache_path.exists():
                        cache_path.write_bytes(data)
                    doc_date = parse_filename_date(path.name) or file_when(path)
                    pool.append(
                        LocalAsset(
                            path=cache_path,
                            sha256=hash_bytes(data),
                            size=len(data),
                            when=doc_date,
                            name_date=doc_date,
                            is_gif=ext == ".gif",
                            is_screenshot=False,
                            kind="docx",
                        )
                    )
        except zipfile.BadZipFile:
            continue
    return pool


def in_window(asset: LocalAsset, issue: date) -> bool:
    start = issue - timedelta(days=3)
    end = issue + timedelta(days=1 if asset.is_screenshot else 0)
    for candidate in (asset.when, asset.name_date):
        if candidate and start <= candidate <= end:
            return True
    return False


def nearest_docx(issue: date) -> Path | None:
    best: tuple[int, Path] | None = None
    for path in CONTENT.glob("*.docx"):
        doc_date = parse_filename_date(path.name)
        if not doc_date:
            continue
        delta = abs((doc_date - issue).days)
        if delta > 14:
            continue
        if best is None or delta < best[0]:
            best = (delta, path)
    return best[1] if best else None


def docx_media_for(path: Path) -> list[LocalAsset]:
    out: list[LocalAsset] = []
    doc_date = parse_filename_date(path.name) or file_when(path)
    try:
        with zipfile.ZipFile(path) as archive:
            for name in archive.namelist():
                if not name.startswith("word/media/"):
                    continue
                data = archive.read(name)
                if len(data) < MIN_BYTES:
                    continue
                ext = Path(name).suffix.lower() or ".png"
                digest = hash_bytes(data)[:16]
                cache_path = CACHE / f"docx-{path.stem[:40]}-{digest}{ext}"
                if not cache_path.exists():
                    cache_path.write_bytes(data)
                out.append(
                    LocalAsset(
                        path=cache_path,
                        sha256=hash_bytes(data),
                        size=len(data),
                        when=doc_date,
                        name_date=doc_date,
                        is_gif=ext == ".gif",
                        is_screenshot=False,
                        kind="docx",
                    )
                )
    except zipfile.BadZipFile:
        pass
    return out


def context_keywords(html: str, url: str) -> set[str]:
    idx = html.find(url)
    if idx < 0:
        return set()
    snippet = html[max(0, idx - 400) : idx + 400].lower()
    words = set(re.findall(r"[a-z]{4,}", snippet))
    return {w for w in TOPIC_WORDS if w in words or w in snippet}


def assign_cache_name(slug: str, n: int, asset: LocalAsset) -> str:
    ext = asset.path.suffix.lower() or ".jpg"
    base = re.sub(r"[^a-z0-9-]", "", asset.path.stem.lower())[:40]
    return f"inferred-{slug}-{n}-{base}{ext}"


def infer_for_issue(
    slug: str,
    issue_date: date,
    missing_urls: list[str],
    html: str,
    pool: list[LocalAsset],
    used_paths: set[Path],
    used_shas: set[str],
) -> list[dict]:
    audit: list[dict] = []
    if not missing_urls:
        return audit

    window = [a for a in pool if a.path not in used_paths and a.sha256 not in used_shas and in_window(a, issue_date)]
    docx = nearest_docx(issue_date)
    docx_media = docx_media_for(docx) if docx else []

    slot = 0
    for url in missing_urls:
        if "gallery.tinyletterapp.com" not in canonical_gallery(url):
            continue
        slot += 1
        chosen: LocalAsset | None = None
        reason = ""

        if docx_media and slot - 1 < len(docx_media):
            candidate = docx_media[slot - 1]
            if candidate.path not in used_paths:
                chosen, reason = candidate, "inferred:docx-order"

        if not chosen:
            keywords = context_keywords(html, url)
            if keywords:
                scored: list[tuple[int, LocalAsset]] = []
                for asset in window:
                    name = asset.path.name.lower()
                    score = sum(1 for kw in keywords if kw in name)
                    if score:
                        scored.append((score, asset))
                if scored:
                    scored.sort(key=lambda row: (-row[0], -row[1].size))
                    chosen, reason = scored[0][1], "inferred:topic"

        if not chosen and re.search(r"gif of the week", html, re.I):
            gifs = [a for a in window if a.is_gif or a.kind == "gifs"]
            if gifs:
                gifs.sort(key=lambda a: (-a.size, abs((a.when - issue_date).days)))
                chosen, reason = gifs[0], "inferred:gif-slot"

        if not chosen and window:
            window.sort(key=lambda a: (abs((a.when - issue_date).days), -a.size))
            chosen, reason = window[0], "inferred:mtime"

        if not chosen:
            named = [a for a in pool if a.path not in used_paths and a.name_date and in_window(a, issue_date)]
            if named:
                named.sort(key=lambda a: abs((a.name_date - issue_date).days))  # type: ignore[operator]
                chosen, reason = named[0], "inferred:filename-date"

        if not chosen:
            month_pool = [
                a
                for a in pool
                if a.path not in used_paths
                and a.when.year == issue_date.year
                and a.when.month == issue_date.month
            ]
            if month_pool:
                month_pool.sort(key=lambda a: (abs((a.when - issue_date).days), -a.size))
                chosen, reason = month_pool[0], "inferred:month"

        if not chosen:
            continue

        cache_name = assign_cache_name(slug, slot, chosen)
        dest = CACHE / cache_name
        if not dest.exists():
            shutil.copy2(chosen.path, dest)

        used_paths.add(chosen.path)
        used_shas.add(chosen.sha256)
        window = [a for a in window if a.path not in used_paths]

        audit.append(
            {
                "slug": slug,
                "url": url,
                "file": cache_name,
                "source": reason,
                "local_path": str(chosen.path),
                "issue_date": issue_date.isoformat(),
            }
        )
    return audit


def load_rows_from_map() -> dict[str, MapRow]:
    if not MAP_PATH.exists():
        return {}
    rows: dict[str, MapRow] = {}
    for item in json.loads(MAP_PATH.read_text(encoding="utf-8")):
        rows[item["url"]] = MapRow(
            url=item["url"],
            file=item.get("file") or "",
            source=item.get("source") or "missing",
            bytes=int(item.get("bytes") or 0),
            local=item.get("local") or "",
            slug=item.get("slug") or "",
        )
    return rows


def row_from_dict(item: dict) -> MapRow:
    return MapRow(
        url=item["url"],
        file=item.get("file", ""),
        source=item.get("source", "missing"),
        bytes=int(item.get("bytes") or 0),
        local=item.get("local", ""),
        slug=item.get("slug", ""),
    )


def load_saved_rows() -> dict[str, MapRow]:
    if not MAP_PATH.exists():
        return {}
    return {row_from_dict(item).url: row_from_dict(item) for item in json.loads(MAP_PATH.read_text())}


def hydrate_rows_from_cache(urls: list[str], rows: dict[str, MapRow]) -> None:
    for url in urls:
        name = cache_name_for(url)
        dest = CACHE / name
        if dest.exists() and dest.stat().st_size > 0:
            if url not in rows or not rows[url].file:
                rows[url] = MapRow(
                    url=url,
                    file=name,
                    source="cached",
                    bytes=dest.stat().st_size,
                )


def merge_canonical(rows: dict[str, MapRow]) -> None:
    """Point google proxy URLs at recovered gallery files when possible."""
    by_file: dict[str, str] = {}
    for url, row in rows.items():
        if row.file:
            by_file.setdefault(row.file, url)
    for url, row in list(rows.items()):
        if row.file:
            continue
        canon = canonical_gallery(url)
        if canon != url and canon in rows and rows[canon].file:
            parent = rows[canon]
            row.file = parent.file
            row.source = parent.source
            row.bytes = parent.bytes
            row.local = f"alias:{canon}"
            row.canonical_url = canon


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--infer-only",
        action="store_true",
        help="Skip network fetch; reuse ingest/images and image_map, then infer and rewrite map.",
    )
    args = parser.parse_args()

    CACHE.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    slug_dates = {entry["slug"]: date.fromisoformat(entry["date"]) for entry in manifest}

    all_urls = all_img_urls()
    urls = urls_to_fetch(all_urls)
    print(f"img src {len(all_urls)} fetch {len(urls)}", flush=True)

    rows = load_rows_from_map()
    hydrate_rows_from_cache(urls, rows)

    if not args.infer_only:
        print("cdx…", flush=True)
        cdx = cdx_hits()
        print(f"cdx hits {len(cdx)}", flush=True)

        for i, url in enumerate(urls, 1):
            existing = rows.get(url)
            if existing and existing.file and (CACHE / existing.file).exists():
                continue
            if existing and not existing.file and existing.local == "no-capture":
                continue
            name, data, status = recover_url(url, cdx, slow=True)
            if data:
                dest = CACHE / name
                if not dest.exists():
                    dest.write_bytes(data)
                rows[url] = MapRow(url=url, file=name, source=status, bytes=len(data))
            else:
                rows[url] = MapRow(url=url, source="missing", local=status)
            if i % 25 == 0:
                print(f"  fetch {i}/{len(urls)}", flush=True)
                time.sleep(0.3)
    else:
        print("infer-only: skipping Wayback/live fetch", flush=True)

    print("hashing local images…", flush=True)
    locals_by_hash = local_hashes()
    for url, row in rows.items():
        if not row.file:
            continue
        dest = CACHE / row.file
        if not dest.exists():
            continue
        digest = hash_file(dest)
        local = locals_by_hash.get(digest, "")
        if row.source == "cached":
            row.source = "wayback"
        if local:
            row.source = f"{row.source}+{local.split(':')[0]}"
            row.local = local
        row.bytes = dest.stat().st_size

    merge_canonical(rows)

    pool = build_local_pool()
    used_paths: set[Path] = set()
    used_shas: set[str] = set()
    for row in rows.values():
        if row.file and (CACHE / row.file).exists():
            used_shas.add(hash_file(CACHE / row.file))

    inference_log: list[dict] = []
    for entry in manifest:
        slug = entry["slug"]
        html = (ISSUES / f"{slug}.html").read_text(encoding="utf-8")
        issue_date = slug_dates[slug]
        ordered = img_urls_in_html(html)
        missing = [u for u in ordered if u not in rows or not rows[u].file]
        audits = infer_for_issue(slug, issue_date, missing, html, pool, used_paths, used_shas)
        for item in audits:
            rows[item["url"]] = MapRow(
                url=item["url"],
                file=item["file"],
                source=item["source"],
                bytes=(CACHE / item["file"]).stat().st_size,
                local=item["local_path"],
                slug=slug,
            )
            inference_log.append(item)

    merge_canonical(rows)
    for url in all_urls:
        if url in rows:
            continue
        canon = canonical_gallery(url)
        if canon in rows and rows[canon].file:
            parent = rows[canon]
            rows[url] = MapRow(
                url=url,
                file=parent.file,
                source=parent.source,
                bytes=parent.bytes,
                local=f"alias:{canon}",
            )

    mapping = []
    for url in all_urls:
        row = rows.get(url) or MapRow(url=url)
        mapping.append(
            {
                "url": row.url,
                "file": row.file,
                "source": row.source,
                "bytes": row.bytes,
                "local": row.local,
                "slug": row.slug,
            }
        )

    MAP_PATH.write_text(json.dumps(mapping, indent=2) + "\n", encoding="utf-8")
    INFERENCE_PATH.write_text(json.dumps(inference_log, indent=2) + "\n", encoding="utf-8")

    got = sum(1 for row in mapping if row["file"])
    inferred = sum(1 for row in mapping if str(row.get("source", "")).startswith("inferred:"))
    print(f"recovered {got} inferred {inferred} missing {len(mapping) - got}")
    print(f"-> {MAP_PATH}")
    print(f"-> {INFERENCE_PATH}")


if __name__ == "__main__":
    main()

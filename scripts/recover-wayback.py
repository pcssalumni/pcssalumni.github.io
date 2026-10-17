#!/usr/bin/env python3
"""Inventory and recover public pcssalumni.com files from the Internet Archive.

The script is intentionally conservative: inventory is the default, downloads need
an explicit --download flag, and files are capped by type and size. It never contacts
the current holder of pcssalumni.com.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import mimetypes
import os
import re
import time
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path
from recovery_http import open_recovery

CDX = "https://web.archive.org/cdx/search/cdx"
WAYBACK = "https://web.archive.org/web/{timestamp}id_/{original}"
USER_AGENT = "PCSS-Alumni-Preservation/1.0 (+https://pcssalumni.github.io/)"
ALLOWED_TYPES = {
    "text/html", "text/css", "text/javascript", "application/javascript",
    "application/x-javascript", "application/json", "application/xml",
    "text/xml", "text/plain", "application/rss+xml", "application/pdf",
    "image/jpeg", "image/png", "image/gif", "image/x-icon",
    "image/webp", "image/svg+xml", "audio/mpeg", "audio/mp4", "video/mp4",
    "font/woff", "font/woff2", "font/ttf", "application/font-woff", "application/x-font-ttf",
    "application/x-shockwave-flash", "application/octet-stream", "unk",
}


@dataclass
class Record:
    timestamp: str
    original: str
    mimetype: str
    length: int
    digest: str


def request(url: str, timeout: int = 90) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with open_recovery(req, scope='wayback', timeout=timeout) as response:
        return response.read()


def download(url: str, target: Path, timeout: int = 180) -> tuple[int, str]:
    """Stream one capture to disk and atomically promote it when complete."""
    request_object = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    temporary = target.with_name(target.name + ".part")
    temporary.parent.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256()
    size = 0
    try:
        with open_recovery(request_object, scope='wayback', timeout=timeout) as response, temporary.open("wb") as handle:
            while chunk := response.read(1024 * 1024):
                handle.write(chunk)
                digest.update(chunk)
                size += len(chunk)
        os.replace(temporary, target)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    return size, digest.hexdigest()


def inventory(domain: str, start: int, end: int) -> list[Record]:
    query = urllib.parse.urlencode({
        "url": f"{domain}/*", "output": "json", "filter": "statuscode:200",
        "fl": "timestamp,original,mimetype,length,digest", "collapse": "urlkey",
        "from": start, "to": end,
    })
    rows = json.loads(request(f"{CDX}?{query}"))
    headers = rows.pop(0)
    records = []
    for row in rows:
        item = dict(zip(headers, row))
        try: length = int(item.get("length", 0) or 0)
        except ValueError: length = 0
        records.append(Record(item["timestamp"], item["original"], item.get("mimetype", ""), length, item.get("digest", "")))
    return records


def target_path(record: Record, output: Path) -> Path | None:
    parsed = urllib.parse.urlsplit(record.original)
    host = (parsed.hostname or "").lower().removeprefix("www.")
    if host != "pcssalumni.com": return None
    raw = urllib.parse.unquote(parsed.path or "/").replace("\\", "/")
    parts = [part for part in raw.split("/") if part not in ("", ".", "..")]
    if not parts: parts = ["index.html"]
    elif raw.endswith("/"): parts.append("index.html")
    elif "." not in parts[-1]: parts.extend(["index.html"])
    safe = [re.sub(r"[^A-Za-z0-9._ -]+", "_", part)[:180] for part in parts]
    candidate = output.joinpath(*safe)
    try: candidate.resolve().relative_to(output.resolve())
    except ValueError: return None
    return candidate


def variant_path(record: Record, output: Path, target: Path) -> Path:
    key = hashlib.sha1(record.original.encode("utf-8")).hexdigest()[:16]
    return output / "_variants" / key / target.name


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--domain", default="pcssalumni.com")
    parser.add_argument("--from-year", type=int, default=2001)
    parser.add_argument("--to-year", type=int, default=2024)
    parser.add_argument("--output", type=Path, default=Path("legacy"))
    parser.add_argument("--inventory", type=Path, default=Path("data/wayback-inventory.json"))
    parser.add_argument("--refresh-inventory", action="store_true")
    parser.add_argument("--manifest", type=Path, default=Path("data/wayback-downloads.jsonl"))
    parser.add_argument("--download", action="store_true")
    parser.add_argument("--max-file-mb", type=int, default=50)
    parser.add_argument("--include-pdfs", action="store_true")
    parser.add_argument("--delay", type=float, default=0.3)
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--retries", type=int, default=3)
    parser.add_argument("--timeout", type=int, default=90, help="Per-read network timeout in seconds")
    parser.add_argument("--preserve-variants", action="store_true")
    args = parser.parse_args()

    if args.download and args.inventory.exists() and not args.refresh_inventory:
        records = [Record(**item) for item in json.loads(args.inventory.read_text(encoding="utf-8"))]
        print(f"Loaded inventory of {len(records)} archived URLs from {args.inventory}", flush=True)
    else:
        records = inventory(args.domain, args.from_year, args.to_year)
        args.inventory.parent.mkdir(parents=True, exist_ok=True)
        args.inventory.write_text(json.dumps([asdict(record) for record in records], indent=2) + "\n", encoding="utf-8")
        print(f"Saved inventory of {len(records)} archived URLs to {args.inventory}", flush=True)
    if not args.download: return

    args.output.mkdir(parents=True, exist_ok=True)
    max_bytes = args.max_file_mb * 1024 * 1024
    downloaded = skipped = failed = 0
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    prior_origins: dict[str, str] = {}
    prior_paths_by_origin: dict[str, Path] = {}
    if args.manifest.exists():
        for line in args.manifest.read_text(encoding="utf-8").splitlines():
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            if item.get("status") in ("downloaded", "existing") and item.get("path"):
                saved_path = Path(item["path"])
                if saved_path.exists():
                    original = item.get("original", "")
                    prior_origins[str(saved_path.resolve())] = original
                    if original:
                        prior_paths_by_origin[original] = saved_path
    manifest = args.manifest.open("a", encoding="utf-8")
    jobs: list[tuple[int, Record, Path]] = []
    scheduled_paths: set[Path] = set()
    for index, record in enumerate(records, start=1):
        prior_path = prior_paths_by_origin.get(record.original)
        if prior_path is not None and prior_path.exists():
            skipped += 1
            manifest.write(json.dumps({"status": "existing", "path": str(prior_path), **asdict(record)}) + "\n")
            manifest.flush()
            continue
        if record.mimetype not in ALLOWED_TYPES or record.length > max_bytes:
            skipped += 1
            manifest.write(json.dumps({"status": "skipped", "reason": "type-or-size", **asdict(record)}) + "\n")
            manifest.flush()
            continue
        if record.mimetype == "application/pdf" and not args.include_pdfs:
            skipped += 1
            manifest.write(json.dumps({"status": "skipped", "reason": "pdf-disabled", **asdict(record)}) + "\n")
            manifest.flush()
            continue
        target = target_path(record, args.output)
        if target is None:
            skipped += 1
            manifest.write(json.dumps({"status": "skipped", "reason": "unsafe-path", **asdict(record)}) + "\n")
            manifest.flush()
            continue
        resolved_target = target.resolve()
        if target.exists() and args.preserve_variants and prior_origins.get(str(resolved_target)) not in (None, record.original):
            target = variant_path(record, args.output, target)
            resolved_target = target.resolve()
        if target.exists():
            skipped += 1
            manifest.write(json.dumps({"status": "existing", "path": str(target), **asdict(record)}) + "\n")
            manifest.flush()
            continue
        if resolved_target in scheduled_paths:
            if args.preserve_variants:
                target = variant_path(record, args.output, target)
                resolved_target = target.resolve()
            else:
                skipped += 1
                manifest.write(json.dumps({"status": "skipped", "reason": "duplicate-target", "path": str(target), **asdict(record)}) + "\n")
                manifest.flush()
                continue
        scheduled_paths.add(resolved_target)
        jobs.append((index, record, target))

    def recover(job: tuple[int, Record, Path]) -> tuple[int, Record, Path, int | None, str | None, Exception | None]:
        index, record, target = job
        error: Exception | None = None
        for attempt in range(1, args.retries + 1):
            try:
                if args.delay:
                    time.sleep(args.delay)
                size, sha256 = download(WAYBACK.format(timestamp=record.timestamp, original=record.original), target, timeout=args.timeout)
                return index, record, target, size, sha256, None
            except Exception as caught:
                error = caught
                if attempt < args.retries:
                    time.sleep(attempt * 2)
        return index, record, target, None, None, error

    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, args.workers)) as executor:
        futures = [executor.submit(recover, job) for job in jobs]
        for future in concurrent.futures.as_completed(futures):
            index, record, target, size, sha256, error = future.result()
            if error is None:
                downloaded += 1
                manifest.write(json.dumps({"status": "downloaded", "path": str(target), "bytes": size, "sha256": sha256, **asdict(record)}) + "\n")
                print(f"[{index}/{len(records)}] {target} ({size} bytes)", flush=True)
            else:  # recovery should continue past isolated captures
                failed += 1
                manifest.write(json.dumps({"status": "failed", "error": str(error), **asdict(record)}) + "\n")
                print(f"FAILED {record.original}: {error}", flush=True)
            manifest.flush()
    manifest.close()
    print(f"Downloaded {downloaded}; skipped {skipped}; failed {failed}.")


if __name__ == "__main__":
    main()


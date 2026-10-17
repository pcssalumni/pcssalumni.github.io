#!/usr/bin/env python3
"""Recover public WordPress content from the surviving PCSS alumni site.

The live installation is treated as untrusted. The API currently prefixes JSON
with PHP notices and rewrites canonical links to an unrelated host. This tool
strips the notice prefix, never follows rewritten hosts, and downloads only
static files located under pcssalumni.com's wp-content/uploads directory.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import os
import time
import urllib.parse
import urllib.request
from pathlib import Path
from recovery_http import open_recovery

ORIGIN = "https://www.pcssalumni.com"
API = f"{ORIGIN}/wp-json/wp/v2"
USER_AGENT = "PCSS-Alumni-Preservation/1.0 (+https://pcssalumni.github.io/)"
ALLOWED_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".pdf",
    ".mp3", ".mp4", ".mov", ".wav", ".avi", ".wmv",
    ".doc", ".docx", ".odt", ".xps", ".xls", ".xlsx", ".ppt", ".pptx",
    ".htm", ".html", ".txt", ".zip",
}


def open_url(url: str, timeout: int = 180):
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    return open_recovery(request, scope='wordpress', timeout=timeout)


def extract_json(payload: bytes):
    text = payload.decode("utf-8-sig", errors="replace")
    candidates = [position for position in (text.find("["), text.find("{")) if position >= 0]
    for position in sorted(candidates):
        try:
            return json.loads(text[position:])
        except json.JSONDecodeError:
            continue
    raise ValueError("No valid JSON payload found after the PHP notice prefix")


def fetch_collection(kind: str, fields: str) -> list[dict]:
    collected: list[dict] = []
    page = 1
    while True:
        query = urllib.parse.urlencode({"per_page": 100, "page": page, "_fields": fields})
        with open_url(f"{API}/{kind}?{query}") as response:
            result = extract_json(response.read())
        if isinstance(result, dict) and result.get("code") == "rest_post_invalid_page_number":
            break
        if not isinstance(result, list):
            raise ValueError(f"Unexpected {kind} response: {type(result).__name__}")
        collected.extend(result)
        print(f"Fetched {kind} page {page}: {len(result)} records", flush=True)
        if len(result) < 100:
            break
        page += 1
        time.sleep(0.5)
    return collected


def safe_media_url(source_url: str) -> str | None:
    parsed = urllib.parse.urlsplit(source_url)
    marker = "/wp-content/uploads/"
    index = parsed.path.lower().find(marker)
    if index < 0:
        return None
    path = parsed.path[index:]
    return urllib.parse.urlunsplit(("https", "www.pcssalumni.com", path, parsed.query, ""))


def media_target(url: str, output: Path) -> Path | None:
    parsed = urllib.parse.urlsplit(url)
    marker = "/wp-content/uploads/"
    index = parsed.path.lower().find(marker)
    if index < 0:
        return None
    relative = urllib.parse.unquote(parsed.path[index + len(marker):]).replace("\\", "/")
    parts = [part for part in relative.split("/") if part not in ("", ".", "..")]
    if not parts or Path(parts[-1]).suffix.lower() not in ALLOWED_EXTENSIONS:
        return None
    safe = ["".join(character if character.isalnum() or character in "._ -" else "_" for character in part)[:180] for part in parts]
    target = output.joinpath(*safe)
    try:
        target.resolve().relative_to(output.resolve())
    except ValueError:
        return None
    return target


def stream_download(url: str, target: Path, max_bytes: int) -> tuple[int, str]:
    temporary = target.with_name(target.name + ".part")
    target.parent.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256()
    size = 0
    try:
        with open_url(url) as response, temporary.open("wb") as handle:
            declared = int(response.headers.get("Content-Length", "0") or 0)
            if declared > max_bytes:
                raise ValueError(f"declared size {declared} exceeds limit {max_bytes}")
            while chunk := response.read(1024 * 1024):
                size += len(chunk)
                if size > max_bytes:
                    raise ValueError(f"download exceeds limit {max_bytes}")
                handle.write(chunk)
                digest.update(chunk)
        os.replace(temporary, target)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    return size, digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("legacy/live-wordpress"))
    parser.add_argument("--download-media", action="store_true")
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--retries", type=int, default=3)
    parser.add_argument("--max-file-mb", type=int, default=2048)
    args = parser.parse_args()

    args.output.mkdir(parents=True, exist_ok=True)
    page_fields = "id,slug,date,modified,link,title,content,excerpt,parent,featured_media"
    post_fields = "id,slug,date,modified,link,title,content,excerpt,featured_media"
    media_fields = "id,slug,date,modified,link,title,caption,description,alt_text,media_type,mime_type,source_url,media_details"
    pages = fetch_collection("pages", page_fields)
    posts = fetch_collection("posts", post_fields)
    media = fetch_collection("media", media_fields)
    for name, items in (("pages", pages), ("posts", posts), ("media", media)):
        (args.output / f"{name}.json").write_text(json.dumps(items, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    summary = {"pages": len(pages), "posts": len(posts), "media": len(media), "origin": ORIGIN}
    (args.output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary), flush=True)
    if not args.download_media:
        return

    jobs: list[tuple[dict, str, Path]] = []
    seen_targets: set[Path] = set()
    for item in media:
        url = safe_media_url(item.get("source_url", ""))
        target = media_target(url, args.output / "media") if url else None
        if not url or not target or target.resolve() in seen_targets:
            continue
        seen_targets.add(target.resolve())
        jobs.append((item, url, target))

    manifest_path = args.output / "downloads.jsonl"
    manifest = manifest_path.open("a", encoding="utf-8")
    max_bytes = args.max_file_mb * 1024 * 1024

    def recover(job):
        item, url, target = job
        if target.exists():
            return {"status": "existing", "id": item.get("id"), "url": url, "path": str(target)}
        error = None
        for attempt in range(1, args.retries + 1):
            try:
                size, sha256 = stream_download(url, target, max_bytes)
                return {"status": "downloaded", "id": item.get("id"), "url": url, "path": str(target), "bytes": size, "sha256": sha256}
            except Exception as caught:
                error = caught
                if attempt < args.retries:
                    time.sleep(attempt * 2)
        return {"status": "failed", "id": item.get("id"), "url": url, "path": str(target), "error": str(error)}

    counts: dict[str, int] = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, args.workers)) as executor:
        futures = [executor.submit(recover, job) for job in jobs]
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            counts[result["status"]] = counts.get(result["status"], 0) + 1
            manifest.write(json.dumps(result, ensure_ascii=False) + "\n")
            manifest.flush()
            print(f"{result['status'].upper()}: {result['path']}", flush=True)
    manifest.close()
    print(json.dumps(counts), flush=True)


if __name__ == "__main__":
    main()


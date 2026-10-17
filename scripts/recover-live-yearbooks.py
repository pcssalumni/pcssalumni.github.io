#!/usr/bin/env python3
"""Recover the public yearbook PDFs still served by pcssalumni.com."""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import os
import time
import urllib.request
from pathlib import Path
from recovery_http import open_recovery

ORIGIN = "https://www.pcssalumni.com/PDF"
USER_AGENT = "PCSS-Alumni-Preservation/1.0 (+https://pcssalumni.github.io/)"


def has_pdf_signature(path: Path) -> bool:
    try:
        with path.open("rb") as handle:
            return handle.read(5) == b"%PDF-"
    except OSError:
        return False


def filenames() -> list[str]:
    names = ["YB-1930.pdf"]
    for year in range(1951, 2018):
        if year == 2002:
            names.extend(("YB-2002-J.pdf", "YB-2002-S.pdf"))
        else:
            names.append(f"YB-{year}.pdf")
    return names


def stream_download(url: str, target: Path, max_bytes: int) -> tuple[int, str]:
    temporary = target.with_name(target.name + ".part")
    existing = temporary.stat().st_size if temporary.exists() else 0
    headers = {"User-Agent": USER_AGENT}
    if existing:
        headers["Range"] = f"bytes={existing}-"
    request = urllib.request.Request(url, headers=headers)
    target.parent.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256()
    size = 0
    if existing:
        with temporary.open("rb") as saved:
            while chunk := saved.read(1024 * 1024):
                digest.update(chunk)
                size += len(chunk)
    with open_recovery(request, scope='yearbooks', timeout=300) as response:
        content_type = response.headers.get("Content-Type", "").lower()
        if "text/html" in content_type:
            temporary.unlink(missing_ok=True)
            raise ValueError(f"server returned {content_type} instead of a PDF")
        append = existing > 0 and response.status == 206
        if not append:
            existing = size = 0
            digest = hashlib.sha256()
        declared = int(response.headers.get("Content-Length", "0") or 0) + existing
        if declared > max_bytes:
            raise ValueError(f"declared size {declared} exceeds limit {max_bytes}")
        with temporary.open("ab" if append else "wb") as handle:
            while chunk := response.read(1024 * 1024):
                size += len(chunk)
                if size > max_bytes:
                    raise ValueError(f"download exceeds limit {max_bytes}")
                handle.write(chunk)
                digest.update(chunk)
    with temporary.open("rb") as handle:
        if handle.read(5) != b"%PDF-":
            temporary.unlink(missing_ok=True)
            raise ValueError("download does not have a PDF signature")
    os.replace(temporary, target)
    return size, digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("legacy/live-yearbooks"))
    parser.add_argument("--manifest", type=Path, default=Path("data/live-yearbook-downloads.jsonl"))
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--retries", type=int, default=5)
    parser.add_argument("--max-file-mb", type=int, default=2048)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    args.manifest.parent.mkdir(parents=True, exist_ok=True)

    recovered_2017 = Path("legacy/PDF/YB-2017.pdf")
    target_2017 = args.output / "YB-2017.pdf"
    if recovered_2017.exists() and not target_2017.exists():
        try:
            os.link(recovered_2017, target_2017)
        except OSError:
            target_2017 = recovered_2017

    def recover(name: str) -> dict:
        target = args.output / name
        url = f"{ORIGIN}/{name}"
        if name == "YB-2017.pdf" and recovered_2017.exists() and not target.exists():
            return {"status": "existing", "url": url, "path": str(recovered_2017), "bytes": recovered_2017.stat().st_size}
        if target.exists() and has_pdf_signature(target):
            return {"status": "existing", "url": url, "path": str(target), "bytes": target.stat().st_size}
        error = None
        for attempt in range(1, args.retries + 1):
            try:
                size, sha256 = stream_download(url, target, args.max_file_mb * 1024 * 1024)
                return {"status": "downloaded", "url": url, "path": str(target), "bytes": size, "sha256": sha256}
            except Exception as caught:
                error = caught
                if attempt < args.retries:
                    time.sleep(attempt * 3)
        return {"status": "failed", "url": url, "path": str(target), "error": str(error)}

    counts: dict[str, int] = {}
    manifest = args.manifest.open("a", encoding="utf-8")
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, args.workers)) as executor:
        futures = [executor.submit(recover, name) for name in filenames()]
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            counts[result["status"]] = counts.get(result["status"], 0) + 1
            manifest.write(json.dumps(result) + "\n")
            manifest.flush()
            print(f"{result['status'].upper()}: {result['path']}", flush=True)
    manifest.close()
    print(json.dumps(counts), flush=True)


if __name__ == "__main__":
    main()


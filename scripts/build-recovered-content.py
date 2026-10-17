"""Build clean Quarto pages from recovered PCSS Alumni HTML.

The original pages contain obsolete WordPress chrome, scripts, forms and links.
This script keeps the historical article body, copies locally recovered media,
and emits self-contained first-party pages for the GitHub Pages site.
"""

from __future__ import annotations

import hashlib
import shutil
from pathlib import Path
from urllib.parse import unquote, urlparse

from bs4 import BeautifulSoup, NavigableString, Tag


ROOT = Path(__file__).resolve().parents[1]
LEGACY = ROOT / "legacy"
MEDIA = ROOT / "assets" / "recovered"


PAGES = {
    "association.qmd": {
        "title": "Alumni Association · PCSS Alumni Archive",
        "description": "Recovered mission, committee history, constitution and bylaws of the PCSS Alumni Association.",
        "eyebrow": "Recovered association records",
        "heading": "The Alumni Association.",
        "intro": "Mission, committee history, constitution and bylaws preserved from the former alumni website.",
        "sources": [
            ("mission", "Mission and mandate", "Mandate.html", ".entry"),
            ("committee", "Alumni Association Committee", "AAC.html", ".entry"),
            ("constitution", "Constitution and bylaws", "Constitution.html", ".entry"),
        ],
    },
    "school-life.qmd": {
        "title": "School Life · PCSS Alumni Archive",
        "description": "Recovered PCSS newspapers, school plays and athletics records.",
        "eyebrow": "Recovered school collections",
        "heading": "School life.",
        "intro": "Newspapers, productions and athletics material preserved from the former alumni website.",
        "sources": [
            ("newspapers", "School newspapers", "reportcreditcopy/index.html", ".entry-content"),
            ("plays", "School plays", "school-plays-2/index.html", ".entry-content"),
            ("athletics", "Athletics", "sports/index.html", ".entry-content"),
        ],
    },
    "events.qmd": {
        "title": "Alumni Events · PCSS Alumni Archive",
        "description": "Recovered PCSS Alumni Nights, commencements and photographs.",
        "eyebrow": "Recovered event collections",
        "heading": "Alumni events.",
        "intro": "Alumni Nights, commencements and photographs preserved from the former alumni website.",
        "sources": [
            ("alumni-nights", "Alumni Nights", "alumni-night/index.html", ".entry-content"),
            ("commencements", "Commencements", "commencements/index.html", ".entry-content"),
            ("photographs", "Photo gallery", "photopage/index.html", ".entry-content"),
        ],
    },
    "course-calendars.qmd": {
        "title": "Course Calendars · PCSS Alumni Archive",
        "description": "Recovered Port Credit Secondary School course calendars.",
        "eyebrow": "Recovered school documents",
        "heading": "Course calendars.",
        "intro": "Course calendar material preserved from the former alumni website.",
        "sources": [
            ("course-calendars", "Course calendars", "course-calendars/index.html", ".entry-content"),
        ],
    },
}


STORY_FILES = [
    "PCS-AboutFootball.html",
    "PCS-Collip.html",
    "PCS-Prank.html",
    "PCS-Click.html",
    "PCS-Football.html",
    "PCS-For.html",
    "PCS-Arn.html",
    "PCS-Lunchbag.html",
    "PCS-Memories-LH.html",
    "PCS-Memories-PG.html",
    "PCS-Choirs.html",
    "PCS-Pistons.html",
    "PCS-Riding-Shotgun.html",
    "PCS-Contest.html",
    "PCS-Track.html",
    "PCS-EndsEarth.html",
    "PCS-Manure.html",
    "PCS-Memory.html",
    "PCS-Mortal.html",
]


def local_source(value: str, html_path: Path) -> Path | None:
    value = value.strip()
    if not value or value.startswith(("data:", "mailto:", "javascript:", "#")):
        return None
    parsed = urlparse(value)
    path_text = unquote(parsed.path).replace("\\", "/")
    candidates: list[Path] = []
    if parsed.netloc:
        if "pcssalumni.com" not in parsed.netloc.lower():
            return None
        candidates.append(LEGACY / path_text.lstrip("/"))
    else:
        candidates.append((html_path.parent / path_text).resolve())
        candidates.append(LEGACY / path_text.lstrip("/"))
    for candidate in candidates:
        try:
            candidate.relative_to(LEGACY.resolve())
        except ValueError:
            continue
        if candidate.is_file():
            return candidate
    return None


def copy_asset(source: Path, page_slug: str) -> str:
    digest = hashlib.sha1(str(source).encode("utf-8")).hexdigest()[:10]
    safe_name = f"{source.stem}-{digest}{source.suffix.lower()}"
    destination = MEDIA / page_slug / safe_name
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    return destination.relative_to(ROOT).as_posix()


def clean_fragment(html_path: Path, selector: str, page_slug: str) -> str:
    soup = BeautifulSoup(html_path.read_text(encoding="utf-8", errors="replace"), "html.parser")
    fragment = soup.select_one(selector)
    if fragment is None:
        raise RuntimeError(f"Missing {selector} in {html_path}")

    for tag in fragment.select("script, style, form, input, button, iframe, object, embed, audio, video, noscript"):
        tag.decompose()
    for comment in fragment.find_all(string=lambda text: getattr(text, "__class__", None).__name__ == "Comment"):
        comment.extract()

    for image in list(fragment.find_all("img")):
        source = local_source(image.get("src", ""), html_path)
        if source is None:
            alt = image.get("alt", "").strip()
            image.replace_with(NavigableString(alt)) if alt else image.decompose()
            continue
        image["src"] = copy_asset(source, page_slug)
        image.attrs = {key: value for key, value in image.attrs.items() if key in {"src", "alt", "title"}}
        image["loading"] = "lazy"

    for link in list(fragment.find_all("a")):
        target = local_source(link.get("href", ""), html_path)
        if target and target.suffix.lower() in {".pdf", ".doc", ".docx", ".jpg", ".jpeg", ".png", ".gif"}:
            link["href"] = copy_asset(target, page_slug)
            link.attrs = {"href": link["href"]}
        else:
            link.unwrap()

    allowed = {
        "p", "div", "span", "strong", "b", "em", "i", "u", "br", "hr",
        "h2", "h3", "h4", "h5", "h6", "ul", "ol", "li", "table", "thead",
        "tbody", "tfoot", "tr", "th", "td", "caption", "figure", "figcaption", "img", "a",
    }
    for tag in list(fragment.find_all(True)):
        if tag.name not in allowed:
            tag.unwrap()
        elif tag.name not in {"img", "a", "th", "td"}:
            tag.attrs = {}
        elif tag.name in {"th", "td"}:
            tag.attrs = {key: value for key, value in tag.attrs.items() if key in {"colspan", "rowspan"}}

    return fragment.decode_contents().strip()


def render_page(filename: str, spec: dict) -> None:
    page_slug = Path(filename).stem
    sections = []
    for anchor, title, source_name, selector in spec["sources"]:
        body = clean_fragment(LEGACY / source_name, selector, page_slug)
        sections.append(f'<section id="{anchor}" class="recovered-section"><h2>{title}</h2>{body}</section>')
    output = f'''---
title: "{spec['title']}"
description: "{spec['description']}"
---

```{{=html}}
<section class="page-hero"><div class="shell"><p class="eyebrow">{spec['eyebrow']}</p><h1>{spec['heading']}</h1><p>{spec['intro']}</p></div></section>

<div class="section shell prose recovered-content">
{''.join(sections)}
</div>
```
'''
    output = output.replace("—", " - ").replace("–", "-")
    (ROOT / filename).write_text(output, encoding="utf-8")


def render_stories() -> None:
    sections = []
    for story_file in STORY_FILES:
        source = LEGACY / story_file
        soup = BeautifulSoup(source.read_text(encoding="utf-8", errors="replace"), "html.parser")
        title_node = soup.select_one(".post .title")
        title = title_node.get_text(" ", strip=True) if title_node else source.stem
        title = title.replace(" --- ", " - ").replace("—", " - ").replace("–", "-")
        anchor = source.stem.lower().replace("pcs-", "").replace("_", "-")
        body = clean_fragment(source, ".entry", "stories")
        sections.append(f'<section id="{anchor}" class="recovered-section story"><h2>{title}</h2>{body}</section>')
    output = f'''---
title: "Alumni Stories · PCSS Alumni Archive"
description: "First-person stories and memories recovered from the former PCSS Alumni website."
---

```{{=html}}
<section class="page-hero"><div class="shell"><p class="eyebrow">Recovered first-person accounts</p><h1>Alumni stories.</h1><p>Memories and feature articles preserved from the former alumni website.</p></div></section>

<div class="section shell prose recovered-content">
{''.join(sections)}
</div>
```
'''
    output = output.replace("—", " - ").replace("–", "-")
    (ROOT / "stories.qmd").write_text(output, encoding="utf-8")


def main() -> None:
    if MEDIA.exists():
        shutil.rmtree(MEDIA)
    for filename, spec in PAGES.items():
        render_page(filename, spec)
    render_stories()


if __name__ == "__main__":
    main()

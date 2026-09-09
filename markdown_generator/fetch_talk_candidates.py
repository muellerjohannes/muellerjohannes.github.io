#!/usr/bin/env python3

"""Fetch talk candidates from trusted sources.

This is a conservative discovery crawler:
- starts from configured seed URLs
- follows same-domain links with event-like keywords
- extracts candidate snippets only when a configured name appears

Output is written to _data/talk_candidates.yml.
"""

from __future__ import annotations

import argparse
import datetime as dt
import html
import re
import sys
import unicodedata
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

try:
    import yaml
except ImportError as exc:  # pragma: no cover
    raise SystemExit(
        "Missing dependency: pyyaml. Install with `python3 -m pip install pyyaml`."
    ) from exc


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "_data"

SOURCES_PATH = DATA_DIR / "talk_sources.yml"
IDENTITY_PATH = DATA_DIR / "talk_identity.yml"
CANDIDATES_PATH = DATA_DIR / "talk_candidates.yml"


DISCOVERY_KEYWORDS = [
    "seminar",
    "colloqu",
    "talk",
    "lecture",
    "workshop",
    "conference",
    "program",
    "schedule",
    "speaker",
    "event",
    "calendar",
    "symposium",
]

TALK_CONTEXT_KEYWORDS = [
    "talk",
    "seminar",
    "colloquium",
    "lecture",
    "speaker",
    "workshop",
    "conference",
    "presentation",
    "invited",
]

MONTH_PATTERN = (
    r"jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|"
    r"jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?"
)

DATE_PATTERNS = [
    re.compile(r"\b(20\d{2})[-/](0[1-9]|1[0-2])[-/](0[1-9]|[12]\d|3[01])\b", re.I),
    re.compile(rf"\b({MONTH_PATTERN})\s+(20\d{{2}})\b", re.I),
    re.compile(rf"\b(0?[1-9]|[12]\d|3[01])\s+({MONTH_PATTERN})\s+(20\d{{2}})\b", re.I),
]


class SimpleHTMLExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.in_script = False
        self.in_style = False
        self.text_parts: List[str] = []
        self.links: List[str] = []
        self.title_parts: List[str] = []
        self._in_title = False

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]) -> None:
        if tag == "script":
            self.in_script = True
        elif tag == "style":
            self.in_style = True
        elif tag == "title":
            self._in_title = True

        if tag == "a":
            href = dict(attrs).get("href")
            if href:
                self.links.append(href)

    def handle_endtag(self, tag: str) -> None:
        if tag == "script":
            self.in_script = False
        elif tag == "style":
            self.in_style = False
        elif tag == "title":
            self._in_title = False
        elif tag in {"p", "div", "br", "li", "section", "article", "h1", "h2", "h3", "h4"}:
            self.text_parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self.in_script or self.in_style:
            return
        if self._in_title:
            self.title_parts.append(data)
        self.text_parts.append(data)

    @property
    def text(self) -> str:
        raw = html.unescape("".join(self.text_parts))
        raw = raw.replace("\xa0", " ")
        return re.sub(r"\n{3,}", "\n\n", raw)

    @property
    def title(self) -> str:
        title = html.unescape(" ".join(self.title_parts)).strip()
        return re.sub(r"\s+", " ", title)


@dataclass
class PageData:
    url: str
    domain: str
    title: str
    text: str
    links: List[str]


def load_yaml(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def save_yaml(path: Path, payload: Dict[str, Any]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(payload, handle, sort_keys=False, allow_unicode=False)


def normalize_text(value: Any) -> str:
    text = "" if value is None else str(value)
    folded = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    lowered = folded.lower()
    lowered = re.sub(r"[^a-z0-9\s:/._-]", " ", lowered)
    return re.sub(r"\s+", " ", lowered).strip()


def contains_any(text: str, terms: Iterable[str]) -> bool:
    return any(normalize_text(term) in text for term in terms)


def fetch_url(url: str, timeout: int = 20) -> Optional[str]:
    request = Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; TalkCandidateBot/0.1; +https://muellerjohannes.github.io)",
            "Accept": "text/html,application/xhtml+xml",
        },
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            content_type = response.headers.get("Content-Type", "")
            if "text/html" not in content_type and "application/xhtml+xml" not in content_type:
                return None
            charset = response.headers.get_content_charset() or "utf-8"
            raw = response.read()
            return raw.decode(charset, errors="replace")
    except Exception:
        return None


def parse_page(url: str, html_text: str) -> PageData:
    parser = SimpleHTMLExtractor()
    parser.feed(html_text)
    domain = urlparse(url).netloc.lower()
    return PageData(url=url, domain=domain, title=parser.title, text=parser.text, links=parser.links)


def is_same_domain(base_domain: str, target_url: str) -> bool:
    target_domain = urlparse(target_url).netloc.lower()
    return target_domain == base_domain or target_domain.endswith("." + base_domain)


def should_consider_link(url: str) -> bool:
    lowered = normalize_text(url)
    if not lowered.startswith("http"):
        return False
    if any(ext in lowered for ext in [".pdf", ".jpg", ".png", ".zip", ".ics"]):
        return False
    return contains_any(lowered, DISCOVERY_KEYWORDS)


def discover_links(page: PageData, max_new_links: int) -> List[str]:
    out: List[str] = []
    seen: Set[str] = set()
    base_domain = urlparse(page.url).netloc.lower()
    for href in page.links:
        candidate = urljoin(page.url, href)
        if candidate in seen:
            continue
        if not is_same_domain(base_domain, candidate):
            continue
        if not should_consider_link(candidate):
            continue
        seen.add(candidate)
        out.append(candidate)
        if len(out) >= max_new_links:
            break
    return out


def find_first_date(text: str) -> Tuple[str, str]:
    normalized = re.sub(r"\s+", " ", text)
    for pattern in DATE_PATTERNS:
        match = pattern.search(normalized)
        if not match:
            continue
        value = " ".join(part for part in match.groups() if part)
        precision = "day"
        if re.fullmatch(r"(20\d{2})\s(0[1-9]|1[0-2])\s(0[1-9]|[12]\d|3[01])", value):
            y, m, d = value.split()
            return f"{y}-{m}-{d}", precision
        if re.fullmatch(rf"({MONTH_PATTERN})\s(20\d{{2}})", value, re.I):
            precision = "month"
            parts = value.split()
            month = dt.datetime.strptime(parts[0][:3], "%b").month
            return f"{parts[1]}-{month:02d}", precision
        if re.fullmatch(rf"(0?[1-9]|[12]\d|3[01])\s({MONTH_PATTERN})\s(20\d{{2}})", value, re.I):
            day, month_name, year = value.split()
            month = dt.datetime.strptime(month_name[:3], "%b").month
            return f"{year}-{month:02d}-{int(day):02d}", precision
    return "", ""


def best_snippet(text: str, names: List[str], max_len: int = 500) -> Tuple[str, str]:
    lines = [re.sub(r"\s+", " ", line).strip() for line in text.splitlines() if line.strip()]
    normalized_names = [normalize_text(n) for n in names]
    for line in lines:
        nline = normalize_text(line)
        if any(name in nline for name in normalized_names):
            if contains_any(nline, TALK_CONTEXT_KEYWORDS):
                return line[:max_len], line
    for line in lines:
        nline = normalize_text(line)
        if any(name in nline for name in normalized_names):
            return line[:max_len], line
    return "", ""


def extract_candidate(
    page: PageData,
    source_id: str,
    names_exact: List[str],
    names_weak: List[str],
) -> Optional[Dict[str, Any]]:
    page_blob = normalize_text(" ".join([page.title, page.text]))
    all_names = names_exact + names_weak
    if not contains_any(page_blob, all_names):
        return None

    snippet, snippet_full = best_snippet(page.text, all_names)
    context_blob = normalize_text(" ".join([page.title, snippet_full or ""]))
    if not contains_any(context_blob, TALK_CONTEXT_KEYWORDS):
        return None

    date_value, date_precision = find_first_date(snippet_full or page.text)
    if not date_value:
        date_value, date_precision = find_first_date(page.text)

    speaker = ""
    for name in names_exact:
        if normalize_text(name) in page_blob:
            speaker = name
            break
    if not speaker:
        for name in names_weak:
            if normalize_text(name) in page_blob:
                speaker = name
                break

    title = page.title or "Talk candidate"
    if snippet and len(snippet) > 20:
        title = snippet[:180]

    return {
        "status": "candidate",
        "source_id": source_id,
        "source_domain": page.domain,
        "source_url": page.url,
        "url": page.url,
        "title": title,
        "speaker": speaker,
        "date": date_value,
        "date_precision": date_precision,
        "venue": page.domain,
        "location": "",
        "description": snippet,
        "fetched_at": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
    }


def crawl_source(
    source: Dict[str, Any],
    names_exact: List[str],
    names_weak: List[str],
    max_pages_default: int,
    max_links_per_page: int,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    if not source.get("enabled", True):
        return [], {"source_id": str(source.get("id", "unknown")), "enabled": False}
    source_id = str(source.get("id", "unknown"))
    seed_urls = source.get("seed_urls", [])
    max_pages = int(source.get("max_pages", max_pages_default))

    queue: List[str] = list(seed_urls)
    seen: Set[str] = set()
    candidates: List[Dict[str, Any]] = []
    fetch_ok = 0
    fetch_failed = 0

    while queue and len(seen) < max_pages:
        url = queue.pop(0)
        if url in seen:
            continue
        seen.add(url)

        html_text = fetch_url(url)
        if not html_text:
            fetch_failed += 1
            continue
        fetch_ok += 1
        page = parse_page(url, html_text)

        candidate = extract_candidate(page, source_id, names_exact, names_weak)
        if candidate:
            candidates.append(candidate)

        discovered = discover_links(page, max_links_per_page)
        for link in discovered:
            if link not in seen and link not in queue:
                queue.append(link)

    stats = {
        "source_id": source_id,
        "enabled": True,
        "seed_urls": len(seed_urls),
        "pages_seen": len(seen),
        "fetch_ok": fetch_ok,
        "fetch_failed": fetch_failed,
        "candidates_found": len(candidates),
    }
    return candidates, stats


def stable_key(item: Dict[str, Any]) -> str:
    return "|".join(
        [
            normalize_text(item.get("date", "")),
            normalize_text(item.get("title", "")),
            normalize_text(item.get("source_domain", "")),
            normalize_text(item.get("source_url", "")),
        ]
    )


def dedupe(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen: Set[str] = set()
    out: List[Dict[str, Any]] = []
    for item in items:
        key = stable_key(item)
        if key in seen:
            continue
        seen.add(key)
        out.append(item)
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch talk candidates from trusted web sources.")
    parser.add_argument("--max-pages", type=int, default=20, help="Max pages crawled per source")
    parser.add_argument("--max-links-per-page", type=int, default=25, help="Max discovered links followed per page")
    args = parser.parse_args()

    sources = load_yaml(SOURCES_PATH).get("sources", [])
    identity = load_yaml(IDENTITY_PATH)
    names_exact = identity.get("names", {}).get("exact", [])
    names_weak = identity.get("names", {}).get("weak", [])

    all_candidates: List[Dict[str, Any]] = []
    source_stats: List[Dict[str, Any]] = []
    for source in sources:
        source_candidates, stats = crawl_source(
            source=source,
            names_exact=names_exact,
            names_weak=names_weak,
            max_pages_default=args.max_pages,
            max_links_per_page=args.max_links_per_page,
        )
        source_stats.append(stats)
        all_candidates.extend(source_candidates)

    all_candidates = sorted(dedupe(all_candidates), key=lambda x: (x.get("date", ""), x.get("title", "")), reverse=True)

    payload = {
        "generated_at": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
        "scope": "europe-us",
        "source_stats": source_stats,
        "candidates": all_candidates,
    }
    save_yaml(CANDIDATES_PATH, payload)

    print(f"Wrote {len(all_candidates)} candidates to {CANDIDATES_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

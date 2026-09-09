#!/usr/bin/env python3

"""Automate publication updates from arXiv with Crossref enrichment.

Pipeline:
1) read existing publications.bib
2) fetch arXiv author page entries
3) merge new entries
4) enrich arXiv entries with Crossref metadata when available
5) write publication transition report for downstream news updates
"""

from __future__ import annotations

import datetime as dt
import json
import re
import unicodedata
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests
import urllib3
import yaml
from pybtex.database import BibliographyData, Entry, Person
from pybtex.database.input import bibtex
from pybtex.database.output import bibtex as bibtex_writer

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "_data"
GEN_DIR = ROOT / "markdown_generator"

CONFIG_PATH = DATA_DIR / "publication_sources.yml"
BIB_PATH = GEN_DIR / "publications.bib"
UPDATES_PATH = DATA_DIR / "publication_updates.yml"


def normalize_text(text: str) -> str:
    folded = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    lowered = folded.lower()
    lowered = re.sub(r"[^a-z0-9\s]", " ", lowered)
    return re.sub(r"\s+", " ", lowered).strip()


def request_text(url: str, timeout: int = 30) -> str:
    response = requests.get(
        url,
        timeout=timeout,
        verify=False,
        headers={"User-Agent": "PublicationUpdater/0.1 (+https://muellerjohannes.github.io)"},
    )
    response.raise_for_status()
    return response.text


def parse_arxiv_author_page(author_id: str) -> List[str]:
    html = request_text(f"https://arxiv.org/a/{author_id}.html")
    ids = set(re.findall(r"/abs/([0-9]{4}\.[0-9]{4,5}(?:v\d+)?)", html))
    return sorted(ids)


def parse_arxiv_abs(abs_id: str) -> Optional[Dict[str, Any]]:
    try:
        html = request_text(f"https://arxiv.org/abs/{abs_id}")
    except Exception:
        return None

    title_match = re.search(r'<meta\s+name="citation_title"\s+content="([^"]+)"', html)
    date_match = re.search(r'<meta\s+name="citation_date"\s+content="([^"]+)"', html)
    doi_match = re.search(r'<meta\s+name="citation_doi"\s+content="([^"]+)"', html)
    journal_match = re.search(r"Journal reference:\s*</span>\s*([^<]+)<", html)
    authors = re.findall(r'<meta\s+name="citation_author"\s+content="([^"]+)"', html)

    if not title_match:
        return None

    title = title_match.group(1).strip()
    date_raw = date_match.group(1).strip() if date_match else ""
    year = ""
    if date_raw:
        year_match = re.match(r"(\d{4})", date_raw)
        if year_match:
            year = year_match.group(1)

    return {
        "arxiv_id": abs_id,
        "title": title,
        "authors": authors,
        "year": year,
        "doi": doi_match.group(1).strip() if doi_match else "",
        "journal_ref": journal_match.group(1).strip() if journal_match else "",
        "url": f"https://arxiv.org/abs/{abs_id}",
    }


def crossref_enrich(title: str, author_variants: List[str]) -> Optional[Dict[str, Any]]:
    try:
        response = requests.get(
            "https://api.crossref.org/works",
            params={"query.title": title, "rows": 5},
            timeout=30,
            verify=False,
            headers={"User-Agent": "PublicationUpdater/0.1 (+https://muellerjohannes.github.io)"},
        )
        response.raise_for_status()
        items = response.json().get("message", {}).get("items", [])
    except Exception:
        return None

    target = normalize_text(title)
    author_targets = [normalize_text(v) for v in author_variants]
    for item in items:
        titles = item.get("title", [])
        if not titles:
            continue
        cand_title = titles[0]
        cand_norm = normalize_text(cand_title)
        if target not in cand_norm and cand_norm not in target:
            continue

        authors = item.get("author", [])
        author_blob = " ".join(
            normalize_text(f"{a.get('given', '')} {a.get('family', '')}") for a in authors
        )
        if author_targets and not any(v in author_blob for v in author_targets):
            continue

        year = ""
        for key in ["published-print", "published-online", "issued"]:
            parts = item.get(key, {}).get("date-parts", [])
            if parts and parts[0]:
                year = str(parts[0][0])
                break

        container = ""
        container_list = item.get("container-title", [])
        if container_list:
            container = container_list[0]

        doi = item.get("DOI", "")
        if not doi:
            continue

        return {
            "title": cand_title,
            "year": year,
            "venue": container,
            "doi": doi,
            "url": item.get("URL", f"https://doi.org/{doi}"),
            "type": item.get("type", ""),
        }

    return None


def load_config() -> Dict[str, Any]:
    with CONFIG_PATH.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def load_bib() -> BibliographyData:
    parser = bibtex.Parser()
    return parser.parse_file(str(BIB_PATH))


def entry_arxiv_id(entry: Entry) -> str:
    for key in ["eprint", "arxiv", "arxiv_id", "url"]:
        value = entry.fields.get(key, "")
        if "arxiv.org/abs/" in value:
            return value.split("/abs/")[-1]
        if re.match(r"\d{4}\.\d{4,5}(v\d+)?", value):
            return value
    return ""


def is_arxiv_entry(entry: Entry) -> bool:
    journal = entry.fields.get("journal", "")
    if "arxiv" in normalize_text(journal):
        return True
    return bool(entry_arxiv_id(entry))


def build_state(entries: Dict[str, Entry]) -> Dict[str, Dict[str, str]]:
    state: Dict[str, Dict[str, str]] = {}
    for key, entry in entries.items():
        title = entry.fields.get("title", "")
        doi = entry.fields.get("doi", "")
        arxiv_id = entry_arxiv_id(entry)
        identifier = doi or arxiv_id or normalize_text(title)
        pub_state = "arxiv" if is_arxiv_entry(entry) else "published"
        state[identifier] = {
            "key": key,
            "title": title,
            "state": pub_state,
            "venue": entry.fields.get("journal", entry.fields.get("booktitle", "")),
            "year": entry.fields.get("year", ""),
            "url": entry.fields.get("url", entry.fields.get("paperurl", "")),
        }
    return state


def pick_key(arxiv_id: str, title: str, year: str) -> str:
    stem = re.sub(r"[^a-z0-9]", "", normalize_text(title))[:30]
    return f"jm{year or 'xxxx'}{stem}{arxiv_id.replace('.', '')[:8]}"


def merge_arxiv_entries(db: BibliographyData, arxiv_entries: List[Dict[str, Any]]) -> int:
    existing_ids = {entry_arxiv_id(e): k for k, e in db.entries.items() if entry_arxiv_id(e)}
    added = 0
    for item in arxiv_entries:
        arxiv_id = item["arxiv_id"]
        if arxiv_id in existing_ids:
            continue

        key = pick_key(arxiv_id, item["title"], item["year"])
        while key in db.entries:
            key = key + "x"

        fields = {
            "title": item["title"],
            "journal": f"arXiv preprint arXiv:{arxiv_id.split('v')[0]}",
            "year": item["year"] or str(dt.datetime.now().year),
            "url": item["url"],
            "eprint": arxiv_id,
        }
        if item.get("doi"):
            fields["doi"] = item["doi"]
        if item.get("journal_ref"):
            fields["note"] = item["journal_ref"]

        persons = {}
        if item.get("authors"):
            persons["author"] = [Person(a) for a in item["authors"]]

        db.entries[key] = Entry("article", fields=fields, persons=persons)
        added += 1
    return added


def enrich_and_upgrade(
    db: BibliographyData,
    author_variants: List[str],
) -> Tuple[int, int]:
    enriched = 0
    upgraded = 0
    for entry in db.entries.values():
        title = entry.fields.get("title", "")
        if not title:
            continue

        is_preprint = is_arxiv_entry(entry)
        has_published_venue = bool(entry.fields.get("booktitle")) or (
            "arxiv" not in normalize_text(entry.fields.get("journal", ""))
            and bool(entry.fields.get("journal"))
        )
        if has_published_venue and entry.fields.get("doi"):
            continue

        meta = crossref_enrich(title, author_variants)
        if not meta:
            continue

        changed = False
        if meta.get("doi") and not entry.fields.get("doi"):
            entry.fields["doi"] = meta["doi"]
            changed = True
        if meta.get("url"):
            entry.fields["url"] = meta["url"]
            changed = True
        if meta.get("year"):
            entry.fields["year"] = meta["year"]
            changed = True
        if meta.get("venue"):
            if meta.get("type", "").startswith("proceedings"):
                entry.fields["booktitle"] = meta["venue"]
            else:
                entry.fields["journal"] = meta["venue"]
            changed = True

        if changed:
            enriched += 1
            if is_preprint:
                upgraded += 1
    return enriched, upgraded


def write_bib(db: BibliographyData) -> None:
    writer = bibtex_writer.Writer()
    content = writer.to_string(db)
    BIB_PATH.write_text(content, encoding="utf-8")


def build_updates(old_state: Dict[str, Dict[str, str]], new_state: Dict[str, Dict[str, str]]) -> Dict[str, Any]:
    changes: List[Dict[str, str]] = []

    for identifier, item in new_state.items():
        before = old_state.get(identifier)
        if before is None:
            changes.append({**item, "change": "new_published" if item["state"] == "published" else "new_arxiv"})
            continue
        if before["state"] == "arxiv" and item["state"] == "published":
            changes.append({**item, "change": "arxiv_to_published"})

    payload = {
        "generated_at": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
        "changes": changes,
    }
    UPDATES_PATH.write_text(yaml.safe_dump(payload, sort_keys=False, allow_unicode=False), encoding="utf-8")
    return payload


def main() -> int:
    config = load_config()
    author_variants = config.get("name_variants", [])
    arxiv_author_id = config.get("arxiv_author_id", "")
    if not arxiv_author_id:
        raise SystemExit("Missing arxiv_author_id in _data/publication_sources.yml")

    db = load_bib()
    old_state = build_state(db.entries)

    arxiv_ids = parse_arxiv_author_page(arxiv_author_id)
    arxiv_entries = []
    for abs_id in arxiv_ids:
        item = parse_arxiv_abs(abs_id)
        if item:
            arxiv_entries.append(item)

    added = merge_arxiv_entries(db, arxiv_entries)
    enriched, upgraded = enrich_and_upgrade(db, author_variants)

    write_bib(db)

    new_state = build_state(db.entries)
    updates = build_updates(old_state, new_state)

    summary = {
        "added_arxiv": added,
        "enriched": enriched,
        "upgraded_arxiv_to_published": upgraded,
        "changes_total": len(updates.get("changes", [])),
    }
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

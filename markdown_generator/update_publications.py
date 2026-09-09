#!/usr/bin/env python3

"""Update publications with safer matching and deduplication.

Goals:
- add missing arXiv entries from author page
- upgrade preprints when published metadata is found
- prevent duplicate preprint/published records
- preserve curated capitalization where possible
"""

from __future__ import annotations

import datetime as dt
import json
import re
import unicodedata
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import requests
import yaml
from pybtex.database import BibliographyData, Entry, Person
from pybtex.database.input import bibtex
from pybtex.database.output import bibtex as bibtex_writer


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "_data"
GEN_DIR = ROOT / "markdown_generator"

CONFIG_PATH = DATA_DIR / "publication_sources.yml"
BIB_PATH = GEN_DIR / "publications.bib"
UPDATES_PATH = DATA_DIR / "publication_updates.yml"

SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "PublicationUpdater/0.2 (+https://muellerjohannes.github.io)"})


def normalize_text(text: str) -> str:
    # Convert common BibTeX/LaTeX accent commands to plain letters.
    cleaned = text
    cleaned = re.sub(r"\\[`'\"\^~=\.uvHcdbkrt]\{?([A-Za-z])\}?", r"\1", cleaned)
    cleaned = cleaned.replace("\\ss", "ss")
    cleaned = cleaned.replace("\\i", "i")
    cleaned = cleaned.replace("\\j", "j")
    cleaned = cleaned.replace("\\_", "_")
    cleaned = cleaned.replace("{", "").replace("}", "")
    cleaned = cleaned.replace("\\", "")
    folded = unicodedata.normalize("NFKD", cleaned).encode("ascii", "ignore").decode("ascii")
    lowered = folded.lower()
    lowered = re.sub(r"[^a-z0-9\s]", " ", lowered)
    return re.sub(r"\s+", " ", lowered).strip()


def title_fingerprint(title: str) -> str:
    text = normalize_text(title)
    for drop in ["a ", "an ", "the "]:
        if text.startswith(drop):
            text = text[len(drop) :]
    return text


def normalize_doi(doi: str) -> str:
    value = doi.strip().lower()
    value = re.sub(r"^https?://(dx\.)?doi\.org/", "", value)
    value = re.sub(r"^doi\s*[:]?\s*", "", value)
    return value


def clean_latex_escapes(value: str) -> str:
    return value.replace("\\\\_", "_").replace("\\_", "_").strip()


def extract_doi_from_url(url: str) -> str:
    if not url:
        return ""
    cleaned = clean_latex_escapes(url)
    m = re.search(r"10\.\d{4,9}/[^\s]+", cleaned)
    if not m:
        return ""
    return normalize_doi(m.group(0))


def parse_arxiv_id(value: str) -> str:
    if not value:
        return ""
    m = re.search(r"(\d{4}\.\d{4,5})(v\d+)?", value)
    return m.group(1) if m else ""


def is_auto_key(key: str) -> bool:
    return key.startswith("jm")


def request_text(url: str, timeout: int = 30) -> str:
    response = SESSION.get(url, timeout=timeout)
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

    def meta(name: str) -> str:
        m = re.search(rf'<meta\s+name="{name}"\s+content="([^"]+)"', html)
        return m.group(1).strip() if m else ""

    title = meta("citation_title")
    if not title:
        return None
    date_raw = meta("citation_date")
    year_match = re.match(r"(\d{4})", date_raw)
    year = year_match.group(1) if year_match else ""

    authors = re.findall(r'<meta\s+name="citation_author"\s+content="([^"]+)"', html)
    doi = clean_latex_escapes(meta("citation_doi"))
    journal_ref_match = re.search(r"Journal reference:\s*</span>\s*([^<]+)<", html)
    journal_ref = journal_ref_match.group(1).strip() if journal_ref_match else ""

    return {
        "arxiv_id": parse_arxiv_id(abs_id),
        "title": title,
        "authors": authors,
        "year": year,
        "doi": normalize_doi(doi),
        "journal_ref": journal_ref,
        "url": f"https://arxiv.org/abs/{parse_arxiv_id(abs_id) or abs_id}",
    }


def author_last_names_from_entry(entry: Entry) -> List[str]:
    out: List[str] = []
    for person in entry.persons.get("author", []):
        if person.last_names:
            out.append(normalize_text(person.last_names[0]))
    return [x for x in out if x]


def author_last_names_from_strings(authors: Iterable[str]) -> List[str]:
    out = []
    for author in authors:
        parts = normalize_text(author).split()
        if parts:
            out.append(parts[-1])
    return [x for x in out if x]


def entry_arxiv_id(entry: Entry) -> str:
    for key in ["eprint", "arxiv", "arxiv_id", "url", "journal"]:
        aid = parse_arxiv_id(entry.fields.get(key, ""))
        if aid:
            return aid
    return ""


def is_arxiv_entry(entry: Entry) -> bool:
    # Treat an entry as preprint only when the venue is explicitly arXiv.
    # Published entries can still carry an eprint/arXiv id for provenance.
    journal = normalize_text(entry.fields.get("journal", ""))
    if "arxiv preprint" in journal:
        return True
    if entry.fields.get("booktitle"):
        return False
    if entry.fields.get("doi") and journal and "arxiv" not in journal:
        return False
    return False


def is_published_entry(entry: Entry) -> bool:
    if entry.fields.get("doi"):
        return True
    if entry.fields.get("booktitle"):
        return True
    journal = normalize_text(entry.fields.get("journal", ""))
    return bool(journal) and "arxiv preprint" not in journal


def load_config() -> Dict[str, Any]:
    with CONFIG_PATH.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def load_bib() -> BibliographyData:
    parser = bibtex.Parser()
    return parser.parse_file(str(BIB_PATH))


def crossref_lookup_by_doi(doi: str) -> Optional[Dict[str, str]]:
    try:
        response = SESSION.get(f"https://api.crossref.org/works/{doi}", timeout=30)
        response.raise_for_status()
        item = response.json().get("message", {})
    except Exception:
        return None
    return crossref_to_fields(item)


def crossref_search_by_title(title: str, last_names: List[str]) -> Optional[Dict[str, str]]:
    try:
        response = SESSION.get(
            "https://api.crossref.org/works",
            params={"query.title": title, "rows": 5},
            timeout=30,
        )
        response.raise_for_status()
        items = response.json().get("message", {}).get("items", [])
    except Exception:
        return None

    target = title_fingerprint(title)
    for item in items:
        titles = item.get("title", [])
        if not titles:
            continue
        cand = title_fingerprint(titles[0])
        if target not in cand and cand not in target:
            continue

        if last_names:
            author_blob = " ".join(
                normalize_text(f"{a.get('given', '')} {a.get('family', '')}") for a in item.get("author", [])
            )
            if not any(name in author_blob for name in last_names):
                continue
        return crossref_to_fields(item)
    return None


def crossref_to_fields(item: Dict[str, Any]) -> Optional[Dict[str, str]]:
    doi = normalize_doi(item.get("DOI", ""))
    if not doi:
        return None

    year = ""
    for key in ["published-print", "published-online", "issued"]:
        parts = item.get(key, {}).get("date-parts", [])
        if parts and parts[0]:
            year = str(parts[0][0])
            break

    venue = ""
    container = item.get("container-title", [])
    if container:
        venue = container[0]

    kind = item.get("type", "")
    out = {
        "doi": doi,
        "year": year,
        "url": item.get("URL", f"https://doi.org/{doi}"),
        "title": item.get("title", [""])[0] if item.get("title") else "",
        "kind": kind,
        "venue": venue,
    }
    return out


def canonicalize_title(title: str) -> str:
    result = title
    replacements = {
        " rl ": " RL ",
        " pde ": " PDE ",
        " pdes ": " PDEs ",
        " pinn ": " PINN ",
        " pinns ": " PINNs ",
        " sciml ": " SciML ",
    }
    wrapped = f" {result} "
    for src, tgt in replacements.items():
        wrapped = re.sub(src, tgt, wrapped, flags=re.IGNORECASE)
    return wrapped.strip()


def parse_meta_title(html: str) -> str:
    patterns = [
        r'<meta\s+name="citation_title"\s+content="([^"]+)"',
        r'<meta\s+property="og:title"\s+content="([^"]+)"',
        r"<title>([^<]+)</title>",
    ]
    for pattern in patterns:
        m = re.search(pattern, html, flags=re.IGNORECASE)
        if m:
            title = m.group(1).strip()
            title = re.sub(r"\s+", " ", title)
            return title
    return ""


def trusted_title_from_url(url: str) -> str:
    if not url:
        return ""
    trusted_hosts = ["proceedings.mlr.press", "openreview.net", "dblp.org"]
    if not any(host in url for host in trusted_hosts):
        return ""
    try:
        html = request_text(url, timeout=30)
    except Exception:
        return ""
    title = parse_meta_title(html)
    if "openreview.net" in url and "| OpenReview" in title:
        title = title.replace("| OpenReview", "").strip()
    if "dblp.org" in url and title.endswith("- dblp"):
        title = title.replace("- dblp", "").strip()
    return title


def find_matching_key(db: BibliographyData, incoming: Dict[str, Any]) -> Optional[str]:
    in_doi = normalize_doi(incoming.get("doi", ""))
    in_arxiv = parse_arxiv_id(incoming.get("arxiv_id", ""))
    in_title = title_fingerprint(incoming.get("title", ""))
    in_last = set(author_last_names_from_strings(incoming.get("authors", [])))

    best_key = None
    best_score = -1

    for key, entry in db.entries.items():
        score = 0
        e_doi = normalize_doi(entry.fields.get("doi", ""))
        e_arxiv = entry_arxiv_id(entry)
        e_title = title_fingerprint(entry.fields.get("title", ""))
        e_last = set(author_last_names_from_entry(entry))

        if in_doi and e_doi and in_doi == e_doi:
            return key
        if in_arxiv and e_arxiv and in_arxiv == e_arxiv:
            return key

        if in_title and e_title:
            if in_title == e_title:
                score += 60
            elif in_title in e_title or e_title in in_title:
                score += 40
        if in_last and e_last:
            overlap = len(in_last.intersection(e_last))
            score += overlap * 12
        if is_published_entry(entry):
            score += 8
        if not is_auto_key(key):
            score += 5

        if score > best_score:
            best_score = score
            best_key = key

    return best_key if best_score >= 52 else None


def new_key_for_item(db: BibliographyData, incoming: Dict[str, Any]) -> str:
    year = incoming.get("year") or "xxxx"
    stem = re.sub(r"[^a-z0-9]", "", normalize_text(incoming.get("title", "")))[:24]
    arx = (incoming.get("arxiv_id") or "").replace(".", "")[:8]
    key = f"jm{year}{stem}{arx}"
    while key in db.entries:
        key += "x"
    return key


def apply_published_metadata(entry: Entry, meta: Dict[str, str]) -> bool:
    changed = False
    if meta.get("doi") and normalize_doi(entry.fields.get("doi", "")) != meta["doi"]:
        entry.fields["doi"] = meta["doi"]
        changed = True
    if meta.get("year") and entry.fields.get("year") != meta["year"]:
        entry.fields["year"] = meta["year"]
        changed = True
    if meta.get("url"):
        published_url = clean_latex_escapes(meta["url"])
        current = entry.fields.get("url", "")
        if not current or "arxiv.org/abs/" in current:
            entry.fields["url"] = published_url
            changed = True

    venue = meta.get("venue", "")
    if venue:
        if "proceedings" in meta.get("kind", "") or "conference" in meta.get("kind", ""):
            if entry.fields.get("booktitle") != venue:
                entry.fields["booktitle"] = venue
                changed = True
        else:
            if entry.fields.get("journal") != venue:
                entry.fields["journal"] = venue
                changed = True

    return changed


def ingest_arxiv(db: BibliographyData, arxiv_items: List[Dict[str, Any]]) -> Tuple[int, int]:
    added = 0
    upgraded = 0

    for item in arxiv_items:
        match_key = find_matching_key(db, item)
        if match_key:
            entry = db.entries[match_key]
            if item.get("arxiv_id") and not entry.fields.get("eprint"):
                entry.fields["eprint"] = item["arxiv_id"]
            if not entry.fields.get("url"):
                entry.fields["url"] = item["url"]
            if not entry.fields.get("year") and item.get("year"):
                entry.fields["year"] = item["year"]
            if item.get("doi") and not entry.fields.get("doi"):
                entry.fields["doi"] = item["doi"]
            continue

        key = new_key_for_item(db, item)
        fields = {
            "title": canonicalize_title(item["title"]),
            "journal": f"arXiv preprint arXiv:{item['arxiv_id']}",
            "year": item.get("year") or str(dt.datetime.now().year),
            "url": item["url"],
            "eprint": item["arxiv_id"],
        }
        if item.get("doi"):
            fields["doi"] = item["doi"]
        persons = {}
        if item.get("authors"):
            persons["author"] = [Person(a) for a in item["authors"]]
        db.entries[key] = Entry("article", fields=fields, persons=persons)
        added += 1

    for entry in db.entries.values():
        if not is_arxiv_entry(entry):
            continue

        title = entry.fields.get("title", "")
        if not title:
            continue

        meta = None
        doi = normalize_doi(entry.fields.get("doi", ""))
        if doi:
            meta = crossref_lookup_by_doi(doi)
        if not meta:
            meta = crossref_search_by_title(title, author_last_names_from_entry(entry))
        if not meta:
            continue

        before_published = is_published_entry(entry)
        changed = apply_published_metadata(entry, meta)
        if changed and not before_published and is_published_entry(entry):
            upgraded += 1

    return added, upgraded


def title_match_score(a: str, b: str) -> int:
    fa = title_fingerprint(a)
    fb = title_fingerprint(b)
    if not fa or not fb:
        return 0
    if fa == fb:
        return 100
    if fa in fb or fb in fa:
        return 70
    tokens_a = set(fa.split())
    tokens_b = set(fb.split())
    if not tokens_a or not tokens_b:
        return 0
    overlap = len(tokens_a.intersection(tokens_b))
    ratio = overlap / max(1, min(len(tokens_a), len(tokens_b)))
    if ratio >= 0.8:
        return 55
    if ratio >= 0.65:
        return 45
    return 0


def reconcile_preprint_published_pairs(db: BibliographyData) -> Tuple[int, int]:
    published_keys = [k for k, e in db.entries.items() if is_published_entry(e)]
    arxiv_keys = [k for k, e in db.entries.items() if is_arxiv_entry(e)]

    merged = 0
    removed = 0
    for akey in arxiv_keys:
        if akey not in db.entries:
            continue
        aentry = db.entries[akey]
        a_title = aentry.fields.get("title", "")
        a_auth = set(author_last_names_from_entry(aentry))
        a_year = int(aentry.fields.get("year", "0") or "0")

        best_pkey = ""
        best_score = 0
        best_entry: Optional[Entry] = None
        for pkey in published_keys:
            if pkey == akey:
                continue
            if pkey not in db.entries:
                continue
            pentry = db.entries[pkey]
            p_title = pentry.fields.get("title", "")
            p_auth = set(author_last_names_from_entry(pentry))
            p_year = int(pentry.fields.get("year", "0") or "0")

            tscore = title_match_score(a_title, p_title)
            if tscore < 55:
                continue
            overlap = len(a_auth.intersection(p_auth))
            if overlap == 0:
                continue

            year_bonus = 0
            if a_year and p_year and p_year >= a_year:
                year_bonus = 8
            score = tscore + overlap * 10 + year_bonus
            if score > best_score:
                best_score = score
                best_pkey = pkey
                best_entry = pentry

        if not best_pkey:
            continue

        pentry = best_entry if best_entry is not None else db.entries[best_pkey]

        # Safety: if arXiv candidate appears to describe a different version with
        # a distinct first author and only weak title overlap, keep both.
        a_first = author_last_names_from_entry(aentry)
        p_first = author_last_names_from_entry(pentry)
        first_author_diff = bool(a_first and p_first and a_first[0] != p_first[0])
        weak_match = title_match_score(a_title, pentry.fields.get("title", "")) < 90
        if first_author_diff and weak_match:
            continue

        merge_entry_fields(pentry, aentry)
        if akey in db.entries:
            del db.entries[akey]
            merged += 1
            removed += 1

    return merged, removed


def normalize_titles_from_trusted_sources(db: BibliographyData) -> int:
    updated = 0
    for entry in db.entries.values():
        current = entry.fields.get("title", "")
        if not current:
            continue
        url = entry.fields.get("url", "")
        candidate = trusted_title_from_url(url)
        if not candidate:
            continue

        # Update only when clearly same paper and candidate improves style.
        same_paper = title_match_score(current, candidate) >= 70
        if not same_paper:
            continue
        if current == candidate:
            continue

        current_norm = normalize_text(current)
        cand_norm = normalize_text(candidate)
        if current_norm == cand_norm or title_match_score(current, candidate) >= 90:
            entry.fields["title"] = candidate
            updated += 1

    return updated


def choose_better_entry(key_a: str, a: Entry, key_b: str, b: Entry) -> Tuple[str, Entry, str, Entry]:
    def score(key: str, entry: Entry) -> int:
        s = 0
        if is_published_entry(entry):
            s += 100
        if entry.fields.get("doi"):
            s += 45
        if entry.fields.get("booktitle"):
            s += 20
        if not is_auto_key(key):
            s += 25
        if entry.fields.get("url") and any(h in entry.fields.get("url", "") for h in ["proceedings.mlr.press", "openreview.net", "dblp.org"]):
            s += 15
        s += len([k for k, v in entry.fields.items() if str(v).strip()])
        return s

    if score(key_a, a) >= score(key_b, b):
        return key_a, a, key_b, b
    return key_b, b, key_a, a


def merge_entry_fields(dst: Entry, src: Entry) -> None:
    preferred_fields = [
        "title",
        "year",
        "journal",
        "booktitle",
        "doi",
        "url",
        "eprint",
        "pages",
        "volume",
        "number",
        "organization",
        "publisher",
        "note",
    ]
    for field in preferred_fields:
        dst_val = str(dst.fields.get(field, "")).strip()
        src_val = str(src.fields.get(field, "")).strip()
        if not src_val:
            continue
        if not dst_val:
            dst.fields[field] = src.fields[field]
            continue

        if field == "title":
            # keep curated title if present; otherwise prefer richer capitalization
            if dst_val.islower() or (dst_val.count("-") > src_val.count("-") and not src_val.islower()):
                dst.fields[field] = src.fields[field]
        elif field == "url":
            if "arxiv.org/abs/" in dst_val and "arxiv.org/abs/" not in src_val:
                dst.fields[field] = src.fields[field]
        elif field in {"journal", "booktitle"}:
            if "arxiv preprint" in normalize_text(dst_val) and "arxiv preprint" not in normalize_text(src_val):
                dst.fields[field] = src.fields[field]

    if "author" not in dst.persons and "author" in src.persons:
        dst.persons["author"] = src.persons["author"]


def sanitize_existing_fields(db: BibliographyData) -> int:
    updated = 0
    for entry in db.entries.values():
        doi = entry.fields.get("doi", "")
        if doi:
            normalized = normalize_doi(clean_latex_escapes(doi))
            if normalized and "/" not in normalized:
                from_url = extract_doi_from_url(entry.fields.get("url", ""))
                if from_url and "/" in from_url:
                    entry.fields["doi"] = from_url
                    updated += 1
                    continue
                repaired = crossref_search_by_title(
                    entry.fields.get("title", ""), author_last_names_from_entry(entry)
                )
                if repaired and repaired.get("doi") and "/" in repaired["doi"]:
                    if apply_published_metadata(entry, repaired):
                        updated += 1
                elif normalized != doi:
                    entry.fields["doi"] = normalized
                    updated += 1
            elif normalized and normalized != doi:
                entry.fields["doi"] = normalized
                updated += 1

        url = entry.fields.get("url", "")
        if url:
            cleaned_url = clean_latex_escapes(url)
            if cleaned_url != url:
                entry.fields["url"] = cleaned_url
                updated += 1
    return updated


def deduplicate(db: BibliographyData) -> Tuple[int, int]:
    groups: Dict[str, List[str]] = {}
    for key, entry in db.entries.items():
        doi = normalize_doi(entry.fields.get("doi", ""))
        arx = entry_arxiv_id(entry)
        title = title_fingerprint(entry.fields.get("title", ""))
        first_author = ""
        authors = author_last_names_from_entry(entry)
        if authors:
            first_author = authors[0]

        if doi:
            gid = f"doi:{doi}"
        elif arx:
            gid = f"arxiv:{arx}"
        else:
            gid = f"title:{title}|{entry.fields.get('year','')}|{first_author}"

        groups.setdefault(gid, []).append(key)

    removed = 0
    merged = 0
    for keys in groups.values():
        if len(keys) < 2:
            continue
        keeper_key = keys[0]
        keeper = db.entries[keeper_key]
        for other_key in keys[1:]:
            other = db.entries[other_key]
            best_key, best_entry, loser_key, loser_entry = choose_better_entry(keeper_key, keeper, other_key, other)
            merge_entry_fields(best_entry, loser_entry)
            if loser_key in db.entries:
                del db.entries[loser_key]
                removed += 1
                merged += 1
            keeper_key, keeper = best_key, best_entry

    return merged, removed


def build_state(entries: Dict[str, Entry]) -> Dict[str, Dict[str, str]]:
    out: Dict[str, Dict[str, str]] = {}
    for key, entry in entries.items():
        doi = normalize_doi(entry.fields.get("doi", ""))
        arx = entry_arxiv_id(entry)
        ident = arx or doi or title_fingerprint(entry.fields.get("title", ""))
        out[ident] = {
            "key": key,
            "title": entry.fields.get("title", ""),
            "state": "published" if is_published_entry(entry) else "arxiv",
            "venue": entry.fields.get("journal", entry.fields.get("booktitle", "")),
            "year": entry.fields.get("year", ""),
            "url": entry.fields.get("url", ""),
        }
    return out


def write_updates(old_state: Dict[str, Dict[str, str]], new_state: Dict[str, Dict[str, str]]) -> Dict[str, Any]:
    changes: List[Dict[str, str]] = []
    for ident, item in new_state.items():
        prev = old_state.get(ident)
        if prev is None:
            changes.append({**item, "change": "new_published" if item["state"] == "published" else "new_arxiv"})
            continue
        if prev["state"] == "arxiv" and item["state"] == "published":
            changes.append({**item, "change": "arxiv_to_published"})

    payload = {
        "generated_at": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
        "changes": changes,
    }
    UPDATES_PATH.write_text(yaml.safe_dump(payload, sort_keys=False, allow_unicode=False), encoding="utf-8")
    return payload


def write_bib(db: BibliographyData) -> None:
    content = bibtex_writer.Writer().to_string(db)
    BIB_PATH.write_text(content, encoding="utf-8")


def main() -> int:
    config = load_config()
    arxiv_author_id = config.get("arxiv_author_id", "")
    if not arxiv_author_id:
        raise SystemExit("Missing arxiv_author_id in _data/publication_sources.yml")

    db = load_bib()
    old_state = build_state(db.entries)

    arxiv_ids = parse_arxiv_author_page(arxiv_author_id)
    arxiv_items = []
    for abs_id in arxiv_ids:
        item = parse_arxiv_abs(abs_id)
        if item:
            arxiv_items.append(item)

    sanitized = sanitize_existing_fields(db)
    added, upgraded = ingest_arxiv(db, arxiv_items)
    reconciled, reconciled_removed = reconcile_preprint_published_pairs(db)
    merged, removed = deduplicate(db)
    title_updates = normalize_titles_from_trusted_sources(db)
    write_bib(db)

    new_state = build_state(db.entries)
    updates = write_updates(old_state, new_state)

    summary = {
        "added_arxiv": added,
        "upgraded_arxiv_to_published": upgraded,
        "reconciled_preprint_published": reconciled,
        "reconciled_removed": reconciled_removed,
        "merged_duplicates": merged,
        "removed_entries": removed,
        "title_updates_from_trusted_sources": title_updates,
        "sanitized_fields": sanitized,
        "changes_total": len(updates.get("changes", [])),
    }
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

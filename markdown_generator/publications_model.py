"""Single source of truth for publication identity, classification and venue.

Every consumer (the harvesting bot, the markdown generator, the tests) uses the
functions in this module.  Nothing else is allowed to decide whether a work is
a preprint, a workshop paper or a publication -- the Liquid templates only read
the ``type`` field that is written here.

Precedence, highest first:

1. ``_data/publication_overrides.yml``   -- your editorial decisions
2. ``markdown_generator/publications_manual.bib`` -- bibtex you paste by hand
3. ``markdown_generator/publications.bib``        -- bot-harvested records
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

import bibio

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "_data"
GEN_DIR = ROOT / "markdown_generator"

AUTO_BIB_PATH = GEN_DIR / "publications.bib"
MANUAL_BIB_PATH = GEN_DIR / "publications_manual.bib"
OVERRIDES_PATH = DATA_DIR / "publication_overrides.yml"
SOURCES_PATH = DATA_DIR / "publication_sources.yml"

PREPRINT = "preprint"
PUBLISHED = "published"
WORKSHOP = "workshop"

# Main-track venues that count as full publications even though they are
# conferences.  Matching is substring-based on the normalised venue string.
DEFAULT_MAIN_VENUE_MARKERS = [
    "international conference on machine learning",
    "conference on neural information processing systems",
    "advances in neural information processing systems",
    "international conference on learning representations",
    "mathematical and scientific machine learning",
    "artificial intelligence and statistics",
    "conference on learning theory",
    "learning for dynamics and control",
    "uncertainty in artificial intelligence",
]

# Acronyms only match as standalone tokens, so "ICML" hits but "icmlws" does not.
DEFAULT_MAIN_VENUE_ACRONYMS = ["icml", "neurips", "nips", "iclr", "msml", "aistats", "colt", "l4dc", "uai"]

# A venue is workshop-like when one of these matches AND the record carries no
# publisher DOI (see ``_has_publisher_doi``).  Deliberately narrow: "symposium"
# is not on the list, because most symposia are ordinary conferences.
DEFAULT_WORKSHOP_PATTERNS = [
    r"\bworkshop\b",
    r"\bworkshops\b",
    r"workshop track",
]

# DOI prefixes that indicate a real publisher record (journal, book series,
# proceedings volume).  A record with such a DOI is never demoted to workshop,
# which is what fixes special issues / post-proceedings of workshops.
NON_PUBLISHER_DOI_PREFIXES = ("10.48550",)  # arXiv


def normalize(text: str) -> str:
    text = (text or "").lower()
    text = re.sub(r"[{}\\]", "", text)
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())


def title_fingerprint(title: str) -> str:
    return normalize(title)


def parse_arxiv_id(value: str) -> str:
    if not value:
        return ""
    match = re.search(r"(\d{4}\.\d{4,5})(v\d+)?", value)
    if match:
        return match.group(1)
    match = re.search(r"arxiv[:/ ]\s*([a-z\-]+/\d{7})", value, re.IGNORECASE)
    return match.group(1) if match else ""


def normalize_doi(doi: str) -> str:
    doi = (doi or "").strip().replace("\\_", "_")
    doi = re.sub(r"^https?://(dx\.)?doi\.org/", "", doi, flags=re.IGNORECASE)
    doi = re.sub(r"^doi:\s*", "", doi, flags=re.IGNORECASE)
    return doi.strip().lower()


def entry_arxiv_id(fields: Dict[str, str]) -> str:
    for key in ("eprint", "arxiv", "archiveprefix_id", "url", "journal", "note"):
        aid = parse_arxiv_id(fields.get(key, ""))
        if aid:
            return aid
    return ""


def entry_doi(fields: Dict[str, str]) -> str:
    doi = normalize_doi(fields.get("doi", ""))
    if doi:
        return doi
    return normalize_doi(_doi_from_url(fields.get("url", "")))


def _doi_from_url(url: str) -> str:
    match = re.search(r"doi\.org/(10\.[^\s\"'<>]+)", url or "", re.IGNORECASE)
    return match.group(1) if match else ""


def _has_publisher_doi(fields: Dict[str, str]) -> bool:
    doi = entry_doi(fields)
    if not doi:
        return False
    return not doi.startswith(NON_PUBLISHER_DOI_PREFIXES)


def venue_of(fields: Dict[str, str]) -> str:
    """The venue as printed in the citation."""

    booktitle = (fields.get("booktitle") or "").strip()
    if booktitle:
        return booktitle
    journal = (fields.get("journal") or "").strip()
    if journal and not is_arxiv_venue(journal):
        return journal
    series = (fields.get("series") or "").strip()
    if series and _has_publisher_doi(fields):
        return series
    return journal


def is_arxiv_venue(venue: str) -> bool:
    return "arxiv preprint" in normalize(venue) or normalize(venue) == "arxiv"


# --------------------------------------------------------------------------
# configuration


def load_yaml(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def load_overrides(path: Optional[Path] = None) -> Dict[str, Dict[str, Any]]:
    """Return overrides keyed by normalised identifier.

    Keys accepted in the YAML file: an arXiv id (``"2402.07318"``), a DOI
    (``"doi:10.1007/..."``) or a title (``"title: ..."``).  All of them are
    normalised here so lookup is forgiving.
    """

    raw = load_yaml(path or OVERRIDES_PATH)
    items = raw.get("overrides", raw) or {}
    out: Dict[str, Dict[str, Any]] = {}
    if isinstance(items, dict):
        pairs = items.items()
    else:  # list form: [{id: ..., type: ...}, ...]
        pairs = [(item.get("id", ""), item) for item in items if isinstance(item, dict)]
    for key, value in pairs:
        if not isinstance(value, dict):
            continue
        out[_override_key(str(key))] = value
    return out


def _override_key(key: str) -> str:
    key = str(key).strip()
    lowered = key.lower()
    if lowered.startswith("doi:"):
        return "doi:" + normalize_doi(key[4:])
    if lowered.startswith("title:"):
        return "title:" + title_fingerprint(key[6:])
    if lowered.startswith("arxiv:"):
        return "arxiv:" + parse_arxiv_id(key[6:])
    arx = parse_arxiv_id(key)
    if arx and arx == key.strip():
        return "arxiv:" + arx
    if key.startswith("10."):
        return "doi:" + normalize_doi(key)
    return "title:" + title_fingerprint(key)


def override_for(fields: Dict[str, str], overrides: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    if not overrides:
        return {}
    arx = entry_arxiv_id(fields)
    if arx and f"arxiv:{arx}" in overrides:
        return overrides[f"arxiv:{arx}"]
    doi = entry_doi(fields)
    if doi and f"doi:{doi}" in overrides:
        return overrides[f"doi:{doi}"]
    key = "title:" + title_fingerprint(fields.get("title", ""))
    return overrides.get(key, {})


def workshop_patterns(config: Optional[Dict[str, Any]] = None) -> List[str]:
    config = config or {}
    extra = config.get("workshop_patterns") or []
    return list(DEFAULT_WORKSHOP_PATTERNS) + [str(x) for x in extra]


def main_venue_markers(config: Optional[Dict[str, Any]] = None) -> List[str]:
    config = config or {}
    extra = config.get("main_venue_markers") or []
    return DEFAULT_MAIN_VENUE_MARKERS + [normalize(str(x)) for x in extra]


def main_venue_acronyms(config: Optional[Dict[str, Any]] = None) -> List[str]:
    config = config or {}
    extra = config.get("main_venue_acronyms") or []
    return DEFAULT_MAIN_VENUE_ACRONYMS + [normalize(str(x)) for x in extra]


# --------------------------------------------------------------------------
# classification


def is_main_conference(venue: str, config: Optional[Dict[str, Any]] = None) -> bool:
    norm = normalize(venue)
    if not norm:
        return False
    if any(marker in norm for marker in main_venue_markers(config)):
        return True
    tokens = set(norm.split())
    return any(acronym in tokens for acronym in main_venue_acronyms(config))


def looks_like_workshop(venue: str, config: Optional[Dict[str, Any]] = None) -> bool:
    norm = normalize(venue)
    if not norm:
        return False
    return any(re.search(pattern, norm) for pattern in workshop_patterns(config))


def classify(
    fields: Dict[str, str],
    overrides: Optional[Dict[str, Dict[str, Any]]] = None,
    config: Optional[Dict[str, Any]] = None,
) -> str:
    """Return ``preprint`` | ``published`` | ``workshop`` for a bibtex entry.

    Rules, in order:

    1. an explicit override wins;
    2. a workshop-looking venue is a workshop paper *unless* the record has a
       publisher DOI (journal special issue, Springer volume, post-proceedings);
    3. an arXiv-only record is a preprint;
    4. everything else -- journals and main-track conferences -- is published.
    """

    override = override_for(fields, overrides or {})
    forced = str(override.get("type", "")).strip().lower()
    if forced in {PREPRINT, PUBLISHED, WORKSHOP}:
        return forced

    venue = str(override.get("venue") or venue_of(fields))

    if looks_like_workshop(venue, config) and not _has_publisher_doi(fields):
        if not is_main_conference(_strip_workshop_host(venue), config):
            return WORKSHOP
        return WORKSHOP

    if venue and not is_arxiv_venue(venue):
        return PUBLISHED

    if fields.get("booktitle"):
        return PUBLISHED
    if _has_publisher_doi(fields):
        return PUBLISHED
    return PREPRINT


def _strip_workshop_host(venue: str) -> str:
    """'Foo Workshop at ICML 2025' -> 'Foo Workshop' (the host is not the venue)."""

    return re.split(r"\bat\b", venue, maxsplit=1)[0]


def resolved_fields(
    fields: Dict[str, str],
    overrides: Optional[Dict[str, Dict[str, Any]]] = None,
    config: Optional[Dict[str, Any]] = None,
) -> Dict[str, str]:
    """Bibtex fields with overrides applied, plus ``type`` and ``venue``."""

    override = override_for(fields, overrides or {})
    out = dict(fields)
    for key in ("title", "year", "url", "venue", "note"):
        value = override.get(key)
        if value:
            out[key] = str(value)
    venue = str(override.get("venue") or venue_of(fields))
    out["venue"] = venue
    out["type"] = classify(fields, overrides, config)
    if override.get("hide"):
        out["hide"] = "true"
    return out


# --------------------------------------------------------------------------
# loading and merging the bibliographies


def _identity_keys(fields: Dict[str, str]) -> List[str]:
    keys = []
    arx = entry_arxiv_id(fields)
    if arx:
        keys.append(f"arxiv:{arx}")
    doi = entry_doi(fields)
    if doi:
        keys.append(f"doi:{doi}")
    fingerprint = title_fingerprint(fields.get("title", ""))
    if fingerprint:
        keys.append(f"title:{fingerprint}")
    return keys


def _record_rank(fields: Dict[str, str], manual: bool) -> tuple:
    """Higher is better when two records describe the same work."""

    venue = venue_of(fields)
    published = 0 if is_arxiv_venue(venue) or not venue else 1
    return (
        1 if manual else 0,
        published,
        1 if _has_publisher_doi(fields) else 0,
        len(fields),
    )


def load_works(
    auto_path: Optional[Path] = None,
    manual_path: Optional[Path] = None,
) -> List[Dict[str, Any]]:
    """Return one merged record per work.

    Each record is ``{"key", "type_", "fields", "persons", "manual"}`` where the
    fields of the weaker duplicate are merged in as a fallback (so the arXiv id
    of a preprint survives on the published record).
    """

    auto = bibio.parse_file(str(auto_path or AUTO_BIB_PATH))
    manual_file = manual_path or MANUAL_BIB_PATH
    manual = bibio.parse_file(str(manual_file)) if Path(manual_file).exists() else bibio.BibliographyData()

    records: List[Dict[str, Any]] = []
    for source, is_manual in ((auto, False), (manual, True)):
        for key, entry in source.entries.items():
            records.append(
                {
                    "key": key,
                    "type_": entry.type,
                    "fields": dict(entry.fields),
                    "persons": {role: list(people) for role, people in entry.persons.items()},
                    "manual": is_manual,
                }
            )

    merged: List[Dict[str, Any]] = []
    index: Dict[str, int] = {}
    for record in records:
        position = None
        for identity in _identity_keys(record["fields"]):
            if identity in index:
                position = index[identity]
                break
        if position is None:
            merged.append(record)
            position = len(merged) - 1
        else:
            existing = merged[position]
            winner, loser = (
                (record, existing)
                if _record_rank(record["fields"], record["manual"]) > _record_rank(existing["fields"], existing["manual"])
                else (existing, record)
            )
            fields = dict(loser["fields"])
            fields.update({k: v for k, v in winner["fields"].items() if v})
            # A published record must not inherit the preprint venue.
            if venue_of(winner["fields"]) and not is_arxiv_venue(venue_of(winner["fields"])):
                if is_arxiv_venue(fields.get("journal", "")):
                    fields.pop("journal", None)
            merged[position] = {
                "key": winner["key"],
                "type_": winner["type_"],
                "fields": fields,
                "persons": winner["persons"] or loser["persons"],
                "manual": winner["manual"] or loser["manual"],
            }
        for identity in _identity_keys(merged[position]["fields"]):
            index[identity] = position

    return _merge_near_duplicates(merged)


def _first_author(record: Dict[str, Any]) -> str:
    people = record.get("persons", {}).get("author") or []
    if not people:
        return ""
    return normalize(" ".join(people[0].last_names))


def titles_are_close(a: str, b: str) -> bool:
    """Conservative fuzzy title match for records that share no identifier."""

    fa, fb = title_fingerprint(a), title_fingerprint(b)
    if not fa or not fb:
        return False
    if fa == fb or fa in fb or fb in fa:
        return True
    ta, tb = set(fa.split()), set(fb.split())
    if len(ta) < 4 or len(tb) < 4:
        return False
    overlap = len(ta & tb) / min(len(ta), len(tb))
    return overlap >= 0.85


def _merge_near_duplicates(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for record in records:
        target = None
        for candidate in out:
            if not titles_are_close(record["fields"].get("title", ""), candidate["fields"].get("title", "")):
                continue
            if _first_author(record) and _first_author(candidate) and _first_author(record) != _first_author(candidate):
                continue
            try:
                year_gap = abs(int(record["fields"].get("year", 0)) - int(candidate["fields"].get("year", 0)))
            except (TypeError, ValueError):
                year_gap = 0
            if year_gap > 2:
                continue
            target = candidate
            break
        if target is None:
            out.append(record)
            continue
        winner, loser = (
            (record, target)
            if _record_rank(record["fields"], record["manual"]) > _record_rank(target["fields"], target["manual"])
            else (target, record)
        )
        fields = dict(loser["fields"])
        fields.update({k: v for k, v in winner["fields"].items() if v})
        if venue_of(winner["fields"]) and not is_arxiv_venue(venue_of(winner["fields"])):
            if is_arxiv_venue(fields.get("journal", "")):
                fields.pop("journal", None)
        target.update(
            {
                "key": winner["key"],
                "type_": winner["type_"],
                "fields": fields,
                "persons": winner["persons"] or loser["persons"],
                "manual": winner["manual"] or loser["manual"],
            }
        )
    return out

#!/usr/bin/env python3

"""Score and bucket talk candidates for manual review.

Usage:
  python3 markdown_generator/score_talk_candidates.py
  python3 markdown_generator/score_talk_candidates.py --write-candidates

By default this script does not modify canonical public talk data.
"""

from __future__ import annotations

import argparse
import datetime as dt
import re
import sys
import unicodedata
from pathlib import Path
from typing import Any, Dict, List, Tuple

try:
    import yaml
except ImportError as exc:  # pragma: no cover
    raise SystemExit(
        "Missing dependency: pyyaml. Install with `python3 -m pip install pyyaml`."
    ) from exc


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "_data"
DOCS_DIR = ROOT / "docs" / "automation"

IDENTITY_PATH = DATA_DIR / "talk_identity.yml"
SOURCES_PATH = DATA_DIR / "talk_sources.yml"
CANDIDATES_PATH = DATA_DIR / "talk_candidates.yml"
REPORT_PATH = DOCS_DIR / "talk-candidate-review.md"


def load_yaml(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Missing required file: {path}")
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


def contains_term(haystack: str, needle: str) -> bool:
    return normalize_text(needle) in haystack


def completeness_score(candidate: Dict[str, Any]) -> int:
    fields = ["url", "talk_url", "location", "description", "speaker", "affiliation", "venue"]
    return sum(1 for field in fields if str(candidate.get(field, "")).strip())


def source_priority(domain: str, trusted_domains: List[str]) -> int:
    norm_domain = normalize_text(domain)
    for idx, trusted in enumerate(trusted_domains):
        if trusted in norm_domain or norm_domain.endswith(trusted):
            return idx
    return len(trusted_domains) + 1


def classify(score: int) -> str:
    if score >= 70:
        return "high"
    if score >= 45:
        return "medium"
    return "low"


def score_candidate(
    candidate: Dict[str, Any],
    identity: Dict[str, Any],
    trusted_domains: List[str],
) -> Dict[str, Any]:
    score = 0
    reasons: List[str] = []

    speaker_norm = normalize_text(candidate.get("speaker", ""))
    title_norm = normalize_text(candidate.get("title", ""))
    venue_norm = normalize_text(candidate.get("venue", ""))
    location_norm = normalize_text(candidate.get("location", ""))
    desc_norm = normalize_text(candidate.get("description", ""))
    aff_norm = normalize_text(candidate.get("affiliation", ""))
    source_domain_norm = normalize_text(candidate.get("source_domain", ""))
    url_norm = normalize_text(candidate.get("url", "") or candidate.get("talk_url", ""))
    blob = " ".join(
        [speaker_norm, title_norm, venue_norm, location_norm, desc_norm, aff_norm, source_domain_norm, url_norm]
    )

    exact_names = identity.get("names", {}).get("exact", [])
    weak_names = identity.get("names", {}).get("weak", [])
    affils = identity.get("affiliations", [])
    coauthors = identity.get("coauthors", [])
    topics = identity.get("topics", [])
    negative_topics = identity.get("negative_topics", [])
    red_flags = identity.get("red_flags", [])
    manual_review_only_terms = identity.get("manual_review_only_if_contains", [])

    if any(contains_term(speaker_norm, name) for name in exact_names):
        score += 60
        reasons.append("+60 exact speaker name match")
    elif any(contains_term(blob, name) for name in exact_names):
        score += 40
        reasons.append("+40 exact name found in metadata")
    elif any(contains_term(blob, name) for name in weak_names):
        score += 20
        reasons.append("+20 weak name variant match")

    if any(contains_term(blob, affiliation) for affiliation in affils):
        score += 18
        reasons.append("+18 affiliation match")

    coauthor_hits = [name for name in coauthors if contains_term(blob, name)]
    if coauthor_hits:
        bonus = min(20, len(coauthor_hits) * 10)
        score += bonus
        reasons.append(f"+{bonus} coauthor match ({', '.join(coauthor_hits[:2])})")

    topic_hits = [keyword for keyword in topics if contains_term(blob, keyword)]
    if topic_hits:
        bonus = min(24, len(topic_hits) * 8)
        score += bonus
        reasons.append(f"+{bonus} topic match ({', '.join(topic_hits[:3])})")

    if any(trusted in source_domain_norm for trusted in trusted_domains):
        score += 10
        reasons.append("+10 trusted source domain")

    negative_hits = [keyword for keyword in negative_topics if contains_term(blob, keyword)]
    if negative_hits:
        penalty = 30
        score -= penalty
        reasons.append(f"-{penalty} negative topic match ({', '.join(negative_hits[:3])})")

    tum_flag = any(contains_term(blob, flag) for flag in red_flags)
    name_flag = any(contains_term(blob, n) for n in ["johannes muller", "johannes mueller"])
    bio_flag = any(contains_term(blob, k) for k in ["math bio", "biology"])
    if tum_flag and name_flag and bio_flag:
        score -= 45
        reasons.append("-45 TUM common-name red flag")

    bucket = classify(score)
    manual_review_only = False
    review_reason = ""
    if any(contains_term(blob, term) for term in manual_review_only_terms):
        manual_review_only = True
        if bucket == "high":
            bucket = "medium"
        review_reason = "manual-review-only term matched"
        reasons.append("manual review only policy applied")

    return {
        "score": score,
        "bucket": bucket,
        "reasons": reasons,
        "topic_hits": topic_hits,
        "negative_hits": negative_hits,
        "manual_review_only": manual_review_only,
        "manual_review_reason": review_reason,
    }


def dedupe_candidates(
    candidates: List[Dict[str, Any]],
    trusted_domains: List[str],
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    chosen: Dict[str, Dict[str, Any]] = {}
    dropped: List[Dict[str, Any]] = []

    for cand in candidates:
        key = "|".join(
            [
                normalize_text(cand.get("date", "")),
                normalize_text(cand.get("title", "")),
                normalize_text(cand.get("venue", "")),
            ]
        )
        if key == "||":
            key = normalize_text(cand.get("url", "") or cand.get("talk_url", "") or str(id(cand)))

        if key not in chosen:
            chosen[key] = cand
            continue

        old = chosen[key]
        old_rank = (
            int(old.get("score", -10**9)),
            completeness_score(old),
            -source_priority(old.get("source_domain", ""), trusted_domains),
        )
        new_rank = (
            int(cand.get("score", -10**9)),
            completeness_score(cand),
            -source_priority(cand.get("source_domain", ""), trusted_domains),
        )

        if new_rank > old_rank:
            dropped.append(old)
            chosen[key] = cand
        else:
            dropped.append(cand)

    return list(chosen.values()), dropped


def build_report(
    candidates: List[Dict[str, Any]],
    dedup_dropped: List[Dict[str, Any]],
    source_stats: List[Dict[str, Any]],
) -> str:
    now = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()
    high = [c for c in candidates if c.get("bucket") == "high"]
    medium = [c for c in candidates if c.get("bucket") == "medium"]
    low = [c for c in candidates if c.get("bucket") == "low"]

    lines: List[str] = []
    lines.append("# Talk Candidate Review")
    lines.append("")
    lines.append(f"Generated: `{now}`")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Total candidates processed: **{len(candidates) + len(dedup_dropped)}**")
    lines.append(f"- After deduplication: **{len(candidates)}**")
    lines.append(f"- High confidence: **{len(high)}**")
    lines.append(f"- Medium confidence: **{len(medium)}**")
    lines.append(f"- Low confidence: **{len(low)}**")
    lines.append(f"- Dropped as duplicates: **{len(dedup_dropped)}**")
    lines.append("")

    lines.append("## Source Crawl Stats")
    lines.append("")
    if not source_stats:
        lines.append("- No source stats found in candidate payload.")
    else:
        for stat in source_stats:
            source_id = stat.get("source_id", "unknown")
            enabled = stat.get("enabled", True)
            if not enabled:
                lines.append(f"- `{source_id}` disabled")
                continue
            lines.append(
                "- `{}` pages_seen={} ok={} failed={} candidates={}".format(
                    source_id,
                    stat.get("pages_seen", 0),
                    stat.get("fetch_ok", 0),
                    stat.get("fetch_failed", 0),
                    stat.get("candidates_found", 0),
                )
            )
    lines.append("")

    for heading, bucket in [
        ("High Confidence (Auto-verified candidates)", high),
        ("Medium Confidence (Manual review needed)", medium),
        ("Low Confidence (Rejected candidates)", low),
    ]:
        lines.append(f"## {heading}")
        lines.append("")
        if not bucket:
            lines.append("- None")
            lines.append("")
            continue
        for item in sorted(bucket, key=lambda c: int(c.get("score", 0)), reverse=True):
            title = item.get("title", "(no title)")
            date = item.get("date", "(no date)")
            venue = item.get("venue", "(no venue)")
            score = item.get("score", "?")
            url = item.get("url", "") or item.get("talk_url", "")
            reasons = "; ".join(item.get("reasons", []))
            lines.append(f"- `{score}` | **{date}** | {title} | {venue}")
            if url:
                lines.append(f"  - URL: {url}")
            if reasons:
                lines.append(f"  - Reasons: {reasons}")
        lines.append("")

    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Score talk candidates for review.")
    parser.add_argument(
        "--write-candidates",
        action="store_true",
        help="Persist scores/buckets back into _data/talk_candidates.yml",
    )
    args = parser.parse_args()

    identity = load_yaml(IDENTITY_PATH)
    sources = load_yaml(SOURCES_PATH)
    candidates_payload = load_yaml(CANDIDATES_PATH)
    candidates = candidates_payload.get("candidates", [])

    trusted_domains = [normalize_text(s.get("domain", "")) for s in sources.get("sources", []) if s.get("enabled", False)]

    evaluated: List[Dict[str, Any]] = []
    for cand in candidates:
        outcome = score_candidate(cand, identity, trusted_domains)
        evaluated.append({**cand, **outcome})

    deduped, dropped = dedupe_candidates(evaluated, trusted_domains)
    source_stats = candidates_payload.get("source_stats", [])
    report = build_report(deduped, dropped, source_stats)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(report, encoding="utf-8")

    if args.write_candidates:
        out = {
            "generated_at": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
            "scope": candidates_payload.get("scope", "europe-us"),
            "source_stats": source_stats,
            "candidates": deduped,
            "duplicates": dropped,
        }
        save_yaml(CANDIDATES_PATH, out)

    print(f"Wrote review report to {REPORT_PATH}")
    if args.write_candidates:
        print(f"Updated candidate scores in {CANDIDATES_PATH}")
    else:
        print("Dry run: candidate file unchanged. Use --write-candidates to persist scores.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

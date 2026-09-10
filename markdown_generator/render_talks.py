#!/usr/bin/env python3
"""Render the Talks section of `_pages/activities.md` from `_data/talks.yml`.

`_data/talks.yml` is the single source of truth for talks: the talk-candidate
bot proposes entries there, you edit them there, and this script renders the
list into the marked block of the activities page. Everything between

    <!-- talks:begin -->
    <!-- talks:end -->

is generated -- do not edit it by hand, it is overwritten on every run.

Only entries with `status: verified` (or `published`) are rendered.

Run:  python3 markdown_generator/render_talks.py [--check]
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List

import yaml

ROOT = Path(__file__).resolve().parents[1]
TALKS_PATH = ROOT / "_data" / "talks.yml"
ACTIVITIES_PATH = ROOT / "_pages" / "activities.md"

BEGIN = "<!-- talks:begin -->"
END = "<!-- talks:end -->"
GENERATED_NOTE = "<!-- generated from _data/talks.yml by markdown_generator/render_talks.py -- do not edit by hand -->"

PUBLISHABLE = {"verified", "published"}

MONTHS = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]


def load_talks() -> List[Dict[str, Any]]:
    data = yaml.safe_load(TALKS_PATH.read_text(encoding="utf-8")) or {}
    talks = data.get("talks") or []
    return [t for t in talks if str(t.get("status", "")).lower() in PUBLISHABLE]


def sort_key(talk: Dict[str, Any]) -> str:
    """Sort by date; a month-precision date sorts after the days of that month."""

    date = str(talk.get("date", "")).strip()
    parts = date.split("-")
    year = parts[0] if parts else "0000"
    month = parts[1] if len(parts) > 1 else "00"
    day = parts[2] if len(parts) > 2 else "99"
    return f"{year}-{month}-{day}"


def month_label(talk: Dict[str, Any]) -> str:
    parts = str(talk.get("date", "")).split("-")
    if not parts or not parts[0]:
        return ""
    year = parts[0]
    if len(parts) < 2:
        return year
    try:
        return f"{MONTHS[int(parts[1]) - 1]} {year}"
    except (ValueError, IndexError):
        return year


def render_talk(talk: Dict[str, Any]) -> str:
    pieces: List[str] = []
    title = str(talk.get("title", "") or "").strip()
    venue = str(talk.get("venue", "") or "").strip()
    location = str(talk.get("location", "") or "").strip()
    url = str(talk.get("url", "") or "").strip()
    note = str(talk.get("note", "") or "").strip()

    if title:
        pieces.append(f"*{title}*")
    if note:
        pieces.append(note)
    if venue:
        pieces.append(f"[{venue}]({url})" if url else venue)
    elif url and not title:
        pieces.append(url)
    if location:
        pieces.append(location)

    label = month_label(talk)
    body = ", ".join(pieces)
    return f"* {label}: {body}" if label else f"* {body}"


def render_block(talks: List[Dict[str, Any]]) -> str:
    ordered = sorted(talks, key=sort_key, reverse=True)
    lines = [BEGIN, GENERATED_NOTE]
    lines.extend(render_talk(talk) for talk in ordered)
    lines.append(END)
    return "\n".join(lines)


def replace_block(text: str, block: str) -> str:
    if BEGIN not in text or END not in text:
        raise SystemExit(
            f"markers {BEGIN} / {END} not found in {ACTIVITIES_PATH.name}; add them around the talks list"
        )
    head, rest = text.split(BEGIN, 1)
    _, tail = rest.split(END, 1)
    return head + block + tail


def main() -> int:
    check_only = "--check" in sys.argv
    talks = load_talks()
    current = ACTIVITIES_PATH.read_text(encoding="utf-8")
    updated = replace_block(current, render_block(talks))

    if check_only:
        if updated != current:
            print("OUT OF DATE: activities.md does not match _data/talks.yml")
            return 1
        print(f"up to date ({len(talks)} talks)")
        return 0

    if updated != current:
        ACTIVITIES_PATH.write_text(updated, encoding="utf-8")
        print(f"UPDATED {ACTIVITIES_PATH.relative_to(ROOT)} ({len(talks)} talks)")
    else:
        print(f"unchanged ({len(talks)} talks)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Render the Talks section of `_pages/activities.md` from `_data/talks.yml`.

`_data/talks.yml` is the single source of truth for talks: the talk-candidate
bot proposes entries there, you edit them there, and this script renders the
list into the marked block of the activities page. Everything between

    <!-- talks:begin -->
    <!-- talks:end -->

is generated -- do not edit it by hand, it is overwritten on every run.

Only entries with `status: verified` (or `published`) are rendered.

Tagged events imported from the private calendar (`_data/calendar_events.yml`,
see fetch_calendar_events.py) are rendered too: `[talk]` events are merged into
the Talks block (skipping ones already in talks.yml), the others go into their
own marked blocks:

    calendar-poster     -> "Poster presentations"
    calendar-attend     -> "Conferences and meetings"
    calendar-organizer  -> "Organization"   ([organizer] and [chair])

Run:  python3 markdown_generator/render_talks.py [--check]
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any, Dict, List

import yaml

ROOT = Path(__file__).resolve().parents[1]
TALKS_PATH = ROOT / "_data" / "talks.yml"
CALENDAR_PATH = ROOT / "_data" / "calendar_events.yml"
ACTIVITIES_PATH = ROOT / "_pages" / "activities.md"

BEGIN = "<!-- talks:begin -->"
END = "<!-- talks:end -->"
GENERATED_NOTE = "<!-- generated from _data/talks.yml by markdown_generator/render_talks.py -- do not edit by hand -->"

CALENDAR_BLOCKS = {
    "calendar-poster": {"poster"},
    "calendar-attend": {"attend"},
    "calendar-organizer": {"organizer", "chair"},
}

PUBLISHABLE = {"verified", "published"}

CAL_NOTE = "<!-- generated from _data/calendar_events.yml by markdown_generator/render_talks.py -- do not edit by hand -->"

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


def load_calendar_events() -> List[Dict[str, Any]]:
    if not CALENDAR_PATH.exists():
        return []
    data = yaml.safe_load(CALENDAR_PATH.read_text(encoding="utf-8")) or {}
    return list(data.get("events") or [])


def _norm(text: Any) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(text or "").lower()).strip()


def merge_calendar_talks(talks: List[Dict[str, Any]], events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Add calendar [talk] events that are not already in talks.yml (same day and title)."""

    seen = {(str(t.get("date", ""))[:10], _norm(t.get("title"))) for t in talks}
    merged = list(talks)
    for event in events:
        if event.get("kind") != "talk":
            continue
        key = (str(event.get("date", ""))[:10], _norm(event.get("title")))
        if key in seen:
            continue
        seen.add(key)
        merged.append(event)
    return merged


def _place(event: Dict[str, Any]) -> str:
    venue = str(event.get("venue", "") or "").strip()
    url = str(event.get("url", "") or "").strip()
    return f"[{venue}]({url})" if venue and url else venue


def render_calendar_event(event: Dict[str, Any]) -> str:
    kind = event.get("kind")
    title = str(event.get("title", "") or "").strip()
    location = str(event.get("location", "") or "").strip()
    url = str(event.get("url", "") or "").strip()
    label = month_label(event)
    place = _place(event)
    if kind == "poster":
        pieces = [f"**{title}**" if title else "", place or (url if not title else ""), location]
    elif kind == "attend":
        name = title or str(event.get("venue", "") or "").strip()
        pieces = [f"[{name}]({url})" if url and name else name, location]
    elif kind == "chair":
        pieces = [f"Session chair: *{title}*" if title else "Session chair", place, location]
    else:  # organizer
        pieces = [f"Organizer of *{title}*" if title else "Organizer", place, location]
    body = ", ".join(p for p in pieces if p)
    return f"* {label}: {body}" if label else f"* {body}"


def render_calendar_block(name: str, events: List[Dict[str, Any]]) -> str:
    kinds = CALENDAR_BLOCKS[name]
    chosen = sorted((e for e in events if e.get("kind") in kinds), key=sort_key, reverse=True)
    lines = [f"<!-- {name}:begin -->", CAL_NOTE]
    lines.extend(render_calendar_event(e) for e in chosen)
    lines.append(f"<!-- {name}:end -->")
    return "\n".join(lines)


def replace_named_block(text: str, name: str, block: str) -> str:
    begin, end = f"<!-- {name}:begin -->", f"<!-- {name}:end -->"
    if begin not in text or end not in text:
        raise SystemExit(f"markers {begin} / {end} not found in {ACTIVITIES_PATH.name}")
    head, rest = text.split(begin, 1)
    _, tail = rest.split(end, 1)
    return head + block + tail


def render_page(text: str) -> str:
    """Return `text` with every generated block replaced by freshly rendered content."""

    events = load_calendar_events()
    talks = merge_calendar_talks(load_talks(), events)
    text = replace_block(text, render_block(talks))
    for name in CALENDAR_BLOCKS:
        text = replace_named_block(text, name, render_calendar_block(name, events))
    return text


def main() -> int:
    check_only = "--check" in sys.argv
    talks = merge_calendar_talks(load_talks(), load_calendar_events())
    current = ACTIVITIES_PATH.read_text(encoding="utf-8")
    updated = render_page(current)

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

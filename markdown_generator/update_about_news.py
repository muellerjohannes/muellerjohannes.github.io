#!/usr/bin/env python3

"""Maintain the News list on the About page.

Two modes:

  update_about_news.py            publications: prepend bullets for new publications
                                  and arXiv -> published transitions (reads
                                  _data/publication_updates.yml).
  update_about_news.py --events   events: add/refresh bullets for [talk] and
                                  [organizer] events from _data/calendar_events.yml
                                  (upcoming ones in future tense, past ones in past
                                  tense), drop cancelled upcoming ones, and prune old items.

Bullets written by this script end with an invisible date marker, e.g.

    <!-- news:talk:2026-11-05:1a2b3c4d -->

Pruning only ever removes marked bullets that lie in the past. Bullets you wrote
by hand have no marker and are never removed. Rules (see `news:` in
_data/calendar_sources.yml): past items older than max_age_days go, then the oldest
past items beyond max_items go, but the list is never cut below min_items.
Upcoming items are never removed by age.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "_data"
PAGES_DIR = ROOT / "_pages"

CONFIG_PATH = DATA_DIR / "publication_sources.yml"
UPDATES_PATH = DATA_DIR / "publication_updates.yml"
ABOUT_PATH = PAGES_DIR / "about.md"
CALENDAR_CONFIG_PATH = DATA_DIR / "calendar_sources.yml"
CALENDAR_EVENTS_PATH = DATA_DIR / "calendar_events.yml"

DEFAULT_NEWS = {"max_age_days": 183, "max_items": 12, "min_items": 5}
NEWS_KINDS = {"talk", "organizer"}

MARK_RE = re.compile(
    r"\s*<!-- news:(?P<kind>[a-z]+):(?P<start>\d{4}-\d{2}-\d{2})"
    r"(?::(?P<hash>[0-9a-f]{8}))?(?::(?P<end>\d{4}-\d{2}-\d{2}))? -->\s*$"
)
MONTHS = ["January", "February", "March", "April", "May", "June", "July",
          "August", "September", "October", "November", "December"]


def load_yaml(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def format_publication_bullet(item: Dict[str, str]) -> str:
    title = item.get("title", "New publication")
    venue = item.get("venue", "")
    url = item.get("url", "")
    year = item.get("year", "")
    today = dt.date.today()
    date_label = today.strftime("%B %-d")
    marker = f" <!-- news:pub:{today.isoformat()} -->"
    return _format_publication_bullet(item, date_label, url, title, venue, year) + marker


def _format_publication_bullet(item, date_label, url, title, venue, year) -> str:

    if item.get("change") == "arxiv_to_published":
        if venue and year:
            return (
                f"* On {date_label}, my preprint [*{title}*]({url}) was published in {venue} ({year})."
                if url
                else f"* On {date_label}, my preprint *{title}* was published in {venue} ({year})."
            )
        return (
            f"* On {date_label}, my preprint [*{title}*]({url}) is now published."
            if url
            else f"* On {date_label}, my preprint *{title}* is now published."
        )

    if venue and year:
        return (
            f"* On {date_label}, a new publication [*{title}*]({url}) appeared in {venue} ({year})."
            if url
            else f"* On {date_label}, a new publication *{title}* appeared in {venue} ({year})."
        )
    return (
        f"* On {date_label}, a new publication [*{title}*]({url}) was added."
        if url
        else f"* On {date_label}, a new publication *{title}* was added."
    )


def update_about_news(max_items: int = 0) -> int:
    updates = load_yaml(UPDATES_PATH).get("changes", [])
    relevant = [
        item
        for item in updates
        if item.get("change") in {"arxiv_to_published", "new_published"}
    ]
    if not relevant:
        return 0

    lines = ABOUT_PATH.read_text(encoding="utf-8").splitlines()
    news_idx = None
    for idx, line in enumerate(lines):
        if line.strip() == "## News":
            news_idx = idx
            break
    if news_idx is None:
        return 0

    start = news_idx + 1
    while start < len(lines) and lines[start].strip() == "":
        start += 1

    end = start
    while end < len(lines) and lines[end].strip().startswith("*"):
        end += 1

    existing = lines[start:end]
    existing_set = {MARK_RE.sub("", line) for line in existing} | set(existing)
    new_bullets = []
    for item in relevant:
        bullet = format_publication_bullet(item)
        if MARK_RE.sub("", bullet) not in existing_set:
            new_bullets.append(bullet)

    if not new_bullets:
        return 0

    merged = new_bullets + existing  # pruning happens in events mode

    updated = lines[:start] + merged + lines[end:]
    ABOUT_PATH.write_text("\n".join(updated) + "\n", encoding="utf-8")
    return len(new_bullets)


# ----------------------------------------------------------------- events mode


def ordinal(day: int) -> str:
    suffix = "th" if 11 <= day % 100 <= 13 else {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")
    return f"{day}{suffix}"


def day_label(d: dt.date) -> str:
    return f"{MONTHS[d.month - 1]} {ordinal(d.day)}"


def span_label(start: dt.date, end: Optional[dt.date]) -> str:
    if not end or end <= start:
        return f"On {day_label(start)}"
    if (end.year, end.month) == (start.year, start.month):
        return f"From {day_label(start)}-{ordinal(end.day)}"
    return f"From {day_label(start)} to {day_label(end)}"


def norm(text: Any) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(text or "").lower()).strip()


def event_key(event: Dict[str, Any]) -> Tuple[str, str, str]:
    digest = hashlib.sha1(norm(event.get("title")).encode("utf-8")).hexdigest()[:8]
    return (event["kind"], str(event["date"])[:10], digest)


def event_marker(event: Dict[str, Any]) -> str:
    kind, start, digest = event_key(event)
    end = str(event.get("end_date", "") or "")[:10]
    return f"<!-- news:{kind}:{start}:{digest}" + (f":{end}" if end else "") + " -->"


def event_bullet(event: Dict[str, Any], today: dt.date) -> str:
    start = dt.date.fromisoformat(str(event["date"])[:10])
    end_raw = str(event.get("end_date", "") or "")[:10]
    end = dt.date.fromisoformat(end_raw) if end_raw else None
    last = end or start
    upcoming = last >= today

    title = str(event.get("title", "") or "").strip()
    venue = str(event.get("venue", "") or "").strip()
    location = str(event.get("location", "") or "").strip()
    url = str(event.get("url", "") or "").strip()

    title_md = (f"[*{title}*]({url})" if url else f"*{title}*") if title else ""
    place = ""
    if venue:
        place = f" at [{venue}]({url})" if url and not title else f" at {venue}"
    elif location:
        place = f" in {location}"

    if event["kind"] == "talk":
        verb = "will give" if start >= today else "gave"
        what = f"the talk {title_md}" if title_md else "a talk"
        sentence = f"On {day_label(start)}, I {verb} {what}{place}."
    else:
        verb = "will organize" if upcoming else "organized"
        what = title_md or "a workshop"
        sentence = f"{span_label(start, end)}, I {verb} {what}{place}."
    return f"* {sentence} {event_marker(event)}"


def parse_marker(line: str) -> Optional[Dict[str, Any]]:
    m = MARK_RE.search(line)
    if not m:
        return None
    start = dt.date.fromisoformat(m.group("start"))
    end = dt.date.fromisoformat(m.group("end")) if m.group("end") else None
    return {"kind": m.group("kind"), "start": start, "last": end or start,
            "key": (m.group("kind"), m.group("start"), m.group("hash") or "")}


def load_news_settings() -> Dict[str, int]:
    settings = dict(DEFAULT_NEWS)
    cfg = load_yaml(CALENDAR_CONFIG_PATH).get("news") or {}
    for name in settings:
        if name in cfg:
            settings[name] = int(cfg[name])
    return settings


def split_news(lines: List[str]) -> Optional[Tuple[int, int]]:
    news_idx = next((i for i, l in enumerate(lines) if l.strip() == "## News"), None)
    if news_idx is None:
        return None
    start = news_idx + 1
    while start < len(lines) and lines[start].strip() == "":
        start += 1
    end = start
    while end < len(lines) and lines[end].strip().startswith("*"):
        end += 1
    return start, end


def sync_events(items: List[str], events: List[Dict[str, Any]], today: dt.date,
                max_age_days: int) -> Tuple[List[str], int, int]:
    """Add/refresh event bullets and drop cancelled upcoming ones. Returns (items, changed, removed)."""

    wanted = {event_key(e): e for e in events if e.get("kind") in NEWS_KINDS and e.get("date")}
    cutoff = today - dt.timedelta(days=max_age_days)
    changed = removed = 0
    out: List[str] = []
    seen = set()
    for line in items:
        info = parse_marker(line)
        if info and info["kind"] in NEWS_KINDS:
            event = wanted.get(info["key"])
            if event is None:
                if info["last"] >= today:  # upcoming event vanished from the calendar
                    removed += 1
                    continue
                out.append(line)
                continue
            seen.add(info["key"])
            new_line = event_bullet(event, today)
            changed += new_line != line
            out.append(new_line)
        else:
            out.append(line)

    plain = " ".join(norm(MARK_RE.sub("", l)) for l in out)
    fresh = []
    for key, event in sorted(wanted.items(), key=lambda kv: kv[0][1], reverse=True):
        if key in seen:
            continue
        last = dt.date.fromisoformat(str(event.get("end_date") or event["date"])[:10])
        if last < cutoff:
            continue
        title = norm(event.get("title"))
        if title and title in plain:  # already written by hand
            continue
        fresh.append(event_bullet(event, today))
    changed += len(fresh)
    return fresh + out, changed, removed


def prune(items: List[str], today: dt.date, max_age_days: int, max_items: int, min_items: int) -> Tuple[List[str], int]:
    cutoff = today - dt.timedelta(days=max_age_days)
    items = list(items)
    dropped = 0

    def removable() -> List[Tuple[dt.date, int]]:
        found = []
        for idx, line in enumerate(items):
            info = parse_marker(line)
            if info and info["last"] < today:
                found.append((info["last"], idx))
        return sorted(found)  # oldest first

    while len(items) > min_items:
        candidates = removable()
        if not candidates:
            break
        last, idx = candidates[0]
        if last < cutoff or len(items) > max_items:
            del items[idx]
            dropped += 1
        else:
            break
    return items, dropped


def update_event_news(today: Optional[dt.date] = None) -> Dict[str, int]:
    today = today or dt.date.today()
    settings = load_news_settings()
    events = load_yaml(CALENDAR_EVENTS_PATH).get("events") or []
    lines = ABOUT_PATH.read_text(encoding="utf-8").splitlines()
    block = split_news(lines)
    if block is None:
        return {"changed": 0, "removed": 0, "pruned": 0}
    start, end = block
    items, changed, removed = sync_events(lines[start:end], events, today, settings["max_age_days"])
    items, pruned = prune(items, today, settings["max_age_days"], settings["max_items"], settings["min_items"])
    if items != lines[start:end]:
        ABOUT_PATH.write_text("\n".join(lines[:start] + items + lines[end:]) + "\n", encoding="utf-8")
    return {"changed": changed, "removed": removed, "pruned": pruned}


def main() -> int:
    if "--events" in sys.argv[1:]:
        print(update_event_news())
        return 0
    config = load_yaml(CONFIG_PATH)
    max_items = int(config.get("news", {}).get("max_items", 12))
    added = update_about_news(max_items=max_items)
    print(f"added_news_items={added}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

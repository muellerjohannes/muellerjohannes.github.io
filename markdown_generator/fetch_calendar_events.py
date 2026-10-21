#!/usr/bin/env python3
"""Import tagged events from a published iCal feed into `_data/calendar_events.yml`.

Privacy model
-------------
* The feed URL is read from the environment variable TALK_CALENDAR_URL
  (a GitHub Actions secret). It is never written to any file or printed.
* Only events whose title starts with one of the tags below are kept:

      [talk]  [poster]  [organizer]  [chair]  [attend]

  All other events are discarded immediately.
* Only public fields are stored: title, date, time, venue, location, url.
  Descriptions, attendees, alarms etc. are dropped. From the description only
  the lines `Venue: ...` and `URL: ...` are read.

Conventions for tagged events
-----------------------------
  SUMMARY      "[talk] Title of the talk @ Name of the venue"   ("@ venue" optional)
  LOCATION     "City, Country"
  URL          link to the event page (or a `URL: https://...` line in the notes)
  DESCRIPTION  optional line `Venue: Name of the venue`

If the download fails, the existing file is left untouched.

Run:  TALK_CALENDAR_URL=... python3 markdown_generator/fetch_calendar_events.py
      python3 markdown_generator/fetch_calendar_events.py --file some.ics
"""

from __future__ import annotations

import os
import re
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_PATH = ROOT / "_data" / "calendar_events.yml"
CONFIG_PATH = ROOT / "_data" / "calendar_sources.yml"

ENV_VAR = "TALK_CALENDAR_URL"
KINDS = {"talk", "poster", "organizer", "chair", "attend"}
ALIASES = {"organiser": "organizer"}
TAG_RE = re.compile(r"^\s*\[\s*([A-Za-z]+)\s*\]\s*(.*)$")
PROP_RE = re.compile(r'^([A-Za-z0-9-]+)((?:;[^:;=]+=(?:"[^"]*"|[^:;"]*))*):(.*)$')
DEFAULT_TZ = "Europe/Berlin"


def unfold(text: str) -> List[str]:
    lines: List[str] = []
    for raw in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        if raw[:1] in (" ", "\t") and lines:
            lines[-1] += raw[1:]
        else:
            lines.append(raw)
    return lines


def unescape(value: str) -> str:
    out, i = [], 0
    while i < len(value):
        ch = value[i]
        if ch == "\\" and i + 1 < len(value):
            nxt = value[i + 1]
            out.append("\n" if nxt in "nN" else nxt)
            i += 2
        else:
            out.append(ch)
            i += 1
    return "".join(out)


def parse_events(text: str) -> List[Dict[str, Any]]:
    """Return raw VEVENTs as {NAME: (params, value)} dicts."""

    events: List[Dict[str, Any]] = []
    current: Optional[Dict[str, Any]] = None
    for line in unfold(text):
        if line == "BEGIN:VEVENT":
            current = {}
        elif line == "END:VEVENT":
            if current is not None:
                events.append(current)
            current = None
        elif current is not None:
            m = PROP_RE.match(line)
            if m:
                name = m.group(1).upper()
                if name not in current:  # keep the first occurrence
                    current[name] = (m.group(2), m.group(3))
    return events


def parse_when(params: str, value: str) -> Optional[Dict[str, Any]]:
    value = value.strip()
    if "VALUE=DATE" in params.upper() and "T" not in value.upper() or re.fullmatch(r"\d{8}", value):
        try:
            return {"date": datetime.strptime(value[:8], "%Y%m%d").date(), "time": ""}
        except ValueError:
            return None
    m = re.fullmatch(r"(\d{8})T(\d{2})(\d{2})(\d{2})?(Z?)", value)
    if not m:
        return None
    day = datetime.strptime(m.group(1), "%Y%m%d")
    hour, minute = int(m.group(2)), int(m.group(3))
    if m.group(5) == "Z":
        try:
            from zoneinfo import ZoneInfo

            moment = datetime(day.year, day.month, day.day, hour, minute, tzinfo=timezone.utc)
            moment = moment.astimezone(ZoneInfo(DEFAULT_TZ))
            return {"date": moment.date(), "time": moment.strftime("%H:%M")}
        except Exception:
            pass
    return {"date": day.date(), "time": f"{hour:02d}:{minute:02d}"}


def find_url(value: str) -> str:
    m = re.search(r"https?://[^\s<>\"]+", value)
    return m.group(0).rstrip(".,;)") if m else ""


def description_field(description: str, field: str) -> str:
    for line in description.splitlines():
        m = re.match(rf"^\s*{field}\s*:\s*(.+?)\s*$", line, re.IGNORECASE)
        if m:
            return m.group(1)
    return ""


def convert(raw: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Turn a raw VEVENT into a public record, or None if it is not a tagged event."""

    summary = unescape(raw.get("SUMMARY", ("", ""))[1]).strip()
    m = TAG_RE.match(summary)
    if not m:
        return None
    kind = ALIASES.get(m.group(1).lower(), m.group(1).lower())
    if kind not in KINDS:
        return None
    if raw.get("STATUS", ("", ""))[1].strip().upper() == "CANCELLED":
        return None
    if "DTSTART" not in raw:
        return None
    start = parse_when(*raw["DTSTART"])
    if not start:
        return None

    title = m.group(2).strip()
    venue = ""
    if " @ " in title:
        title, venue = (part.strip() for part in title.rsplit(" @ ", 1))

    description = unescape(raw.get("DESCRIPTION", ("", ""))[1])
    venue = venue or description_field(description, "Venue")
    location = unescape(raw.get("LOCATION", ("", ""))[1]).replace("\n", ", ").strip()
    url = find_url(raw.get("URL", ("", ""))[1]) or find_url(description_field(description, "URL"))

    end_date = ""
    if "DTEND" in raw:
        end = parse_when(*raw["DTEND"])
        if end:
            last = end["date"]
            if not start["time"] and last > start["date"]:  # all-day DTEND is exclusive
                last = date.fromordinal(last.toordinal() - 1)
            if last > start["date"]:
                end_date = last.isoformat()

    record = {
        "kind": kind,
        "title": title,
        "date": start["date"].isoformat(),
        "end_date": end_date,
        "time": start["time"],
        "venue": venue,
        "location": location,
        "url": url,
    }
    return {k: v for k, v in record.items() if v != ""}


def select_events(text: str, include_from: str = "") -> List[Dict[str, Any]]:
    out = []
    for raw in parse_events(text):
        record = convert(raw)
        if record and record["date"] >= include_from:
            out.append(record)
    out.sort(key=lambda r: (r["date"], r.get("time", ""), r["title"]))
    return out


def load_include_from() -> str:
    if CONFIG_PATH.exists():
        data = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8")) or {}
        return str(data.get("include_from", "") or "")
    return ""


def download(url: str) -> str:
    import requests

    if url.lower().startswith("webcal://"):
        url = "https://" + url[len("webcal://"):]
    response = requests.get(url, timeout=60, headers={"User-Agent": "CalendarImport/0.1"})
    response.raise_for_status()
    return response.text


def write_events(events: List[Dict[str, Any]], path: Path = OUTPUT_PATH) -> None:
    header = (
        "# Generated by markdown_generator/fetch_calendar_events.py from the private calendar feed.\n"
        "# Contains only events tagged [talk]/[poster]/[organizer]/[chair]/[attend]. Do not edit by hand.\n"
    )
    body = yaml.safe_dump({"events": events}, sort_keys=False, allow_unicode=True, width=1000)
    path.write_text(header + body, encoding="utf-8")


def main() -> int:
    args = sys.argv[1:]
    if "--file" in args:
        text = Path(args[args.index("--file") + 1]).read_text(encoding="utf-8")
    else:
        url = os.environ.get(ENV_VAR, "").strip()
        if not url:
            print(f"::notice::{ENV_VAR} is not set; skipping calendar import")
            return 0
        try:
            text = download(url)
        except Exception as exc:  # never print the URL
            print(f"::warning::calendar download failed ({type(exc).__name__}); keeping the existing file")
            return 0
    if "BEGIN:VCALENDAR" not in text:
        print("::warning::response is not an iCalendar feed; keeping the existing file")
        return 0
    events = select_events(text, load_include_from())
    write_events(events)
    counts: Dict[str, int] = {}
    for e in events:
        counts[e["kind"]] = counts.get(e["kind"], 0) + 1
    print(f"wrote {len(events)} tagged events to {OUTPUT_PATH.relative_to(ROOT)}: {counts}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

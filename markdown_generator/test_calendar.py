#!/usr/bin/env python3
"""Offline tests for the calendar import and its rendering.

Run with:  python3 markdown_generator/test_calendar.py
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import fetch_calendar_events as fce  # noqa: E402
import render_talks as rt  # noqa: E402

ICS = "\r\n".join([
    "BEGIN:VCALENDAR",
    "VERSION:2.0",
    "BEGIN:VEVENT",
    "SUMMARY:[talk] Fisher-Rao geometry @ Seminar\\, Oxford",
    "DTSTART;TZID=Europe/Berlin:20261105T141500",
    "LOCATION:Oxford\\, UK",
    "URL:https://example.org/seminar",
    "DESCRIPTION:Private notes: dinner with X\\nVenue: ignored because summary has one",
    "END:VEVENT",
    "BEGIN:VEVENT",
    "SUMMARY:[Poster] KFAC for PINNs",
    "DTSTART;VALUE=DATE:20261201",
    "DTEND;VALUE=DATE:20261204",
    "DESCRIPTION:Venue: NeurIPS Workshop\\nURL: https://example.org/ws\\nzoom https://zoom.us/j/123",
    "LOCATION:Vancouver",
    "END:VEVENT",
    "BEGIN:VEVENT",
    "SUMMARY:[organizer] Mini-Workshop on",
    " Geometry",
    "DTSTART:20270110T080000Z",
    "END:VEVENT",
    "BEGIN:VEVENT",
    "SUMMARY:[attend] Some Conference",
    "DTSTART;VALUE=DATE:20270201",
    "STATUS:CANCELLED",
    "END:VEVENT",
    "BEGIN:VEVENT",
    "SUMMARY:Doctor appointment",
    "DTSTART:20261106T090000Z",
    "DESCRIPTION:very private",
    "END:VEVENT",
    "BEGIN:VEVENT",
    "SUMMARY:[chair] Session on RL",
    "DTSTART;VALUE=DATE:20261105",
    "END:VEVENT",
    "BEGIN:VEVENT",
    "SUMMARY:[talk] Old talk",
    "DTSTART;VALUE=DATE:20200101",
    "END:VEVENT",
    "END:VCALENDAR",
])


class ImportTests(unittest.TestCase):
    def setUp(self):
        self.events = fce.select_events(ICS, "2026-09-01")
        self.by_kind = {e["kind"]: e for e in self.events}

    def test_only_tagged_future_events_survive(self):
        self.assertEqual(sorted(e["kind"] for e in self.events), ["chair", "organizer", "poster", "talk"])

    def test_untagged_and_cancelled_events_are_dropped(self):
        dump = repr(self.events)
        for secret in ("Doctor", "private", "dinner", "zoom", "Some Conference"):
            self.assertNotIn(secret, dump)

    def test_talk_fields(self):
        talk = self.by_kind["talk"]
        self.assertEqual(talk["title"], "Fisher-Rao geometry")
        self.assertEqual(talk["venue"], "Seminar, Oxford")
        self.assertEqual(talk["date"], "2026-11-05")
        self.assertEqual(talk["time"], "14:15")
        self.assertEqual(talk["location"], "Oxford, UK")
        self.assertEqual(talk["url"], "https://example.org/seminar")

    def test_tag_is_case_insensitive_and_venue_and_url_come_from_notes(self):
        poster = self.by_kind["poster"]
        self.assertEqual(poster["venue"], "NeurIPS Workshop")
        self.assertEqual(poster["url"], "https://example.org/ws")
        self.assertEqual(poster["end_date"], "2026-12-03")  # all-day DTEND is exclusive

    def test_folded_lines_and_utc_times(self):
        org = self.by_kind["organizer"]
        self.assertEqual(org["title"], "Mini-Workshop onGeometry")
        self.assertEqual(org["date"], "2027-01-10")
        self.assertEqual(org["time"], "09:00")  # 08:00Z in Berlin


class RenderingTests(unittest.TestCase):
    def test_calendar_talk_is_merged_without_duplicates(self):
        talks = [{"title": "Fisher-Rao Geometry", "date": "2026-11-05", "venue": "v"}]
        events = [
            {"kind": "talk", "title": "Fisher-Rao geometry", "date": "2026-11-05"},
            {"kind": "talk", "title": "Another", "date": "2026-12-01", "venue": "w"},
            {"kind": "poster", "title": "P", "date": "2026-12-02"},
        ]
        merged = rt.merge_calendar_talks(talks, events)
        self.assertEqual([t["title"] for t in merged], ["Fisher-Rao Geometry", "Another"])

    def test_poster_organizer_chair_attend_lines(self):
        self.assertEqual(
            rt.render_calendar_event({"kind": "poster", "title": "T", "date": "2026-12-01", "venue": "V", "url": "https://u", "location": "L"}),
            "* December 2026: **T**, [V](https://u), L",
        )
        self.assertEqual(
            rt.render_calendar_event({"kind": "organizer", "title": "W", "date": "2027-01-10", "location": "L"}),
            "* January 2027: Organizer of *W*, L",
        )
        self.assertEqual(
            rt.render_calendar_event({"kind": "chair", "title": "S", "date": "2026-11-05"}),
            "* November 2026: Session chair: *S*",
        )
        self.assertEqual(
            rt.render_calendar_event({"kind": "attend", "title": "C", "date": "2026-11-05", "location": "L"}),
            "* November 2026: C, L",
        )

    def test_url_without_venue_links_the_title(self):
        self.assertEqual(
            rt.render_talk({"title": "T", "date": "2026-11-05", "url": "https://u", "location": "L"}),
            "* November 2026: [*T*](https://u), L",
        )
        self.assertEqual(
            rt.render_calendar_event({"kind": "poster", "title": "P", "date": "2026-12-01", "url": "https://u"}),
            "* December 2026: [**P**](https://u)",
        )
        self.assertEqual(
            rt.render_calendar_event({"kind": "organizer", "title": "W", "date": "2027-01-10", "url": "https://u"}),
            "* January 2027: Organizer of [*W*](https://u)",
        )

    def test_blocks_are_split_by_kind(self):
        events = [{"kind": "poster", "title": "P", "date": "2026-12-02"}, {"kind": "attend", "title": "C", "date": "2026-12-03"}]
        self.assertIn("**P**", rt.render_calendar_block("calendar-poster", events))
        self.assertNotIn("**P**", rt.render_calendar_block("calendar-attend", events))

    def test_activities_page_has_all_markers(self):
        text = rt.ACTIVITIES_PATH.read_text(encoding="utf-8")
        for name in rt.CALENDAR_BLOCKS:
            self.assertIn(f"<!-- {name}:begin -->", text)
            self.assertIn(f"<!-- {name}:end -->", text)

    def test_calendar_events_file_contains_only_public_fields(self):
        allowed = {"kind", "title", "date", "end_date", "time", "venue", "location", "url"}
        for event in rt.load_calendar_events():
            self.assertLessEqual(set(event), allowed)
            self.assertIn(event["kind"], fce.KINDS)


if __name__ == "__main__":
    unittest.main(verbosity=2)

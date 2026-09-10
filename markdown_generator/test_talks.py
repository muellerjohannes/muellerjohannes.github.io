#!/usr/bin/env python3
"""Offline tests for the talks rendering.

Run with:  python3 markdown_generator/test_talks.py
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import render_talks as rt  # noqa: E402


class RenderingTests(unittest.TestCase):
    def test_full_entry(self):
        talk = {
            "title": "A Talk",
            "date": "2026-08-13",
            "venue": "Some Institute",
            "location": "Hamburg, Germany",
            "url": "https://example.org",
        }
        self.assertEqual(
            rt.render_talk(talk),
            "* August 2026: *A Talk*, [Some Institute](https://example.org), Hamburg, Germany",
        )

    def test_entry_without_title(self):
        talk = {"title": "", "date": "2022-05", "venue": "Algebraic Statistics 2022", "location": "Honolulu"}
        self.assertEqual(rt.render_talk(talk), "* May 2022: Algebraic Statistics 2022, Honolulu")

    def test_entry_without_url_is_not_linked(self):
        talk = {"title": "T", "date": "2025-02", "venue": "Seminar", "location": "ETH Zurich"}
        self.assertEqual(rt.render_talk(talk), "* February 2025: *T*, Seminar, ETH Zurich")

    def test_note_is_kept(self):
        talk = {"title": "T", "date": "2024-06", "venue": "V", "note": "Invited talk"}
        self.assertEqual(rt.render_talk(talk), "* June 2024: *T*, Invited talk, V")

    def test_newest_first_and_month_precision_sorts_last_in_month(self):
        talks = [
            {"title": "day", "date": "2026-08-13", "venue": "v"},
            {"title": "month", "date": "2026-08", "venue": "v"},
            {"title": "older", "date": "2020-04", "venue": "v"},
        ]
        block = rt.render_block(talks).splitlines()
        self.assertIn("*month*", block[2])
        self.assertIn("*day*", block[3])
        self.assertIn("*older*", block[4])

    def test_only_verified_talks_are_published(self):
        self.assertEqual(rt.PUBLISHABLE, {"verified", "published"})


class RepositoryConsistencyTests(unittest.TestCase):
    def test_activities_page_matches_talks_yaml(self):
        talks = rt.load_talks()
        current = rt.ACTIVITIES_PATH.read_text(encoding="utf-8")
        self.assertEqual(
            rt.replace_block(current, rt.render_block(talks)),
            current,
            "activities.md is out of date -- run markdown_generator/render_talks.py",
        )

    def test_every_published_talk_has_date_and_venue(self):
        for talk in rt.load_talks():
            self.assertTrue(str(talk.get("date", "")).strip(), f"talk without date: {talk}")
            self.assertTrue(str(talk.get("venue", "")).strip(), f"talk without venue: {talk}")

    def test_talks_file_parses_and_is_not_empty(self):
        self.assertGreater(len(rt.load_talks()), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)

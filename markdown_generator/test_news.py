#!/usr/bin/env python3
"""Offline tests for the event news on the About page.

Run with:  python3 markdown_generator/test_news.py
"""

from __future__ import annotations

import datetime as dt
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import update_about_news as un  # noqa: E402

TODAY = dt.date(2026, 10, 21)


def talk(date, title="A Talk", **kw):
    return {"kind": "talk", "title": title, "date": date, **kw}


class FormattingTests(unittest.TestCase):
    def test_upcoming_talk_is_future_tense_with_linked_title(self):
        line = un.event_bullet(talk("2026-11-05", venue="Seminar", url="https://u"), TODAY)
        self.assertTrue(line.startswith("* On November 5th, I will give the talk [*A Talk*](https://u) at Seminar."))
        self.assertIn("<!-- news:talk:2026-11-05:", line)

    def test_past_talk_is_past_tense(self):
        line = un.event_bullet(talk("2026-08-13", location="Hamburg"), TODAY)
        self.assertTrue(line.startswith("* On August 13th, I gave the talk *A Talk* in Hamburg."))

    def test_today_still_counts_as_upcoming(self):
        self.assertIn("will give", un.event_bullet(talk("2026-10-21"), TODAY))

    def test_organizer_span_and_tense(self):
        ev = {"kind": "organizer", "title": "Workshop", "date": "2026-11-03", "end_date": "2026-11-07"}
        self.assertIn("From November 3rd-7th, I will organize *Workshop*.", un.event_bullet(ev, TODAY))
        ev = {"kind": "organizer", "title": "W", "date": "2026-08-31", "end_date": "2026-09-02"}
        self.assertIn("From August 31st to September 2nd, I organized *W*.", un.event_bullet(ev, TODAY))

    def test_ordinals(self):
        self.assertEqual([un.ordinal(d) for d in (1, 2, 3, 4, 11, 12, 13, 21, 22, 23, 31)],
                         ["1st", "2nd", "3rd", "4th", "11th", "12th", "13th", "21st", "22nd", "23rd", "31st"])


class SyncTests(unittest.TestCase):
    def sync(self, items, events, today=TODAY):
        return un.sync_events(items, events, today, 183)

    def test_new_event_is_added_on_top(self):
        items, changed, removed = self.sync(["* hand written"], [talk("2026-11-05")])
        self.assertEqual(changed, 1)
        self.assertIn("will give", items[0])
        self.assertEqual(items[1], "* hand written")

    def test_sync_is_idempotent(self):
        items, _, _ = self.sync(["* x"], [talk("2026-11-05")])
        again, changed, removed = self.sync(items, [talk("2026-11-05")])
        self.assertEqual((again, changed, removed), (items, 0, 0))

    def test_tense_flips_after_the_event(self):
        items, _, _ = self.sync([], [talk("2026-11-05")])
        later, changed, _ = self.sync(items, [talk("2026-11-05")], today=dt.date(2026, 11, 6))
        self.assertEqual(changed, 1)
        self.assertIn("gave", later[0])

    def test_event_already_written_by_hand_is_not_duplicated(self):
        hand = "* On November 5th, I will give the talk *A Talk* at Seminar."
        items, changed, _ = self.sync([hand], [talk("2026-11-05")])
        self.assertEqual((items, changed), ([hand], 0))

    def test_cancelled_upcoming_event_is_removed_but_past_one_is_kept(self):
        upcoming = un.event_bullet(talk("2026-11-05"), TODAY)
        past = un.event_bullet(talk("2026-09-05", title="Old"), TODAY)
        items, _, removed = self.sync([upcoming, past], [])
        self.assertEqual((items, removed), ([past], 1))

    def test_ancient_events_are_not_added(self):
        items, changed, _ = self.sync([], [talk("2025-01-05")])
        self.assertEqual((items, changed), ([], 0))

    def test_only_talks_and_organizer_events_become_news(self):
        events = [{"kind": "poster", "title": "P", "date": "2026-11-05"}, {"kind": "attend", "title": "A", "date": "2026-11-05"}]
        self.assertEqual(self.sync([], events)[0], [])


class PruningTests(unittest.TestCase):
    def marked(self, date, tag="x"):
        return f"* {tag} <!-- news:pub:{date} -->"

    def test_hand_written_bullets_are_never_removed(self):
        items = ["* hand"] * 20
        self.assertEqual(un.prune(items, TODAY, 183, 12, 5), (items, 0))

    def test_old_marked_items_are_dropped(self):
        items = [self.marked("2026-10-01", "new")] + [self.marked("2026-01-01", f"old{i}") for i in range(2)] + ["* h"] * 5
        out, dropped = un.prune(items, TODAY, 183, 12, 5)
        self.assertEqual(dropped, 2)
        self.assertEqual(len(out), 6)

    def test_floor_keeps_at_least_min_items(self):
        items = [self.marked("2025-01-01", f"old{i}") for i in range(6)]
        out, dropped = un.prune(items, TODAY, 183, 12, 5)
        self.assertEqual((len(out), dropped), (5, 1))

    def test_cap_drops_oldest_past_items_even_if_recent(self):
        items = [self.marked(f"2026-10-{d:02d}", f"n{d}") for d in range(20, 1, -1)]  # 18 recent items
        out, dropped = un.prune(items, TODAY, 183, 12, 5)
        self.assertEqual(len(out), 12)
        self.assertIn("n20", out[0])
        self.assertNotIn("n2 ", " ".join(out))

    def test_upcoming_items_are_never_pruned(self):
        items = [self.marked(f"2027-0{m}-01", f"f{m}") for m in range(1, 9)]
        self.assertEqual(un.prune(items, TODAY, 183, 3, 1), (items, 0))

    def test_end_date_counts_for_multi_day_events(self):
        line = "* w <!-- news:organizer:2026-10-19:0123abcd:2026-10-23 -->"  # still running
        self.assertEqual(un.prune([line] * 20, TODAY, 183, 3, 1)[1], 0)


class RepositoryTests(unittest.TestCase):
    def test_about_page_has_a_news_list(self):
        lines = un.ABOUT_PATH.read_text(encoding="utf-8").splitlines()
        block = un.split_news(lines)
        self.assertIsNotNone(block)
        self.assertGreater(block[1] - block[0], 0)

    def test_news_settings_are_sane(self):
        s = un.load_news_settings()
        self.assertGreaterEqual(s["max_items"], s["min_items"])
        self.assertGreater(s["max_age_days"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)

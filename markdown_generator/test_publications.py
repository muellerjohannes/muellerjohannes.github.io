#!/usr/bin/env python3
"""Offline tests for the publication pipeline.

Run with:  python3 markdown_generator/test_publications.py
No network, no third-party dependencies beyond PyYAML.
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import bibio  # noqa: E402
import publications_model as model  # noqa: E402


class BibParsingTests(unittest.TestCase):
    def test_quoted_author_list_is_not_split_on_commas(self):
        db = bibio.parse_string(
            '@article{k, author = "Gess, Benjamin and M{\\"u}ller, Johannes", title = "T", year = "2026"}'
        )
        people = db.entries["k"].persons["author"]
        self.assertEqual(len(people), 2)
        self.assertEqual(people[0].full_name(), "Benjamin Gess")
        self.assertEqual(people[1].last_names, ['M{\\"u}ller'])

    def test_braced_multiline_entry(self):
        db = bibio.parse_string(
            """@inproceedings{DBLP:conf/icml/MullerZ24,
  author       = {Johannes M{\\"{u}}ller and
                  Marius Zeinhofer},
  title        = {Position: Optimization in SciML},
  booktitle    = {Forty-first International Conference on Machine Learning, {ICML} 2024},
  year         = {2024}
}"""
        )
        entry = db.entries["DBLP:conf/icml/MullerZ24"]
        self.assertEqual(entry.type, "inproceedings")
        self.assertEqual(entry.fields["year"], "2024")
        self.assertIn("ICML", entry.fields["booktitle"])
        self.assertEqual(len(entry.persons["author"]), 2)

    def test_von_particle_is_kept_in_display_name(self):
        person = bibio.Person("van Oostrum, Jesse")
        self.assertEqual(person.last_names, ["Oostrum"])
        self.assertEqual(person.full_name(), "Jesse van Oostrum")

    def test_round_trip_preserves_fields(self):
        source = '@article{k, author = "Doe, Jane", title = "A, B and C", journal = "J", year = "2020"}'
        first = bibio.parse_string(source)
        second = bibio.parse_string(bibio.to_string(first))
        self.assertEqual(second.entries["k"].fields["title"], "A, B and C")
        self.assertEqual(second.entries["k"].persons["author"][0].full_name(), "Jane Doe")

    def test_duplicate_keys_are_kept_apart(self):
        db = bibio.parse_string(
            '@article{k, title = "One", year = "2020"}\n@article{k, title = "Two", year = "2021"}'
        )
        self.assertEqual(len(db.entries), 2)


class ClassificationTests(unittest.TestCase):
    def test_arxiv_only_is_preprint(self):
        fields = {"title": "T", "journal": "arXiv preprint arXiv:2608.12111", "year": "2026"}
        self.assertEqual(model.classify(fields), model.PREPRINT)

    def test_journal_is_published(self):
        fields = {"title": "T", "journal": "SIAM Journal on Optimization", "doi": "10.1137/24m1653422"}
        self.assertEqual(model.classify(fields), model.PUBLISHED)

    def test_main_track_ml_conference_is_published(self):
        fields = {"title": "T", "booktitle": "International Conference on Machine Learning (ICML)"}
        self.assertEqual(model.classify(fields), model.PUBLISHED)
        fields = {"title": "T", "booktitle": "Advances in Neural Information Processing Systems (NeurIPS)"}
        self.assertEqual(model.classify(fields), model.PUBLISHED)

    def test_ml_workshop_is_workshop(self):
        fields = {
            "title": "T",
            "booktitle": "The Exploration in AI Today Workshop at ICML 2025",
            "url": "https://openreview.net/forum?id=2cvUHCgZbF",
        }
        self.assertEqual(model.classify(fields), model.WORKSHOP)

    def test_workshop_volume_with_publisher_doi_is_published(self):
        """The regression that put a Springer volume under workshop papers."""

        fields = {
            "title": "Non-asymptotic analysis of projected gradient descent",
            "booktitle": "International Workshop of Scientific Machine Learning: Emerging Topics",
            "series": "SEMA SIMAI Springer Series",
            "doi": "10.1007/978-3-032-11527-0_4",
        }
        self.assertEqual(model.classify(fields), model.PUBLISHED)

    def test_symposium_is_not_a_workshop(self):
        fields = {"title": "T", "booktitle": "ACM-SIAM Symposium on Discrete Algorithms"}
        self.assertEqual(model.classify(fields), model.PUBLISHED)

    def test_arxiv_doi_does_not_count_as_publication(self):
        fields = {
            "title": "T",
            "journal": "arXiv preprint arXiv:2407.07873",
            "doi": "10.48550/arXiv.2407.07873",
        }
        self.assertEqual(model.classify(fields), model.PREPRINT)

    def test_override_wins_over_heuristics(self):
        fields = {"title": "T", "journal": "Some Journal", "eprint": "1234.56789"}
        overrides = {"arxiv:1234.56789": {"type": "workshop", "venue": "Custom Workshop"}}
        self.assertEqual(model.classify(fields, overrides), model.WORKSHOP)
        resolved = model.resolved_fields(fields, overrides)
        self.assertEqual(resolved["venue"], "Custom Workshop")
        self.assertEqual(resolved["type"], model.WORKSHOP)

    def test_override_keys_accept_arxiv_doi_and_title(self):
        raw = {
            "overrides": {
                "2402.07318": {"type": "published"},
                "doi:10.1007/978-3-032-11527-0_4": {"type": "published"},
                "title: Deep Ritz revisited": {"hide": True},
            }
        }
        overrides = {model._override_key(k): v for k, v in raw["overrides"].items()}
        self.assertEqual(model.classify({"title": "x", "eprint": "2402.07318"}, overrides), model.PUBLISHED)
        self.assertEqual(
            model.classify({"title": "x", "doi": "10.1007/978-3-032-11527-0_4"}, overrides), model.PUBLISHED
        )
        self.assertTrue(model.override_for({"title": "Deep Ritz revisited"}, overrides).get("hide"))


class MergingTests(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmpdir.name)

    def tearDown(self):
        self._tmpdir.cleanup()

    def _write(self, name: str, text: str) -> Path:
        path = self.tmp / name
        path.write_text(text, encoding="utf-8")
        return path

    def test_manual_record_wins_and_arxiv_id_links_the_two(self):
        auto = self._write(
            "auto.bib",
            '@article{a, author = "M{\\"u}ller, Johannes", title = "Position: Optimization in SciML",'
            ' journal = "arXiv preprint arXiv:2402.07318", year = "2024", eprint = "2402.07318"}',
        )
        manual = self._write(
            "manual.bib",
            '@inproceedings{b, author = "M{\\"u}ller, Johannes",'
            ' title = "Position: Optimization in SciML Should Employ the Function Space Geometry",'
            ' booktitle = "International Conference on Machine Learning (ICML)", year = "2024",'
            ' eprint = "2402.07318"}',
        )
        works = model.load_works(auto, manual)
        self.assertEqual(len(works), 1)
        fields = works[0]["fields"]
        self.assertEqual(model.venue_of(fields), "International Conference on Machine Learning (ICML)")
        self.assertEqual(model.classify(fields), model.PUBLISHED)

    def test_title_variant_without_shared_id_still_merges(self):
        auto = self._write(
            "auto.bib",
            '@article{a, author = "M{\\"u}ller, Johannes",'
            ' title = "Achieving High Accuracy with PINNs via Energy Natural Gradients",'
            ' journal = "arXiv preprint arXiv:2302.13163", year = "2023"}',
        )
        manual = self._write(
            "manual.bib",
            '@inproceedings{b, author = "M{\\"u}ller, Johannes",'
            ' title = "Achieving High Accuracy with PINNs via Energy Natural Gradient Descent",'
            ' booktitle = "International Conference on Machine Learning (ICML)", year = "2023"}',
        )
        works = model.load_works(auto, manual)
        self.assertEqual(len(works), 1)
        self.assertEqual(works[0]["fields"]["title"].endswith("Gradient Descent"), True)

    def test_distinct_papers_are_not_merged(self):
        auto = self._write(
            "auto.bib",
            '@article{a, author = "M{\\"u}ller, Johannes", title = "Error Estimates for the Deep Ritz Method'
            ' with Boundary Penalty", journal = "arXiv preprint arXiv:2103.01007", year = "2021"}\n'
            '@article{b, author = "M{\\"u}ller, Johannes", title = "Notes on Exact Boundary Values in'
            ' Residual Minimisation", journal = "arXiv preprint arXiv:2105.02550", year = "2021"}',
        )
        manual = self._write("manual.bib", "")
        self.assertEqual(len(model.load_works(auto, manual)), 2)


class RepositoryConsistencyTests(unittest.TestCase):
    """Guards against the real bibliographies drifting back into a mess."""

    def test_every_work_has_a_single_output_and_a_known_type(self):
        works = model.load_works()
        overrides = model.load_overrides()
        config = model.load_yaml(model.SOURCES_PATH)
        seen_titles = set()
        for work in works:
            fields = work["fields"]
            kind = model.classify(fields, overrides, config)
            self.assertIn(kind, {model.PREPRINT, model.PUBLISHED, model.WORKSHOP})
            fingerprint = model.title_fingerprint(fields.get("title", ""))
            self.assertNotIn(fingerprint, seen_titles, f"duplicate work: {fields.get('title')}")
            seen_titles.add(fingerprint)
            self.assertTrue(fields.get("year"), f"missing year: {fields.get('title')}")

    def test_no_published_work_is_labelled_as_arxiv_venue(self):
        for work in model.load_works():
            fields = model.resolved_fields(work["fields"], model.load_overrides())
            if fields["type"] != model.PREPRINT:
                self.assertFalse(
                    model.is_arxiv_venue(fields["venue"]),
                    f"{fields.get('title')} is {fields['type']} but shows an arXiv venue",
                )


if __name__ == "__main__":
    unittest.main(verbosity=2)

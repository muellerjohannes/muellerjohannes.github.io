# Publications Automation

The pipeline harvests publication metadata, regenerates the publication pages
and adds news bullets to the About page.

## Who owns which file

| File | Owner | Purpose |
| --- | --- | --- |
| `markdown_generator/publications.bib` | **bot** (rewritten every run) | harvested records |
| `markdown_generator/publications_manual.bib` | **you** (bot never writes) | records you paste by hand (DBLP, PMLR, OpenReview) |
| `_data/publication_overrides.yml` | **you** (bot never writes) | editorial decisions: section, venue label, title, hiding |
| `_publications/*.md` | generated | one file per work |
| `_pages/publications.md` | you | layout only, groups by `type` |

Precedence when the same work appears twice: **overrides > manual bib > auto bib**.
Records are matched by DOI, then arXiv id (`eprint`), then title. When you paste
a published version by hand, always add `eprint = "<arXiv id>"` so it merges with
the preprint record instead of showing up twice.

## Sections and classification

`/publications/` has three sections, in this order: **Preprints**,
**Publications**, **Workshop Papers**.

The decision lives in exactly one place, `markdown_generator/publications_model.py`,
and is written into the `type:` field of each generated file. The Liquid template
only groups by that field -- it must never re-derive anything from venue strings.

Rules, applied in order:

1. an entry in `_data/publication_overrides.yml` wins, always;
2. a workshop-looking venue is a **workshop** paper *unless* the record carries a
   publisher DOI -- that is what keeps a Springer volume or journal special issue
   of a workshop under Publications;
3. an arXiv-only record is a **preprint**;
4. everything else -- journals, book chapters and main-track conferences
   (ICML, NeurIPS, ICLR, MSML, AISTATS, COLT, L4DC, UAI) -- is **published**.

"Symposium" is deliberately not a workshop marker. Extra venue rules can be added
in `_data/publication_sources.yml` (`main_venue_markers`, `main_venue_acronyms`,
`workshop_patterns`) without touching code.

## Fixing a wrong entry

Wrong section or ugly venue name: add an override, keyed by arXiv id, `doi:` or `title:`.

```yaml
overrides:
  "2505.07311":
    type: published
    venue: "Scientific Machine Learning: Emerging Topics (SEMA SIMAI Springer Series)"
```

Missing conference or workshop version: paste the BibTeX into
`markdown_generator/publications_manual.bib` and add the `eprint` field.

Never edit `_publications/*.md` or `markdown_generator/publications.bib` by hand --
both are regenerated.

## Sources

- arXiv author page: `https://arxiv.org/a/muller_j_3.html` plus the arXiv API (discovery)
- DBLP title search (ML conference and workshop metadata)
- Crossref (journal DOIs and venue metadata)
- ORCID `0000-0001-8729-0466` and zbMATH `ai:muller.johannes.3` are configured for future use

Discovery is arXiv-driven, so anything that never went to arXiv, and any
conference version that DBLP does not return for a title search, has to come from
`publications_manual.bib`. Adding your DBLP author id (pid) to
`_data/publication_sources.yml` would let the bot enumerate the conference
records directly -- that is the single biggest recall improvement still open.

## Local run

No third-party dependencies beyond `requests` and `PyYAML` (the `pybtex`
dependency was removed; BibTeX parsing lives in `markdown_generator/bibio.py`).

```bash
python3 -m pip install requests pyyaml
python3 markdown_generator/test_publications.py      # offline, no network
python3 markdown_generator/update_publications.py    # network: arXiv, DBLP, Crossref
python3 markdown_generator/pubsFromBib.py
python3 markdown_generator/update_about_news.py
```

## CI workflow

`.github/workflows/publications-pipeline.yml`, every Monday (`17 6 * * 1` UTC)
and on manual dispatch. It runs the tests before and after the update and opens a
PR on branch `bot/publications-pipeline`.

## Tests

`markdown_generator/test_publications.py` covers the BibTeX parser, the
classification rules (including the workshop-special-issue regression), record
merging, and consistency of the checked-in bibliographies: every work appears
exactly once and no non-preprint shows an arXiv venue.

## What you need to do

- Review the weekly PR.
- Correct anything wrong via `publication_overrides.yml` or `publications_manual.bib`,
  never in the generated files.
- Add your DBLP pid when convenient.

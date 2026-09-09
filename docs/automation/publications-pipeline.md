# Publications Automation

This pipeline updates `markdown_generator/publications.bib`, regenerates publication pages, and adds news bullets on publication upgrades.

## Sources

- arXiv author page: `https://arxiv.org/a/muller_j_3.html`
- zbMATH id (configured for future integration): `ai:muller.johannes.3`
- ORCID id (configured): `0000-0001-8729-0466`
- Crossref enrichment for DOI and venue metadata

## Policy

- Preprints are added from arXiv.
- When publication metadata is found (DOI + venue), preprint records are upgraded in place.
- Duplicate visible entries are not kept for preprint/published variants.
- Exactly one canonical record is kept per work.
- Classification used for site sections:
  - `published`: journal papers and proper ML main-track conference papers (ICML/NeurIPS/ICLR).
  - `workshop`: workshop-style venues.
  - `preprint`: arXiv-only entries.
- Deduplication keys are resolved in this order: DOI, arXiv id, then title+author overlap.
- `About` page news gets auto-generated bullets for:
  - `arxiv_to_published`
  - `new_published`
- About-page news list is trimmed to the latest 12 items.

## Metadata quality

- Discovery uses arXiv author page.
- Published metadata enrichment currently uses Crossref.
- If a URL points to trusted sources (`proceedings.mlr.press`, `openreview.net`, `dblp.org`),
  the pipeline can use page metadata to improve title capitalization while preserving identity matching.

Planned next source priority for ML conference metadata:

1. DBLP
2. PMLR / OpenReview
3. Crossref
4. arXiv

## Local Run

```bash
python3 -m pip install requests pyyaml pybtex
python3 markdown_generator/update_publications.py
python3 markdown_generator/pubsFromBib.py
python3 markdown_generator/update_about_news.py
```

## CI Workflow

Workflow file: `.github/workflows/publications-pipeline.yml`

Schedule:
- every Monday (`17 6 * * 1` UTC)
- manual dispatch

The workflow opens a PR with publication updates and news updates.

## Files Produced

- `markdown_generator/publications.bib` (updated)
- `_data/publication_updates.yml` (transition report)
- `_publications/*.md` (regenerated)
- `_pages/about.md` (news section updated)

## What You Need To Do

- Review PRs.
- Confirm publication upgrades and generated news bullets.
- Merge if correct.
- Share DBLP id once available to improve recall.

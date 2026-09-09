# Phase 1 Talk Automation Policy

This document defines the Phase 1 policy for automatically finding talks while minimizing false positives for common names.

## Goal

Use external web sources to discover talk candidates, then publish only verified talks after scoring and review.

Pipeline states:

1. `candidate` - scraped from trusted sources, not published
2. `verified` - high confidence identity match, publishable
3. `published` - rendered on site after PR merge

## Data Files

- `_data/talk_sources.yml` - trusted source registry
- `_data/talk_identity.yml` - name, affiliation, coauthor, topic, and negative filters
- `_data/talk_candidates.yml` - discovered candidates + score metadata
- `_data/talks.yml` - verified canonical talks used by website pages

## Scoring Rubric

Each candidate receives a confidence score based on positive and negative signals. Name-only matches are not enough.

### Positive signals

- `+60` exact speaker name match with one configured name variant
- `+20` weak name variant match (e.g. initials or ASCII fallback)
- `+18` affiliation match (`MPI MiS`, `RWTH Aachen`, `TU Berlin`)
- `+10` coauthor name match (max `+20`)
- `+8` topic keyword match (max `+24`)
- `+10` source domain is trusted

### Negative signals

- `-30` negative topic keyword match (`medicine`, `law`, `biology`, `finance`, `math bio`)
- `-45` disambiguation red flag (`Johannes Muller` + `TUM` + `math bio` context)

### Bucket thresholds

- `score >= 70`: `high` confidence -> auto-verified candidate
- `45 <= score < 70`: `medium` confidence -> manual review required
- `score < 45`: `low` confidence -> rejected (kept in report)

### Hard safety rule

- If candidate metadata contains `TUM`, it is always treated as `manual review only`.
- If such a candidate scores `high`, it is downgraded to `medium` for explicit review.

## Deduplication

Candidates are deduplicated by canonical key:

- normalized date (`YYYY-MM-DD` or `YYYY-MM`)
- normalized title
- normalized venue

If duplicates conflict, keep the entry with:

1. higher confidence score
2. richer metadata (URL, location, description)
3. source priority (trusted source order)

## Publish Rules

- Only `_data/talks.yml` is used for public rendering.
- `type` is not shown on website output.
- Month/year dates are allowed and rendered as month/year.
- Online talks are included.
- No auto-merge or direct publish; PR review is always required.

## Weekly PR Checklist

For each automation PR, review these sections:

1. New `high` confidence talks proposed for `_data/talks.yml`
2. `medium` confidence candidates that need your approve/reject decision
3. Rejected `low` confidence candidates and reasons
4. Duplicates merged and source links preserved
5. Broken/missing URLs

## Operator Runbook

Current manual run command:

```bash
python3 markdown_generator/score_talk_candidates.py
```

The script reads candidates and writes a review report. No public files are changed unless a write flag is explicitly used.

Fetch + score sequence:

```bash
python3 markdown_generator/fetch_talk_candidates.py
python3 markdown_generator/score_talk_candidates.py --write-candidates
```

## Your Responsibilities

- Keep trusted source registry up to date over time.
- Review weekly PRs and decide on medium-confidence candidates.
- Merge approved PRs.
- Add occasional manual corrections in canonical data if needed.

## Information Still Needed From You

- 5-15 specific event or seminar page URLs (not just broad homepages) to improve fetch precision.
- Whether talks at TUM should always be treated as manual-review-only by default.

## First-Time Setup (What You Need To Do)

1. Add Python dependency locally:

```bash
python3 -m pip install pyyaml
```

2. Run fetch + score:

```bash
python3 markdown_generator/fetch_talk_candidates.py
python3 markdown_generator/score_talk_candidates.py --write-candidates
```

3. Inspect report:

- `docs/automation/talk-candidate-review.md`

4. If source fetch success is low, add more specific event URLs to `_data/talk_sources.yml`.

## Current Limitations

- Some websites block simple crawlers; this may produce `fetch_failed` stats.
- Broad source domains can be noisy; precision improves as source registry gets more specific.
- Candidate-only mode is enabled. No public talks pages are generated yet from this pipeline.

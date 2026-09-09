#!/usr/bin/env python3

"""Update About page news with publication transition items.

Reads _data/publication_updates.yml and prepends new publication-related bullets
to _pages/about.md, then trims news list to configured max length.
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path
from typing import Any, Dict, List

import yaml


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "_data"
PAGES_DIR = ROOT / "_pages"

CONFIG_PATH = DATA_DIR / "publication_sources.yml"
UPDATES_PATH = DATA_DIR / "publication_updates.yml"
ABOUT_PATH = PAGES_DIR / "about.md"


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


def update_about_news(max_items: int) -> int:
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
    existing_set = set(existing)
    new_bullets = []
    for item in relevant:
        bullet = format_publication_bullet(item)
        if bullet not in existing_set:
            new_bullets.append(bullet)

    if not new_bullets:
        return 0

    merged = new_bullets + existing
    merged = merged[:max_items]

    updated = lines[:start] + merged + lines[end:]
    ABOUT_PATH.write_text("\n".join(updated) + "\n", encoding="utf-8")
    return len(new_bullets)


def main() -> int:
    config = load_yaml(CONFIG_PATH)
    max_items = int(config.get("news", {}).get("max_items", 12))
    added = update_about_news(max_items=max_items)
    print(f"added_news_items={added}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python
# coding: utf-8
"""Generate `_publications/*.md` from the bibliographies.

Inputs
------
* ``markdown_generator/publications.bib``        -- bot-harvested (rewritten by the bot)
* ``markdown_generator/publications_manual.bib`` -- hand-maintained (never touched by the bot)
* ``_data/publication_overrides.yml``            -- your editorial decisions, highest precedence

The classification (preprint / published / workshop) comes from
``publications_model`` and is written into the ``type:`` front-matter field.
The Liquid template groups on that field only -- it must not re-derive anything
from venue strings.

Run from anywhere:  ``python3 markdown_generator/pubsFromBib.py``
"""

from __future__ import annotations

import html
import os
import re
import sys
from pathlib import Path
from time import strptime

sys.path.insert(0, str(Path(__file__).resolve().parent))

import publications_model as model  # noqa: E402

OUTPUT_DIR = model.ROOT / "_publications"
COLLECTION = "publications"
PERMALINK_PREFIX = "/publication/"

html_escape_table = {"&": "&amp;", '"': "&quot;", "'": "&apos;"}


def html_escape(text: str) -> str:
    return "".join(html_escape_table.get(c, c) for c in text)


def clean_bibtex(text: str) -> str:
    """Convert BibTeX escapes to Unicode."""

    replacements = [
        (r'{\"u}', "ü"), (r'{\"{u}}', "ü"), (r'{\-"u}', "ü"),
        (r'{\"o}', "ö"), (r'{\"{o}}', "ö"),
        (r'{\"a}', "ä"), (r'{\"{a}}', "ä"),
        (r"{\ss}", "ß"), (r"{\ s}", "ß"), (r"{\ss{}}", "ß"),
        (r'{\"U}', "Ü"), (r'{\"{U}}', "Ü"),
        (r'{\"O}', "Ö"), (r'{\"{O}}', "Ö"),
        (r'{\"A}', "Ä"), (r'{\"{A}}', "Ä"),
        (r"{\'a}", "á"), (r"{\'e}", "é"), (r"{\'i}", "í"), (r"{\'o}", "ó"), (r"{\'u}", "ú"),
        (r"{\'{a}}", "á"), (r"{\'{e}}", "é"), (r"{\'{i}}", "í"), (r"{\'{o}}", "ó"), (r"{\'{u}}", "ú"),
        (r"{\`a}", "à"), (r"{\`e}", "è"), (r"{\`i}", "ì"), (r"{\`o}", "ò"), (r"{\`u}", "ù"),
        (r"{\c{C}}", "Ç"), (r"{\c{c}}", "ç"),
        (r"{\~n}", "ñ"), (r"{\~a}", "ã"), (r"{\~o}", "õ"),
        (r"{\.z}", "ż"), (r"{\.a}", "ą"),
        (r"{\i}", "ı"), (r"{\\i}", "ı"),
        (r"{ff}", "ff"), (r"{fi}", "fi"), (r"{fl}", "fl"), (r"{ffi}", "ffi"), (r"{ffl}", "ffl"),
        ("---", "—"), ("--", "–"),
        (r"\_", "_"), (r"\&", "&"), (r"\%", "%"),
    ]
    result = text or ""
    for pattern, replacement in replacements:
        result = result.replace(pattern, replacement)
    return result.replace("{", "").replace("}", "")


def escape_yaml_string(text: str) -> str:
    return text.replace('"', '\\"')


def pub_date_from(fields) -> str:
    year = str(fields.get("year", "") or "1900")
    month = "01"
    day = "01"
    raw_month = str(fields.get("month", "") or "")
    if raw_month:
        if raw_month.isdigit():
            month = f"{int(raw_month):02d}"
        else:
            try:
                month = "{:02d}".format(strptime(raw_month[:3], "%b").tm_mon)
            except ValueError:
                month = "01"
    raw_day = str(fields.get("day", "") or "")
    if raw_day.isdigit():
        day = f"{int(raw_day):02d}"
    return f"{year}-{month}-{day}"


def author_names(persons, name_fixes=None) -> list:
    """Author list for the citation, with configured display-name fixes."""

    name_fixes = name_fixes or {}
    names = []
    for person in persons.get("author", []):
        name = clean_bibtex(person.full_name()).strip()
        if not name:
            continue
        names.append(name_fixes.get(model.normalize(name), name))
    return names


def load_name_fixes(config) -> dict:
    raw = (config or {}).get("author_name_fixes") or {}
    return {model.normalize(str(k)): str(v) for k, v in raw.items()}


def paper_url(fields) -> str:
    url = str(fields.get("url", "") or "").strip()
    if len(url) > 5:
        return clean_bibtex(url)
    doi = clean_bibtex(str(fields.get("doi", "") or "")).strip()
    if len(doi) > 5:
        return doi if doi.startswith("http") else f"https://doi.org/{doi}"
    arxiv_id = model.entry_arxiv_id(fields)
    if arxiv_id:
        return f"https://arxiv.org/abs/{arxiv_id}"
    return ""


def slug_for(title: str, pub_date: str) -> str:
    clean_title = clean_bibtex(title).replace(" ", "-")
    url_slug = re.sub(r"\[.*\]|[^a-zA-Z0-9_-]", "", clean_title)
    url_slug = url_slug.replace("--", "-")
    return f"{pub_date}-{url_slug}".replace("--", "-")


def build_markdown(record, overrides, config, name_fixes=None) -> tuple:
    fields = model.resolved_fields(record["fields"], overrides, config)
    if fields.get("hide") == "true":
        return "", ""

    title = clean_bibtex(fields.get("title", "")).strip()
    if not title:
        raise KeyError("title")
    pub_date = pub_date_from(fields)
    pub_year = pub_date.split("-")[0]
    filename_stem = slug_for(fields.get("title", ""), pub_date)

    venue = clean_bibtex(fields.get("venue", "")).strip()
    pub_type = fields.get("type", model.PREPRINT)
    url = paper_url(fields)

    citation = ", ".join(author_names(record["persons"], name_fixes)) + ". "
    citation += f"<em>{title}</em>. "
    if venue:
        citation += f"{venue} "
    citation += f"({pub_year})."

    md = f'---\ntitle: "{escape_yaml_string(title)}"\n'
    md += f"collection: {COLLECTION}\n"
    md += f"permalink: {PERMALINK_PREFIX}{filename_stem}\n"

    note = clean_bibtex(str(fields.get("note", "") or ""))
    has_note = len(note) > 5
    if has_note:
        md += f'excerpt: "{escape_yaml_string(note)}"\n'

    md += f"date: {pub_date}\n"
    md += f'venue: "{escape_yaml_string(venue)}"\n'
    md += f"type: '{pub_type}'\n"
    if url:
        md += f"paperurl: '{url}'\n"
    md += f'citation: "{escape_yaml_string(citation)}"\n'
    if url:
        md += f"link: '{url}'\n"
    md += "---"

    if has_note:
        md += "\n" + html_escape(note) + "\n"
    if url:
        md += f'\n[Access paper here]({url}){{:target="_blank"}}\n'
    else:
        query = html.escape(clean_bibtex(fields.get("title", "")).replace(" ", "+"))
        md += (
            f'\nUse [Google Scholar](https://scholar.google.com/scholar?q={query})'
            '{:target="_blank"} for full citation'
        )

    return f"{filename_stem}.md", md


def main() -> int:
    overrides = model.load_overrides()
    config = model.load_yaml(model.SOURCES_PATH)
    records = model.load_works()
    name_fixes = load_name_fixes(config)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    generated = {}
    for record in records:
        try:
            filename, md = build_markdown(record, overrides, config, name_fixes)
        except KeyError as exc:
            print(f"WARNING missing field {exc} in entry {record['key']}")
            continue
        if not filename:
            print(f"SKIPPED (hidden by override): {record['key']}")
            continue
        if filename in generated:
            print(f"WARNING duplicate output file {filename} from {record['key']} -- skipped")
            continue
        generated[filename] = md

    for filename, md in generated.items():
        (OUTPUT_DIR / filename).write_text(md, encoding="utf-8")
        print(f"WROTE {filename}")

    # Case-insensitive filesystems (macOS) report the OLD spelling of a file
    # that was just rewritten under a new capitalisation -- deleting it as
    # "stale" would delete the fresh file. Rename it instead.
    canonical_by_casefold = {name.casefold(): name for name in generated}
    for existing in sorted(os.listdir(OUTPUT_DIR)):
        if not existing.endswith(".md") or existing in generated:
            continue
        path = OUTPUT_DIR / existing
        canonical = canonical_by_casefold.get(existing.casefold())
        if canonical:
            target = OUTPUT_DIR / canonical
            try:
                if target.exists() and not os.path.samefile(path, target):
                    path.unlink()
                    print(f"REMOVED stale publication file: {existing}")
                    continue
                staging = OUTPUT_DIR / f"{canonical}.rename-tmp"
                path.rename(staging)
                staging.rename(target)
                print(f"RENAMED {existing} -> {canonical}")
            except OSError as exc:
                print(f"WARNING could not rename {existing}: {exc}")
            continue
        try:
            if f"collection: {COLLECTION}" in path.read_text(encoding="utf-8"):
                path.unlink()
                print(f"REMOVED stale publication file: {existing}")
        except OSError as exc:
            print(f"WARNING could not inspect/remove {existing}: {exc}")

    counts = {}
    for md in generated.values():
        match = re.search(r"^type: '(\w+)'$", md, re.MULTILINE)
        if match:
            counts[match.group(1)] = counts.get(match.group(1), 0) + 1
    print(f"\n{len(generated)} works: " + ", ".join(f"{k}={v}" for k, v in sorted(counts.items())))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

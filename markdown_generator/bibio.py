"""Minimal dependency-free BibTeX reader/writer.

Replaces the previous ``pybtex`` dependency.  The API mirrors the small part of
pybtex that the publication scripts used (``BibliographyData``, ``Entry``,
``Person``) so that call sites stay readable.

Design notes:
* Field values keep their raw BibTeX source (``M{\\"u}ller`` stays as written);
  unescaping happens later in ``pubsFromBib.clean_bibtex``.
* Entry keys and field names are compared case-insensitively, field names are
  stored lowercase.
* Only ``@string``-free, plain BibTeX is supported, which is what both the bot
  and DBLP/OpenReview exports produce.
"""

from __future__ import annotations

import re
from collections import OrderedDict
from typing import Dict, Iterable, List, Optional

__all__ = ["Person", "Entry", "BibliographyData", "parse_string", "parse_file", "to_string"]


def _strip_outer_braces(value: str) -> str:
    value = value.strip()
    while len(value) > 1 and value[0] == "{" and value[-1] == "}":
        depth = 0
        balanced = True
        for index, char in enumerate(value):
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0 and index != len(value) - 1:
                    balanced = False
                    break
        if not balanced:
            break
        value = value[1:-1].strip()
    return value


def _split_top_level(value: str, separator: str, respect_quotes: bool = True) -> List[str]:
    """Split on ``separator`` (a word or a character) outside braces and quotes."""

    parts: List[str] = []
    depth = 0
    in_quote = False
    current: List[str] = []
    index = 0
    sep_len = len(separator)
    while index < len(value):
        char = value[index]
        if char == "{":
            depth += 1
        elif char == "}":
            depth = max(0, depth - 1)
        elif char == '"' and respect_quotes and depth == 0 and (index == 0 or value[index - 1] != "\\"):
            in_quote = not in_quote
        if depth == 0 and not in_quote and value[index : index + sep_len] == separator:
            parts.append("".join(current))
            current = []
            index += sep_len
            continue
        current.append(char)
        index += 1
    parts.append("".join(current))
    return [p.strip() for p in parts if p.strip()]


class Person:
    """A BibTeX author/editor name split into first/von/last/jr parts."""

    def __init__(self, name: str = "") -> None:
        self.first_names: List[str] = []
        self.middle_names: List[str] = []
        self.prelast_names: List[str] = []
        self.last_names: List[str] = []
        self.lineage_names: List[str] = []
        if name:
            self._parse(name)

    # -- parsing ---------------------------------------------------------
    def _parse(self, name: str) -> None:
        name = " ".join(name.replace("\n", " ").split())
        chunks = _split_top_level(name, ",", respect_quotes=False)
        if len(chunks) >= 2:
            last_part = chunks[0]
            if len(chunks) >= 3:
                self.lineage_names = chunks[1].split()
                first_part = chunks[2]
            else:
                first_part = chunks[1]
            von, last = self._split_von(last_part.split())
            self.prelast_names = von
            self.last_names = last
            firsts = first_part.split()
            if firsts:
                self.first_names = [firsts[0]]
                self.middle_names = firsts[1:]
            return

        tokens = name.split()
        if not tokens:
            return
        if len(tokens) == 1:
            self.last_names = tokens
            return

        # "First [Middle...] [von] Last"
        von_start = None
        for index, token in enumerate(tokens[:-1]):
            if index == 0:
                continue
            if self._is_von_token(token):
                von_start = index
                break
        if von_start is None:
            self.first_names = [tokens[0]]
            self.middle_names = tokens[1:-1]
            self.last_names = [tokens[-1]]
        else:
            self.first_names = [tokens[0]]
            self.middle_names = tokens[1:von_start]
            von_end = von_start
            while von_end + 1 < len(tokens) and self._is_von_token(tokens[von_end + 1]):
                von_end += 1
            self.prelast_names = tokens[von_start : von_end + 1]
            self.last_names = tokens[von_end + 1 :]

    @staticmethod
    def _is_von_token(token: str) -> bool:
        bare = token.lstrip("{").lstrip("\\")
        return bool(bare) and bare[0].islower()

    @classmethod
    def _split_von(cls, tokens: List[str]):
        von: List[str] = []
        index = 0
        while index < len(tokens) - 1 and cls._is_von_token(tokens[index]):
            von.append(tokens[index])
            index += 1
        return von, tokens[index:]

    # -- rendering -------------------------------------------------------
    def bibtex_name(self) -> str:
        last = " ".join(self.prelast_names + self.last_names)
        first = " ".join(self.first_names + self.middle_names)
        lineage = " ".join(self.lineage_names)
        if lineage:
            return f"{last}, {lineage}, {first}".strip().strip(",")
        if first:
            return f"{last}, {first}"
        return last

    def full_name(self) -> str:
        parts = self.first_names + self.middle_names + self.prelast_names + self.last_names + self.lineage_names
        return " ".join(p for p in parts if p)

    def __repr__(self) -> str:  # pragma: no cover - debugging helper
        return f"Person({self.bibtex_name()!r})"


class Entry:
    def __init__(
        self,
        type_: str = "article",
        fields: Optional[Dict[str, str]] = None,
        persons: Optional[Dict[str, List[Person]]] = None,
    ) -> None:
        self.type = (type_ or "article").lower()
        self.fields: "OrderedDict[str, str]" = OrderedDict()
        for key, value in (fields or {}).items():
            self.fields[key.lower()] = value
        self.persons: Dict[str, List[Person]] = {k: list(v) for k, v in (persons or {}).items()}

    def copy(self) -> "Entry":
        return Entry(self.type, dict(self.fields), {k: list(v) for k, v in self.persons.items()})


class BibliographyData:
    def __init__(self, entries: Optional[Dict[str, Entry]] = None) -> None:
        self.entries: "OrderedDict[str, Entry]" = OrderedDict(entries or {})


_ENTRY_START = re.compile(r"@(\w+)\s*[{(]", re.IGNORECASE)


def parse_string(text: str) -> BibliographyData:
    db = BibliographyData()
    position = 0
    while True:
        match = _ENTRY_START.search(text, position)
        if not match:
            break
        entry_type = match.group(1).lower()
        body_start = match.end()
        depth = 1
        index = body_start
        while index < len(text) and depth > 0:
            char = text[index]
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
            index += 1
        body = text[body_start : index - 1]
        position = index
        if entry_type in {"comment", "preamble", "string"}:
            continue
        key, entry = _parse_entry_body(entry_type, body)
        if not key:
            continue
        if key in db.entries:
            # Duplicate BibTeX keys are a hard error in LaTeX and silently
            # dropped by most parsers; keep both by suffixing the later one.
            suffix = 2
            while f"{key}-{suffix}" in db.entries:
                suffix += 1
            key = f"{key}-{suffix}"
        db.entries[key] = entry
    return db


def _parse_entry_body(entry_type: str, body: str):
    chunks = _split_top_level(body, ",")
    if not chunks:
        return "", Entry(entry_type)
    key = chunks[0].strip()
    fields: "OrderedDict[str, str]" = OrderedDict()
    for chunk in chunks[1:]:
        if "=" not in chunk:
            continue
        name, _, raw_value = chunk.partition("=")
        name = name.strip().lower()
        if not name:
            continue
        value = _clean_value(raw_value)
        if value:
            fields[name] = value
    persons: Dict[str, List[Person]] = {}
    for role in ("author", "editor"):
        if role in fields:
            names = _split_top_level(fields.pop(role), " and ", respect_quotes=False)
            persons[role] = [Person(n) for n in names if n]
    return key, Entry(entry_type, fields, persons)


def _clean_value(raw: str) -> str:
    value = raw.strip()
    if value.startswith('"') and value.endswith('"') and len(value) > 1:
        value = value[1:-1]
    else:
        value = _strip_outer_braces(value)
    return " ".join(value.replace("\n", " ").split())


def to_string(db: BibliographyData) -> str:
    blocks: List[str] = []
    for key, entry in db.entries.items():
        lines = [f"@{entry.type}{{{key},"]
        rendered: List[str] = []
        for role in ("author", "editor"):
            people = entry.persons.get(role) or []
            if people:
                joined = " and ".join(p.bibtex_name() for p in people)
                rendered.append(f'    {role} = "{joined}"')
        for name, value in entry.fields.items():
            if name in {"author", "editor"}:
                continue
            rendered.append(f'    {name} = "{value}"')
        lines.append(",\n".join(rendered))
        lines.append("}")
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks) + "\n"


def parse_file(path: str) -> BibliographyData:
    with open(path, "r", encoding="utf-8") as handle:
        return parse_string(handle.read())


def merge_databases(databases: Iterable[BibliographyData]) -> BibliographyData:
    out = BibliographyData()
    for db in databases:
        for key, entry in db.entries.items():
            new_key = key
            suffix = 2
            while new_key in out.entries:
                new_key = f"{key}-{suffix}"
                suffix += 1
            out.entries[new_key] = entry
    return out

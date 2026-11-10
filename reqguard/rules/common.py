"""Text helpers shared by the rule packs. Pure functions, no I/O."""
from __future__ import annotations

import re
from typing import Iterable

_NUMBER_WITH_UNIT = re.compile(r"\d")


def has_number(text: str) -> bool:
    """True if the text states any number (a quick 'is it measurable?' check)."""
    return bool(_NUMBER_WITH_UNIT.search(text))


def find_terms(text: str, terms: Iterable[str]) -> list[tuple[int, int, str]]:
    """Return (start, end, matched text) for every whole-word, case-insensitive match.

    Terms may contain spaces, hyphens or slashes ("as soon as possible", "and/or").
    """
    hits: list[tuple[int, int, str]] = []
    for term in terms:
        pattern = re.compile(r"(?<![A-Za-z])" + re.escape(term) + r"(?![A-Za-z])", re.IGNORECASE)
        for m in pattern.finditer(text):
            hits.append((m.start(), m.end(), m.group(0)))
    hits.sort()
    return hits


def joined(hits: list[tuple[int, int, str]]) -> str:
    """'quickly, should' - distinct matched words in first-seen order."""
    seen: list[str] = []
    for _, _, w in hits:
        if w.lower() not in seen:
            seen.append(w.lower())
    return ", ".join(seen)


def span_of(hits: list[tuple[int, int, str]]) -> tuple[int, int] | None:
    return (hits[0][0], hits[0][1]) if hits else None

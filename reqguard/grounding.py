"""Grounding check (FR-03, ADR-004) and requirement classifier. Pure functions.

An extracted requirement is kept only if its text appears verbatim in the
source document after whitespace and quote normalisation. This guarantees
the reviewer never sees a requirement the AI invented or paraphrased.
"""
from __future__ import annotations

import re

from .models import Requirement

_QUOTES = str.maketrans({"‘": "'", "’": "'", "“": '"', "”": '"',
                         "–": "-", "—": "-", " ": " "})
_WS = re.compile(r"\s+")


def normalise(text: str) -> str:
    return _WS.sub(" ", text.translate(_QUOTES)).strip()


def line_of(text: str, source: str) -> int | None:
    """1-based line where the normalised text starts, or None if it is not in the source."""
    needle = normalise(text)
    if not needle:
        return None
    lines = source.splitlines()
    # Fast path: the text sits inside one line.
    for i, line in enumerate(lines, start=1):
        if needle in normalise(line):
            return i
    # Slow path: the text spans several lines.
    flat = normalise(source)
    pos = flat.find(needle)
    if pos < 0:
        return None
    consumed = 0
    for i, line in enumerate(lines, start=1):
        consumed += len(normalise(line)) + 1
        if consumed > pos:
            return i
    return None


def filter_grounded(candidates: list[dict], source: str) -> tuple[list[Requirement], list[dict]]:
    """Split extractor candidates into grounded requirements and dropped items.

    Kept requirements get fresh sequential IDs (REQ-01 ...) and the line number
    found in the source, so a wrong ID or line from the model cannot leak through.
    """
    kept: list[Requirement] = []
    dropped: list[dict] = []
    seen: set[str] = set()
    for cand in candidates:
        text = normalise(str(cand.get("text", "")))
        line = line_of(text, source)
        if line is None:
            dropped.append({"text": text, "reason": "not found in source"})
            continue
        if text.lower() in seen:
            dropped.append({"text": text, "reason": "duplicate extraction"})
            continue
        seen.add(text.lower())
        kept.append(Requirement(id=f"REQ-{len(kept) + 1:02d}", text=text, line=line, kind=classify(text)))
    return kept, dropped


_NFR = re.compile(
    r"(?:\d\s*%)|\b(seconds?|ms|milliseconds?|percent|inactivity|session|available|availability|uptime|"
    r"concurrent|latency|performance|respond|response|load|loads|secure|securely|encrypt\w*|"
    r"usab\w*|user-friendly|intuitive|accessib\w*|maintain\w*|scal\w*|reliab\w*|wcag|fast|quickly)\b",
    re.IGNORECASE,
)


def classify(text: str) -> str:
    """Functional vs non-functional, by quality vocabulary. Deterministic."""
    return "non_functional" if _NFR.search(text) else "functional"

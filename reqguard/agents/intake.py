"""Intake agents: Idea-to-SRS and Extractor."""
from __future__ import annotations

import json
from typing import Any

from ..grounding import filter_grounded
from ..models import Requirement
from .base import Agent, require_list

MAX_REQUIREMENTS = 120


class IdeaToSRSAgent(Agent):
    """Turns a short idea into draft SRS text, which then goes through the normal review."""
    name = "idea_to_srs"

    def validate(self, data: Any) -> list[str]:
        problems = require_list(data, "requirements")
        if problems:
            return problems
        if not data["requirements"]:
            return ["no requirements written"]
        if any(not isinstance(r, dict) or not str(r.get("text", "")).strip() for r in data["requirements"]):
            return ["every requirement needs non-empty text"]
        return []

    def run(self, idea: str) -> str:
        data = self.call(json.dumps({"idea": idea}))
        title = str(data.get("title") or "Draft SRS").strip()
        lines = [f"# {title}", "", f"Generated from the idea: {idea.strip()}", ""]
        lines += [f"{i}. {str(r['text']).strip()}" for i, r in enumerate(data["requirements"][:MAX_REQUIREMENTS], 1)]
        return "\n".join(lines) + "\n"


class ExtractorAgent(Agent):
    """Splits the SRS into requirements. Output is never trusted: the grounding check filters it."""
    name = "extractor"

    def validate(self, data: Any) -> list[str]:
        problems = require_list(data, "requirements")
        if problems:
            return problems
        if any(not isinstance(r, dict) or "text" not in r for r in data["requirements"]):
            return ['every item needs a "text" field']
        return []

    def run(self, document: str) -> tuple[list[Requirement], list[dict]]:
        data = self.call("<document>\n" + document + "\n</document>")
        candidates = data["requirements"][:MAX_REQUIREMENTS]
        return filter_grounded(candidates, document)

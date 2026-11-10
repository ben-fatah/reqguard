"""Test-writer: Given-When-Then acceptance tests for approved requirements."""
from __future__ import annotations

import json
from typing import Any

from ..models import TestCase
from .base import Agent, require_list


class TestWriterAgent(Agent):
    name = "test_writer"
    __test__ = False   # tell pytest this is not a test class

    def validate(self, data: Any) -> list[str]:
        problems = require_list(data, "tests")
        if problems:
            return problems
        for t in data["tests"]:
            if not isinstance(t, dict):
                return ["every test must be an object"]
            missing = [k for k in ("req_id", "given", "when", "then") if not str(t.get(k, "")).strip()]
            if missing:
                return [f"test is missing {', '.join(missing)}"]
        return []

    def run(self, requirements: list[dict]) -> list[TestCase]:
        """`requirements` = [{"id", "text"}] using the reviewer's final text."""
        data = self.call(json.dumps({"requirements": requirements}))
        valid = {r["id"] for r in requirements}
        return [TestCase(req_id=t["req_id"], given=t["given"].strip(), when=t["when"].strip(),
                         then=t["then"].strip())
                for t in data["tests"] if t["req_id"] in valid]

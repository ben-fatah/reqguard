"""Benchmark (FR-13): rule precision and recall against a labelled synthetic SRS.

    python -m reqguard.bench benchmark/srs_inventory_v1.labels.json

Only the rule engine is scored, so the result is deterministic and repeatable.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from .grounding import classify
from .models import Requirement
from .rules import PACKS

SCORED_RULES = {"R1", "R2", "R3", "R4", "R5", "R6"}


def evaluate(labels_path: str | Path) -> dict:
    data = json.loads(Path(labels_path).read_text(encoding="utf-8"))
    reqs = [Requirement(r["id"], r["text"], r["line"], classify(r["text"])) for r in data["requirements"]]
    expected = {(r["id"], rule) for r in data["requirements"] for rule in r["expected_rules"]}
    found = {(f.req_id, f.rule_id) for pack in PACKS.values() for f in pack(reqs)
             if f.rule_id in SCORED_RULES}
    per_rule = {}
    for rule in sorted(SCORED_RULES):
        e = {x for x in expected if x[1] == rule}
        g = {x for x in found if x[1] == rule}
        tp = len(e & g)
        per_rule[rule] = {"expected": len(e), "found": len(g), "true_positive": tp,
                          "false_positive": len(g - e), "missed": len(e - g)}
    tp = len(expected & found)
    precision = tp / len(found) if found else 1.0
    recall = tp / len(expected) if expected else 1.0
    return {"document": data.get("document"), "requirements": len(reqs), "planted_defects": len(expected),
            "precision": round(precision, 3), "recall": round(recall, 3),
            "false_positives": sorted(found - expected), "missed": sorted(expected - found),
            "per_rule": per_rule}


def main(argv: list[str]) -> int:
    path = argv[0] if argv else "benchmark/srs_inventory_v1.labels.json"
    result = evaluate(path)
    print(json.dumps(result, indent=2))
    ok = result["precision"] >= 0.90 and result["recall"] >= 0.80   # NFR-02 targets
    print("NFR-02:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

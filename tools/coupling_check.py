"""Coupling check for ReqGuard architecture specs (implements NFR-08 evidence).

Reads a JSON architecture spec (modules, their bounded context, and their
dependencies) and reports:
  C1  dependency cycles between modules
  C2  forbidden cross-context edges (context rules below)
  C3  tables written by more than one module (shared-write coupling)
  C4  modules whose fan-out exceeds MAX_FAN_OUT

Usage:
    python tools/coupling_check.py architecture/option_a.json [more.json ...]
Exit code is 1 if any spec has a violation, so it can run in CI.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

MAX_FAN_OUT = 6

# Context -> contexts it must never call or import.
FORBIDDEN = {
    "analysis": {"storage", "review", "identity", "web", "pipeline"},
    "llm": {"storage", "review", "identity", "web", "pipeline", "analysis", "ingestion", "reporting"},
    "ingestion": {"analysis", "review", "pipeline"},
    "review": {"analysis"},
    "identity": {"analysis", "review", "pipeline", "ingestion", "reporting"},
}
# Contexts that must never write to any table.
READ_ONLY_CONTEXTS = {"analysis", "reporting", "llm"}


def load(path: Path) -> dict:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def find_cycles(graph: dict[str, list[str]]) -> list[list[str]]:
    """Return each distinct cycle once, found by depth-first search."""
    cycles: list[list[str]] = []
    seen: set[frozenset[str]] = set()

    def dfs(node: str, stack: list[str]) -> None:
        for nxt in graph.get(node, []):
            if nxt in stack:
                cycle = stack[stack.index(nxt):] + [nxt]
                key = frozenset(cycle)
                if key not in seen:
                    seen.add(key)
                    cycles.append(cycle)
            elif nxt in graph:
                dfs(nxt, stack + [nxt])

    for start in graph:
        dfs(start, [start])
    return cycles


def check(spec: dict) -> list[str]:
    modules = spec["modules"]
    context_of = {name: m["context"] for name, m in modules.items()}
    calls = {name: m.get("calls", []) for name, m in modules.items()}
    violations: list[str] = []

    for cycle in find_cycles(calls):
        violations.append(f"C1 cycle: {' -> '.join(cycle)}")

    for src, targets in calls.items():
        for dst in targets:
            if dst not in context_of:
                violations.append(f"C2 unknown module '{dst}' called by '{src}'")
                continue
            src_ctx, dst_ctx = context_of[src], context_of[dst]
            if dst_ctx in FORBIDDEN.get(src_ctx, set()):
                violations.append(
                    f"C2 forbidden edge: {src} ({src_ctx}) -> {dst} ({dst_ctx})"
                )

    writers: dict[str, list[str]] = {}
    for name, m in modules.items():
        for table in m.get("writes", []):
            writers.setdefault(table, []).append(name)
            if context_of[name] in READ_ONLY_CONTEXTS:
                violations.append(
                    f"C2 forbidden write: {name} ({context_of[name]}) writes table '{table}'"
                )
    for table, ws in sorted(writers.items()):
        if len(ws) > 1:
            violations.append(f"C3 shared write: table '{table}' written by {sorted(ws)}")

    for name, targets in calls.items():
        if len(set(targets)) > MAX_FAN_OUT:
            violations.append(
                f"C4 fan-out {len(set(targets))} > {MAX_FAN_OUT}: {name} -> {sorted(set(targets))}"
            )
    return violations


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 2
    failed = False
    for arg in argv:
        spec = load(Path(arg))
        violations = check(spec)
        status = "PASS" if not violations else f"FAIL ({len(violations)} violations)"
        print(f"== {spec.get('name', arg)}: {status}")
        for v in violations:
            print(f"   - {v}")
        failed = failed or bool(violations)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

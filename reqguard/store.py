"""SQLite persistence. The only module that writes the database.

Decisions are append-only (FR-09): there is no function to update or delete one.
The current status of a finding or test is its latest decision.
"""
from __future__ import annotations

import json
import os
import sqlite3
import threading
from dataclasses import asdict
from datetime import datetime, timezone

from .models import RunResult, TestCase, Usage

SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
  id INTEGER PRIMARY KEY AUTOINCREMENT, created_at TEXT NOT NULL, source_type TEXT NOT NULL,
  source_text TEXT NOT NULL, score INTEGER, grade TEXT, summary TEXT,
  usage_json TEXT, errors_json TEXT, dropped_json TEXT);
CREATE TABLE IF NOT EXISTS requirements (
  run_id INTEGER NOT NULL, id TEXT NOT NULL, text TEXT NOT NULL, line INTEGER, kind TEXT,
  PRIMARY KEY (run_id, id));
CREATE TABLE IF NOT EXISTS findings (
  run_id INTEGER NOT NULL, id TEXT NOT NULL, req_id TEXT, agent TEXT, source TEXT, severity TEXT,
  rule_id TEXT, problem TEXT, suggestion TEXT, span_json TEXT, related_json TEXT,
  PRIMARY KEY (run_id, id));
CREATE TABLE IF NOT EXISTS tests (
  run_id INTEGER NOT NULL, id TEXT NOT NULL, req_id TEXT, given TEXT, when_ TEXT, then_ TEXT,
  PRIMARY KEY (run_id, id));
CREATE TABLE IF NOT EXISTS decisions (
  id INTEGER PRIMARY KEY AUTOINCREMENT, run_id INTEGER NOT NULL, target_type TEXT NOT NULL,
  target_id TEXT NOT NULL, decision TEXT NOT NULL, reason TEXT, new_text TEXT,
  role TEXT NOT NULL, created_at TEXT NOT NULL);
"""

REWRITE_EXCLUDED_AGENTS = {"consistency"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class Store:
    def __init__(self, path: str | None = None):
        self.path = path or os.getenv("REQGUARD_DB", "reqguard.db")
        self._lock = threading.Lock()
        self._db = sqlite3.connect(self.path, check_same_thread=False)
        self._db.row_factory = sqlite3.Row
        self._db.executescript(SCHEMA)

    # ---------- writes ----------
    def save_run(self, r: RunResult) -> int:
        with self._lock, self._db:
            cur = self._db.execute(
                "INSERT INTO runs (created_at, source_type, source_text, score, grade, summary, usage_json,"
                " errors_json, dropped_json) VALUES (?,?,?,?,?,?,?,?,?)",
                (_now(), r.source_type, r.source_text, r.score, r.grade, r.summary,
                 json.dumps([asdict(u) for u in r.usage]), json.dumps(r.errors), json.dumps(r.dropped)))
            run_id = int(cur.lastrowid)
            self._db.executemany("INSERT INTO requirements VALUES (?,?,?,?,?)",
                                 [(run_id, q.id, q.text, q.line, q.kind) for q in r.requirements])
            self._db.executemany(
                "INSERT INTO findings VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                [(run_id, f.id, f.req_id, f.agent, f.source, f.severity, f.rule_id, f.problem, f.suggestion,
                  json.dumps(f.span), json.dumps(f.related)) for f in r.findings])
        return run_id

    def save_tests(self, run_id: int, tests: list[TestCase], usage: Usage) -> None:
        with self._lock, self._db:
            n = self._db.execute("SELECT COUNT(*) FROM tests WHERE run_id=?", (run_id,)).fetchone()[0]
            rows = []
            for i, t in enumerate(tests, start=n + 1):
                t.id = f"T-{i:03d}"
                rows.append((run_id, t.id, t.req_id, t.given, t.when, t.then))
            self._db.executemany("INSERT INTO tests VALUES (?,?,?,?,?,?)", rows)
            usage_rows = json.loads(self._db.execute("SELECT usage_json FROM runs WHERE id=?",
                                                     (run_id,)).fetchone()[0] or "[]")
            usage_rows.append(asdict(usage))
            self._db.execute("UPDATE runs SET usage_json=? WHERE id=?", (json.dumps(usage_rows), run_id))

    def add_decision(self, run_id: int, target_type: str, target_id: str, decision: str,
                     reason: str | None, new_text: str | None, role: str) -> None:
        with self._lock, self._db:
            self._db.execute(
                "INSERT INTO decisions (run_id, target_type, target_id, decision, reason, new_text, role,"
                " created_at) VALUES (?,?,?,?,?,?,?,?)",
                (run_id, target_type, target_id, decision, reason, new_text, role, _now()))

    # ---------- reads ----------
    def list_runs(self) -> list[dict]:
        rows = self._db.execute(
            "SELECT r.id, r.created_at, r.source_type, r.score, r.grade,"
            " (SELECT COUNT(*) FROM requirements q WHERE q.run_id=r.id) AS requirements,"
            " (SELECT COUNT(*) FROM findings f WHERE f.run_id=r.id) AS findings,"
            " substr(r.source_text, 1, 80) AS preview FROM runs r ORDER BY r.id DESC LIMIT 50").fetchall()
        return [dict(x) for x in rows]

    def exists(self, run_id: int) -> bool:
        return self._db.execute("SELECT 1 FROM runs WHERE id=?", (run_id,)).fetchone() is not None

    def get_run(self, run_id: int) -> dict | None:
        run = self._db.execute("SELECT * FROM runs WHERE id=?", (run_id,)).fetchone()
        if run is None:
            return None
        latest: dict[tuple[str, str], dict] = {}
        history = [dict(d) for d in self._db.execute(
            "SELECT * FROM decisions WHERE run_id=? ORDER BY id", (run_id,)).fetchall()]
        for d in history:
            latest[(d["target_type"], d["target_id"])] = d

        findings = []
        for f in self._db.execute("SELECT * FROM findings WHERE run_id=? ORDER BY id", (run_id,)):
            d = latest.get(("finding", f["id"]))
            findings.append({
                "id": f["id"], "req_id": f["req_id"], "agent": f["agent"], "source": f["source"],
                "severity": f["severity"], "rule_id": f["rule_id"], "problem": f["problem"],
                "suggestion": f["suggestion"], "span": json.loads(f["span_json"] or "null"),
                "related": json.loads(f["related_json"] or "[]"),
                "status": d["decision"] if d else "open", "reason": d["reason"] if d else None,
                "new_text": d["new_text"] if d else None})

        requirements = []
        for q in self._db.execute("SELECT * FROM requirements WHERE run_id=? ORDER BY rowid", (run_id,)):
            own = [f for f in findings if f["req_id"] == q["id"]]
            requirements.append({"id": q["id"], "text": q["text"], "line": q["line"], "kind": q["kind"],
                                 "final_text": self._final_text(q["text"], own, history),
                                 "open_findings": sum(1 for f in own if f["status"] == "open"),
                                 "findings": len(own)})

        tests = []
        for t in self._db.execute("SELECT * FROM tests WHERE run_id=? ORDER BY id", (run_id,)):
            d = latest.get(("test", t["id"]))
            tests.append({"id": t["id"], "req_id": t["req_id"], "given": t["given"], "when": t["when_"],
                          "then": (d["new_text"] if d and d["decision"] == "edit" else t["then_"]),
                          "status": d["decision"] if d else "open", "reason": d["reason"] if d else None})

        return {"id": run["id"], "created_at": run["created_at"], "source_type": run["source_type"],
                "source_text": run["source_text"], "score": run["score"], "grade": run["grade"],
                "summary": run["summary"], "usage": json.loads(run["usage_json"] or "[]"),
                "errors": json.loads(run["errors_json"] or "[]"),
                "dropped": json.loads(run["dropped_json"] or "[]"),
                "requirements": requirements, "findings": findings, "tests": tests,
                "decisions": history,
                "open_findings": sum(1 for f in findings if f["status"] == "open")}

    @staticmethod
    def _final_text(original: str, own_findings: list[dict], history: list[dict]) -> str:
        """Apply this requirement's accepted rewrites and edits in decision order."""
        by_id = {f["id"]: f for f in own_findings}
        text = original
        for d in history:
            f = by_id.get(d["target_id"]) if d["target_type"] == "finding" else None
            if f is None:
                continue
            if d["decision"] == "edit" and d["new_text"]:
                text = d["new_text"]
            elif (d["decision"] == "accept" and f["suggestion"] and text == original
                  and f["agent"] not in REWRITE_EXCLUDED_AGENTS):
                text = f["suggestion"]   # a rewrite applies only to unrevised text; later ones need an edit
        return text

"""Command line:  python -m reqguard review FILE.md   |   python -m reqguard idea "text"

Prints the findings without starting the web app. Uses the model set by REQGUARD_LLM
(read from the environment or from .env). REQGUARD_LOG=INFO shows each agent call's start and end.
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path

from .env import load_env
from .pipeline import Orchestrator, PipelineError


def main(argv: list[str] | None = None) -> int:
    load_env()
    logging.basicConfig(level=os.getenv("REQGUARD_LOG", "WARNING").upper(),
                        format="%(asctime)s.%(msecs)03d %(levelname)s %(message)s", datefmt="%H:%M:%S")
    logging.getLogger("httpx").setLevel(logging.WARNING)   # one line per poll is noise
    p = argparse.ArgumentParser(prog="reqguard")
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("review", help="review an SRS text file")
    r.add_argument("file")
    r.add_argument("--json", action="store_true", help="print the full result as JSON")
    i = sub.add_parser("idea", help="draft an SRS from an idea, then review it")
    i.add_argument("idea")
    i.add_argument("--json", action="store_true")
    args = p.parse_args(argv)

    try:
        if args.cmd == "review":
            result = Orchestrator().review(text=Path(args.file).read_text(encoding="utf-8"))
        else:
            result = Orchestrator().review(idea=args.idea)
    except PipelineError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
        return 0
    if result.source_type == "idea":
        print(result.source_text)
    print(f"Score {result.score}/100 ({result.grade}) - {len(result.requirements)} requirements, "
          f"{len(result.findings)} findings (rule {sum(f.source == 'rule' for f in result.findings)}, scored; "
          f"AI advisory {sum(f.source == 'ai' for f in result.findings)}, not scored)")
    models = sorted({u.model for u in result.usage if u.model})
    if models:
        print("Model:", ", ".join(models))
    print(result.summary, "\n")
    texts = {q.id: q.text for q in result.requirements}
    for f in result.findings:
        src = f"rule {f.rule_id}" if f.source == "rule" else "AI"
        print(f"{f.id} [{f.severity:<6}] {f.req_id or 'DOC':<6} {f.agent:<14} {src:<8} {f.problem}")
        if f.req_id:
            print(f"        text: {texts[f.req_id]}")
        if f.suggestion:
            print(f"        suggestion: {f.suggestion}")
    for e in result.errors:
        print("warning:", e, file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())

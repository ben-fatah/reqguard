"""HTTP API and web UI. Run with:  uvicorn reqguard.api:app --reload

Access control (FR-12): every API call sends an X-Role header.
  engineer -> create reviews, export the report
  reviewer -> decide findings, generate and decide tests
This is a course-demo login (no passwords); see the README limitations.
"""
from __future__ import annotations

from pathlib import Path
from typing import Literal

from fastapi import Depends, FastAPI, File, Header, HTTPException, UploadFile
from fastapi.responses import FileResponse, PlainTextResponse
from pydantic import BaseModel, Field

from .env import load_env
from .llm import LLMError
from .pipeline import MAX_DOCUMENT_BYTES, Orchestrator, PipelineError
from .report import build_report
from .store import Store

WEB = Path(__file__).resolve().parent / "web"
ROLES = ("engineer", "reviewer")
ALLOWED_EXTENSIONS = (".txt", ".md")


class NewRun(BaseModel):
    text: str | None = Field(default=None, max_length=MAX_DOCUMENT_BYTES)
    idea: str | None = Field(default=None, max_length=2000)


class Decision(BaseModel):
    decision: Literal["accept", "edit", "reject"]
    reason: str | None = Field(default=None, max_length=500)
    new_text: str | None = Field(default=None, max_length=2000)


def create_app(store: Store | None = None, orchestrator: Orchestrator | None = None) -> FastAPI:
    app = FastAPI(title="ReqGuard", version="0.2.0")
    app.state.store = store
    app.state.orchestrator = orchestrator

    def get_store() -> Store:
        if app.state.store is None:
            app.state.store = Store()
        return app.state.store

    def get_orchestrator() -> Orchestrator:
        if app.state.orchestrator is None:
            try:
                app.state.orchestrator = Orchestrator()
            except LLMError as exc:
                raise HTTPException(500, str(exc)) from exc
        return app.state.orchestrator

    def role(x_role: str | None = Header(default=None)) -> str:
        if not x_role:
            raise HTTPException(401, "Choose a role: send the X-Role header (engineer or reviewer).")
        if x_role not in ROLES:
            raise HTTPException(403, f"Unknown role {x_role!r}.")
        return x_role

    def require(*allowed: str):
        def check(r: str = Depends(role)) -> str:
            if r not in allowed:
                raise HTTPException(403, f"The {r} role cannot do this. Allowed: {', '.join(allowed)}.")
            return r
        return check

    def load(run_id: int, s: Store) -> dict:
        run = s.get_run(run_id)
        if run is None:
            raise HTTPException(404, f"Run {run_id} not found.")
        return run

    def start(s: Store, o: Orchestrator, **kwargs) -> dict:
        try:
            result = o.review(**kwargs)
        except PipelineError as exc:
            raise HTTPException(422, str(exc)) from exc
        return s.get_run(s.save_run(result))

    @app.get("/", include_in_schema=False)
    def index() -> FileResponse:
        return FileResponse(WEB / "index.html")

    @app.get("/api/health")
    def health(o: Orchestrator = Depends(get_orchestrator)) -> dict:
        return {"status": "ok", "llm": o.llm.name}

    @app.post("/api/runs")
    def create_run(body: NewRun, _: str = Depends(require("engineer")),
                   s: Store = Depends(get_store), o: Orchestrator = Depends(get_orchestrator)) -> dict:
        return start(s, o, text=body.text, idea=body.idea)

    @app.post("/api/runs/upload")
    async def upload_run(file: UploadFile = File(...), _: str = Depends(require("engineer")),
                         s: Store = Depends(get_store), o: Orchestrator = Depends(get_orchestrator)) -> dict:
        name = (file.filename or "").lower()
        if not name.endswith(ALLOWED_EXTENSIONS):
            raise HTTPException(415, "Only .txt or .md files up to 200 KB are accepted.")
        data = await file.read(MAX_DOCUMENT_BYTES + 1)
        if len(data) > MAX_DOCUMENT_BYTES:
            raise HTTPException(413, "Only .txt or .md files up to 200 KB are accepted.")
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise HTTPException(415, "The file must be UTF-8 text.") from exc
        return start(s, o, text=text)

    @app.get("/api/runs")
    def list_runs(_: str = Depends(role), s: Store = Depends(get_store)) -> list[dict]:
        return s.list_runs()

    @app.get("/api/runs/{run_id}")
    def get_run(run_id: int, _: str = Depends(role), s: Store = Depends(get_store)) -> dict:
        return load(run_id, s)

    @app.post("/api/runs/{run_id}/findings/{finding_id}/decision")
    def decide_finding(run_id: int, finding_id: str, body: Decision, r: str = Depends(require("reviewer")),
                       s: Store = Depends(get_store)) -> dict:
        run = load(run_id, s)
        if not any(f["id"] == finding_id for f in run["findings"]):
            raise HTTPException(404, f"Finding {finding_id} not found in run {run_id}.")
        _check_decision(body)
        s.add_decision(run_id, "finding", finding_id, body.decision, _clean(body.reason), _clean(body.new_text), r)
        return s.get_run(run_id)

    @app.post("/api/runs/{run_id}/tests")
    def generate_tests(run_id: int, _: str = Depends(require("reviewer")), s: Store = Depends(get_store),
                       o: Orchestrator = Depends(get_orchestrator)) -> dict:
        run = load(run_id, s)
        covered = {t["req_id"] for t in run["tests"]}
        ready = [{"id": q["id"], "text": q["final_text"]} for q in run["requirements"]
                 if q["open_findings"] == 0 and q["id"] not in covered]
        if not ready:
            raise HTTPException(409, "No requirement is ready: decide all of a requirement's findings first.")
        try:
            tests, usage = o.write_tests(ready)
        except PipelineError as exc:
            raise HTTPException(502, str(exc)) from exc
        s.save_tests(run_id, tests, usage)
        return s.get_run(run_id)

    @app.post("/api/runs/{run_id}/tests/{test_id}/decision")
    def decide_test(run_id: int, test_id: str, body: Decision, r: str = Depends(require("reviewer")),
                    s: Store = Depends(get_store)) -> dict:
        run = load(run_id, s)
        if not any(t["id"] == test_id for t in run["tests"]):
            raise HTTPException(404, f"Test {test_id} not found in run {run_id}.")
        _check_decision(body)
        s.add_decision(run_id, "test", test_id, body.decision, _clean(body.reason), _clean(body.new_text), r)
        return s.get_run(run_id)

    @app.get("/api/runs/{run_id}/report.md", response_class=PlainTextResponse)
    def report(run_id: int, _: str = Depends(role), s: Store = Depends(get_store)) -> str:
        run = load(run_id, s)
        if run["open_findings"]:
            raise HTTPException(409, f"Export blocked: {run['open_findings']} findings are still undecided.")
        return build_report(run)

    return app


def _clean(value: str | None) -> str | None:
    value = (value or "").strip()
    return value or None


def _check_decision(body: Decision) -> None:
    reason = _clean(body.reason)
    if body.decision == "reject" and (reason is None or not 10 <= len(reason) <= 500):
        raise HTTPException(422, "A rejection needs a reason of 10 to 500 characters.")
    if body.decision == "edit" and not _clean(body.new_text):
        raise HTTPException(422, "An edit needs the new text.")


load_env()   # .env is read before the first request creates the model client
app = create_app()

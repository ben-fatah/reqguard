"""HTTP API: roles, upload limits, decisions, tests, export."""
import pytest
from fastapi.testclient import TestClient

from reqguard.api import create_app
from reqguard.llm import MockLLM
from reqguard.pipeline import Orchestrator
from reqguard.store import Store

ENG = {"X-Role": "engineer"}
REV = {"X-Role": "reviewer"}
SRS = ("Passwords shall be stored.\n"
       "The system shall export reports as CSV files.\n"
       "Reports should load quickly.\n")


@pytest.fixture
def client(tmp_path):
    app = create_app(Store(str(tmp_path / "t.db")), Orchestrator(MockLLM()))
    return TestClient(app)


@pytest.fixture
def run(client):
    return client.post("/api/runs", json={"text": SRS}, headers=ENG).json()


def test_health_reports_model(client):
    assert client.get("/api/health").json() == {"status": "ok", "llm": "mock"}


def test_create_run(run):
    assert len(run["requirements"]) == 3 and run["open_findings"] == len(run["findings"]) > 0


def test_role_required(client):
    assert client.post("/api/runs", json={"text": SRS}).status_code == 401
    assert client.post("/api/runs", json={"text": SRS}, headers={"X-Role": "admin"}).status_code == 403


def test_reviewer_cannot_start_and_engineer_cannot_decide(client, run):
    assert client.post("/api/runs", json={"text": SRS}, headers=REV).status_code == 403
    fid = run["findings"][0]["id"]
    r = client.post(f"/api/runs/{run['id']}/findings/{fid}/decision", json={"decision": "accept"}, headers=ENG)
    assert r.status_code == 403
    assert client.get(f"/api/runs/{run['id']}", headers=ENG).json()["decisions"] == []   # nothing stored


def test_upload_rules(client):
    ok = client.post("/api/runs/upload", files={"file": ("srs.md", SRS.encode(), "text/markdown")}, headers=ENG)
    assert ok.status_code == 200
    pdf = client.post("/api/runs/upload", files={"file": ("srs.pdf", b"%PDF", "application/pdf")}, headers=ENG)
    assert pdf.status_code == 415
    big = client.post("/api/runs/upload", files={"file": ("big.txt", b"a" * 200_001, "text/plain")}, headers=ENG)
    assert big.status_code == 413
    edge = ("The system shall export reports as CSV files.\n" * 5000)[:200_000].encode()
    assert len(edge) == 200_000
    assert client.post("/api/runs/upload", files={"file": ("edge.txt", edge, "text/plain")},
                       headers=ENG).status_code == 200
    arabic = "يجب أن يكون النظام سريعاً وسهل الاستخدام.\n".encode()
    r = client.post("/api/runs/upload", files={"file": ("ar.txt", arabic, "text/plain")}, headers=ENG)
    assert r.status_code == 422 and "English" in r.json()["detail"]


@pytest.mark.parametrize("reason,status", [(None, 422), ("x" * 9, 422), ("x" * 10, 200), ("x" * 500, 200),
                                           ("x" * 501, 422)])
def test_reject_reason_boundaries(client, run, reason, status):
    fid = run["findings"][0]["id"]
    r = client.post(f"/api/runs/{run['id']}/findings/{fid}/decision",
                    json={"decision": "reject", "reason": reason}, headers=REV)
    assert r.status_code == status


def test_edit_needs_text(client, run):
    fid = run["findings"][0]["id"]
    r = client.post(f"/api/runs/{run['id']}/findings/{fid}/decision", json={"decision": "edit"}, headers=REV)
    assert r.status_code == 422


def test_accepting_a_rewrite_changes_final_text(client, run):
    s1 = next(f for f in run["findings"] if f["rule_id"] == "S1")
    after = client.post(f"/api/runs/{run['id']}/findings/{s1['id']}/decision",
                        json={"decision": "accept"}, headers=REV).json()
    req = next(q for q in after["requirements"] if q["id"] == s1["req_id"])
    assert req["final_text"] == s1["suggestion"] and req["text"] == "Passwords shall be stored."


def test_decisions_are_append_only_history(client, run):
    fid = run["findings"][0]["id"]
    url = f"/api/runs/{run['id']}/findings/{fid}/decision"
    client.post(url, json={"decision": "reject", "reason": "Not a real problem here."}, headers=REV)
    after = client.post(url, json={"decision": "accept"}, headers=REV).json()
    assert [d["decision"] for d in after["decisions"]] == ["reject", "accept"]
    assert next(f for f in after["findings"] if f["id"] == fid)["status"] == "accept"


def test_unknown_finding_and_run(client, run):
    assert client.post(f"/api/runs/{run['id']}/findings/F-999/decision", json={"decision": "accept"},
                       headers=REV).status_code == 404
    assert client.get("/api/runs/999", headers=ENG).status_code == 404


def decide_all(client, run):
    for f in run["findings"]:
        client.post(f"/api/runs/{run['id']}/findings/{f['id']}/decision", json={"decision": "accept"}, headers=REV)


def test_tests_only_for_ready_requirements(client, run):
    # REQ-02 has no findings, so it is ready immediately; the others are not.
    r = client.post(f"/api/runs/{run['id']}/tests", headers=REV).json()
    assert {t["req_id"] for t in r["tests"]} == {"REQ-02"}
    decide_all(client, run)
    r = client.post(f"/api/runs/{run['id']}/tests", headers=REV).json()
    assert {t["req_id"] for t in r["tests"]} == {"REQ-01", "REQ-02", "REQ-03"}
    assert client.post(f"/api/runs/{run['id']}/tests", headers=REV).status_code == 409   # nothing left


def test_test_decision(client, run):
    r = client.post(f"/api/runs/{run['id']}/tests", headers=REV).json()
    tid = r["tests"][0]["id"]
    out = client.post(f"/api/runs/{run['id']}/tests/{tid}/decision", json={"decision": "accept"}, headers=REV).json()
    assert out["tests"][0]["status"] == "accept"


def test_export_blocked_until_all_decided(client, run):
    blocked = client.get(f"/api/runs/{run['id']}/report.md", headers=ENG)
    assert blocked.status_code == 409 and str(len(run["findings"])) in blocked.json()["detail"]
    decide_all(client, run)
    report = client.get(f"/api/runs/{run['id']}/report.md", headers=ENG).text
    assert report.startswith("# ReqGuard review report") and "REQ-01" in report and "Decision: accepted" in report


def test_pipeline_error_returns_422(client):
    r = client.post("/api/runs", json={"text": "# heading only"}, headers=ENG)
    assert r.status_code == 422 and "No requirements" in r.json()["detail"]


def test_index_page(client):
    assert "ReqGuard" in client.get("/").text


def test_second_rewrite_does_not_overwrite_a_revised_requirement(client, run):
    # REQ-01 "Passwords shall be stored." has S1 and R6 findings, each with a suggested rewrite.
    s1 = next(f for f in run["findings"] if f["rule_id"] == "S1")
    r6 = next(f for f in run["findings"] if f["rule_id"] == "R6")
    base = f"/api/runs/{run['id']}/findings/"
    client.post(base + s1["id"] + "/decision", json={"decision": "accept"}, headers=REV)
    after = client.post(base + r6["id"] + "/decision", json={"decision": "accept"}, headers=REV).json()
    assert after["requirements"][0]["final_text"] == s1["suggestion"]

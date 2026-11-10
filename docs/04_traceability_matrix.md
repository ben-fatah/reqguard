# 04 — Traceability Matrix

Format follows Week 6 (requirement → design → code → test), extended with the ADR and trade-off-matrix row each requirement drives.

- **Status** at M1 is *Planned*; it becomes *Implemented* (code linked) at M2 and *Verified* (test passing) from M2 onwards.
- Code references are planned `file:symbol` locations from the chosen architecture (Option A, `05_architecture.md`). Each function will carry a `# implements FR-xx` tag so the links can be checked by `grep`.
- **Verification of links:** every Req ID below exists in `02_requirements.md`; every ADR ID exists in `docs/adr/`; every trade-off row exists in `06_tradeoff_matrix.md`. No requirement is orphaned (each has at least one design element and one planned test), and no planned module lacks a requirement.

## Functional requirements

| Req ID | Requirement (short) | Design element (Option A) | ADR | Code (planned) | Planned test(s) | Status |
|---|---|---|---|---|---|---|
| FR-01 | Accept only .txt/.md ≤ 200 KB | Web/API container → Ingestion | — | `reqguard/ingestion/upload.py:validate_upload` | T-01 valid upload; T-02 wrong extension; T-03 exactly 200 KB accepted / 200 KB + 1 byte rejected | Planned |
| FR-02 | Extract requirements with ID and line | Extractor agent | ADR-003 | `reqguard/agents/extractor.py:ExtractorAgent.run` | T-04 extractor output parsed with mocked LLM; T-05 line numbers correct | Planned |
| FR-03 | Keep only verbatim-grounded requirements | Grounding check (Analysis context) | ADR-004 | `reqguard/analysis/grounding.py:filter_grounded` | T-06 invented requirement dropped; T-07 whitespace-only difference kept | Planned |
| FR-04 | Apply rules R1–R6 with span | Rule engine (Analysis context) | ADR-002 | `reqguard/analysis/rules.py:check_requirement` | T-08..T-13 one positive and one negative case per rule; T-14 R1 not raised when a number+unit is present | Planned |
| FR-05 | AI advisory findings and rewrite, labelled | Quality agent | ADR-002, ADR-003 | `reqguard/agents/quality.py:QualityAgent.run` | T-15 findings stored with source = AI advisory; T-16 rule findings unchanged when AI returns nothing | Planned |
| FR-06 | Generate GWT tests for decided requirements | Test-writer agent | ADR-003 | `reqguard/agents/test_writer.py:TestWriterAgent.run` | T-17 one test per decided requirement (mocked LLM) | Planned |
| FR-07 | Schema/GWT validation, one retry, then fail | Orchestrator + validators | ADR-003 | `reqguard/analysis/validation.py:validate_output`, `reqguard/pipeline/orchestrator.py:run_stage` | T-18 missing *Then* rejected; T-19 retry once then *Failed – retryable* | Planned |
| FR-08 | Accept / edit / reject with reason 10–500 chars | Review context | — | `reqguard/review/service.py:decide` | T-20 reject without reason refused; T-21 reason of 9 chars refused, 10 accepted, 500 accepted, 501 refused | Planned |
| FR-09 | Immutable audit record of decisions | Review context → audit table | — | `reqguard/review/audit.py:record_decision` | T-22 decision creates audit row with before/after; T-23 no API route updates or deletes audit rows | Planned |
| FR-10 | Run record with stage, times, tokens | Orchestrator → runs table (task record) | ADR-001 | `reqguard/pipeline/orchestrator.py:Orchestrator`, `reqguard/llm/devai_client.py:DevAIClient.complete` | T-24 stage transitions in order; T-25 token counts stored per call | Planned |
| FR-11 | Markdown export, blocked while undecided | Reporting context | — | `reqguard/reporting/export.py:build_report` | T-26 report contains requirement → finding → test links; T-27 export blocked with undecided count | Planned |
| FR-12 | Login; role-based permissions | Identity context + API dependency | — | `reqguard/identity/auth.py:require_role` | T-28 engineer cannot decide; T-29 reviewer cannot upload | Planned |
| FR-13 | Benchmark precision / recall / FP per rule | Benchmark CLI | ADR-002 | `reqguard/bench/benchmark.py:main` | T-30 benchmark on a 5-item fixture gives known precision and recall | Planned |

## Non-functional requirements (quality-attribute scenarios)

| Req ID | Scenario (short) | Design element | ADR | Trade-off row | Verification (planned) | Status |
|---|---|---|---|---|---|---|
| NFR-01 | p95 ≤ 120 s to *Awaiting review* (40 reqs) | Batched agent calls, in-process orchestrator | ADR-001, ADR-003 | TM-1 | Timed run × 10 on benchmark SRS (M3) | Planned |
| NFR-02 | Rule precision ≥ 0.90, recall ≥ 0.80; 0 invented reqs | Rule engine + grounding check | ADR-002, ADR-004 | TM-2 | FR-13 benchmark (M3) | Planned |
| NFR-03 | Rule findings identical 5/5; AI Jaccard ≥ 0.80 | Deterministic rules; fixed temperature | ADR-002 | TM-3 | Repeated-run script (M3) | Planned |
| NFR-04 | 12/12 authz cases → 401/403 | `require_role` dependency on every write route | — | TM-5 | T-28, T-29 + 10 parametrised cases | Planned |
| NFR-05 | 5/5 injection fixtures: rules unaffected, nothing auto-accepted | Rules independent of LLM; schema validation; human gate | ADR-002 | TM-5 | Injection fixtures in sandbox (M3) | Planned |
| NFR-06 | ≤ 30,000 tokens, ≤ USD 0.02 per run | Batched calls | ADR-003 | TM-4 | `tools/cost_model.py` + token log from FR-10 | Planned |
| NFR-07 | LLM failure: error ≤ 35 s, 0 rule findings lost | Rules run before AI stage; 30 s timeout | ADR-001, ADR-002 | TM-6 | Fault-injection test with mocked timeout (T-31) | Planned |
| NFR-08 | 0 cycles, 0 forbidden edges | Bounded contexts | ADR-001 | TM-7 | `tools/coupling_check.py` in CI | Planned |

## Reverse check (design → requirement)

| Planned module | Requirements it implements |
|---|---|
| `ingestion/upload.py` | FR-01 |
| `agents/extractor.py` | FR-02 |
| `analysis/grounding.py` | FR-03, NFR-02 |
| `analysis/rules.py` | FR-04, NFR-02, NFR-03, NFR-05 |
| `agents/quality.py` | FR-05 |
| `agents/test_writer.py` | FR-06 |
| `analysis/validation.py` | FR-07, NFR-05 |
| `pipeline/orchestrator.py` | FR-07, FR-10, NFR-01, NFR-07 |
| `llm/devai_client.py` | FR-10, NFR-06, NFR-07 |
| `review/service.py`, `review/audit.py` | FR-08, FR-09 |
| `reporting/export.py` | FR-11 |
| `identity/auth.py` | FR-12, NFR-04 |
| `bench/benchmark.py` | FR-13, NFR-02 |

Every module maps to at least one requirement, so nothing extra has crept in.

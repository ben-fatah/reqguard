# 07 — Coupling Report

Week 7 §8 asks for two coupling checks: **bounded-context discovery** and **dependency-graph analysis**. We encode each architecture as a module dependency spec (`architecture/*.json`) and run `tools/coupling_check.py` on it. The raw output is saved in `reports/coupling_run.txt`.

## 1. Bounded contexts (discovery)

Contexts and their vocabulary are defined in `05_architecture.md` §1.1. The seams follow the business language of requirements review: a *requirement* is a value produced by Analysis, a *decision* belongs to Review, a *run* belongs to Pipeline. Analysis never sees users or decisions, and Review never sees prompts.

## 2. Checks performed (dependency-graph analysis)

| Check | Rule | Why it matters for ReqGuard |
|---|---|---|
| C1 | No dependency cycles between modules | Cycles make modules impossible to test or replace separately |
| C2 | No forbidden cross-context edges. Analysis must not touch storage, review, identity, web or pipeline; the LLM client depends on nothing; Analysis, Reporting and the LLM client never write tables | Keeps agents and rules pure, so they can be unit-tested and mutation-tested with a mocked LLM |
| C3 | Each table has exactly one writing module | Prevents the "billing reads the auth table" failure from Week 7: two writers to one table means a hidden contract |
| C4 | Fan-out ≤ 6 per module | Flags god-modules |

## 3. Results

| Spec | Result | Violations |
|---|---|---|
| Option A — modular monolith (chosen) | **PASS** | 0 |
| Option B — distributed workers (rejected) | **FAIL** | 7 |
| DevAI architecture draft (as proposed) | **FAIL** | 8 |

Option B violations (verbatim from `reports/coupling_run.txt`):

```
- C2 forbidden write: analysis.extractor (analysis) writes table 'requirements'
- C2 forbidden write: analysis.rules (analysis) writes table 'findings'
- C2 forbidden write: analysis.quality (analysis) writes table 'findings'
- C2 forbidden write: analysis.test_writer (analysis) writes table 'test_cases'
- C3 shared write: table 'findings' written by ['analysis.quality', 'analysis.rules', 'review.service']
- C3 shared write: table 'runs' written by ['api.routes', 'worker.jobs']
- C3 shared write: table 'test_cases' written by ['analysis.test_writer', 'review.service']
```

**How Option A clears C3:** Review never updates a finding or a test. It appends a row to `review_actions`, and an item's current status is its latest decision. The Pipeline is the only writer of `runs`, `requirements`, `findings` and `test_cases`; Review is the only writer of `review_actions`.

## 4. DevAI draft

The raw DevAI architecture draft is encoded as `architecture/devai_draft.json` exactly as drawn in its C4 diagram and described in its text, without fixes, and checked with the same rules. **The detector flags the draft and clears our chosen option.**

```
== DevAI architecture draft (as proposed, unedited): FAIL (8 violations)
   - C1 cycle: api.gateway -> ingestion.service -> queue.redis -> api.gateway
   - C2 forbidden edge: ingestion.service (ingestion) -> queue.redis (pipeline)
   - C2 forbidden write: analysis.flagging (analysis) writes table 'flag_findings'
   - C2 forbidden write: analysis.acceptance_test (analysis) writes table 'acceptance_tests'
   - C2 forbidden write: reporting.exporter (reporting) writes table 'requirements'
   - C3 shared write: table 'acceptance_tests' written by ['analysis.acceptance_test', 'review.decision_service']
   - C3 shared write: table 'flag_findings' written by ['analysis.flagging', 'review.decision_service']
   - C3 shared write: table 'requirements' written by ['pipeline.orchestrator', 'reporting.exporter', 'review.decision_service']
```

What each finding means in the draft:
- **The cycle.** The API calls Ingestion, Ingestion enqueues to Redis, and Redis pushes progress back into the API.
- **Agents writing tables.** The Flagging and Acceptance-test agents write their own tables directly (the diagram's "write findings" and "write tests" edges).
- **Shared `requirements` table.** It has three writers: the orchestrator ("persist enriched items"), the Review service ("updates the item's status") and the Exporter (its "re-import" feature).

Our changes are recorded in `05_architecture.md` §5 and `03_correction_log.md`.

## 5. Residual risk the coupling check cannot reveal

The check only sees **code-level edges**: imports, calls and table writes. ReqGuard's most dangerous coupling is invisible to it:

**Prompt and schema coupling between agents.** The Quality agent's prompt assumes the Extractor's output fields (`id`, `text`, `line`) and the rule-finding format. The Test-writer assumes the Reviewer's edited text is the authoritative requirement. These contracts live in natural-language prompts and JSON shapes, not in imports. If someone renames a field or rewords the Extractor prompt so that it starts normalising text, there is no import edge to break. The check still says PASS, while the grounding check silently drops every requirement, or the Quality agent reviews the wrong text.

**Mitigation:**
1. One versioned Pydantic schema module is shared by all agents and validated on every output (FR-07).
2. A contract test per agent runs on a recorded golden output.
3. Prompts are versioned files under `prompts/`, and changing one requires a reviewed commit.
4. Risk RK-08 alerts when the grounding drop rate exceeds 10% on any run.

A second residual risk is **model behaviour drift**. DeepSeek retired the model name selected in DevAI and now serves those requests with V4.1-Flash. A provider-side model change alters agent behaviour with zero code change, which is tracked by the repeated-run checks (NFR-03, RK-03).

# AI Use Disclosure — Milestone 1

**Team:** Abderrahmane Benfatah, Omar Ramadhan · **Log owner for M1:** Abderrahmane Benfatah (rotates to Omar Ramadhan for M2)
**Period covered:** up to the M1 submission, 21 October 2026

## 1. Tools, models, mode and purpose

| Tool | Model | Mode | Purpose |
|---|---|---|---|
| DevAI (course-approved), web chat | DeepSeek-V4-Flash-Vision-Exp (served upstream by DeepSeek-V4.1-Flash, per DeepSeek's pricing page) | Chat, manual approval | First draft of requirements (Prompt 1); first draft of the architecture (Prompt 2); Extractor prompt token measurement |
| Claude (Anthropic, claude.ai) | Claude Opus 5.5 | Chat with file tools | Drafting help for the M1 documents: charter structure, requirement wording, C4 diagrams, ADR text, the coupling-check and cost-model scripts, benchmark SRS |

_Keep this table accurate. If the instructor restricts tools to DevAI only, raise it with the instructor; do not remove a tool that was actually used._

## 2. AI contribution by area (none / minor / substantial / primary)

| Area | AI contribution | Human contribution |
|---|---|---|
| Problem choice and project type | Minor | Chose ReqGuard over EvidenceBrief; chose multi-agent with fixed orchestration |
| Charter and non-goals | Substantial | Reviewed scope, set ceilings and module ownership |
| Requirements (FR, NFR, use cases) | Substantial | Validated each item against the charter; correction log |
| Traceability matrix | Substantial | Checked every ID link |
| Architecture options and C4 diagrams | Substantial | Selected the two options; rejected the DevAI draft's coupling |
| Trade-off matrix scores | Minor | Scores tied to measured or computed evidence |
| Cost model | Substantial (script) | Verified rates on DeepSeek's page; measured tokens in DevAI |
| Coupling check | Substantial (script) | Wrote the module specs; reviewed the results |
| ADRs | Substantial | Decisions and accepted downsides agreed by both members |
| Risk register | Substantial | Thresholds and owners agreed |

## 3. Errors and rejections

| # | What the AI produced | How we detected it | What we did |
|---|---|---|---|
| E-1 | DevAI requirements draft, NFR-02: a garbled clause ("reachable without reading-decisions-loading secondary steps") with no meaning | Read against the testability criterion; no test could pass or fail it | Rejected; accessibility recorded as a known limitation (`03_correction_log.md`) |
| E-2 | DevAI requirements draft, FR-09: a contradictory requirement, "requiring an optional but tracked reason" | Consistency criterion | Resolved as a mandatory reason of 10–500 characters (FR-08) |
| E-3 | DevAI requirements draft: no check that extracted requirements exist in the uploaded file, so the AI's own fabrications would reach the reviewer | Compared with Week 6 §6 (fabricated requirements) | Added FR-03 and ADR-004, the verbatim grounding check |
| E-4 | DevAI architecture draft: agents write tables directly, three tables have several writers, and there is a cycle API → Ingestion → Redis → API | `tools/coupling_check.py` on `architecture/devai_draft.json`: FAIL, 8 violations | Rejected; Option A keeps agents pure and one writer per table (PASS) |
| R-1 | **Rejected suggestion:** DevAI's per-requirement fan-out to meet "500 requirements in 60 seconds" | Cost model: fan-out uses 71,720 tokens per 40-requirement run vs 14,894 batched, which breaks NFR-06 | Kept batched calls (ADR-003); rewrote NFR-01 as a measurable 40-requirement scenario |
| R-2 | **Rejected suggestion:** DevAI's LiteLLM failover to other providers (GPT / Claude / self-hosted) | The brief names DEVAI as the approved tool; failover would send SRS text to unapproved tools | One LLM client, DevAI only |
| K-1 | **Kept suggestion:** DevAI's open question proposing "a short lexicon of ambiguity terms" | Matches ADR-002 | Became the deterministic rule engine R1–R6 |

## 4. Provenance

- Raw AI output is committed separately from human fixes: commit messages `raw(ai): …` and `fix(human): …`.
- AI involvement is recorded in this disclosure log (tools, areas, and the files each member reviewed) rather than in commit trailers.
- Named reader of each generated file:

| File | Read and checked by |
|---|---|
| `docs/01_charter.md`, `docs/02_requirements.md`, `docs/04_traceability_matrix.md` | _name_ |
| `docs/05_architecture.md`, `docs/06_tradeoff_matrix.md`, `docs/07_coupling_report.md` | _name_ |
| `docs/08_cost_model.md`, `tools/cost_model.py` | _name_ |
| `tools/coupling_check.py`, `architecture/*.json` | _name_ |
| `docs/adr/ADR-001…004`, `docs/09_risk_register.md` | _name_ |

## 5. Data and licensing

- Only synthetic data was used. `benchmark/srs_inventory_v1.md` was written for this project and describes no real organisation.
- No personal data, secrets or proprietary material were sent to any AI tool. The DevAI developer key is kept in `.env`, which is git-ignored; `.env.example` holds fake values only.
- No third-party code was copied. Rates are cited from DeepSeek's public pricing page (accessed 21 Oct 2026).
- No dependencies are installed at M1; the scripts use the Python standard library only.

## 6. Cost (required from M3; recorded early)

DevAI usage page during M1: _fill input/output tokens and requests_. Cash cost to the team: 0.00 SAR (course budget). Market cost at published rates: see `docs/08_cost_model.md`.

## 7. Individual ownership

> I can explain and defend every part of this submission that carries my name.

| Member | Areas | Signature | Date |
|---|---|---|---|
| Abderrahmane Benfatah | Charter, requirements, cost model, ADR-003, ADR-004 | | 2026-10-21 |
| Omar Ramadhan | Architecture options, coupling check, trade-off matrix, ADR-001, ADR-002, risk register | | 2026-10-21 |

---

## 8. Addendum — 10 November 2026: running the agents on DevAI

**Log owner for this entry:** _name_

### 8.1 Tools, models, mode and purpose

| Tool | Model | Mode | Purpose |
|---|---|---|---|
| Claude (Anthropic, claude.ai) | _confirm: model shown in claude.ai (M1 used Claude Opus 5.5)_ | Chat with file tools | Design of the app and its first version: rules, agents, orchestrator, store, API, web UI, tests |
| Claude Code (Anthropic) in VS Code | Claude Opus 5.5 (`claude-opus-5-5`) | Agent with per-action permission: file edits, shell commands, HTTP calls to the local DevAI | DevAI integration: finding DevAI's flow and agent formats, the DevAI client and CLI, tests, docs, real runs |
| DevAI Desktop 2.4.0 (course-approved), local | `anthropic/claude-haiku-4.5` (global DevAI setting) | Runtime: 8 agents `reqguard-<name>`, each in a webhook flow | Every AI call ReqGuard makes at runtime (Idea-to-SRS, Extractor, 4 specialists, Judge, Test-writer) |

### 8.2 What the AI produced

| Area | AI contribution | Human contribution |
|---|---|---|
| DevAI investigation (placeholder `{{trigger.payload.message}}`, agent folder format, tool fallback, agent API) | Primary (Claude Code read DevAI's installed files and ran test flows) | Set the investigation steps; reviewed the findings before any agent was created |
| `reqguard/llm/devai_flow.py`, `reqguard/devai.py` (setup / check / ping), `reqguard/env.py` | Primary | Specified the behaviour: polling, timeout, one retry, error text, least privilege, sandbox, model traceability |
| Tests `tests/test_devai_flow.py`, the score and grade-gate tests | Primary | Specified the cases (success, failed run, timeout, connection error; boundaries 0/1/4/5) |
| Score from rule findings only, grade gate, "AI advisory: N" in UI / report / CLI | Substantial (code) | Decided both rules and the thresholds |
| ADR-005, risks RK-12 and RK-13, README "Run with DevAI" | Substantial (text) | Decided the content; set the risk owners and thresholds |
| Prompt change in the four specialist prompts | Minor (inserted it) | Wrote the sentence (at most 15 findings, suggestions under 60 words, enrich rule findings instead of repeating them) |

### 8.3 What we verified

- **Tests:** `python -m pytest -q` passed with 104 tests at the DevAI-integration commit and 112 after the grade gate. The DevAI client is tested against a fake DevAI (`httpx.MockTransport`): success, failed run, timeout, connection refused.
- **Two real benchmark runs through DevAI** after the prompt change: score 89 in both, 28 rule findings identical in both (and identical to the runs before the change), 29 and 27 AI advisory findings, 0 JSON failures, 0 errors, 44 s and 39 s. After the grade gate, one more run gave score 89, grade "High risk".
- **Parallel-run timing check:** DevAI's own step timestamps show the four specialist agents starting within 0.1 s of each other (07:55:41.886–41.988 UTC). The stage took 54 s, against 178 s if they ran one after another.
- **Least privilege:** DevAI's code shows an empty tool list gives an agent DevAI's full default set (including shell and write), so each agent got the smallest set DevAI allows (read, list, to-do). DevAI rejects paths outside a flow's working folder, which is the empty sandbox. `python -m reqguard.devai check` confirms each deployed prompt matches `reqguard/prompts/*.md`.
- **One JSON failure observed** in 22 real calls before the prompt change: the Security agent dropped a closing quote (`"req_id":"REQ-08,`) in an 8 KB reply. The existing single retry recovered it.

### 8.4 Errors, rejections and changes

| # | What the AI produced or suggested | How we detected it | What we did |
|---|---|---|---|
| R-3 | **Rejected suggestion:** Claude Code offered to escape `{{` in the text sent to DevAI, because DevAI's template engine replaces `{{name.output}}` inside a prompt | Escaping changes the SRS text, and the verbatim grounding check (ADR-004) drops any requirement that is not found word for word | Text is sent unchanged; the client logs a warning when it contains `{{`; added to the README known limitations |
| R-4 | **Changed:** the judge's score subtracted penalties for both rule and AI findings | Two identical DevAI reviews of the benchmark gave the same 28 rule findings but scores 31 and 25 | Score from rule findings only (ADR-005). When that graded the benchmark "Needs work" at 89, we added the grade gate on high-severity rule findings |

### 8.5 Provenance, data and cost

- Commits for this work carry no AI co-author trailer: the trailers first added were removed from the history on 10 November 2026, and AI involvement is recorded in this log instead (section 4). The commits were **not** split into `raw(ai)` / `fix(human)` commits as section 4 describes; the decisions in 8.2 and 8.4 are the human part.
- Only synthetic data was sent to any model: `benchmark/srs_inventory_v1.md` and the idea "A mobile app for students to book study rooms". No secrets: DevAI runs locally with no key in ReqGuard.
- Claude Code read DevAI Desktop's installed files only to learn its formats. No DevAI code was copied into ReqGuard.
- Estimated tokens per 40-requirement benchmark run (ReqGuard's 4-characters-per-token estimate, 6 calls): about 11,200 input and 7,000 output. DevAI adds its own instructions, so real usage is higher. DevAI usage page: _fill_.

### 8.6 Individual ownership

> I can explain and defend every part of this submission that carries my name.

| Member | Areas | Signature | Date |
|---|---|---|---|
| Abderrahmane Benfatah | | | |
| Omar Ramadhan | | | |

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
- AI-generated files carry a `Co-authored-by:` trailer naming the tool.
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

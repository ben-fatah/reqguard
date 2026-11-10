# 03 — Human Correction Log (AI requirements draft)

**AI draft:** DevAI web chat, model shown as *DeepSeek-V4-Flash-Vision-Exp*, Prompt 1 (`docs/ai_drafts/README.md`). The unedited output is `docs/ai_drafts/devai_requirements_draft.md`, committed as `raw(ai): DevAI requirements draft` before any human change.

**Rule (Week 6):** every AI-drafted requirement is a proposal to validate, not a fact. Each item was checked against the charter (scope and non-goals), the persona, the brief's ceilings, and the six quality criteria: correctness, completeness, consistency, feasibility, testability and traceability.

## Persona, stories and use cases

| AI item | AI proposed (short) | Validated against | Decision | Final ID | Rationale |
|---|---|---|---|---|---|
| Persona | Priya, senior engineer at a 400-engineer fintech with PCI / SOC 2 obligations | Charter §2 stakeholder | **Revise** | P-1 Sara, P-2 Khalid | The compliance needs (PCI, SOC 2, defensible in audits) are invented stakeholder requirements we cannot validate; they would pull in encryption and retention requirements. Replaced with a small-team engineer, and added the missing Reviewer persona because the draft had two roles but only one persona. |
| US-01 | Upload an SRS text file | Charter §4 | **Revise** | US-01 | Kept the intent; added Given–When–Then with a failure path (wrong file type) because the draft stories had no acceptance criteria at all. |
| US-02 | Each requirement gets a stable ID | ADR-004 | **Revise** | US-02 | Added the line number, which the grounding check and the findings page need to point at exact text. |
| US-03 | Flag ambiguous or untestable requirements | ADR-002 | **Revise** | US-03 | Reframed around trust: each finding must show whether it came from a rule or from the AI. |
| US-04 | Suggest a rewrite for each flagged requirement | — | **Merge** | US-03, FR-05 | The rewrite is part of the AI advisory finding, not a separate story. |
| US-05 | Generate tests for **each** requirement | ADR-003, NFR-06 | **Revise** | US-05 | Tests are generated only after the reviewer decides the findings. Generating them before review writes tests for text the reviewer may change, wasting tokens and producing tests that no longer match. |
| US-06 | Reviewer accepts, edits or rejects each finding | FR-08 | **Revise** | US-04 | Added the mandatory reason and a boundary case (10 characters). |
| — | (missing) | Persona P-1, brief | **Added** | US-06, US-07 | Export of the reviewed report, and visible progress and token use per stage (the shared task record). |
| UC 1 | Review a submitted SRS, reviewer-only | Charter §3 | **Revise** | UC-01 | Rewritten end to end (upload to export). The draft had **no failure paths**; added LLM unavailable, invalid AI output and prompt injection in the SRS. |
| UC 1 A1 | Bulk decision: accept or reject many items at once | Charter NG-3, FR-09 | **Reject** | — | Bulk accept turns the human gate into a rubber stamp and defeats the per-item audit trail, the core of the human-approval requirement. |
| UC 1 A2 | Every requirement needs an accept decision even with no findings | FR-08 | **Reject** | — | Decisions are made on findings and tests, not on clean requirements. Forcing 40 clicks on clean items adds effort without adding evidence. |
| UC 2 | Generate and finalise acceptance tests | — | **Merge** | UC-01 steps 9–10 | Same actor and flow; kept as part of UC-01. |
| UC 2 A2 | Reviewer adds hand-written tests | Charter §6 ceilings | **Reject** | — | Out of v1 scope; it needs another endpoint and screen and is not needed to show the pipeline. |

## Functional requirements

| AI item | AI proposed (short) | Validated against | Decision | Final ID | Rationale |
|---|---|---|---|---|---|
| FR-01 | Accept .txt / .md upload | Charter NG-2 | **Revise** | FR-01 | Not testable as written: no size limit and no behaviour for a bad file. Added "≤ 200 KB" and "reject with a message, store nothing". |
| FR-02 | Extract each requirement with a stable ID | Week 6 §6 | **Revise** | FR-02 + **new FR-03** | The draft never guards against the AI inventing or paraphrasing requirements during extraction. Added exact text, line number and a deterministic verbatim grounding check (ADR-004). This is the most important correction. |
| FR-03 | AI flags ambiguous language with a reason | ADR-002, NFR-03 | **Revise** | FR-04 + FR-05 | Relying on AI judgment alone is not repeatable or testable. The draft's own open question suggested "a short lexicon of ambiguity terms"; **we adopted that suggestion** as the deterministic rule engine R1–R6, with the AI kept as a labelled advisory. |
| FR-04 | Flag untestable requirements | Rule R5 | **Merge** | FR-04 (R5), FR-05 | "Untestable" is covered by rule R5 (no measurable value) plus the AI advisory; a separate requirement duplicated FR-03. |
| FR-05 | Suggested rewrite for flagged requirements | — | **Keep** (reworded) | FR-05 | Kept; added that AI findings are stored separately and labelled *AI advisory*. |
| FR-06 | Tests for each requirement | ADR-003 | **Revise** | FR-06 | Only for requirements whose findings are decided (see US-05). |
| FR-07, FR-08 | Accept; edit | — | **Merge** | FR-08 | One decision requirement with three outcomes is easier to trace and test. |
| FR-09 | Reject "requiring an optional but tracked reason" | Consistency criterion | **Revise** | FR-08 | **Self-contradictory** (required and optional at once). Resolved as mandatory, 10–500 characters, so it is testable at the boundary. |
| FR-10 | Per-item status and a filterable queue | Charter §6 ceilings | **Revise** | FR-10 | Replaced with the run's task record (stage, times, tokens per call). Item status is derived from the latest decision, which keeps a single writer per table (`07_coupling_report.md`). Filter UI dropped to stay within the screen ceiling. |
| FR-11 | Immutable audit log with before/after | — | **Keep** | FR-09 | Matches our need exactly. |
| FR-12 | Export Markdown **and JSON** | Charter NG-7 | **Revise** | FR-11 | Markdown only; added "blocked while items are undecided". JSON export has no persona need. |
| — | (missing) | Brief, NFRs | **Added** | FR-07, FR-12, FR-13 | Schema validation with one retry; role-based permissions as a functional rule (the draft only had them inside an NFR); the benchmark command for M3. |

## Non-functional requirements

| AI item | AI proposed (short) | Validated against | Decision | Final ID | Rationale |
|---|---|---|---|---|---|
| NFR-01 | Up to **500 requirements in 60 seconds** | Cost model, persona | **Revise** | NFR-01 | No evidence for the number, 500 requirements is 10× the persona's documents, and meeting it forces per-requirement fan-out, which breaks our cost budget (ADR-003). Rewritten as a quality-attribute scenario: 40 requirements, p95 ≤ 120 s over 10 runs. |
| NFR-02 | Keyboard-only, WCAG 2.2 AA; "decision controls must be reachable without reading-decisions-loading secondary steps" | Testability | **Reject** (deferred) | — | The last clause is **garbled and has no meaning** (AI error E-1). Accessibility is a valid goal, but we have no way to verify WCAG 2.2 AA in this course; recorded as a known limitation rather than a requirement we cannot test. |
| NFR-03 | RBAC, authentication, **encryption at rest and in transit** | Charter NG-1 | **Revise** | NFR-04 | Kept access control with a measurable target (12/12 cases return 401/403). Dropped encryption at rest: single host, synthetic data only, and no way to test it within scope. |
| NFR-04 | **99.9% availability during business hours**; recoverable review | Feasibility | **Revise** | NFR-07 | 99.9% cannot be measured in a seven-week course project on one host. Replaced with a degraded-mode scenario we can test: LLM failure keeps rule findings and shows the error within 35 s. |
| NFR-05 | Audit trail **retained for at least one year** | Feasibility | **Merge / Reject retention** | FR-09 | Immutability is merged into FR-09. One-year retention cannot be verified within the project and has no stakeholder source once the compliance persona was removed. |
| NFR-06 | Markdown + JSON export **and batch re-import** | Charter NG-7 | **Reject** | — | Re-import adds endpoints and an edit-round-trip we do not need. |
| — | (missing) | Brief M2/M3, Week 7 §12 | **Added** | NFR-02, NFR-03, NFR-05, NFR-06, NFR-08 | The draft had **no** grounding/accuracy target, no repeatability target, no prompt-injection scenario, no cost target and no coupling target, even though the system's core risk is AI output. All five were added as measurable scenarios. |

## Summary

| Decision | Count |
|---|---|
| Kept (possibly reworded) | 2 (FR-05, FR-11) |
| Revised | 17 |
| Merged | 5 (US-04, UC 2, FR-04, FR-07 + FR-08, NFR-05 immutability) |
| Rejected | 5 (bulk decision, forced accept on clean items, manual tests, WCAG clause, re-import) |
| Added by humans | 13 (P-2, US-06, US-07, failure paths, FR-03, FR-07, FR-12, FR-13, NFR-02, NFR-03, NFR-05, NFR-06, NFR-08) |

## Patterns in the AI draft

1. **No guard against its own fabrication.** The draft trusts AI extraction completely; nothing checks that an extracted requirement exists in the uploaded file.
2. **Invented stakeholder needs.** The persona brought in regulated-industry requirements (PCI, SOC 2, 1-year retention, encryption) that nobody asked for.
3. **Unmeasured or unmeasurable NFRs.** 500 requirements / 60 s and 99.9% availability came with no basis, and none were written as quality-attribute scenarios.
4. **Missing failure paths.** No use case covered LLM failure, invalid output or malicious input.
5. **Internal contradiction and garbled text.** "Requiring an optional reason"; an NFR clause that does not parse.
6. **Useful ideas we kept:** the ambiguity-term lexicon (now rules R1–R6), keeping .txt/.md only for v1, and the immutable before/after audit log.

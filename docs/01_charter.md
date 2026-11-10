# 01 — Project Charter: ReqGuard

**Course:** SWE 485 Advanced Software Engineering with AI — Term 1, 1448 AH (2026–2027)
**Milestone:** M1 Requirements and Architecture — due 21 October 2026
**Project type:** Multi-agent system (fixed-order orchestration with a human approval gate)
**Declared implementation language:** **Python 3.12** (backend, agents, rule engine, tests). Changing it after M1 forfeits the Week 10 mutation-gauntlet marks.
**Approved AI tool:** DEVAI (see `AI_USE_DISCLOSURE.md` for every AI tool and model used)

## 1. Team

| Member | KSU ID | Primary ownership (defended in M4) |
|---|---|---|
| Abderrahmane Benfatah | 444106928 | Orchestrator, Extractor agent, grounding check, cost model, DevAI LLM client |
| Omar Ramadhan | 444106902 | Rule engine (R1–R6), Quality agent, Test-writer agent, review UI and access control |

Both members review each other's modules; review records are kept in `REVIEW.md` from M2 onwards.

## 2. Stakeholder problem

Small software teams and student project teams write Software Requirements Specifications (SRS) by hand, increasingly with AI help. Ambiguous or untestable requirements ("the system should be fast", "users can manage their data, etc.") pass review unnoticed and surface later as defects, disputes and untestable acceptance criteria. Manual review of a 40-requirement SRS against quality criteria (correctness, completeness, consistency, feasibility, testability, traceability) takes a reviewer one to two hours, and general-purpose chatbots are unreliable reviewers: they paraphrase, invent requirements that are not in the document, and give different answers on each run.

**Simulated stakeholder:** Sara, a junior engineer and team lead at a small Riyadh software house (persona in `02_requirements.md`), and Khalid, the QA lead who signs off requirements before testing starts.

## 3. Product vision

ReqGuard is a requirements review crew. An engineer uploads an SRS text file. Three agents with distinct roles run in a fixed order:

1. **Extractor agent** splits the document into requirements with IDs. A deterministic **grounding check** discards anything that does not appear verbatim in the source.
2. **Quality agent** flags ambiguous or untestable requirements. A deterministic **rule engine** (rules R1–R6) is the source of truth; the LLM adds advisory findings and proposed rewrites, clearly labelled as AI-generated.
3. **Test-writer agent** drafts Given–When–Then acceptance tests for each requirement the reviewer has accepted.

A **human reviewer** accepts, edits or rejects every finding and every generated test before anything is exported. Every decision is logged, and the exported report links requirement → finding → test.

## 4. Scope (in)

- Upload of plain-text SRS files (`.txt`, `.md`), English only, up to 200 KB.
- The three-agent pipeline above, with a shared task record (run status, per-stage outputs, token usage).
- A deterministic rule engine for six ambiguity and testability rules (R1–R6).
- Human review of findings and generated tests, with mandatory reasons for edits and rejections and a full audit trail.
- Markdown export of the reviewed report with traceability links.
- Two roles: **Engineer** and **Reviewer**.
- A labelled benchmark of synthetic SRS documents with planted defects, used to measure precision and recall (supports M3).

## 5. Explicit non-goals

| ID | Non-goal | Why it is out |
|---|---|---|
| NG-1 | No real customer, company or university SRS documents; only public or synthetic data | Brief's data rule; avoids sending private material to an AI tool |
| NG-2 | No PDF or DOCX parsing in v1 | Parsing quality would dominate the project; plain text is enough to show the pipeline |
| NG-3 | No automatic acceptance of any AI finding or test; a human decides every item | Human approval is a core requirement, not an option |
| NG-4 | No validation of whether a requirement reflects a real stakeholder need | ReqGuard checks quality, not authority; that stays with humans (Week 6 rule) |
| NG-5 | No generation of application code or executable test scripts; tests are Given–When–Then text | Keeps scope within limits |
| NG-6 | No Arabic or multilingual requirements in v1 | Rule word lists are English; avoids untestable claims |
| NG-7 | No Jira, GitHub or other tool integrations; no editing of the original document | Export is a Markdown report only |
| NG-8 | No model fine-tuning, no RAG vector store, no Kubernetes or multi-region deployment | Brief's scope ceilings; not needed for the problem |

## 6. Scope ceilings (brief maximums) and our plan

| Item | Brief maximum | ReqGuard plan |
|---|---|---|
| Screens / views | 6 | 5 (Login, Documents & runs, Findings review, Tests review, Report) |
| API endpoints | 10 | 9 |
| Tables | 8 | 7 |
| User roles | 2 | 2 (Engineer, Reviewer) |
| Deployment targets | 1 | 1 (single Docker container) |

## 7. Technical elements (brief requires at least four)

Frontend · Backend · Persistence · API integration (DevAI LLM API) · Access control · Automated tests · Security scanning · AI / agentic functionality. Eight of the listed elements; retrieval/RAG is deliberately not included (NG-8).

## 8. Success criteria (measured at M3 and M4)

- Rule engine precision ≥ 0.90 and recall ≥ 0.80 on the labelled benchmark (NFR-02).
- Zero fabricated requirements reach the reviewer on the benchmark (FR-03, NFR-02).
- Identical rule findings across 5 repeated runs; AI flag agreement ≥ 0.80 (NFR-03).
- A 40-requirement review costs ≤ 30,000 tokens and ≤ USD 0.02 at published peak rates (NFR-06).

# Raw AI drafts (unedited)

These files are the exact DevAI outputs used as the starting point for M1. They are committed **before** any human edits, in a commit whose message starts with `raw(ai):`. Human changes are recorded in `docs/03_correction_log.md` and `docs/05_architecture.md` §5.

| File | Prompt | Tool / model | Date | Read by |
|---|---|---|---|---|
| `devai_requirements_draft.md` | Prompt 1 (below) | DevAI chat, DeepSeek-V4-Flash-Vision-Exp | 2026-10-21 | _name_ |
| `devai_architecture_draft.md` | Prompt 2 (below) | DevAI chat, same | 2026-10-21 | _name_ |

`extractor_v0.md` is not a DevAI output: it is the v0 Extractor prompt the team pasted into DevAI for the M1 token measurement (`docs/08_cost_model.md`). It was replaced by `reqguard/prompts/extractor.md` and is kept here as M1 evidence.

## Prompt 1
```
You are a requirements engineer. Draft requirements for "ReqGuard", a system where a software engineer uploads a software requirements specification (SRS) text file; AI agents extract each requirement with an ID, flag ambiguous or untestable requirements, suggest a rewrite, and generate Given-When-Then acceptance tests; a human reviewer accepts, edits or rejects each finding. Two roles: engineer and reviewer. Give: 1 persona, 6 user stories, 2 use cases, 12 functional requirements (FR-01..), 6 non-functional requirements (NFR-01..).
```

## Prompt 2
```
Propose an architecture for ReqGuard (the system above). Use Python. Describe the components, how the AI agents hand off work, where data is stored, and give a C4 Container diagram in Mermaid.
```

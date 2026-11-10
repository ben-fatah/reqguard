# ADR-005: The quality score is computed from rule findings only

- **Status:** Accepted
- **Date:** 2026-11-10
- **Deciders:** Abderrahmane Benfatah, Omar Ramadhan
- **Related requirements:** FR-04, FR-05, FR-11, NFR-03
- **Related decisions:** ADR-002 (rules are the source of truth)
- **Trade-off matrix rows:** TM-2, TM-3

## Context and problem

The Judge gives every run a quality score (0–100) and a grade. Until now the score subtracted a penalty for every finding, both rule findings and AI advisory findings. Since the agents moved to DevAI flows, temperature is ignored and the model is a global DevAI setting (risk RK-13). Two reviews of the same benchmark SRS then gave the same 28 rule findings but 50 and 55 AI findings, and the score moved from 31 to 25. The score is the number a reader looks at first. If it changes when the document has not changed, it cannot be used to compare versions of an SRS or to show progress after fixes, and it contradicts NFR-03.

## Considered options

- **Option 1 — Score from all findings (rule + AI):** keep the current formula.
- **Option 2 — Score from rule findings only:** the same formula, applied only to findings with `source == "rule"`. AI advisory findings are still shown, ranked and counted, and the UI and report show their count separately ("AI advisory: N, not scored").

## Decision

Chose **Option 2**. Rule findings are deterministic (ADR-002), so the score is identical for the same document on every run and with every model, which meets NFR-03 by construction. It also follows ADR-002: AI output is advice for the reviewer, not a verdict. An AI finding can still be important, and the reviewer still sees, ranks and decides every one of them.

## Consequences

- **Positive:** the same SRS always gets the same score and grade, whichever model DevAI uses; a score change now means the document changed; the score is testable with an exact oracle (`test_ai_findings_do_not_change_the_score`); a slow or failing AI agent can no longer move the score.
- **Accepted downside:** the score ignores problems that only the AI found, such as a contradiction between two requirements or a missing security requirement that no word list catches. A document can score well and still have serious AI advisory findings. Mitigation: the AI advisory count is shown next to the score in the UI, the report and the CLI, every AI finding still needs a reviewer decision before export (FR-11), and the Judge's summary names the most important problems, whatever their source.
- **Rejected:** Option 1, because the score would vary between identical runs (31 vs 25 in our measurement), and the score could change because of a model change in DevAI that ReqGuard cannot control.

## Y-statement

In the context of the Judge's quality score, facing AI findings that vary between identical runs and a model that DevAI sets globally, we decided to compute the score from deterministic rule findings only and show AI advisory findings as a separate count, to achieve a repeatable score that matches NFR-03, accepting that the score ignores problems only the AI found.

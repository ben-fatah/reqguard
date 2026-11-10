# ADR-004: Verbatim grounding check on extracted requirements

- **Status:** Accepted
- **Date:** 2026-10-21
- **Deciders:** Abderrahmane Benfatah, Omar Ramadhan
- **Related requirements:** FR-02, FR-03, NFR-02, NFR-05
- **Trade-off matrix rows:** TM-2

## Context and problem

The Extractor agent can paraphrase, merge or invent requirements. A fabricated requirement looks exactly like a real one and passes every downstream check (Week 6 §6), so anything the reviewer sees must provably come from the uploaded document.

## Considered options

- **Option 1 — Trust the Extractor's output** and ask the reviewer to spot inventions.
- **Option 2 — Verbatim grounding check:** keep a candidate only if its text, after whitespace normalisation, appears exactly in the source; list dropped candidates.
- **Option 3 — Similarity matching:** keep candidates whose embedding similarity to some source sentence exceeds a threshold.

## Decision

Chose **Option 2**: a deterministic substring check gives a hard guarantee (0 invented requirements reach the reviewer, NFR-02) and is trivially testable.

## Consequences

- **Positive:** invented or paraphrased requirements cannot reach review; the drop list itself measures Extractor quality (risk RK-08).
- **Accepted downside:** legitimate requirements that the model copies with small changes (a fixed typo, merged lines, smart quotes) are dropped and must be added back by the reviewer. Requirements that span two lines in the source are only kept because whitespace is normalised; a requirement written as a bulleted list split across lines will be dropped.
- **Rejected:** Option 1, because the reviewer cannot reliably spot fluent fabrications. Option 3, because it lets close paraphrases through (exactly the failure we are preventing) and adds an embedding model and threshold tuning.

## Y-statement

In the context of AI extraction of requirements, facing fabricated or paraphrased output, we decided to keep only candidates found verbatim in the source to guarantee zero invented requirements, accepting that slightly altered real requirements are dropped and must be restored by the reviewer.

# ADR-002: Deterministic rules as source of truth; LLM findings advisory only

- **Status:** Accepted
- **Date:** 2026-10-21
- **Deciders:** Abderrahmane Benfatah, Omar Ramadhan
- **Related requirements:** FR-04, FR-05, FR-13, NFR-02, NFR-03, NFR-05, NFR-07
- **Trade-off matrix rows:** TM-2, TM-3, TM-5, TM-6

## Context and problem

The Quality stage decides which requirements are ambiguous or untestable. An LLM-only reviewer gives different answers on repeated runs, can be steered by text inside the SRS (prompt injection), and cannot be checked against an exact oracle. The course grades a live instructor-introduced mutation (M2), repeated-run variation (M3) and a partial oracle (M3).

## Considered options

- **Option 1 — LLM-only review:** the Quality agent alone produces all findings.
- **Option 2 — Rules-first hybrid:** a deterministic Python rule engine (R1–R6) produces findings that are the source of truth; the LLM adds separately labelled *AI advisory* findings and suggested rewrites.
- **Option 3 — Rules only:** no LLM in the Quality stage.

## Decision

Chose **Option 2**. Rule findings are deterministic, so NFR-03 can require 5/5 identical results. They are unaffected by injected text (NFR-05) and survive an LLM outage (NFR-07). They also have an exact oracle on the labelled benchmark (NFR-02). The LLM still catches context-dependent problems that word lists cannot, such as a requirement that contradicts another.

## Consequences

- **Positive:** the rule engine is plain Python, ideal for mutation testing; every finding carries its source so the reviewer knows how far to trust it; an LLM outage degrades the review instead of stopping it.
- **Accepted downside:** word-list rules produce false positives — "fast" in "fast-moving goods category" raises R1 — and miss ambiguity that uses no listed word. The word lists must be maintained by hand in one versioned file. The reviewer sees two kinds of findings, which adds some review effort. Mitigation: rules flag *potential* ambiguity and never auto-reject; precision is measured on the benchmark (risk RK-02).
- **Rejected:** Option 1, because it has no exact oracle, fails NFR-03's repeatability target by design, and can be steered by injected text. Option 3, because rules alone cannot propose rewrites or detect contradictions, which removes most of the value for persona P-1.

## Y-statement

In the context of the Quality stage, facing non-repeatable and injectable LLM judgements, we decided to make a deterministic rule engine the source of truth with LLM findings as labelled advisories, to achieve repeatability, injection resistance and a testable oracle, accepting word-list false positives and hand-maintained rule lists.

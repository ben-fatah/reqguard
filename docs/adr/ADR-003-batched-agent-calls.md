# ADR-003: Batched agent calls (one per document chunk) instead of per-requirement fan-out

- **Status:** Accepted
- **Date:** 2026-10-21
- **Deciders:** Abderrahmane Benfatah, Omar Ramadhan
- **Related requirements:** NFR-01, NFR-06, NFR-03, FR-02, FR-05, FR-06, FR-07, FR-10
- **Trade-off matrix rows:** TM-1, TM-3, TM-4

## Context and problem

Each agent can be called once with all requirements, or once per requirement. Cost and energy are quality attributes (Week 7 §12), and NFR-06 limits a 40-requirement run to 30,000 tokens and USD 0.02.

## Considered options

- **Option 1 — Batched:** one call per agent per chunk of at most 40 requirements (3 calls per typical run).
- **Option 2 — Per-requirement fan-out:** one call per requirement for Quality and Test-writer (81 calls per typical run).

## Decision

Chose **Option 1**. The cost model at published DeepSeek Flash peak rates gives 14,894 tokens and $0.0104 per run for batching, against 71,720 tokens and $0.0284 for fan-out (`08_cost_model.md`). Only batching meets NFR-06. Fewer sampled outputs also improve repeatability (TM-3).

## Consequences

- **Positive:** 4.8× fewer tokens; the Quality agent sees the whole requirement list and can spot contradictions; fewer calls to log and validate.
- **Accepted downside:**
  - **Latency:** three sequential calls generating about 6,000 output tokens are slower than parallel fan-out, so NFR-01 has less margin (TM-1, risk RK-05).
  - **Blast radius:** one malformed JSON response invalidates a whole stage, not one requirement, so the retry re-sends the full batch.
  - **Document size:** documents over 40 requirements need chunking logic.
- **Rejected:** fan-out, because it repeats the system prompt 80 times. Even with prompt-cache pricing, the 71,720 tokens exceed the 30,000-token budget, and the 27× more sampled outputs reduce consistency.
- **Revisit trigger:** if M2 timing shows p95 > 120 s for 40 requirements, a new ADR will supersede this one with *parallel batched chunks of 10*, keeping most of the token saving.

## Y-statement

In the context of agent calls on a 40-requirement SRS, facing a token and cost budget, we decided to batch each agent's work into one call per 40-requirement chunk to achieve a run under 15,000 tokens and $0.011, accepting slower sequential runs and whole-stage retries.

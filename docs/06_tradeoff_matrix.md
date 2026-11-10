# 06 — Trade-off Matrix: Option A vs Option B

Each row is one of our quality-attribute scenarios from `02_requirements.md` §6. Every score cites evidence: a computed number (`tools/cost_model.py`, `tools/coupling_check.py`) or a structural property visible in the C4 diagrams. Where the number can only be measured once code exists, the row says so and names the milestone; no invented latency figures are used.

**Scale:** 3 = meets the scenario with margin · 2 = meets it with risk · 1 = fails or is at high risk of failing.
**Weights:** H = 3, M = 2.

| Row | Quality attribute (QA scenario) | Weight | Option A — modular monolith, batched | Option B — distributed, fan-out | Evidence / justification |
|---|---|:-:|:-:|:-:|---|
| TM-1 | Performance — NFR-01: p95 ≤ 120 s to *Awaiting review* | H | 2 | 3 | A makes 3 sequential calls producing ~6,100 output tokens per run (cost model). Output generation dominates latency, so A has less margin than B, whose 80 per-requirement calls run in parallel on N workers. Actual throughput of the DevAI endpoint is **not yet measured**; it is timed in M2 (risk RK-05). |
| TM-2 | Correctness — NFR-02: rule precision ≥ 0.90, recall ≥ 0.80; 0 invented requirements | H | 3 | 2 | Both use the same deterministic rule engine and grounding check. B's Quality agent sees one requirement at a time and loses document context (it cannot notice that two requirements contradict each other); A's batched call sees the whole list. |
| TM-3 | Consistency — NFR-03: identical rule findings 5/5; AI Jaccard ≥ 0.80 | M | 3 | 2 | Rule findings are deterministic in both. A makes 3 LLM calls per run, B makes 81 (cost model), so B has 27× more independently sampled outputs that can vary between runs. |
| TM-4 | Cost — NFR-06: ≤ 30,000 tokens and ≤ USD 0.02 per 40-requirement run | H | 3 | 1 | Cost model at published DeepSeek Flash peak rates: **A = 14,894 tokens, USD 0.0104** (meets both). **B = 71,720 tokens, USD 0.0284** (fails both). Even with prompt-cache hits B costs USD 0.0120 but still uses 71,720 tokens, 2.4× the token budget. |
| TM-5 | Security — NFR-04 access control, NFR-05 prompt injection | H | 3 | 2 | A has one authorisation boundary (one FastAPI app). B adds a second service boundary (UI → API) and a Redis queue that has no authentication by default, so there are more places to get access control wrong. Injection defence (rules independent of the LLM, schema validation, human gates) is identical. |
| TM-6 | Availability — NFR-07: LLM failure visible ≤ 35 s, 0 rule findings lost | M | 2 | 3 | Both run rules before the AI stage, so rule findings survive an LLM failure. B isolates failures to one job and retries one requirement; A retries a whole stage, and a process crash loses the in-flight stage. |
| TM-7 | Maintainability and operational burden — NFR-08: 0 cycles, 0 forbidden edges | M | 3 | 1 | Coupling check: **A PASS (0 violations), B FAIL (7 violations)** — agents write tables directly and three tables have multiple writers. Operational burden: A = 1 container; B = 5 containers including Redis and PostgreSQL. |

## Weighted totals

| | Option A | Option B |
|---|---|---|
| Weighted score (max 54) | **49** | 36 |
| Rows where it wins | TM-2, TM-3, TM-4, TM-5, TM-7 | TM-1, TM-6 |

**Decision:** Option A (ADR-001). The rows A loses — TM-1 latency and TM-6 failure isolation — are the **accepted downsides** recorded in ADR-001 and ADR-003, and both are tracked as risks (RK-05, RK-06) with measurable alert thresholds.

## How to use this matrix in the M1 review

If the examiner picks a quality-attribute scenario, find its row above:

- **NFR-06 cost → TM-4.** Show the arithmetic in `08_cost_model.md`: B repeats the system prompt in all 80 per-requirement calls. Even prompt caching does not fix the token count, which also drives latency and context size.
- **NFR-01 latency → TM-1.** We accepted a slower run in exchange for cost, consistency and coupling. Batching is the cause; chunking at 40 requirements bounds the worst case; the M2 timing decides whether we need parallel chunks (ADR-003, superseding ADR if so).
- **NFR-07 availability → TM-6.** Rules run before the AI stage, so an LLM outage never loses deterministic findings. Losing the in-flight stage on a crash is the accepted cost of a single process.

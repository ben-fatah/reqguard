# 10 — M1 Review Preparation (both members must be able to answer)

## 30-second pitch
ReqGuard reviews software requirements documents with three agents in a fixed order — Extractor, Quality, Test-writer — and two human approval gates. The design principle is **deterministic first, AI advisory**: a verbatim grounding check guarantees no invented requirements, a Python rule engine is the source of truth for ambiguity, and the LLM adds labelled suggestions. Everything an agent produces is schema-validated and decided by a human.

## Likely questions and our answers

**"Here is a quality-attribute scenario — which matrix row, and defend the decision."**
Find the NFR in `02_requirements.md` §6, then its TM row in `06_tradeoff_matrix.md`. Example: **NFR-06 cost → TM-4** — A costs 14,894 tokens / $0.0104 per run, B costs 71,720 / $0.0284. B fails both limits. Even with prompt caching B costs $0.0120 but still uses 71,720 tokens.

**"Why did you reject Option B?"**
It breaks the cost budget (4.8× tokens), fails the coupling check with 7 violations (agents write tables directly; three tables have two writers), and needs five containers including an unauthenticated-by-default Redis. Its real strengths — parallel latency and job-level fault isolation — matter only at a scale we don't have.

**"What downside did you accept?"**
- ADR-001: a crash loses the in-flight stage; no horizontal scaling (RK-06).
- ADR-003: slower sequential runs, so NFR-01 has less margin; one bad JSON response retries the whole stage (RK-05, RK-01).
- ADR-002: word-list false positives (RK-02).
- ADR-004: slightly altered real requirements get dropped (RK-08).

**"Top three risks?"**
- RK-04 prompt injection: threshold is any fixture changing rule findings or auto-accepting an item. Owner Omar.
- RK-01 schema failures: threshold > 5% of calls over 20 runs. Owner Thabit.
- RK-03 non-determinism and model drift: threshold Jaccard < 0.80. Owner Omar.

**"Show the cost arithmetic."**
Option A before retries: input 7,500 × $0.30/M = $0.00225; output 6,040 × $1.20/M = $0.007248; total $0.009498; × 1.10 retries = **$0.0104**. Rates are from DeepSeek's pricing page, Flash peak. The peak window is 09:00–13:00 Riyadh, which is when we work.

**"Show the coupling evidence."**
Run `python tools/coupling_check.py architecture/option_a.json architecture/option_b.json architecture/devai_draft.json`. Result: A PASS, B FAIL (7), and the DevAI draft result.

**"What residual risk can the coupling detector not see?"**
Prompt and schema coupling. Agents depend on each other's JSON field names and on prompt wording, with no import edge. Renaming a field, or an Extractor prompt that starts "fixing" text, passes the check but silently breaks grounding. We mitigate it with one shared Pydantic schema, contract tests on golden outputs, versioned prompts, and RK-08's drop-rate alert.

**"Why is this multi-agent and not just a workflow?"**
The three agents have distinct roles, separate prompts and permitted tools, typed inputs and outputs, explicit handoffs and stopping conditions, with a shared task record (the run). We chose fixed orchestration on purpose: the next agent is never chosen by a model, which keeps the system testable and predictable.

**"How did you use AI, and where did you overrule it?"**
Point to `03_correction_log.md` (requirements we rejected or rewrote) and `05_architecture.md` §5 (the DevAI architecture draft and why its coupling was rejected).

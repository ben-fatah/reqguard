# 08 — Cost Model

All arithmetic is in `tools/cost_model.py` and can be re-run live with `python tools/cost_model.py`. The raw output is saved in `reports/cost_model_run.txt`.

## 1. Published rates (re-verified 21 Oct 2026)

Source: DeepSeek *Models & Pricing* — https://api-docs.deepseek.com/quick_start/pricing/

| Model (API name) | Input, cache hit | Input, cache miss | Output | Notes |
|---|---|---|---|---|
| `deepseek-flash` (DeepSeek-V4.1-Flash-1017), **peak** | $0.006 / 1M | $0.30 / 1M | $1.20 / 1M | Base case |
| `deepseek-flash`, **off-peak** | $0.003 / 1M | $0.15 / 1M | $0.60 / 1M | Half price |
| `deepseek-v4-pro`, peak | $0.044 / 1M | $1.32 / 1M | $3.96 / 1M | Sensitivity only |

- The model selected in DevAI is *DeepSeek-V4-Flash-Vision-Exp*. DeepSeek's pricing page states this legacy name is retired, served by V4.1-Flash and billed at the Flash price, so the Flash rates apply.
- **Peak hours:** 01:00–04:00 and 06:00–10:00 UTC, Monday–Friday, which is **04:00–07:00 and 09:00–13:00 Riyadh time**. Our working sessions fall mostly in peak, so peak is the conservative base case.
- **Currency:** 1 USD = 3.75 SAR (fixed peg).
- **What we actually pay:** DevAI shows our course team's budget as unlimited and our cost as 0.00 SAR. The model below prices usage at **published market rates**, which is what the same system would cost outside the course.

## 2. Usage assumptions (stated)

| Assumption | Value | Basis |
|---|---|---|
| Requirements per SRS | 40 | Persona P-1 writes 30–60; benchmark SRS has 40 |
| Tokens per requirement | 40 | Benchmark SRS sentences are 8–25 words, about 10–35 tokens; rounded up |
| Document overhead | 400 tokens | Headings and intro text in the benchmark SRS |
| System prompts | Extractor 600, Quality 700, Test-writer 600 | Prompt drafts in `prompts/` plus JSON schema |
| Share of requirements flagged by Quality | 40% | Benchmark: 19 of 40 requirements have planted defects (48%); 40% assumes some are left to rules alone |
| Output tokens | Extractor 45 / req; Quality 90 / flag (A) or 60 / req (B); Test-writer 70 / test | JSON field overhead plus text |
| Retry rate | 10% of calls retried once | FR-07 allows one retry |
| Volume | Project: 1,000 runs (development + M3 repeated-run evaluation). Pilot: 10 engineers × 3 SRS × 3 runs = 90 runs/month. Stress: 100 engineers × 3 × 3 = 900 runs/month | |

## 3. Measured tokens

| Measurement | Input tokens | Output tokens | Source |
|---|---|---|---|
| DevAI requirements draft (Prompt 1) | _fill from Usage page_ | _fill_ | DevAI Usage page, before/after difference |
| DevAI architecture draft (Prompt 2) | _fill_ | _fill_ | same |
| **Extractor v0 on `srs_inventory_v1.md`** | _fill_ | _fill_ | same, with `prompts/extractor_v0.md` |

When the Extractor measurement is available, the model is **calibrated**: `python tools/cost_model.py --measured-extractor-in <in> --measured-extractor-out <out>` scales every stage by the measured/estimated ratio. The calibrated output replaces §4 below.

## 4. Results per run (40 requirements, peak rates, 10% retries)

| Option | LLM calls | Input tokens | Output tokens | Total tokens | Cost (USD) | Cost (SAR) | Meets NFR-06 (≤ 30,000 tokens, ≤ $0.02)? |
|---|---|---|---|---|---|---|---|
| A — batched | 3 | 8,250 | 6,644 | **14,894** | **0.0104** | 0.0392 | **Yes** |
| B — fan-out | 81 | 64,020 | 7,700 | **71,720** | **0.0284** | 0.1067 | **No** (both limits) |

Worked check for Option A, before retries: input 2,600 + 2,700 + 2,200 = 7,500; output 1,800 + 1,440 + 2,800 = 6,040.
Cost = (7,500 × 0.30 + 6,040 × 1.20) / 1,000,000 = (2,250 + 7,248) / 1,000,000 = $0.009498.
With 10% retries: × 1.10 = **$0.0104**.

## 5. Sensitivity

| Scenario | A tokens | A cost | B tokens | B cost | B / A |
|---|---|---|---|---|---|
| Base: peak, 10% retries | 14,894 | $0.0104 | 71,720 | $0.0284 | 2.72 |
| Off-peak hours | 14,894 | $0.0052 | 71,720 | $0.0142 | 2.72 |
| B with prompt-cache hits on repeated system prompts | 14,894 | $0.0104 | 71,720 | $0.0120 | 1.15 |
| Retries 30% | 17,602 | $0.0123 | 84,760 | $0.0336 | 2.72 |
| Document × 2 (80 requirements) | 27,258 | $0.0201 | 142,340 | $0.0566 | 2.81 |
| Switch to V4-Pro (peak) | 14,894 | $0.0372 | 71,720 | $0.1150 | 3.09 |

| Volume (base rates) | Option A | Option B |
|---|---|---|
| Project lifetime, 1,000 runs | $10.45 (39.18 SAR) | $28.45 (106.67 SAR) |
| Pilot, 90 runs / month | $0.94 (3.53 SAR) | $2.56 (9.60 SAR) |
| Stress, 900 runs / month | $9.40 (35.26 SAR) | $25.60 (96.01 SAR) |

## 6. Interpretation

1. **Output tokens dominate A's cost.** Output is 4× the input price, and in Option A output is 45% of tokens but about 76% of cost ($0.007248 of $0.009498 before retries). The cheapest lever is shorter outputs (compact JSON, no explanations for unflagged requirements), not cheaper input.
2. **B's problem is repeated input.** B sends the 700- and 600-token system prompts 40 times each. Prompt caching cuts B's price to 1.15× A, but **not its token count** (71,720). Tokens also drive latency and context limits, so caching does not rescue B on NFR-06.
3. **Model choice is the largest lever.** Switching to V4-Pro multiplies A's cost by 3.6× ($0.0372) and breaks NFR-06, so Flash is right-sized for extraction and checking (Week 7: right-size the model).
4. **The budget breaks first on document size.** An 80-requirement SRS costs A $0.0201, just over the $0.02 limit, while staying under 30,000 tokens. NFR-06 is stated for 40 requirements; larger documents are chunked at 40 requirements (ADR-003), so the cost is linear and predictable.
5. **Scheduling matters.** Running the M3 repeated-run evaluation off-peak (after 13:00 Riyadh time) halves its cost.
6. **One way to reduce cost further:** skip the Quality call for requirements with no rule finding and fewer than 8 words. This trades recall for cost and will only be evaluated against the M3 benchmark.

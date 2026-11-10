"""Cost model for ReqGuard (evidence for NFR-06, trade-off row TM-4, ADR-003).

All arithmetic is in this file so it can be re-run and checked live.

Rates: DeepSeek "deepseek-flash" (DeepSeek-V4.1-Flash-1017), USD per 1M tokens,
from https://api-docs.deepseek.com/quick_start/pricing/ (re-verified 2026-10-21).
DeepSeek states that the legacy names deepseek-v4-flash and
deepseek-v4-flash-vision-exp (the model selected in DevAI) are served by
V4.1-Flash and billed at the Flash price.
Peak hours: 01:00-04:00 and 06:00-10:00 UTC, Mon-Fri
(= 04:00-07:00 and 09:00-13:00 Riyadh time). Off-peak is half price.

Usage:
    python tools/cost_model.py
    python tools/cost_model.py --measured-extractor-in 2410 --measured-extractor-out 1650
The --measured-* flags replace the estimated Extractor stage with the token
counts read from the DevAI usage page, and scale the other stages by the same
ratio (measured / estimated).
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass

USD_TO_SAR = 3.75  # SAR is pegged to USD

RATES = {  # USD per 1M tokens
    "flash_peak": {"in_miss": 0.30, "in_hit": 0.006, "out": 1.20},
    "flash_offpeak": {"in_miss": 0.15, "in_hit": 0.003, "out": 0.60},
    "pro_peak": {"in_miss": 1.32, "in_hit": 0.044, "out": 3.96},
}

# ---- Stated assumptions (documented in docs/08_cost_model.md) -------------
N_REQ = 40              # requirements in a typical SRS (persona P-1: 30-60)
TOK_PER_REQ = 40        # tokens per requirement statement
DOC_OVERHEAD = 400      # headings, intro text, line numbers
SYS_EXTRACT = 600       # system prompt + output schema, Extractor
SYS_QUALITY = 700       # system prompt + schema, Quality
SYS_TESTS = 600         # system prompt + schema, Test-writer
FLAG_SHARE = 0.40       # share of requirements the Quality agent flags
OUT_EXTRACT_PER_REQ = 45
OUT_QUALITY_PER_FLAG = 90
OUT_QUALITY_PER_REQ_B = 60   # option B returns a verdict for every requirement
OUT_TEST_PER_REQ = 70
RULE_FINDINGS_TOK = 10       # rule findings passed to Quality, per requirement
RETRY_RATE = 0.10            # share of calls retried once (FR-07)


@dataclass
class Stage:
    name: str
    calls: int
    tok_in: int
    tok_out: int
    cacheable_in: int = 0  # repeated identical prefix tokens (system prompt) after call 1


def stages_option_a(n: int = N_REQ) -> list[Stage]:
    doc = n * TOK_PER_REQ + DOC_OVERHEAD
    return [
        Stage("Extractor", 1, SYS_EXTRACT + doc, n * OUT_EXTRACT_PER_REQ),
        Stage("Quality", 1, SYS_QUALITY + n * (TOK_PER_REQ + RULE_FINDINGS_TOK),
              int(n * FLAG_SHARE * OUT_QUALITY_PER_FLAG)),
        Stage("Test-writer", 1, SYS_TESTS + n * TOK_PER_REQ, n * OUT_TEST_PER_REQ),
    ]


def stages_option_b(n: int = N_REQ) -> list[Stage]:
    doc = n * TOK_PER_REQ + DOC_OVERHEAD
    return [
        Stage("Extractor", 1, SYS_EXTRACT + doc, n * OUT_EXTRACT_PER_REQ),
        Stage("Quality", n, n * (SYS_QUALITY + TOK_PER_REQ + RULE_FINDINGS_TOK),
              n * OUT_QUALITY_PER_REQ_B, cacheable_in=(n - 1) * SYS_QUALITY),
        Stage("Test-writer", n, n * (SYS_TESTS + TOK_PER_REQ), n * OUT_TEST_PER_REQ,
              cacheable_in=(n - 1) * SYS_TESTS),
    ]


def scale(stages: list[Stage], f_in: float, f_out: float) -> list[Stage]:
    return [Stage(s.name, s.calls, round(s.tok_in * f_in), round(s.tok_out * f_out),
                  round(s.cacheable_in * f_in)) for s in stages]


def run_cost(stages: list[Stage], rate: dict, use_cache: bool = False,
             retry: float = RETRY_RATE) -> tuple[int, int, float]:
    """Return (input tokens, output tokens, USD) for one run, including retries."""
    tin = sum(s.tok_in for s in stages)
    tout = sum(s.tok_out for s in stages)
    hit = sum(s.cacheable_in for s in stages) if use_cache else 0
    usd = ((tin - hit) * rate["in_miss"] + hit * rate["in_hit"] + tout * rate["out"]) / 1e6
    f = 1 + retry
    return round(tin * f), round(tout * f), usd * f


def fmt(usd: float) -> str:
    return f"${usd:.4f} ({usd * USD_TO_SAR:.4f} SAR)"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--measured-extractor-in", type=int)
    ap.add_argument("--measured-extractor-out", type=int)
    args = ap.parse_args()

    a, b = stages_option_a(), stages_option_b()
    basis = "ESTIMATED (assumptions above)"
    if args.measured_extractor_in and args.measured_extractor_out:
        est = a[0]
        f_in = args.measured_extractor_in / est.tok_in
        f_out = args.measured_extractor_out / est.tok_out
        a, b = scale(a, f_in, f_out), scale(b, f_in, f_out)
        basis = (f"CALIBRATED to measured Extractor call: in {args.measured_extractor_in} "
                 f"(x{f_in:.2f}), out {args.measured_extractor_out} (x{f_out:.2f})")

    print(f"Basis: {basis}\n")
    for label, st in (("Option A (batched)", a), ("Option B (fan-out)", b)):
        print(f"{label} - per run of {N_REQ} requirements")
        for s in st:
            print(f"   {s.name:12s} calls={s.calls:3d}  in={s.tok_in:6d}  out={s.tok_out:6d}")
        tin, tout, usd = run_cost(st, RATES["flash_peak"])
        print(f"   TOTAL incl. {RETRY_RATE:.0%} retries: in={tin} out={tout} "
              f"tokens={tin + tout}  cost(peak)={fmt(usd)}\n")

    print("Sensitivity (per run, USD at Flash prices unless noted)")
    rows = [
        ("Base: peak, 10% retries", a, b, RATES["flash_peak"], False, RETRY_RATE, N_REQ),
        ("Off-peak hours", a, b, RATES["flash_offpeak"], False, RETRY_RATE, N_REQ),
        ("B with prompt-cache hits", a, b, RATES["flash_peak"], True, RETRY_RATE, N_REQ),
        ("Retries 30%", a, b, RATES["flash_peak"], False, 0.30, N_REQ),
        ("Document x2 (80 reqs)", None, None, RATES["flash_peak"], False, RETRY_RATE, 2 * N_REQ),
        ("Switch to V4-Pro (peak)", a, b, RATES["pro_peak"], False, RETRY_RATE, N_REQ),
    ]
    print(f"   {'Scenario':28s} {'A tokens':>9s} {'A cost':>10s} {'B tokens':>9s} {'B cost':>10s} {'B/A':>6s}")
    for name, sa, sb, rate, cache, retry, n in rows:
        if sa is None:
            sa, sb = stages_option_a(n), stages_option_b(n)
        ta_in, ta_out, ua = run_cost(sa, rate, False, retry)
        tb_in, tb_out, ub = run_cost(sb, rate, cache, retry)
        print(f"   {name:28s} {ta_in + ta_out:9d} {ua:10.4f} {tb_in + tb_out:9d} {ub:10.4f} {ub / ua:6.2f}")

    print("\nMonthly / project totals at base (peak) rates")
    _, _, ua = run_cost(a, RATES["flash_peak"])
    _, _, ub = run_cost(b, RATES["flash_peak"])
    for name, runs in (("Project lifetime (dev + M3 evaluation) - 1,000 runs", 1000),
                       ("Pilot: 10 engineers x 3 SRS x 3 runs / month", 90),
                       ("Stress: 100 engineers x 3 SRS x 3 runs / month", 900)):
        print(f"   {name:52s} A={fmt(ua * runs)}  B={fmt(ub * runs)}")


if __name__ == "__main__":
    main()

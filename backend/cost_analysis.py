"""
cost_analysis.py — Cost Reduction Analysis for NumeriX ACW
==============================================================

Reads the latest measured token counts from:
    acw_experiment_results_v2.json

The script:
  1. Reports measured token usage and token reduction.
  2. Projects hypothetical monthly input/context-token costs.
  3. Estimates monthly savings versus the baseline.

IMPORTANT:
- Token-reduction results are measured experimental results.
- Dollar figures are hypothetical estimates based on the price constant below.
- Verify the provider's current pricing before using any dollar figure
  in a research paper.
- The cost projection considers context/input tokens only. It does not
  represent the total API bill, which can also include query, system,
  cached, and output tokens depending on the provider.

USAGE
-----
From numerix/backend/:

    python run_experiment.py
    python cost_analysis.py
"""

import json
from pathlib import Path


# ---------------------------------------------------------------------------
# Pricing assumption
# ---------------------------------------------------------------------------
# This is a PLACEHOLDER only. Verify the current price for the model/provider
# used in the paper before citing any dollar amount.
PRICE_PER_1K_INPUT_TOKENS_USD = 0.000075

PRICING_SOURCE_NOTE = (
    "Illustrative only — verify current pricing at your provider's "
    "pricing page before citing a dollar figure in the paper."
)


# ---------------------------------------------------------------------------
# Deployment volumes used only for hypothetical projections
# ---------------------------------------------------------------------------
QUERY_VOLUMES_PER_MONTH = [
    1_000,
    10_000,
    100_000,
    1_000_000,
]


# IMPORTANT: This is the latest experiment file.
RESULTS_FILE = "acw_experiment_results_v2.json"


def load_measured_data():
    """Load measured experiment results from the latest JSON file."""
    results_path = Path(__file__).resolve().parent / RESULTS_FILE

    if not results_path.exists():
        raise FileNotFoundError(
            f"Results file not found:\n{results_path}\n\n"
            "Run run_experiment.py first."
        )

    with results_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def summarize_strategy(records):
    """
    Calculate averages using only successful experiment records.

    Expected record fields:
        status
        tokens_before
        tokens_after
        token_reduction_pct
    """
    ok = [
        r for r in records
        if r.get("status") == "ok"
        and r.get("tokens_before") is not None
        and r.get("tokens_after") is not None
    ]

    if not ok:
        return None

    n = len(ok)

    avg_before = sum(r["tokens_before"] for r in ok) / n
    avg_after = sum(r["tokens_after"] for r in ok) / n

    # Calculate reduction from the averaged token counts rather than averaging
    # rounded per-query percentages. This gives a consistent aggregate value.
    if avg_before > 0:
        reduction_pct = ((avg_before - avg_after) / avg_before) * 100
    else:
        reduction_pct = 0.0

    return {
        "n": n,
        "avg_tokens_before": avg_before,
        "avg_tokens_after": avg_after,
        "avg_reduction_pct": reduction_pct,
    }


def calculate_monthly_cost(avg_tokens, queries_per_month):
    """Estimate monthly cost for context/input tokens only."""
    monthly_tokens = avg_tokens * queries_per_month
    return (monthly_tokens / 1000) * PRICE_PER_1K_INPUT_TOKENS_USD


def main():
    data = load_measured_data()

    print("\n" + "=" * 78)
    print("  Cost Reduction Analysis — NumeriX ACW")
    print("=" * 78)
    print(f"  Results file: {RESULTS_FILE}")
    print(f"  Pricing note: {PRICING_SOURCE_NOTE}")
    print(
        f"  Assumed price: {PRICE_PER_1K_INPUT_TOKENS_USD:.6f} "
        "(hypothetical token-cost units, not currency)"
    )
    print("=" * 78)

    # -----------------------------------------------------------------------
    # Summarize each strategy
    # -----------------------------------------------------------------------
    summaries = {}

    for strategy, records in data.items():
        if not isinstance(records, list):
            continue

        summary = summarize_strategy(records)

        if summary:
            summaries[strategy] = summary

    # Keep the paper's expected order when available.
    ordered_strategies = [
        strategy
        for strategy in ("baseline", "moderate", "aggressive")
        if strategy in summaries
    ]

    # Add any other strategies that may exist in the JSON.
    for strategy in summaries:
        if strategy not in ordered_strategies:
            ordered_strategies.append(strategy)

    baseline = summaries.get("baseline")

    if not baseline:
        print("\nERROR: No successful baseline data found.")
        print("Run run_experiment.py first and check the JSON file.")
        return

    # -----------------------------------------------------------------------
    # Measured token reduction
    # -----------------------------------------------------------------------
    print("\nMEASURED EXPERIMENT RESULTS")
    print("-" * 78)
    print(
        f"{'Strategy':<14}"
        f"{'Successful N':>14}"
        f"{'Avg Tok Before':>18}"
        f"{'Avg Tok After':>17}"
        f"{'Reduction %':>15}"
    )
    print("-" * 78)

    for strategy in ordered_strategies:
        s = summaries[strategy]

        print(
            f"{strategy:<14}"
            f"{s['n']:>14}"
            f"{s['avg_tokens_before']:>18.1f}"
            f"{s['avg_tokens_after']:>17.1f}"
            f"{s['avg_reduction_pct']:>14.1f}%"
        )

    # -----------------------------------------------------------------------
    # Hypothetical monthly cost projection
    # -----------------------------------------------------------------------
    print("\n" + "-" * 78)
    print("HYPOTHETICAL MONTHLY COST PROJECTION")
    print("(Context/input tokens only — estimate, NOT experimental data)")
    print("-" * 78)

    header = f"{'Queries/mo':>14}"

    for strategy in ordered_strategies:
        header += f"{strategy:>18}"

    print(header)
    print("-" * (14 + 18 * len(ordered_strategies)))

    for volume in QUERY_VOLUMES_PER_MONTH:
        row = f"{volume:>14,}"

        for strategy in ordered_strategies:
            s = summaries[strategy]

            monthly_cost = calculate_monthly_cost(
                s["avg_tokens_after"],
                volume,
            )

            row += f"{format(monthly_cost, ',.4f'):>18}"

        print(row)

    # -----------------------------------------------------------------------
    # Estimated dollar savings versus baseline
    # -----------------------------------------------------------------------
    print("\n" + "-" * 78)
    print("ESTIMATED MONTHLY SAVINGS VS. BASELINE")
    print("(Context/input tokens only — hypothetical estimate)")
    print("-" * 78)

    non_baseline = [
        strategy
        for strategy in ordered_strategies
        if strategy != "baseline"
    ]

    header = f"{'Queries/mo':>14}"

    for strategy in non_baseline:
        header += f"{strategy:>18}"

    print(header)
    print("-" * (14 + 18 * len(non_baseline)))

    baseline_avg_after = baseline["avg_tokens_after"]

    for volume in QUERY_VOLUMES_PER_MONTH:
        row = f"{volume:>14,}"

        for strategy in non_baseline:
            s = summaries[strategy]

            tokens_saved = (
                baseline_avg_after - s["avg_tokens_after"]
            ) * volume

            dollars_saved = (
                tokens_saved / 1000
            ) * PRICE_PER_1K_INPUT_TOKENS_USD

            row += f"{format(dollars_saved, ',.4f'):>18}"

        print(row)

    # -----------------------------------------------------------------------
    # Estimated percentage cost saving
    # -----------------------------------------------------------------------
    print("\n" + "=" * 78)
    print("ESTIMATED INPUT-COST SAVING")
    print("For context/input tokens, cost saving approximately follows")
    print("the measured token reduction.")
    print("=" * 78)

    for strategy in ordered_strategies:
        if strategy == "baseline":
            continue

        s = summaries[strategy]

        print(
            f"  {strategy:<14} → "
            f"~{s['avg_reduction_pct']:.1f}% estimated "
            "context/input-token cost saving"
        )

    print("=" * 78)

    print("\nResearch-paper guidance:")
    print(
        "  • Report token reductions as measured experimental results."
    )
    print(
        "  • Report dollar projections only as hypothetical practical "
        "implications."
    )
    print(
        "  • Verify current provider pricing before citing dollar amounts."
    )
    print(
        "  • Do not describe the projected dollar figures as measured "
        "costs."
    )
    print()


if __name__ == "__main__":
    main()

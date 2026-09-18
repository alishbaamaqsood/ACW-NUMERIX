"""
run_experiment_v2.py — NumeriX ACW Research Data Collector (Rate-Limit Safe)
=============================================================================
10 queries x 3 strategies = 30 total API calls
2 second delay between calls to stay within Gemini free tier limits.
"""

import json
import time
import requests
from datetime import datetime

BASE_URL = "http://localhost:8000/api/chatbot/ask"

# 10 queries — one per module + 3 general (covers all 7 modules)
TEST_QUERIES = [
    "What is the Bisection method?",           # Root Finding
    "How does Newton-Raphson converge?",        # Root Finding
    "What is Simpson's 1/3 rule?",             # Integration
    "Why is RK4 more accurate than Euler?",    # ODE
    "What is Lagrange interpolation?",         # Interpolation
    "What is finite difference?",              # Differentiation
    "What is LU decomposition?",               # Linear Systems
    "What is truncation error?",               # Error Analysis
    "What is NumeriX?",                        # General
    "What topics does this app cover?",        # General
]

STRATEGIES = ["baseline", "moderate", "aggressive"]
RESULTS = {s: [] for s in STRATEGIES}
DELAY = 2  # seconds between calls


def run_query(query: str, strategy: str) -> dict:
    payload = {"message": query, "history": [], "strategy": strategy}
    try:
        start = time.time()
        resp = requests.post(BASE_URL, json=payload, timeout=30)
        latency = round((time.time() - start) * 1000, 1)
        data = resp.json()
        metrics = data.get("acw_metrics", {})
        return {
            "query": query,
            "strategy": strategy,
            "latency_ms": latency,
            "tokens_before": metrics.get("tokens_before", 0),
            "tokens_after": metrics.get("tokens_after", 0),
            "token_reduction_pct": metrics.get("token_reduction_pct", 0),
            "chunks_retrieved": metrics.get("chunks_retrieved", 0),
            "chunks_selected": metrics.get("chunks_selected", 0),
            "reply_length": len(data.get("reply", "")),
            "sources": data.get("sources", []),
            "status": "ok"
        }
    except Exception as e:
        return {"query": query, "strategy": strategy, "status": "error", "error": str(e)}


def print_summary(results: dict):
    print("\n" + "="*65)
    print("  NumeriX ACW — Research Results Summary")
    print(f"  Run at: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    print("="*65)
    print(f"\n{'Strategy':<12} {'Queries':>8} {'Avg Tok Before':>15} "
          f"{'Avg Tok After':>14} {'Reduction %':>12} {'Avg Latency':>12}")
    print("-"*65)
    for strategy in STRATEGIES:
        records = [r for r in results[strategy] if r.get("status") == "ok"]
        if not records:
            continue
        n = len(records)
        avg_before = sum(r["tokens_before"] for r in records) / n
        avg_after  = sum(r["tokens_after"]  for r in records) / n
        avg_red    = sum(r["token_reduction_pct"] for r in records) / n
        avg_lat    = sum(r["latency_ms"] for r in records) / n
        print(f"{strategy:<12} {n:>8} {avg_before:>15.1f} "
              f"{avg_after:>14.1f} {avg_red:>11.1f}% {avg_lat:>10.0f}ms")
    print("\n" + "="*65)
    print("  Full results saved to: acw_experiment_results_v2.json")
    print("="*65 + "\n")


def main():
    total = len(TEST_QUERIES) * len(STRATEGIES)
    print(f"\nNumeriX ACW Experiment (Rate-Limit Safe)")
    print(f"Testing {len(TEST_QUERIES)} queries x {len(STRATEGIES)} strategies = {total} calls")
    print(f"Delay: {DELAY}s between calls (~{total * DELAY // 60}min total)\n")

    done = 0
    for strategy in STRATEGIES:
        print(f"\n--- Strategy: {strategy.upper()} ---")
        for query in TEST_QUERIES:
            result = run_query(query, strategy)
            RESULTS[strategy].append(result)
            done += 1
            status = "OK" if result.get("status") == "ok" else "ERR"
            reduction = result.get("token_reduction_pct", 0)
            print(f"  [{done:02d}/{total}] [{status}] Reduction: {reduction:5.1f}%  | {query[:45]}")
            if done < total:
                time.sleep(DELAY)

    with open("acw_experiment_results_v2.json", "w") as f:
        json.dump(RESULTS, f, indent=2)

    print_summary(RESULTS)


if __name__ == "__main__":
    main()
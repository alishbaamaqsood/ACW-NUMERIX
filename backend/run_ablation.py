"""
run_ablation.py — Ablation Study for the ACW Scoring Function

Place this file in:
    numerix/backend/

Run:
    cd numerix/backend
    python run_ablation.py

Requirements:
    - Server running at http://localhost:8000
    - acw.py supports alpha/scoring_mode
    - chatbot.py forwards alpha/scoring_mode
    - run_experiment.py contains TEST_QUERIES
    - answer_quality.py contains judge_answer
"""

import json
import time
from typing import Dict, List

import requests

from run_experiment import TEST_QUERIES
from answer_quality import judge_answer   # FIXED: actual file name


# API endpoint
ASK_URL = "http://localhost:8000/api/chatbot/ask"

# Delay between calls
SLEEP_BETWEEN_CALLS = 1.0


# ─────────────────────────────────────────────────────────────────────────────
# ABLATION CONFIGURATIONS
# ─────────────────────────────────────────────────────────────────────────────

CONFIGS = [
    {
        "label": "cosine_only",
        "scoring_mode": "cosine_only",
        "alpha": None,
    },
    {
        "label": "density_only",
        "scoring_mode": "density_only",
        "alpha": None,
    },
    {
        "label": "alpha_0.3",
        "scoring_mode": "hybrid",
        "alpha": 0.3,
    },
    {
        "label": "alpha_0.5",
        "scoring_mode": "hybrid",
        "alpha": 0.5,
    },
    {
        "label": "alpha_0.7",
        "scoring_mode": "hybrid",
        "alpha": 0.7,
    },
    {
        "label": "alpha_0.9",
        "scoring_mode": "hybrid",
        "alpha": 0.9,
    },
]


# ─────────────────────────────────────────────────────────────────────────────
# ASK CHATBOT
# ─────────────────────────────────────────────────────────────────────────────

def ask_chatbot(query: str, config: Dict) -> Dict:

    payload = {
        "message": query,
        "history": [],
        "strategy": "moderate",
        "alpha": config["alpha"],
        "scoring_mode": config["scoring_mode"],
    }

    try:
        response = requests.post(
            ASK_URL,
            json=payload,
            timeout=60,
        )

        response.raise_for_status()

        return response.json()

    except Exception as e:

        return {
            "reply": "",
            "sources": [],
            "acw_metrics": {},
            "error": str(e),
        }


# ─────────────────────────────────────────────────────────────────────────────
# SAFE AVERAGE
# ─────────────────────────────────────────────────────────────────────────────

def average(rows: List[Dict], key: str):

    values = [
        row.get(key)
        for row in rows
        if isinstance(row.get(key), (int, float))
    ]

    if not values:
        return None

    return sum(values) / len(values)


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main():

    all_results: List[Dict] = []

    total = len(CONFIGS) * len(TEST_QUERIES)
    done = 0

    print("=" * 100)
    print("ACW SCORING FUNCTION — ABLATION STUDY")
    print("=" * 100)

    print(f"Configurations : {len(CONFIGS)}")
    print(f"Test queries   : {len(TEST_QUERIES)}")
    print(f"Total runs     : {total}")

    print("=" * 100)

    # ─────────────────────────────────────────────────────────────────────────
    # RUN EACH CONFIGURATION
    # ─────────────────────────────────────────────────────────────────────────

    for config in CONFIGS:

        print(f"\n--- Config: {config['label']} ---")

        for query in TEST_QUERIES:

            done += 1

            chat_resp = ask_chatbot(query, config)

            answer = chat_resp.get("reply", "")
            metrics = chat_resp.get("acw_metrics", {})

            # Request failed
            if chat_resp.get("error"):

                print(
                    f"[{done:03d}/{total}] "
                    f"ERROR: {chat_resp['error']}"
                )

                continue

            # No answer
            if not answer:

                print(
                    f"[{done:03d}/{total}] "
                    f"SKIP — no answer — {query[:40]}"
                )

                continue

            # ─────────────────────────────────────────────────────────────────
            # LLM JUDGE
            # ─────────────────────────────────────────────────────────────────

            try:

                scores = judge_answer(
                    query,
                    answer
                )

            except Exception as e:

                print(
                    f"[{done:03d}/{total}] "
                    f"JUDGE ERROR: {e}"
                )

                continue

            # ─────────────────────────────────────────────────────────────────
            # SAVE RESULT
            # ─────────────────────────────────────────────────────────────────

            record = {
                "config": config["label"],
                "query": query,

                "token_reduction_pct": metrics.get(
                    "token_reduction_pct"
                ),

                "chunks_selected": metrics.get(
                    "chunks_selected"
                ),

                **scores,
            }

            all_results.append(record)

            print(
                f"[{done:03d}/{total}] "
                f"reduction={record['token_reduction_pct']}%  "
                f"correctness={record.get('correctness')}  "
                f"relevance={record.get('relevance')}  "
                f"completeness={record.get('completeness')}  "
                f"faithfulness={record.get('faithfulness')}  "
                f"| {query[:30]}"
            )

            time.sleep(SLEEP_BETWEEN_CALLS)

    # ─────────────────────────────────────────────────────────────────────────
    # SAVE RESULTS
    # ─────────────────────────────────────────────────────────────────────────

    output_file = "ablation_results.json"

    with open(
        output_file,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            all_results,
            f,
            indent=2,
            ensure_ascii=False,
        )

    # ─────────────────────────────────────────────────────────────────────────
    # SUMMARY TABLE
    # ─────────────────────────────────────────────────────────────────────────

    print("\n")
    print("=" * 110)
    print("ACW SCORING FUNCTION — ABLATION STUDY RESULTS")
    print("=" * 110)

    header = (
        f"{'Config':<16}"
        f"{'N':>5}"
        f"{'Reduction %':>16}"
        f"{'Correctness':>15}"
        f"{'Relevance':>13}"
        f"{'Completeness':>15}"
        f"{'Faithfulness':>15}"
    )

    print(header)
    print("-" * 110)

    for config in CONFIGS:

        label = config["label"]

        rows = [
            r
            for r in all_results
            if r["config"] == label
        ]

        if not rows:

            print(f"{label:<16} No results")
            continue

        reduction = average(
            rows,
            "token_reduction_pct"
        )

        correctness = average(
            rows,
            "correctness"
        )

        relevance = average(
            rows,
            "relevance"
        )

        completeness = average(
            rows,
            "completeness"
        )

        faithfulness = average(
            rows,
            "faithfulness"
        )

        def fmt(value):

            if value is None:
                return "N/A"

            return f"{value:.2f}"

        reduction_text = (
            "N/A"
            if reduction is None
            else f"{reduction:.1f}%"
        )

        print(
            f"{label:<16}"
            f"{len(rows):>5}"
            f"{reduction_text:>16}"
            f"{fmt(correctness):>15}"
            f"{fmt(relevance):>13}"
            f"{fmt(completeness):>15}"
            f"{fmt(faithfulness):>15}"
        )

    print("=" * 110)

    print(
        "\nInterpretation:\n"
        "  cosine_only  -> cosine similarity only\n"
        "  density_only -> density only\n"
        "  alpha=0.3    -> stronger density weighting\n"
        "  alpha=0.5    -> equal cosine/density weighting\n"
        "  alpha=0.7    -> proposed configuration\n"
        "  alpha=0.9    -> stronger cosine weighting\n"
    )

    print(
        "The ablation compares answer quality against "
        "token reduction to evaluate the quality-efficiency trade-off."
    )

    print(f"\nSaved: {output_file}")
    print(f"Successful experiments: {len(all_results)}/{total}")


if __name__ == "__main__":
    main()
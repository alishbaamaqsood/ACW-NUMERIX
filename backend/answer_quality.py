"""
answer_quality.py — Answer Quality / Accuracy Evaluation for NumeriX ACW
=========================================================================

Evaluates whether ACW token reduction affects answer quality.

For every query and strategy:
    1. Calls the running FastAPI chatbot.
    2. Sends the chatbot answer to a Gemini judge.
    3. Scores:
       - correctness
       - relevance
       - completeness
       - faithfulness
    4. Saves detailed results and prints averages.

Outputs:
    answer_quality_results.json
    answer_quality_for_human_review.csv
"""

import csv
import json
import os
import time
from typing import Dict, List

import requests

# ─────────────────────────────────────────────────────────────────────
# Load variables from .env
# ─────────────────────────────────────────────────────────────────────

try:
    from dotenv import load_dotenv
except ImportError:
    raise SystemExit(
        "python-dotenv is not installed.\n"
        "Run: pip install python-dotenv"
    )

load_dotenv()

# ─────────────────────────────────────────────────────────────────────
# Gemini
# ─────────────────────────────────────────────────────────────────────

try:
    import google.generativeai as genai
except ImportError:
    raise SystemExit(
        "google-generativeai is not installed.\n"
        "Run: pip install google-generativeai"
    )

# ─────────────────────────────────────────────────────────────────────
# Reuse the same test queries
# ─────────────────────────────────────────────────────────────────────

from run_experiment import TEST_QUERIES

# ─────────────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────────────

ASK_URL = "http://localhost:8000/api/chatbot/ask"

STRATEGIES = [
    "baseline",
    "moderate",
    "aggressive"
]

# Judge model
# Can be overridden in .env:
# ACW_JUDGE_MODEL=gemini-3.5-flash-lite

JUDGE_MODEL = os.environ.get(
    "ACW_JUDGE_MODEL",
    "gemini-3.5-flash-lite"
)

GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")

if not GOOGLE_API_KEY:
    raise SystemExit(
        "GOOGLE_API_KEY is not set in your environment/.env"
    )

genai.configure(api_key=GOOGLE_API_KEY)

_judge = genai.GenerativeModel(JUDGE_MODEL)

# Delay between API calls
SLEEP_BETWEEN_CALLS = 1.5


# ─────────────────────────────────────────────────────────────────────
# Knowledge Base
# ─────────────────────────────────────────────────────────────────────

from routers.chatbot import KNOWLEDGE_BASE

REFERENCE_TEXT = "\n\n".join(
    f"[{c['title']}]\n{c['content']}"
    for c in KNOWLEDGE_BASE
)


# ─────────────────────────────────────────────────────────────────────
# Judge Prompt
# ─────────────────────────────────────────────────────────────────────

JUDGE_PROMPT_TEMPLATE = """
You are an impartial evaluator grading a tutoring chatbot's answer.

You are given:

1. QUESTION — the student's question.

2. REFERENCE MATERIAL — the complete authoritative knowledge base
   used by the NumeriX chatbot.

3. ANSWER — the answer produced by the chatbot.

The chatbot may only receive a filtered subset of the reference material.
The purpose of this evaluation is to determine whether context reduction
affects answer quality.

Score the ANSWER from 1 to 5 on each metric.

SCORING:

correctness:
Are the facts accurate and consistent with the reference material?

relevance:
Does the answer directly address the student's question?

completeness:
Does the answer include the important information needed to answer
the question properly?

faithfulness:
Does the answer avoid unsupported claims or hallucinations and remain
faithful to the reference material?

Use:

1 = Very poor
2 = Poor
3 = Acceptable
4 = Good
5 = Excellent

Respond with ONLY a valid JSON object.
Do not use markdown.
Do not include commentary outside the JSON.

Required format:

{{
  "correctness": <1-5>,
  "relevance": <1-5>,
  "completeness": <1-5>,
  "faithfulness": <1-5>,
  "notes": "<one short sentence>"
}}

QUESTION:
{question}

REFERENCE MATERIAL:
{reference}

ANSWER:
{answer}
"""


# ─────────────────────────────────────────────────────────────────────
# Judge one answer
# ─────────────────────────────────────────────────────────────────────

def judge_answer(
    question: str,
    answer: str,
    retries: int = 2
) -> Dict:

    prompt = JUDGE_PROMPT_TEMPLATE.format(
        question=question,
        reference=REFERENCE_TEXT,
        answer=answer
    )

    for attempt in range(retries + 1):

        try:

            response = _judge.generate_content(prompt)

            text = response.text.strip()

            # Remove accidental markdown fences
            if text.startswith("```"):

                text = text.strip("`")

                if "\n" in text:
                    text = text.split("\n", 1)[1]

                if "```" in text:
                    text = text.rsplit("```", 1)[0]

                text = text.strip()

            data = json.loads(text)

            # Validate / convert scores
            for key in (
                "correctness",
                "relevance",
                "completeness",
                "faithfulness"
            ):

                data[key] = float(
                    data.get(key, 0)
                )

            return data

        except Exception as e:

            # Retry if attempts remain
            if attempt < retries:

                print(
                    f"\nJudge attempt "
                    f"{attempt + 1}/{retries + 1} failed:"
                )

                print(e)
                print("Retrying...\n")

                time.sleep(3)

            # Final failure — SHOW ACTUAL ERROR
            else:

                print("\n" + "=" * 70)
                print("JUDGE ERROR")
                print("=" * 70)
                print(f"Model: {JUDGE_MODEL}")
                print(f"Error: {e}")
                print("=" * 70 + "\n")

                return {
                    "correctness": None,
                    "relevance": None,
                    "completeness": None,
                    "faithfulness": None,
                    "error": str(e)
                }


# ─────────────────────────────────────────────────────────────────────
# Ask chatbot
# ─────────────────────────────────────────────────────────────────────

def ask_chatbot(
    query: str,
    strategy: str
) -> Dict:

    payload = {
        "message": query,
        "history": [],
        "strategy": strategy
    }

    try:

        response = requests.post(
            ASK_URL,
            json=payload,
            timeout=30
        )

        response.raise_for_status()

        return response.json()

    except Exception as e:

        print("\nCHATBOT ERROR:")
        print(e)
        print()

        return {
            "reply": "",
            "sources": [],
            "acw_metrics": {},
            "error": str(e)
        }


# ─────────────────────────────────────────────────────────────────────
# Main evaluation
# ─────────────────────────────────────────────────────────────────────

def main():

    all_results: List[Dict] = []

    total = len(TEST_QUERIES) * len(STRATEGIES)

    done = 0

    print()
    print("=" * 78)
    print(" NumeriX ACW — Answer Quality Evaluation")
    print("=" * 78)
    print(f" Judge model: {JUDGE_MODEL}")
    print(f" Queries: {len(TEST_QUERIES)}")
    print(f" Strategies: {len(STRATEGIES)}")
    print(f" Total evaluations: {total}")
    print("=" * 78)

    for strategy in STRATEGIES:

        print()
        print(
            f"--- Evaluating strategy: "
            f"{strategy.upper()} ---"
        )

        for query in TEST_QUERIES:

            done += 1

            chat_resp = ask_chatbot(
                query,
                strategy
            )

            answer = chat_resp.get(
                "reply",
                ""
            )

            if not answer:

                print(
                    f"[{done:02d}/{total}] "
                    f"SKIP — no chatbot answer — "
                    f"{query[:50]}"
                )

                continue

            scores = judge_answer(
                query,
                answer
            )

            record = {
                "query": query,
                "strategy": strategy,
                "answer": answer,
                "acw_metrics": chat_resp.get(
                    "acw_metrics",
                    {}
                ),
                **scores
            }

            all_results.append(record)

            print(
                f"[{done:02d}/{total}] "
                f"correctness="
                f"{scores.get('correctness')} "
                f"relevance="
                f"{scores.get('relevance')} "
                f"completeness="
                f"{scores.get('completeness')} "
                f"faithfulness="
                f"{scores.get('faithfulness')} "
                f"| {query[:45]}"
            )

            time.sleep(
                SLEEP_BETWEEN_CALLS
            )


    # ────────────────────────────────────────────────────────────────
    # Save JSON
    # ────────────────────────────────────────────────────────────────

    with open(
        "answer_quality_results.json",
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            all_results,
            f,
            indent=2,
            ensure_ascii=False
        )


    # ────────────────────────────────────────────────────────────────
    # Save CSV for human evaluation
    # ────────────────────────────────────────────────────────────────

    with open(
        "answer_quality_for_human_review.csv",
        "w",
        newline="",
        encoding="utf-8"
    ) as f:

        writer = csv.writer(f)

        writer.writerow([
            "query",
            "strategy",
            "answer",
            "llm_correctness",
            "llm_relevance",
            "llm_completeness",
            "llm_faithfulness",
            "human_correctness",
            "human_relevance",
            "human_completeness",
            "human_faithfulness"
        ])

        for result in all_results:

            writer.writerow([
                result["query"],
                result["strategy"],
                result["answer"],
                result.get("correctness"),
                result.get("relevance"),
                result.get("completeness"),
                result.get("faithfulness"),
                "",
                "",
                "",
                ""
            ])


    # ────────────────────────────────────────────────────────────────
    # Summary
    # ────────────────────────────────────────────────────────────────

    print()
    print("=" * 78)
    print(" Answer Quality Summary (1–5 scale)")
    print("=" * 78)

    header = (
        f"{'Strategy':<14}"
        f"{'Correctness':>14}"
        f"{'Relevance':>12}"
        f"{'Completeness':>15}"
        f"{'Faithfulness':>15}"
    )

    print(header)
    print("-" * 78)

    for strategy in STRATEGIES:

        rows = [
            r
            for r in all_results
            if r["strategy"] == strategy
            and r.get("correctness") is not None
        ]

        if not rows:
            continue

        n = len(rows)

        def average(metric):

            return sum(
                r[metric]
                for r in rows
            ) / n

        print(
            f"{strategy:<14}"
            f"{average('correctness'):>14.2f}"
            f"{average('relevance'):>12.2f}"
            f"{average('completeness'):>15.2f}"
            f"{average('faithfulness'):>15.2f}"
        )

    print("=" * 78)

    print()
    print("Saved:")
    print("  answer_quality_results.json")
    print("  answer_quality_for_human_review.csv")
    print()


# ─────────────────────────────────────────────────────────────────────
# Run
# ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    main()
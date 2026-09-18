"""
acw.py — Adaptive Context Wrapper for NumeriX
================================================
Drop this file into: numerix-na-webapp/backend/

It sits between your Pinecone retrieval (_retrieve) and your Gemini call.
No extra dependencies needed — uses only what you already have installed.

HOW IT WORKS:
1. Takes the chunks Pinecone returns (already ranked by cosine similarity)
2. Re-scores each chunk using: Pinecone score + information density
3. Applies a relevance threshold — drops chunks below MIN_SCORE
4. Enforces a token budget — stops adding chunks once budget is hit
5. Logs token counts before/after for your research data collection

RESEARCH DATA:
All logs are written to acw_log.jsonl in your backend folder.
Each line = one query's metrics. Use this for your paper's Section 5.
"""

import json
import math
import os
import time
from datetime import datetime
from typing import List, Dict, Tuple

# ─── Config ────────────────────────────────────────────────────────────────
ALPHA = 0.7          # weight for Pinecone similarity score (0-1)
MIN_SCORE = 0.25     # drop chunks below this relevance threshold
TOKEN_BUDGET = 400   # max tokens to send to Gemini (your chunks are short)
LOG_FILE = os.path.join(os.path.dirname(__file__), "acw_log.jsonl")


# ─── Token counter (no tiktoken needed — simple word-based estimate) ────────
def count_tokens(text: str) -> int:
    """
    Approximate token count. 
    Rule of thumb: 1 token ≈ 0.75 words for English text.
    Good enough for research measurement purposes.
    """
    words = len(text.split())
    return math.ceil(words / 0.75)


# ─── Density scorer ─────────────────────────────────────────────────────────
def information_density(text: str) -> float:
    """
    Measures how information-rich a chunk is.
    density = unique_words / total_words
    Higher = more diverse content, less repetition.
    """
    words = text.lower().split()
    if not words:
        return 0.0
    return len(set(words)) / len(words)


# ─── Main ACW function ──────────────────────────────────────────────────────
def adaptive_context_wrapper(
    query: str,
    chunks: List[Dict],
    strategy: str = "moderate",   # "baseline" | "moderate" | "aggressive"
    alpha: float = None,          # override ALPHA for this call (ablation study)
    scoring_mode: str = "hybrid", # "hybrid" | "cosine_only" | "density_only"
    log: bool = True,             # set False to keep ablation runs out of acw_log.jsonl
) -> Tuple[List[Dict], Dict]:
    """
    Filters and ranks Pinecone chunks before sending to Gemini.

    Args:
        query:        The user's question
        chunks:       List of dicts from _retrieve(), each has:
                      { id, title, content, score }
        strategy:     "baseline"   → no filtering (original behavior)
                      "moderate"   → top-2 chunks within token budget
                      "aggressive" → top-1 chunk only
        alpha:        Weight on cosine similarity in the hybrid score
                      (0-1). If None, falls back to the module-level
                      ALPHA constant. Only used when scoring_mode="hybrid".
                      Used by run_ablation.py to sweep alpha values.
        scoring_mode: "hybrid"       → alpha*cosine + (1-alpha)*density (default/original)
                      "cosine_only"  → ignore density, rank by Pinecone score alone
                      "density_only" → ignore cosine, rank by information density alone
        log:          Whether to append this call's metrics to acw_log.jsonl.
                      Ablation/eval scripts can set this False to avoid mixing
                      sweep data into your main research log.

    Returns:
        selected_chunks: filtered list to use in context
        metrics:         dict of research measurements
    """
    a = ALPHA if alpha is None else alpha

    # ── Tokens BEFORE filtering (baseline) ──────────────────────────────────
    all_text = "\n\n".join(
        f"[{c['title']}]\n{c['content']}" for c in chunks
    )
    tokens_before = count_tokens(all_text)

    # ── BASELINE: return all chunks unchanged ────────────────────────────────
    if strategy == "baseline":
        metrics = {
            "timestamp": datetime.utcnow().isoformat(),
            "query": query,
            "strategy": "baseline",
            "chunks_retrieved": len(chunks),
            "chunks_selected": len(chunks),
            "tokens_before": tokens_before,
            "tokens_after": tokens_before,
            "token_reduction_pct": 0.0,
            "scores": [round(c["score"], 4) for c in chunks],
            "scoring_mode": "baseline",
            "alpha_used": None,
        }
        if log:
            _log(metrics)
        return chunks, metrics

    # ── Set K based on strategy ──────────────────────────────────────────────
    k = 2 if strategy == "moderate" else 1

    # ── Score each chunk ─────────────────────────────────────────────────────
    scored = []
    for chunk in chunks:
        content = chunk.get("content", "")
        pinecone_score = chunk.get("score", 0.0)        # already 0-1 cosine
        density = information_density(content)

        if scoring_mode == "cosine_only":
            combined = pinecone_score
        elif scoring_mode == "density_only":
            combined = density
        else:  # "hybrid" (default / original ACW formulation)
            combined = a * pinecone_score + (1 - a) * density

        scored.append((combined, chunk))

    # Sort by combined score descending
    scored.sort(key=lambda x: x[0], reverse=True)

    # ── Apply threshold + token budget + K limit ─────────────────────────────
    selected = []
    total_tokens = 0

    for combined_score, chunk in scored:
        # Drop below threshold
        if combined_score < MIN_SCORE:
            continue
        # Stop at K
        if len(selected) >= k:
            break
        # Check token budget
        chunk_tokens = count_tokens(chunk["content"])
        if total_tokens + chunk_tokens > TOKEN_BUDGET:
            continue
        selected.append(chunk)
        total_tokens += chunk_tokens

    # ── If nothing passed threshold, fall back to top-1 ─────────────────────
    if not selected and scored:
        selected = [scored[0][1]]
        total_tokens = count_tokens(scored[0][1]["content"])

    # ── Tokens AFTER filtering ───────────────────────────────────────────────
    tokens_after = count_tokens(
        "\n\n".join(f"[{c['title']}]\n{c['content']}" for c in selected)
    )
    reduction = round((1 - tokens_after / tokens_before) * 100, 2) if tokens_before > 0 else 0.0

    # ── Build metrics for research logging ──────────────────────────────────
    metrics = {
        "timestamp": datetime.utcnow().isoformat(),
        "query": query,
        "strategy": strategy,
        "chunks_retrieved": len(chunks),
        "chunks_selected": len(selected),
        "tokens_before": tokens_before,
        "tokens_after": tokens_after,
        "token_reduction_pct": reduction,
        "scores_before": [round(c["score"], 4) for c in chunks],
        "combined_scores": [round(s, 4) for s, _ in scored[:len(chunks)]],
        "selected_titles": [c["title"] for c in selected],
        "scoring_mode": scoring_mode,
        "alpha_used": a if scoring_mode == "hybrid" else None,
    }
    if log:
        _log(metrics)

    return selected, metrics


# ─── Logger ─────────────────────────────────────────────────────────────────
def _log(metrics: Dict):
    """Append one JSON line to acw_log.jsonl for research data collection."""
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(metrics) + "\n")
    except Exception:
        pass  # Never crash the chatbot over logging


# ─── Analysis helper (run this to see your research results) ────────────────
def analyze_log():
    """
    Run this separately to print a summary of your collected data.
    Usage:  python acw.py
    """
    if not os.path.exists(LOG_FILE):
        print("No log file yet. Send some queries first!")
        return

    records = []
    with open(LOG_FILE, "r") as f:
        for line in f:
            try:
                records.append(json.loads(line.strip()))
            except Exception:
                continue

    if not records:
        print("Log file is empty.")
        return

    strategies = {}
    for r in records:
        s = r["strategy"]
        if s not in strategies:
            strategies[s] = {"reductions": [], "tokens_before": [], "tokens_after": []}
        strategies[s]["reductions"].append(r["token_reduction_pct"])
        strategies[s]["tokens_before"].append(r["tokens_before"])
        strategies[s]["tokens_after"].append(r["tokens_after"])

    print(f"\n{'='*60}")
    print(f"  NumeriX ACW Research Results  ({len(records)} total queries)")
    print(f"{'='*60}")
    for s, data in strategies.items():
        n = len(data["reductions"])
        avg_before = sum(data["tokens_before"]) / n
        avg_after = sum(data["tokens_after"]) / n
        avg_reduction = sum(data["reductions"]) / n
        print(f"\nStrategy: {s.upper()}  ({n} queries)")
        print(f"  Avg tokens before ACW : {avg_before:.1f}")
        print(f"  Avg tokens after  ACW : {avg_after:.1f}")
        print(f"  Avg token reduction   : {avg_reduction:.1f}%")
        print(f"  Estimated cost saving : {avg_reduction:.1f}%")
    print(f"\n{'='*60}\n")


if __name__ == "__main__":
    analyze_log()

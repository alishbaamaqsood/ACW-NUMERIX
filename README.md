# ACW — Adaptive Context Wrapper

> **Smarter RAG. Fewer tokens. Same quality.**

ACW dynamically compresses the context sent to LLMs in RAG pipelines — cutting token usage by up to **66%** while maintaining perfect answer quality scores (5/5 across all metrics).

Built on top of **NumeriX**, an AI-powered numerical analysis chatbot.

---

## Key Results

| Strategy | Tokens Sent | Reduction | Avg Latency |
|---|---|---|---|
| Baseline | 231.3 | 0% | 4154ms |
| Moderate | 157.7 | **31.7%** | 3949ms |
| Aggressive | 79.1 | **66%** | 4040ms |

> **Latency Note:** Latency is dominated by the Gemini API round-trip (~3.5–5s), not by compression. ACW saves **cost**, not time.

---

## Features

| Module | What it does |
|---|---|
| **ACW Core** (`routers/acw.py`) | Scores & selects context chunks using `α·cosine + (1−α)·density` |
| **Risk-Aware Compression** | Scores query risk (0–100) and picks compression level automatically |
| **Semantic Safety Guard** | Blocks compression if critical info (numbers, dates, constraints) would be lost |
| **Evidence Coverage Compression** | Ensures selected chunks cover all key evidence before generation |
| **Context Recovery** | Low-confidence answer? Auto-retries with progressively more context |
| **Neurosymbolic Reasoning** | Detects mathematical queries and parses them symbolically before LLM call |
| **Semantic Response Cache** | Skips LLM entirely for similar past queries using cosine similarity |

---

## Pipeline (Risk-Aware Mode)

```
Query -> Risk Score -> Evidence Check -> Safety Guard -> Generate -> Evaluate -> Recover
```

If still low-confidence after recovery exhausted — **abstains** instead of hallucinating.

---

## Evaluation Scripts

| Script | Measures |
|---|---|
| `run_experiment.py` | Token reduction, latency, chunks used |
| `answer_quality.py` | Correctness, relevance, completeness, faithfulness (LLM-as-judge) |
| `run_ablation.py` | Quality vs alpha across 6 scoring configurations |
| `cost_analysis.py` | Estimated token-cost savings (hypothetical units, not currency) |
| `test_wrong.py` | Sanity-checks judge: correct answer vs deliberately wrong answer |

---

## Quickstart

```bash
uvicorn main:app --reload

# from backend/
python run_experiment.py
python answer_quality.py
python run_ablation.py
python cost_analysis.py
python test_wrong.py
```

---

## File Structure

```
backend/
├── modules/
│   ├── risk_aware_compression.py
│   ├── semantic_safety_guard.py
│   ├── evidence_coverage_compression.py
│   ├── neurosymbolic_reasoning.py
│   ├── context_recovery.py
│   └── semantic_response_cache.py
├── routers/
│   ├── acw.py
│   └── chatbot.py
├── run_experiment.py
├── answer_quality.py
├── run_ablation.py
├── cost_analysis.py
└── test_wrong.py

frontend/src/pages/Chatbot.jsx
```

---

## Stack

Python · FastAPI · Google Gemini · Pinecone · React · RAG · Semantic Embeddings

---

*Academic research project — NumeriX AI Chatbot*

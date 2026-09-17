"""
NumeriX AI Assistant — with Adaptive Context Wrapper (ACW)
-----------------------------------------------------------
Changes from previous version:
  1. Wired in the 3 new modules under backend/modules/:
       - risk_aware_compression.py  -> picks a compression strategy per-query risk
       - semantic_safety_guard.py   -> pre-checks that filtering didn't drop
                                        numbers/dates/constraints before we ever
                                        call Gemini
       - context_recovery.py        -> scores the generated answer's quality and,
                                        if it's weak, retries with less compression
                                        (Compress -> Generate -> Evaluate -> Recover)
  2. All of this is OPT-IN via `use_risk_aware: true` in the request body.
     Default behavior (use_risk_aware=False, the default) is UNCHANGED, so
     run_experiment.py / run_ablation.py / evaluate_answer_quality.py keep
     working exactly as before with the explicit strategy/alpha they pass.
  3. Response now includes `risk_assessment`, `safety_report`, and
     `recovery` fields when risk-aware mode is used (null otherwise).

COST/QUOTA NOTE: with use_risk_aware=True, a low-confidence answer can
trigger up to `max_recovery_attempts` EXTRA Gemini generate_content calls
per request (it regenerates the answer with more context, not just re-scores
the old one). If you're still tight on free-tier quota, leave use_risk_aware
off for your bulk experiment runs and only turn it on for a small demo.
"""

import os
import sys
from typing import List, Optional

# Make sure backend/ is on sys.path so `routers.acw` and `modules.*` resolve
# the same way regardless of where this file is launched from.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import google.generativeai as genai
from fastapi import APIRouter, HTTPException
from pinecone import Pinecone, ServerlessSpec
from pydantic import BaseModel

from routers.acw import adaptive_context_wrapper
from modules.risk_aware_compression import RiskAwareCompression, CompressionLevel
from modules.semantic_safety_guard import SemanticSafetyGuard
from modules.context_recovery import ContextRecovery
from modules.semantic_response_cache import semantic_cache
from modules.neurosymbolic_reasoning import process_query as ns_process_query

router = APIRouter()

GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
if GOOGLE_API_KEY:
    genai.configure(api_key=GOOGLE_API_KEY)

PINECONE_API_KEY = os.environ.get("PINECONE_API_KEY")
PINECONE_CLOUD = os.environ.get("PINECONE_CLOUD", "aws")
PINECONE_REGION = os.environ.get("PINECONE_REGION", "us-east-1")

EMBED_MODEL = "models/gemini-embedding-001"
EMBED_DIM = 768
# NOTE: double-check this model name is actually enabled on your account —
# "gemini-3.5-flash-lite" isn't a published Gemini model as of this writing.
# If /ask starts returning 400s unrelated to quota, this is the first thing
# to check — try "gemini-2.5-flash-lite" or "gemini-2.5-flash" instead.
CHAT_MODEL = "gemini-3.5-flash-lite"
INDEX_NAME = "acw-index"

_pc = Pinecone(api_key=PINECONE_API_KEY) if PINECONE_API_KEY else None
_index = None

# Risk-aware ACW pipeline components (stateless, safe to reuse)
_risk_scorer = RiskAwareCompression()
_safety_guard = SemanticSafetyGuard()
_recovery = ContextRecovery()

# Maps the 5-level compression ladder from risk_aware_compression.py onto the
# 3 strategies acw.py actually implements. NONE/MILD lean toward keeping more
# context; AGGRESSIVE/EXTREME lean toward keeping less.
COMPRESSION_TO_STRATEGY = {
    CompressionLevel.NONE: "baseline",
    CompressionLevel.MILD: "moderate",
    CompressionLevel.MODERATE: "moderate",
    CompressionLevel.AGGRESSIVE: "aggressive",
    CompressionLevel.EXTREME: "aggressive",
}

# Escalation order used by the recovery ladder: from most compressed to least.
_STRATEGY_RANK = {"aggressive": 0, "moderate": 1, "baseline": 2}
_ESCALATION_ORDER = ["aggressive", "moderate", "baseline"]
ABSTENTION_REPLY = (
    "I don't have enough reliable evidence in the available context to answer "
    "that definitively. Please provide more details or rephrase the question."
)


def _next_strategies_above(strategy: str) -> List[str]:
    """Strategies with strictly more context than `strategy`, ordered nearest-first."""
    rank = _STRATEGY_RANK.get(strategy, 1)
    return [s for s in _ESCALATION_ORDER if _STRATEGY_RANK[s] > rank]


def _get_index():
    global _index
    if _index is not None:
        return _index
    if _pc is None:
        raise HTTPException(
            status_code=500,
            detail="PINECONE_API_KEY is not configured on the server.",
        )
    existing = [i.name for i in _pc.list_indexes()]
    if INDEX_NAME not in existing:
        _pc.create_index(
            name=INDEX_NAME,
            dimension=EMBED_DIM,
            metric="cosine",
            spec=ServerlessSpec(cloud=PINECONE_CLOUD, region=PINECONE_REGION),
        )
    _index = _pc.Index(INDEX_NAME)
    return _index


KNOWLEDGE_BASE = [
    {
        "id": "errors",
        "title": "Error Analyzer (Lab 2)",
        "content": (
            "The Error Analyzer computes Absolute Error, Relative Error, "
            "Round-off Error, and Truncation Error. Absolute error is the "
            "magnitude of the difference between the true value and the "
            "approximate value. Relative error divides that by the true "
            "value, often expressed as a percentage. Round-off error comes "
            "from representing numbers with finite precision. Truncation "
            "error comes from approximating an infinite process (like a "
            "Taylor series) with a finite number of terms. Endpoint: "
            "/api/errors."
        ),
    },
    {
        "id": "rootfinder",
        "title": "Root Finder (Labs 4-5)",
        "content": (
            "The Root Finder module solves f(x) = 0 using Bisection, False "
            "Position (Regula Falsi), Newton-Raphson, and Fixed-Point "
            "iteration. Bisection and False Position need a bracketing "
            "interval [a, b] where f(a) and f(b) have opposite signs. "
            "Newton-Raphson needs f(x), its derivative f'(x), and an "
            "initial guess x0, and converges quadratically near the root. "
            "Fixed-Point iteration rewrites f(x)=0 as x = g(x) and iterates "
            "x_new = g(x). Each method returns an iteration table with the "
            "approximate error at each step. Endpoint: /api/roots."
        ),
    },
    {
        "id": "interpolation",
        "title": "Interpolator (Labs 6-7)",
        "content": (
            "The Interpolator module estimates values between known data "
            "points using Newton's Forward Difference, Newton's Backward "
            "Difference, Newton's Divided Difference, and Lagrange "
            "Interpolation. Forward/backward difference formulas assume "
            "equally spaced x-values, while divided difference and "
            "Lagrange work for unequally spaced points. Endpoint: "
            "/api/interpolation."
        ),
    },
    {
        "id": "differentiation",
        "title": "Differentiator (Lab 8)",
        "content": (
            "The Differentiator module estimates derivatives numerically "
            "using Forward and Backward Finite Difference formulas, for "
            "both first and second order derivatives, given a step size h "
            "and a set of function values. Endpoint: /api/differentiation."
        ),
    },
    {
        "id": "integration",
        "title": "Integrator (Labs 9-10)",
        "content": (
            "The Integrator module approximates definite integrals using "
            "the Trapezoidal Rule, Simpson's 1/3 Rule, Simpson's 3/8 Rule, "
            "and rules for unequally spaced segments. Simpson's 1/3 "
            "requires an even number of intervals; Simpson's 3/8 works in "
            "groups of three intervals. Endpoint: /api/integration."
        ),
    },
    {
        "id": "ode",
        "title": "ODE Solver (Labs 11-12)",
        "content": (
            "The ODE Solver module solves first-order ordinary "
            "differential equations dy/dx = f(x, y) using Euler's Method, "
            "Improved Euler (Heun's Method), and 4th Order Runge-Kutta "
            "(RK4). RK4 is generally the most accurate for a given step "
            "size h because it evaluates the slope at four points per "
            "step. Endpoint: /api/ode."
        ),
    },
    {
        "id": "linear",
        "title": "Linear Systems (Lab 13)",
        "content": (
            "The Linear Systems module solves systems of linear equations "
            "Ax = b using LU Decomposition, with both the Doolittle method "
            "(unit lower-triangular L) and the Crout method (unit "
            "upper-triangular U). The system is factored into L and U, "
            "then solved via forward substitution (Ly = b) followed by "
            "back substitution (Ux = y). Endpoint: /api/linear."
        ),
    },
    {
        "id": "about",
        "title": "About NumeriX",
        "content": (
            "NumeriX is a full-stack interactive numerical methods "
            "calculator built for the BSE-6C Numerical Analysis course at "
            "Bahria University Karachi Campus. It has a React + Tailwind "
            "frontend and a Python FastAPI backend, covering 13 labs "
            "across error analysis, root finding, interpolation, "
            "differentiation, integration, ODE solving, and linear "
            "systems, each with iteration tables and live charts."
        ),
    },
]

_kb_seeded = False


def _ensure_kb_seeded():
    global _kb_seeded
    if _kb_seeded:
        return
    index = _get_index()
    stats = index.describe_index_stats()
    if stats.get("total_vector_count", 0) >= len(KNOWLEDGE_BASE):
        _kb_seeded = True
        return
    vectors = []
    for chunk in KNOWLEDGE_BASE:
        result = genai.embed_content(
            model=EMBED_MODEL,
            content=chunk["content"],
            task_type="retrieval_document",
            title=chunk["title"],
            output_dimensionality=EMBED_DIM,
        )
        vectors.append(
            {
                "id": chunk["id"],
                "values": result["embedding"],
                "metadata": {"title": chunk["title"], "content": chunk["content"]},
            }
        )
    index.upsert(vectors=vectors)
    _kb_seeded = True


def _embed_query(query: str) -> List[float]:
    return genai.embed_content(
        model=EMBED_MODEL,
        content=query,
        task_type="retrieval_query",
        output_dimensionality=EMBED_DIM,
    )["embedding"]


def _retrieve_by_embedding(q_embed: List[float], top_k: int = 3) -> List[dict]:
    _ensure_kb_seeded()
    index = _get_index()
    results = index.query(vector=q_embed, top_k=top_k, include_metadata=True)
    return [
        {"id": m.id, "title": m.metadata.get("title", ""),
         "content": m.metadata.get("content", ""), "score": m.score}
        for m in results.matches
    ]

def _retrieve(query: str, top_k: int = 3) -> List[dict]:
    _ensure_kb_seeded()
    index = _get_index()
    q_embed = genai.embed_content(
        model=EMBED_MODEL,
        content=query,
        task_type="retrieval_query",
        output_dimensionality=EMBED_DIM,
    )["embedding"]
    results = index.query(vector=q_embed, top_k=top_k, include_metadata=True)
    return [
        {
            "id": match.id,
            "title": match.metadata.get("title", ""),
            "content": match.metadata.get("content", ""),
            "score": match.score,
        }
        for match in results.matches
    ]


def _build_context(selected_chunks: List[dict]) -> str:
    return "\n\n".join(f"[{c['title']}]\n{c['content']}" for c in selected_chunks)


def _generate(query: str, context: str, history_payload: list, structured_block: Optional[str] = None) -> str:
    system_prompt = (
        "You are the NumeriX Assistant, a helpful tutor embedded in a "
        "numerical methods web app for a Numerical Analysis course. "
        "Answer the user's question using the reference context below "
        "when relevant. Explain concepts clearly and concisely, use "
        "the method names and endpoints from the context when helpful, "
        "and if a question is unrelated to numerical methods or this "
        "app, politely say so and redirect to what you can help with.\n\n"
        f"Reference context:\n{context}"
    )
    if structured_block:
        system_prompt += f"\n\n{structured_block}"
    model = genai.GenerativeModel(
        model_name=CHAT_MODEL,
        system_instruction=system_prompt,
    )
    chat = model.start_chat(history=history_payload)
    response = chat.send_message(query)
    return response.text


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatInput(BaseModel):
    message: str
    history: Optional[List[ChatMessage]] = []
    strategy: Optional[str] = "moderate"
    # Ablation-study controls (unchanged; used by run_ablation.py)
    alpha: Optional[float] = None
    scoring_mode: Optional[str] = "hybrid"
    # New: risk-aware pipeline controls (opt-in, default OFF)
    use_risk_aware: Optional[bool] = False
    max_recovery_attempts: Optional[int] = 1  # caps extra Gemini calls
    use_cache: Optional[bool] = False
    cache_threshold: Optional[float] = None
    # New: neurosymbolic reasoning (opt-in, default OFF). When enabled, math/
    # numerical/logic queries get parsed into a structured JSON (values,
    # operations, relationships, symbolic_expression) that is appended to the
    # system prompt alongside the ACW context. User still gets a normal
    # answer; the structured form is only logged for evaluation.
    use_neurosymbolic: Optional[bool] = False


@router.post("/ask")
def ask(data: ChatInput):
    if not GOOGLE_API_KEY:
        raise HTTPException(status_code=500, detail="GOOGLE_API_KEY is not configured.")
    if not PINECONE_API_KEY:
        raise HTTPException(status_code=500, detail="PINECONE_API_KEY is not configured.")

    try:
        history_payload = []
        for m in data.history or []:
            role = "model" if m.role == "assistant" else "user"
            history_payload.append({"role": role, "parts": [m.content]})
        
        q_embed = _embed_query(data.message)

        # Step 0: Structured/neurosymbolic reasoning (opt-in). Deterministic,
        # no extra LLM call — just parses the query into values/operations/
        # relationships/symbolic_expression before Gemini ever sees it. Done
        # before the cache check so it's populated even on a cache hit.
        neurosymbolic_info = None
        structured_block = None
        if data.use_neurosymbolic:
            detected, structured, structured_block = ns_process_query(data.message)
            neurosymbolic_info = {
                "detected_as_math_or_logic": detected,
                "structured": structured,
            }

        if data.use_cache:
            cached, similarity = semantic_cache.find_similar(q_embed, data.cache_threshold)
            if cached is not None:
                return {
                    "reply": cached.answer,
                    "sources": cached.sources,
                    "acw_metrics": cached.acw_metrics,
                    "risk_assessment": cached.risk_assessment,
                    "safety_report": cached.safety_report,
                    "recovery": cached.recovery,
                    "neurosymbolic": neurosymbolic_info,
                    "from_cache": True,
                    "cache_similarity": round(similarity, 4),
                }
            near_miss_similarity = round(similarity, 4)

        # Step 1: Retrieve from Pinecone
        raw_chunks = _retrieve_by_embedding(q_embed, top_k=3)

        risk_assessment = None
        safety_report = None
        recovery_info = None

        # Step 2: Pick a strategy — either exactly what the caller asked for
        # (default, backward-compatible with run_experiment.py / run_ablation.py)
        # or risk-driven, if use_risk_aware=True.
        if data.use_risk_aware:
            compression_level, risk_meta = _risk_scorer.select_compression_level(
                query=data.message,
                domain="numerical methods",
            )
            strategy = COMPRESSION_TO_STRATEGY.get(compression_level, "moderate")
            risk_assessment = risk_meta
        else:
            strategy = data.strategy or "moderate"

        # Step 3: ACW filters chunks
        selected_chunks, acw_metrics = adaptive_context_wrapper(
            query=data.message,
            chunks=raw_chunks,
            strategy=strategy,
            alpha=data.alpha,
            scoring_mode=data.scoring_mode or "hybrid",
        )

        if data.use_risk_aware:
            # Step 4: Semantic safety pre-check, BEFORE spending a Gemini call.
            # If compression dropped too many critical tokens (numbers, dates,
            # constraints), escalate to the next-fuller strategy immediately.
            is_safe, safety_meta = _safety_guard.validate_compression_safety(
                raw_chunks, selected_chunks, threshold=0.6
            )
            safety_report = safety_meta
            if not is_safe:
                fuller_strategies = _next_strategies_above(strategy)
                if fuller_strategies:
                    strategy = fuller_strategies[0]
                    selected_chunks, acw_metrics = adaptive_context_wrapper(
                        query=data.message,
                        chunks=raw_chunks,
                        strategy=strategy,
                        alpha=data.alpha,
                        scoring_mode=data.scoring_mode or "hybrid",
                    )

        # Step 5: Build context from selected chunks and generate the answer
        context = _build_context(selected_chunks)
        reply_text = _generate(data.message, context, history_payload, structured_block)

        # Step 6: Evaluate confidence and recover (retry with less compression)
        # if the answer looks weak. Bounded by max_recovery_attempts so a bad
        # query can't silently burn through your Gemini quota.
        if data.use_risk_aware:
            confidence, score, eval_meta = _recovery.evaluate_response_quality(
                data.message, reply_text, context
            )
            attempts = []
            ladder = _next_strategies_above(strategy)
            budget = max(0, data.max_recovery_attempts or 0)

            while _recovery.should_recover(confidence, score) and ladder and budget > 0:
                strategy = ladder.pop(0)
                selected_chunks, acw_metrics = adaptive_context_wrapper(
                    query=data.message,
                    chunks=raw_chunks,
                    strategy=strategy,
                    alpha=data.alpha,
                    scoring_mode=data.scoring_mode or "hybrid",
                )
                context = _build_context(selected_chunks)
                reply_text = _generate(data.message, context, history_payload, structured_block)
                confidence, score, eval_meta = _recovery.evaluate_response_quality(
                    data.message, reply_text, context
                )
                attempts.append({
                    "compression_level": strategy,
                    "confidence": confidence.name,
                    "score": round(score, 3),
                })
                budget -= 1
            abstained = _recovery.should_abstain(confidence, score)
            if abstained:
                reply_text = ABSTENTION_REPLY
            recovery_info = {
                "final_confidence": confidence.name,
                "final_score": round(score, 3),
                "recovery_attempts": attempts,
                "recovered": len(attempts) > 0,
                "abstained": abstained,
            }

        if data.use_cache and not (recovery_info and recovery_info.get("abstained")):
            semantic_cache.add(
                query=data.message,
                embedding=q_embed,
                answer=reply_text,
                sources=[c["title"] for c in selected_chunks],
                acw_metrics={
                    "strategy": strategy,
                    "chunks_retrieved": acw_metrics["chunks_retrieved"],
                    "chunks_selected": acw_metrics["chunks_selected"],
                    "tokens_before": acw_metrics["tokens_before"],
                    "tokens_after": acw_metrics["tokens_after"],
                    "token_reduction_pct": acw_metrics["token_reduction_pct"],
                    "scoring_mode": acw_metrics.get("scoring_mode"),
                    "alpha_used": acw_metrics.get("alpha_used"),
                },
                risk_assessment=risk_assessment,
                safety_report=safety_report,
                recovery=recovery_info,
            )

        return {
            "reply": reply_text,
            "neurosymbolic": neurosymbolic_info,
            "sources": [c["title"] for c in selected_chunks],
            "acw_metrics": {
                "strategy": strategy,
                "chunks_retrieved": acw_metrics["chunks_retrieved"],
                "chunks_selected": acw_metrics["chunks_selected"],
                "tokens_before": acw_metrics["tokens_before"],
                "tokens_after": acw_metrics["tokens_after"],
                "token_reduction_pct": acw_metrics["token_reduction_pct"],
                "scoring_mode": acw_metrics.get("scoring_mode"),
                "alpha_used": acw_metrics.get("alpha_used"),
            },
            "risk_assessment": risk_assessment,
            "safety_report": safety_report,
            "recovery": recovery_info,
            "from_cache": False,
            "cache_similarity": near_miss_similarity if data.use_cache else None,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/suggestions")
def suggestions():
    return {
        "suggestions": [
            "What's the difference between Bisection and Newton-Raphson?",
            "When should I use Simpson's 1/3 vs Simpson's 3/8?",
            "Why does RK4 give better accuracy than Euler's method?",
            "What's the difference between Doolittle and Crout?",
        ]
    }

"""
neurosymbolic_reasoning.py — Structured/Neurosymbolic Reasoning for ACW
=========================================================================

Detects math/numerical/logic queries and converts the relevant information
into a structured JSON representation (values, operation, relationships,
symbolic expression) BEFORE the query reaches Gemini.

This structured "symbolic scratchpad" is appended to the system prompt
alongside the ACW-selected context, so the LLM has an explicit, parsed
view of the numbers/operations/relationships in the query in addition to
its own free-text reasoning. This is the "neurosymbolic" part: a cheap,
deterministic symbolic parse (no extra LLM call) feeding a neural model.

The user still gets a normal natural-language answer. The structured
representation itself is never shown to the user — it is logged to
neurosymbolic_log.jsonl (same pattern as acw_log.jsonl) for offline
evaluation of whether structuring the query improves answer quality.

Place in: backend/modules/neurosymbolic_reasoning.py
"""

import json
import os
import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple

LOG_FILE = os.path.join(os.path.dirname(__file__), "..", "routers", "neurosymbolic_log.jsonl")
LOG_FILE = os.path.normpath(LOG_FILE)

# ─── Detection ────────────────────────────────────────────────────────────

# Numeric literals, e.g. 12, -3.5, 1e-3
_NUMBER_RE = re.compile(r"-?\d+\.?\d*(?:[eE][-+]?\d+)?")

# Arithmetic / comparison / logic operators worth flagging
_OPERATOR_PATTERNS = {
    "add": [r"\+", r"\bplus\b", r"\bsum\b", r"\badd(ed|s)?\b"],
    "subtract": [r"-", r"\bminus\b", r"\bsubtract(ed|s)?\b", r"\bdifference\b"],
    "multiply": [r"\*", r"\btimes\b", r"\bmultipl(y|ied|ies)\b", r"\bproduct\b"],
    "divide": [r"/", r"\bdivide[d]?\b", r"\bquotient\b", r"\bratio\b"],
    "power": [r"\^", r"\*\*", r"\bsquared\b", r"\bcubed\b", r"\bpower of\b", r"\bexponent\b"],
    "root": [r"\bsqrt\b", r"\bsquare root\b", r"\bcube root\b", r"√"],
    "equals": [r"=", r"\bequals?\b", r"\bis equal to\b"],
    "derivative": [r"\bderivative\b", r"\bdifferentiat(e|ion)\b", r"dy/dx", r"f'\("],
    "integral": [r"\bintegral\b", r"\bintegrat(e|ion)\b", r"∫"],
    "compare": [r"[<>]=?", r"\bgreater than\b", r"\bless than\b", r"\bat least\b", r"\bat most\b"],
    "root_find": [r"\broot(s)?\b", r"\bf\(x\)\s*=\s*0\b", r"\bzero(es)?\s+of\b"],
    "solve_system": [r"\bsystem of equations\b", r"\blinear system\b", r"Ax\s*=\s*b"],
}

# Relationship / connector words that indicate structure between values
_RELATIONSHIP_KEYWORDS = [
    "if", "then", "given", "such that", "where", "when", "and", "or",
    "greater than", "less than", "equal to", "between", "such that",
]

# Broad trigger list: if any of these show up (or 2+ numbers do), the query
# is considered "math/numerical/logic" and gets a structured extraction.
_TRIGGER_KEYWORDS = [
    "calculate", "compute", "solve", "evaluate", "find the value",
    "equation", "function", "derivative", "integral", "matrix",
    "interpolat", "root", "iteration", "converge", "error", "bisection",
    "newton", "raphson", "simpson", "trapezoidal", "runge", "kutta",
    "euler", "lu decomposition", "doolittle", "crout",
]


def is_math_or_logic_query(query: str) -> bool:
    """
    Cheap, deterministic classifier: True if the query looks like it needs
    numerical/symbolic reasoning (numbers + operators, or domain keywords).
    No LLM call — this must be fast enough to run on every request.
    """
    q = query.lower()

    if any(kw in q for kw in _TRIGGER_KEYWORDS):
        return True

    numbers = _NUMBER_RE.findall(query)
    has_operator = any(
        re.search(pat, q) for pats in _OPERATOR_PATTERNS.values() for pat in pats
    )

    # Two or more numeric values, or one number plus a clear operator/relation
    if len(numbers) >= 2:
        return True
    if len(numbers) >= 1 and has_operator:
        return True

    return False


# ─── Extraction ──────────────────────────────────────────────────────────

def _extract_values(query: str) -> List[float]:
    values = []
    for match in _NUMBER_RE.findall(query):
        try:
            values.append(float(match) if ("." in match or "e" in match.lower()) else int(match))
        except ValueError:
            continue
    return values


def _extract_operations(query: str) -> List[str]:
    q = query.lower()
    found = []
    for op_name, patterns in _OPERATOR_PATTERNS.items():
        for pat in patterns:
            if re.search(pat, q):
                found.append(op_name)
                break
    return found


def _extract_relationships(query: str) -> List[str]:
    q = query.lower()
    return [kw for kw in _RELATIONSHIP_KEYWORDS if kw in q]


def _extract_symbolic_expression(query: str) -> Optional[str]:
    """
    Best-effort extraction of an inline symbolic expression, e.g.
    "f(x) = x^2 - 4" -> "f(x) = x^2 - 4"
    "integrate x^2 from 0 to 1" -> left as None (no literal expression found)
    Looks for common math-expression shapes rather than trying to fully parse.
    """
    patterns = [
        r"[a-zA-Z]\(?[a-zA-Z]?\)?\s*=\s*[^,.;\n]+",       # f(x) = ...
        r"\b[a-zA-Z]\^?\d*(?:\s*[\+\-\*/]\s*[a-zA-Z0-9\^]+)+",  # x^2 - 4x + 3
        r"∫[^,.;\n]+",
        r"d[a-zA-Z]/d[a-zA-Z][^,.;\n]*",
    ]
    for pat in patterns:
        m = re.search(pat, query)
        if m:
            return m.group(0).strip()
    return None


def extract_structured_representation(query: str) -> Dict:
    """
    Convert a math/numerical/logic query into a structured dict:
      {
        "values": [...],
        "operations": [...],
        "relationships": [...],
        "symbolic_expression": str | None,
        "raw_query": str
      }
    """
    return {
        "values": _extract_values(query),
        "operations": _extract_operations(query),
        "relationships": _extract_relationships(query),
        "symbolic_expression": _extract_symbolic_expression(query),
        "raw_query": query,
    }


# ─── Prompt injection helper ────────────────────────────────────────────

def build_structured_context_block(structured: Dict) -> str:
    """
    Render the structured representation as a compact block to append to
    the system prompt, alongside the ACW-selected retrieval context. Kept
    short and explicit so the LLM can use it as a symbolic scratchpad
    instead of re-deriving values from the free-text question.
    """
    lines = ["Structured problem representation (for internal reasoning; "
             "do not repeat this block verbatim to the user):"]
    if structured["values"]:
        lines.append(f"  values: {structured['values']}")
    if structured["operations"]:
        lines.append(f"  operations: {structured['operations']}")
    if structured["relationships"]:
        lines.append(f"  relationships: {structured['relationships']}")
    if structured["symbolic_expression"]:
        lines.append(f"  symbolic_expression: {structured['symbolic_expression']}")
    return "\n".join(lines)


# ─── Logging (for evaluation, never shown to the user) ──────────────────

def log_structured_representation(query: str, structured: Dict, detected: bool):
    """Append one JSON line to neurosymbolic_log.jsonl for offline evaluation."""
    record = {
        "timestamp": datetime.utcnow().isoformat(),
        "query": query,
        "detected_as_math_or_logic": detected,
        "structured": structured,
    }
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")
    except Exception:
        pass  # Never crash the chatbot over logging


# ─── Main entry point ────────────────────────────────────────────────────

def process_query(query: str, log: bool = True) -> Tuple[bool, Optional[Dict], Optional[str]]:
    """
    Run detection + extraction for a single query.

    Returns:
        (detected, structured | None, context_block | None)

        detected:      True if this query was classified as math/numerical/logic
        structured:    the structured dict (None if not detected)
        context_block: prompt-ready text block to append to the system prompt
                        (None if not detected)
    """
    detected = is_math_or_logic_query(query)
    structured = extract_structured_representation(query) if detected else None
    context_block = build_structured_context_block(structured) if structured else None

    if log:
        log_structured_representation(query, structured or {}, detected)

    return detected, structured, context_block


if __name__ == "__main__":
    tests = [
        "What is 12 + 7 * 3?",
        "Find the root of f(x) = x^2 - 4 using Newton-Raphson starting at x0=3",
        "Explain the difference between Bisection and Newton-Raphson.",
        "Integrate x^2 from 0 to 1 using Simpson's 1/3 rule with h=0.1",
        "What's the difference between Doolittle and Crout?",
    ]
    for q in tests:
        detected, structured, block = process_query(q, log=False)
        print(f"\nQuery: {q}")
        print(f"Detected: {detected}")
        if structured:
            print(json.dumps(structured, indent=2))

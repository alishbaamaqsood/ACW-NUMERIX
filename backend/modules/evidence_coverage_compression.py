
import re
import math
from typing import Dict, List, Tuple, Set
from enum import Enum


class CoverageLevel(Enum):
    """How well the selected chunks cover the query's requirements."""
    FULL = "FULL"              # every requirement covered
    PARTIAL = "PARTIAL"        # some requirements covered, some not
    NONE = "NONE"              # nothing covered (bad retrieval / off-topic)


# Words that carry no evidence-requirement signal on their own.
STOPWORDS = {
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
    "do", "does", "did", "of", "in", "on", "at", "to", "for", "with",
    "and", "or", "but", "if", "so", "than", "then", "this", "that",
    "these", "those", "it", "its", "as", "by", "from", "into", "about",
    "what", "when", "where", "which", "who", "whom", "how", "why",
    "can", "could", "should", "would", "will", "shall", "may", "might",
    "i", "you", "he", "she", "we", "they", "me", "him", "her", "us",
    "them", "my", "your", "his", "their", "our", "please", "explain",
    "tell", "give", "show", "describe",
}

# Query-level separators that usually mark a NEW requirement:
#  - explicit conjunctions joining two asks ("X and Y", "X or Y")
#  - "vs"/"versus"/"compared to" (comparison => two requirements)
#  - semicolons, numbered/bulleted list markers, and multiple "?"
_REQUIREMENT_SPLIT_PATTERN = re.compile(
    r"\s*(?:\band\b|\bor\b|\bvs\.?\b|\bversus\b|\bcompared to\b|;|\n|"
    r"(?<=\?)\s+|(?=\b\d+[\.\)]\s))\s*",
    re.IGNORECASE,
)


def _tokenize(text: str) -> List[str]:
    """Lowercase word tokenizer, strips punctuation."""
    return re.findall(r"[a-zA-Z][a-zA-Z0-9\-]*", text.lower())


def _keywords(text: str) -> Set[str]:
    """Extract meaningful (non-stopword) keywords from a piece of text.

    Includes a light singular/plural normalization (trailing 's') so
    "constraint" and "constraints" count as the same evidence signal.
    """
    words = _tokenize(text)
    kws = set()
    for w in words:
        if len(w) <= 2 or w in STOPWORDS:
            continue
        normalized = w[:-1] if w.endswith("s") and len(w) > 3 else w
        kws.add(normalized)
    return kws


def count_tokens(text: str) -> int:
    """Same approximate token counter used in acw.py, kept consistent
    so tokens_before/tokens_after numbers are directly comparable across
    the team's modules and the research logs."""
    words = len(text.split())
    return math.ceil(words / 0.75)


def split_requirements(query: str) -> List[Dict]:
    """
    Break a query into distinct evidence requirements.

    Returns a list of requirement dicts:
        { "text": "<the requirement's own text>", "keywords": {set of str} }

    If the query doesn't split into multiple clear parts (a single simple
    question), it falls back to ONE requirement containing the whole
    query's keywords — this makes the module a safe drop-in even for
    simple queries: coverage collapses to "does at least one chunk
    contain the query's own keywords", which is a sane baseline.
    """
    raw_parts = [p.strip() for p in _REQUIREMENT_SPLIT_PATTERN.split(query) if p.strip()]

    # Merge accidental 1-2 word fragments (e.g. a lone "or") back into
    # the previous requirement instead of treating them as their own.
    parts: List[str] = []
    for part in raw_parts:
        if parts and len(part.split()) <= 2:
            parts[-1] = f"{parts[-1]} {part}"
        else:
            parts.append(part)

    if not parts:
        parts = [query]

    requirements = []
    for part in parts:
        kws = _keywords(part)
        if kws:
            requirements.append({"text": part, "keywords": kws})

    # Total fallback: query had content but nothing survived stopword
    # filtering (e.g. "What is it?") — keep one empty-keyword requirement
    # so the rest of the pipeline degrades gracefully instead of crashing.
    if not requirements:
        requirements = [{"text": query, "keywords": set()}]

    return requirements


def _chunk_keywords(chunk: Dict) -> Set[str]:
    title = chunk.get("title", "")
    content = chunk.get("content", "")
    return _keywords(f"{title} {content}")


def _requirement_coverage(requirement_kws: Set[str], chunk_kws: Set[str]) -> float:
    """
    Fraction of a requirement's keywords found in a chunk.
    Empty requirement keyword sets are treated as trivially uncoverable
    (0.0) rather than divide-by-zero.
    """
    if not requirement_kws:
        return 0.0
    overlap = requirement_kws & chunk_kws
    return len(overlap) / len(requirement_kws)


class EvidenceCoverageCompression:
    """
    Selects a compact, evidence-covering set of chunks for a query.

    COVERAGE_THRESHOLD: a requirement counts as "covered" by a chunk once
    at least this fraction of the requirement's keywords appear in that
    chunk. 0.34 means: for a 3-keyword requirement, 1 matching keyword is
    enough; for a 2-keyword requirement, both are effectively required
    (1/2 = 0.5 clears it, 0/2 doesn't) — deliberately lenient for short
    requirements, stricter as requirements get more specific.
    """

    COVERAGE_THRESHOLD = 0.34

    def __init__(self, coverage_threshold: float = None):
        self.coverage_threshold = coverage_threshold or self.COVERAGE_THRESHOLD

    def analyze_requirements(self, query: str) -> List[Dict]:
        """Public wrapper so callers/tests can inspect the split without
        running full selection."""
        return split_requirements(query)

    def select(
        self,
        query: str,
        chunks: List[Dict],
        k: int = 2,
        token_budget: int = 400,
        relevance_scores: Dict[str, float] = None,
    ) -> Tuple[List[Dict], Dict]:
        """
        Greedy evidence-coverage selection.

        Args:
            query:            the user's question
            chunks:           list of dicts with at least {id, title, content};
                               a "score" key (Pinecone cosine similarity) is
                               used as a fallback ranking signal if present.
            k:                max chunks to select (Top-1/Top-2, matching
                               acw.py's "moderate"/"aggressive" strategies).
            token_budget:     max total tokens across selected chunks.
            relevance_scores: optional override map {chunk_id: score} — lets
                               this plug in downstream of acw.py's hybrid
                               (cosine + density) score instead of raw
                               Pinecone score, if the caller wants that.

        Returns:
            (selected_chunks, metrics)
        """
        requirements = split_requirements(query)
        n_reqs = len(requirements)

        all_text = "\n\n".join(f"[{c.get('title','')}]\n{c.get('content','')}" for c in chunks)
        tokens_before = count_tokens(all_text)

        # Precompute: which requirements each chunk covers, and its
        # fallback relevance score.
        chunk_coverage: Dict[int, Set[int]] = {}
        chunk_relevance: Dict[int, float] = {}
        for idx, chunk in enumerate(chunks):
            c_kws = _chunk_keywords(chunk)
            covered = set()
            for r_idx, req in enumerate(requirements):
                if _requirement_coverage(req["keywords"], c_kws) >= self.coverage_threshold:
                    covered.add(r_idx)
            chunk_coverage[idx] = covered

            if relevance_scores is not None and chunk.get("id") in relevance_scores:
                chunk_relevance[idx] = relevance_scores[chunk["id"]]
            else:
                chunk_relevance[idx] = chunk.get("score", 0.0)

        selected_idx: List[int] = []
        uncovered = set(range(n_reqs))
        total_tokens = 0
        coverage_trace = []  # per-selection debug/research trail

        remaining = set(range(len(chunks)))

        # ── Greedy weighted set-cover ────────────────────────────────────
        while remaining and len(selected_idx) < k and uncovered:
            best_idx = None
            best_gain = -1
            best_relevance = -1.0
            for idx in remaining:
                gain = len(chunk_coverage[idx] & uncovered)
                relevance = chunk_relevance[idx]
                if gain > best_gain or (gain == best_gain and relevance > best_relevance):
                    best_idx, best_gain, best_relevance = idx, gain, relevance

            if best_idx is None or best_gain == 0:
                break  # no remaining chunk adds new coverage

            chunk_tokens = count_tokens(chunks[best_idx].get("content", ""))
            if total_tokens + chunk_tokens > token_budget and selected_idx:
                # Budget would be blown and we already have something —
                # stop here rather than exceeding TOKEN_BUDGET.
                break

            selected_idx.append(best_idx)
            remaining.discard(best_idx)
            newly_covered = chunk_coverage[best_idx] & uncovered
            uncovered -= newly_covered
            total_tokens += chunk_tokens
            coverage_trace.append({
                "chunk_id": chunks[best_idx].get("id"),
                "title": chunks[best_idx].get("title"),
                "newly_covered_requirements": sorted(newly_covered),
                "relevance_score": round(best_relevance, 4),
            })

        # ── Backstop: if requirements remain uncovered (or none existed)
        # and we still have room, fill remaining Top-K slots by raw
        # relevance so this never selects FEWER chunks than acw.py would
        # for the same strategy — evidence-coverage narrows/reorders the
        # choice, it doesn't starve the model of context.
        if len(selected_idx) < k and remaining:
            by_relevance = sorted(remaining, key=lambda i: chunk_relevance[i], reverse=True)
            for idx in by_relevance:
                if len(selected_idx) >= k:
                    break
                chunk_tokens = count_tokens(chunks[idx].get("content", ""))
                if total_tokens + chunk_tokens > token_budget and selected_idx:
                    continue
                selected_idx.append(idx)
                total_tokens += chunk_tokens
                coverage_trace.append({
                    "chunk_id": chunks[idx].get("id"),
                    "title": chunks[idx].get("title"),
                    "newly_covered_requirements": sorted(chunk_coverage[idx] & uncovered),
                    "relevance_score": round(chunk_relevance[idx], 4),
                })
                uncovered -= chunk_coverage[idx]

        # Absolute fallback: nothing selected at all (e.g. empty chunks
        # list never reaches here, but a zero-token_budget edge case might)
        if not selected_idx and chunks:
            selected_idx = [max(range(len(chunks)), key=lambda i: chunk_relevance[i])]
            total_tokens = count_tokens(chunks[selected_idx[0]].get("content", ""))

        selected_chunks = [chunks[i] for i in selected_idx]

        tokens_after = count_tokens(
            "\n\n".join(f"[{c.get('title','')}]\n{c.get('content','')}" for c in selected_chunks)
        )
        reduction = round((1 - tokens_after / tokens_before) * 100, 2) if tokens_before > 0 else 0.0

        covered_count = n_reqs - len(uncovered)
        coverage_ratio = round(covered_count / n_reqs, 4) if n_reqs else 1.0

        if n_reqs == 0 or covered_count == n_reqs:
            coverage_level = CoverageLevel.FULL if selected_chunks else CoverageLevel.NONE
        elif covered_count == 0:
            coverage_level = CoverageLevel.NONE
        else:
            coverage_level = CoverageLevel.PARTIAL

        metrics = {
            "requirements_identified": [r["text"] for r in requirements],
            "requirements_count": n_reqs,
            "covered_requirements": sorted(set(range(n_reqs)) - uncovered),
            "uncovered_requirements": sorted(uncovered),
            "uncovered_requirement_texts": [requirements[i]["text"] for i in sorted(uncovered)],
            "coverage_ratio": coverage_ratio,
            "coverage_level": coverage_level.value,
            "fully_covered": coverage_level == CoverageLevel.FULL,
            "chunks_retrieved": len(chunks),
            "chunks_selected": len(selected_chunks),
            "selected_titles": [c.get("title") for c in selected_chunks],
            "selection_trace": coverage_trace,
            "tokens_before": tokens_before,
            "tokens_after": tokens_after,
            "token_reduction_pct": reduction,
        }

        return selected_chunks, metrics


# Module-level convenience function, mirroring acw.py's functional style
# (adaptive_context_wrapper) so it's a drop-in alternative call in
# chatbot.py / run_experiment.py / run_ablation.py.
_default_ecc = EvidenceCoverageCompression()


def evidence_coverage_compression(
    query: str,
    chunks: List[Dict],
    k: int = 2,
    token_budget: int = 400,
    relevance_scores: Dict[str, float] = None,
) -> Tuple[List[Dict], Dict]:
    """Functional wrapper around EvidenceCoverageCompression().select()."""
    return _default_ecc.select(
        query=query,
        chunks=chunks,
        k=k,
        token_budget=token_budget,
        relevance_scores=relevance_scores,
    )


# Example usage / quick manual test
if __name__ == "__main__":
    demo_chunks = [
        {
            "id": "rootfinder",
            "title": "Root Finder (Labs 4-5)",
            "content": (
                "Newton-Raphson needs f(x), its derivative f'(x), and an "
                "initial guess x0, and converges quadratically near the root."
            ),
            "score": 0.81,
        },
        {
            "id": "rootfinder-pitfalls",
            "title": "Root Finder Pitfalls",
            "content": (
                "Newton-Raphson can diverge or fail if the initial guess is "
                "far from the root, or if f'(x) is close to zero near x0, "
                "causing overflow in the next iterate."
            ),
            "score": 0.62,
        },
        {
            "id": "interpolation",
            "title": "Interpolator (Labs 6-7)",
            "content": (
                "Lagrange Interpolation works for unequally spaced points "
                "and does not require solving a linear system."
            ),
            "score": 0.30,
        },
    ]

    query = "What is Newton-Raphson and when does it diverge?"
    ecc = EvidenceCoverageCompression()
    selected, metrics = ecc.select(query, demo_chunks, k=2, token_budget=400)

    print(f"\nQuery: {query}")
    print(f"Requirements identified: {metrics['requirements_identified']}")
    print(f"Coverage: {metrics['coverage_level']} ({metrics['coverage_ratio']*100:.0f}%)")
    print(f"Selected: {metrics['selected_titles']}")
    print(f"Uncovered: {metrics['uncovered_requirement_texts']}")
    print(f"Token reduction: {metrics['token_reduction_pct']}%")
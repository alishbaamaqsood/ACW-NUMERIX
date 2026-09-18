"""
Semantic Response Cache
------------------------
Caches (query_embedding, answer, chunks_used) tuples from previous /ask
calls. Before spending a Gemini generation call on a new query, checks
whether the new query's embedding is highly similar (cosine similarity
>= threshold, default 0.95) to a cached query. If so, the cached answer
is returned instantly: zero tokens, zero latency, zero Gemini call.

This is a *different* savings lever from ACW: ACW reduces tokens spent
PER call; this cache reduces the NUMBER of calls made at all. The two
are complementary, not overlapping.

Design notes:
  - In-memory list + JSONL persistence (mirrors routers/acw_log.jsonl),
    so the cache is inspectable and survives a backend restart.
  - Linear-scan cosine similarity. Fine at FAQ scale (dozens to a few
    hundred distinct questions) -- if it ever needs to scale further,
    swap in a proper ANN index (Pinecone is already in this project).
  - OFF by default on /ask. run_experiment.py / run_ablation.py /
    answer_quality.py deliberately replay the SAME query set across
    different strategies/configs to get a fair per-strategy
    measurement. If caching were on by default, the 2nd+ strategy run
    for a given query would silently return the 1st strategy's cached
    answer and corrupt the comparison. Enable per-request in the
    frontend chatbot with `use_cache: true`.
"""

import json
import math
import os
import time
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

# Lives next to acw_log.jsonl under routers/, so both logs are in one place.
CACHE_LOG_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "routers",
    "semantic_cache.jsonl",
)

DEFAULT_SIMILARITY_THRESHOLD = 0.95


@dataclass
class CacheEntry:
    query: str
    embedding: List[float]
    answer: str
    sources: List[str]
    acw_metrics: dict
    risk_assessment: Optional[dict] = None
    safety_report: Optional[dict] = None
    recovery: Optional[dict] = None
    created_at: float = field(default_factory=time.time)
    hits: int = 0


def _cosine_similarity(a: List[float], b: List[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


class SemanticResponseCache:
    def __init__(
        self,
        threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
        persist: bool = True,
        log_path: str = CACHE_LOG_PATH,
    ):
        self.threshold = threshold
        self.persist = persist
        self.log_path = log_path
        self._entries: List[CacheEntry] = []
        if self.persist:
            self._load()

    def _load(self):
        if not os.path.exists(self.log_path):
            return
        try:
            with open(self.log_path, "r") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    d = json.loads(line)
                    self._entries.append(
                        CacheEntry(
                            query=d["query"],
                            embedding=d["embedding"],
                            answer=d["answer"],
                            sources=d.get("sources", []),
                            acw_metrics=d.get("acw_metrics", {}),
                            risk_assessment=d.get("risk_assessment"),
                            safety_report=d.get("safety_report"),
                            recovery=d.get("recovery"),
                            created_at=d.get("created_at", time.time()),
                            hits=d.get("hits", 0),
                        )
                    )
        except (IOError, json.JSONDecodeError, KeyError):
            # A corrupt/partial cache file shouldn't take the backend down --
            # just start with an empty cache.
            pass

    def _append_to_log(self, entry: CacheEntry):
        if not self.persist:
            return
        try:
            os.makedirs(os.path.dirname(self.log_path), exist_ok=True)
            with open(self.log_path, "a") as f:
                f.write(
                    json.dumps(
                        {
                            "query": entry.query,
                            "embedding": entry.embedding,
                            "answer": entry.answer,
                            "sources": entry.sources,
                            "acw_metrics": entry.acw_metrics,
                            "risk_assessment": entry.risk_assessment,
                            "safety_report": entry.safety_report,
                            "recovery": entry.recovery,
                            "created_at": entry.created_at,
                            "hits": entry.hits,
                        }
                    )
                    + "\n"
                )
        except IOError:
            pass

    def find_similar(self, embedding: List[float], threshold: Optional[float] = None) -> Tuple[Optional[CacheEntry], float]:
        """Returns (best_matching_entry_or_None, best_similarity_score)."""
        threshold = self.threshold if threshold is None else threshold
        best_entry = None
        best_score = 0.0
        for entry in self._entries:
            score = _cosine_similarity(embedding, entry.embedding)
            if score > best_score:
                best_score = score
                best_entry = entry
        if best_entry is not None and best_score >= threshold:
            best_entry.hits += 1
            return best_entry, best_score
        return None, best_score

    def add(
        self,
        query: str,
        embedding: List[float],
        answer: str,
        sources: List[str],
        acw_metrics: dict,
        risk_assessment: Optional[dict] = None,
        safety_report: Optional[dict] = None,
        recovery: Optional[dict] = None,
    ):
        entry = CacheEntry(
            query=query,
            embedding=embedding,
            answer=answer,
            sources=sources,
            acw_metrics=acw_metrics,
            risk_assessment=risk_assessment,
            safety_report=safety_report,
            recovery=recovery,
        )
        self._entries.append(entry)
        self._append_to_log(entry)

    def stats(self) -> dict:
        return {
            "cached_queries": len(self._entries),
            "total_hits": sum(e.hits for e in self._entries),
            "threshold": self.threshold,
        }


# Singleton reused across requests -- same pattern as _risk_scorer /
# _safety_guard / _recovery in routers/chatbot.py.
semantic_cache = SemanticResponseCache()
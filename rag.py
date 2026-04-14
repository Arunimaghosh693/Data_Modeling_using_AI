from __future__ import annotations

from typing import List

import numpy as np

try:
    import faiss
except ImportError:  # pragma: no cover - demo can still run with keyword fallback
    faiss = None

try:
    from sentence_transformers import SentenceTransformer
except ImportError:  # pragma: no cover - demo can still run with keyword fallback
    SentenceTransformer = None


KNOWLEDGE_BASE = [
    "Customer is a business party who can own one or more accounts.",
    "An account belongs to exactly one customer in the standard retail banking model.",
    "A transaction records the movement of funds on an account.",
    "Conceptual modeling should focus on business entities and relationships, not physical columns.",
    "Logical modeling introduces primary keys, foreign keys, and normalization guidance.",
    "Common relationship patterns include 1:1, 1:N, and M:N cardinality.",
    "SME validation is required before the conceptual model is promoted to logical design.",
]


_model = None
_index = None
_embeddings = None


def _build_vector_store() -> None:
    global _model, _index, _embeddings
    if SentenceTransformer is None or faiss is None or _index is not None:
        return

    _model = SentenceTransformer("all-MiniLM-L6-v2")
    _embeddings = np.array(_model.encode(KNOWLEDGE_BASE))
    _index = faiss.IndexFlatL2(_embeddings.shape[1])
    _index.add(_embeddings)


def _keyword_fallback(query: str, k: int) -> List[str]:
    query_terms = set(query.lower().split())
    scored = []
    for item in KNOWLEDGE_BASE:
        item_terms = set(item.lower().split())
        overlap = len(query_terms.intersection(item_terms))
        scored.append((overlap, item))
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [item for _, item in scored[:k]]


def get_relevant_context(query: str, k: int = 3) -> str:
    _build_vector_store()

    if _index is not None and _model is not None:
        query_embedding = np.array(_model.encode([query]))
        _, indices = _index.search(query_embedding, k)
        results = [KNOWLEDGE_BASE[i] for i in indices[0]]
    else:
        results = _keyword_fallback(query, k)

    return "\n".join(results)

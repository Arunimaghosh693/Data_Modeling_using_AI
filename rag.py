from __future__ import annotations

import logging
import re
from typing import List

import numpy as np

try:
    from core_banking_glossary_knowledge_base import CORE_BANKING_GLOSSARY_KNOWLEDGE_BASE
except ImportError:  # pragma: no cover - supports package-style imports
    from .core_banking_glossary_knowledge_base import CORE_BANKING_GLOSSARY_KNOWLEDGE_BASE

try:
    import faiss
except ImportError:  # pragma: no cover - demo can still run with keyword fallback
    faiss = None

try:
    from sentence_transformers import SentenceTransformer
except ImportError:  # pragma: no cover - demo can still run with keyword fallback
    SentenceTransformer = None

#editd by mani
KNOWLEDGE_BASE = CORE_BANKING_GLOSSARY_KNOWLEDGE_BASE

logger = logging.getLogger(__name__)

_model = None
_index = None
_embeddings = None


def _tokenize(text: str) -> List[str]:
    return re.findall(r"[a-z0-9]+", text.lower().replace("_", " "))


def _build_vector_store() -> None:
    global _model, _index, _embeddings
    if SentenceTransformer is None or faiss is None or _index is not None:
        return

    _model = SentenceTransformer("all-MiniLM-L6-v2")
    _embeddings = np.array(_model.encode(KNOWLEDGE_BASE))
    _index = faiss.IndexFlatL2(_embeddings.shape[1])
    _index.add(_embeddings)


#editd by mani
def warm_rag() -> None:
    try:
        _build_vector_store()
    except Exception as exc:  # pragma: no cover - app can still run with keyword fallback
        logger.warning("RAG warmup skipped: %s", exc)


def _keyword_fallback(query: str, k: int) -> List[str]:
    query_terms = set(_tokenize(query))
    scored = []
    for item in KNOWLEDGE_BASE:
        item_terms = set(_tokenize(item))
        overlap = len(query_terms.intersection(item_terms))
        scored.append((overlap, item))
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [item for _, item in scored[:k]]


def get_relevant_context(query: str, k: int = 3) -> str:
    _build_vector_store()

    if _index is not None and _model is not None:
        query_embedding = np.array(_model.encode([query]))
        _, indices = _index.search(query_embedding, k)
        semantic_results = [KNOWLEDGE_BASE[i] for i in indices[0]]
        keyword_results = _keyword_fallback(query, k)
        results = []
        for item in keyword_results + semantic_results:
            if item not in results:
                results.append(item)
        results = results[:k]
    else:
        results = _keyword_fallback(query, k)

    return "\n".join(results)

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

try:
    import faiss
except ImportError:  # pragma: no cover
    faiss = None

try:
    from sentence_transformers import SentenceTransformer
except ImportError:  # pragma: no cover
    SentenceTransformer = None

try:
    from langchain_google_genai import ChatGoogleGenerativeAI
except ImportError:  # pragma: no cover
    ChatGoogleGenerativeAI = None

try:
    from config import get_analytics_glossary_json_path, get_gemini_api_key, get_gemini_model
    from prompts import get_analytics_prompt
    from schemas import AnalyticsGlossaryDocument, AnalyticsLLMSelection, AnalyticsOutputMatch, AnalyticsResponse
except ImportError:  # pragma: no cover
    from .config import get_analytics_glossary_json_path, get_gemini_api_key, get_gemini_model
    from .prompts import get_analytics_prompt
    from .schemas import AnalyticsGlossaryDocument, AnalyticsLLMSelection, AnalyticsOutputMatch, AnalyticsResponse


logger = logging.getLogger(__name__)

ANALYTICS_TOP_K = 10
LLM_TOP_K = 5
MIN_VECTOR_SIMILARITY = 0.40
PREVIEW_VECTOR_SIMILARITY = 0.40
MIN_MEANINGFUL_SCORE = 12.0
MDA_WIN_MARGIN = 2.5
CDA_WIN_MARGIN = 6.0
BEST_MATCH_PROMOTION_MARGIN = 5.0
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"
INDEX_VERSION = "poc-v4"
LAYER_ORDER = ("gda", "mda", "cda")
REGION_TOKENS = {"uk", "eu", "hk"}
NO_MATCH_ANSWER = "We dont find any suitable response pls connect with source team."
CDA_APPROVAL_MESSAGE = (
    "No suitable response was found in GDA or MDA. "
    "CDA layer may contain possible matches. Please approve CDA fallback to continue."
)
GLOSSARY_PATHS = [
    Path(__file__).with_name("Business_Glossary_Output.json"),
    Path(__file__).with_name("DATA") / "Business_Glossary_Output.json",
    Path(r"C:\Users\pilla\Desktop\HSBC_DATA_POC\DATA\Business_Glossary_Output.json"),
]

_analytics_index: "AnalyticsIndex | None" = None
_embedding_model = None


@dataclass
class AttributeRecord:
    doc_id: str
    entityname: str
    layer: str
    layer_key: str
    physical_region: str
    region_key: str
    attribute: str
    attribute_key: str
    family: str
    group: str | None
    group_key: str
    attribute_description: str
    entity_description: str
    search_text: str


@dataclass
class AnalyticsIndex:
    attributes: list[AttributeRecord]
    faiss_index: Any | None


@dataclass
class CandidateMatch:
    position: int
    score: float
    exact_match: bool = False


@dataclass
class QueryMeta:
    focus_name: str
    attribute_hints: list[str]
    layer_filters: set[str]
    region_filters: set[str]


def _normalize_text(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", (text or "").lower()).strip("_")


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", (text or "").lower().replace("_", " "))


def _extract_attribute_hints(*texts: str) -> list[str]:
    hints: list[str] = []
    pattern = r"[A-Za-z][A-Za-z0-9]*(?:_[A-Za-z0-9]+)+"
    for text in texts:
        for match in re.finditer(pattern, text or ""):
            value = _normalize_text(match.group(0))
            if value and value not in hints:
                hints.append(value)
    return hints


def _attribute_family(attribute_key: str) -> str:
    return re.sub(r"(?:_\d+|\d+)+$", "", attribute_key or "").strip("_")


def _name_similarity(left: str, right: str) -> float:
    if not left or not right:
        return 0.0
    return SequenceMatcher(None, left, right).ratio()


def _resolve_query(query: str, user_context: str) -> str:
    query_text = (query or "").strip()
    context_text = (user_context or "").strip()
    if query_text.lower() in {"", "string", "query"} and context_text:
        return context_text
    return query_text


def _build_query_meta(query: str, user_context: str) -> QueryMeta:
    text = " ".join(part for part in [query, user_context] if part)
    tokens = set(_tokenize(text))
    attribute_hints = _extract_attribute_hints(query, user_context)
    return QueryMeta(
        focus_name=attribute_hints[0] if attribute_hints else _normalize_text(query),
        attribute_hints=attribute_hints,
        layer_filters=tokens.intersection(set(LAYER_ORDER)),
        region_filters=tokens.intersection(REGION_TOKENS),
    )


def _resolve_glossary_path() -> Path:
    configured = get_analytics_glossary_json_path()
    paths = [Path(configured)] if configured else []
    paths.extend(GLOSSARY_PATHS)
    for path in paths:
        if path.exists():
            return path
    searched = ", ".join(str(path) for path in paths)
    raise FileNotFoundError(
        "Analytics glossary JSON file not found. "
        f"Set ANALYTICS_GLOSSARY_JSON_PATH or place the file in one of: {searched}"
    )


def _get_embedding_model():
    global _embedding_model
    if faiss is None or SentenceTransformer is None:
        return None
    if _embedding_model is None:
        _embedding_model = SentenceTransformer(EMBEDDING_MODEL_NAME)
    return _embedding_model


def _get_llm_client():
    api_key = get_gemini_api_key()
    if not api_key or ChatGoogleGenerativeAI is None:
        return None
    return ChatGoogleGenerativeAI(
        model=get_gemini_model(),
        google_api_key=api_key,
        temperature=0,
        max_retries=0,
        timeout=30,
    )


def _load_attributes() -> tuple[Path, list[AttributeRecord]]:
    source_path = _resolve_glossary_path()
    raw_data = json.loads(source_path.read_text(encoding="utf-8"))
    if not isinstance(raw_data, list):
        raise ValueError("Analytics glossary JSON must contain a top-level list.")

    attributes: list[AttributeRecord] = []
    seen_doc_ids: set[str] = set()

    for item in raw_data:
        if not isinstance(item, dict):
            continue

        try:
            document = AnalyticsGlossaryDocument.model_validate(item)
        except Exception as exc:
            logger.warning("Skipping invalid analytics row: %s", exc)
            continue

        if document.doc_type != "entity":
            continue

        layer_key = document.metadata.layer_normalized or _normalize_text(document.layer)
        physical_region = document.metadata.physical_region or ""
        entity_description = document.content.entity_description or ""

        for attribute in document.attributes:
            if not attribute.doc_id or attribute.doc_id in seen_doc_ids:
                continue

            seen_doc_ids.add(attribute.doc_id)
            attribute_key = attribute.attribute_normalized or _normalize_text(attribute.attribute)
            attributes.append(
                AttributeRecord(
                    doc_id=attribute.doc_id,
                    entityname=document.entityname,
                    layer=document.layer,
                    layer_key=layer_key,
                    physical_region=physical_region,
                    region_key=_normalize_text(physical_region),
                    attribute=attribute.attribute,
                    attribute_key=attribute_key,
                    family=attribute.family or _attribute_family(attribute_key),
                    group=attribute.group,
                    group_key=attribute.group_normalized or _normalize_text(attribute.group or ""),
                    attribute_description=attribute.attribute_description or "",
                    entity_description=entity_description,
                    search_text=attribute.search_text or "",
                )
            )

    if not attributes:
        raise ValueError("Analytics glossary JSON did not contain any usable attributes.")

    return source_path, attributes


def _store_embeddings(source_path: Path, attributes: list[AttributeRecord]):
    model = _get_embedding_model()
    if model is None or faiss is None or not attributes:
        return None

    index_path = source_path.with_name(f"{source_path.stem}.attribute.faiss")
    meta_path = source_path.with_name(f"{source_path.stem}.attribute.faiss.meta.json")
    texts = [
        " ".join(
            part
            for part in [
                attribute.entityname,
                attribute.layer,
                attribute.physical_region,
                attribute.attribute,
                attribute.group or "",
                attribute.family,
                attribute.attribute_description,
                attribute.entity_description,
                attribute.search_text,
            ]
            if part
        )
        for attribute in attributes
    ]

    if index_path.exists() and meta_path.exists():
        try:
            metadata = json.loads(meta_path.read_text(encoding="utf-8"))
            stat = source_path.stat()
            if (
                metadata.get("source_path") == str(source_path)
                and metadata.get("source_mtime_ns") == stat.st_mtime_ns
                and metadata.get("item_count") == len(texts)
                and metadata.get("model_name") == EMBEDDING_MODEL_NAME
                and metadata.get("index_version") == INDEX_VERSION
            ):
                return faiss.read_index(str(index_path))
        except Exception as exc:  # pragma: no cover
            logger.warning("Could not load saved analytics FAISS index: %s", exc)

    embeddings = model.encode(texts, convert_to_numpy=True, normalize_embeddings=True).astype("float32")
    index = faiss.IndexFlatIP(embeddings.shape[1])
    index.add(embeddings)

    try:
        faiss.write_index(index, str(index_path))
        meta_path.write_text(
            json.dumps(
                {
                    "source_path": str(source_path),
                    "source_mtime_ns": source_path.stat().st_mtime_ns,
                    "item_count": len(texts),
                    "model_name": EMBEDDING_MODEL_NAME,
                    "index_version": INDEX_VERSION,
                },
                indent=2,
            ),
            encoding="utf-8",
        )
    except Exception as exc:  # pragma: no cover
        logger.warning("Could not save analytics FAISS index: %s", exc)

    return index


def _get_index() -> AnalyticsIndex:
    global _analytics_index
    if _analytics_index is None:
        source_path, attributes = _load_attributes()
        _analytics_index = AnalyticsIndex(attributes=attributes, faiss_index=_store_embeddings(source_path, attributes))
    return _analytics_index


def warm_analytics_index() -> None:
    _get_index()


def retrieve_analytics_candidates(
    query: str,
    user_context: str = "",
    top_k: int = ANALYTICS_TOP_K,
    forced_layer: str = "",
    allow_exact_match: bool = True,
    min_similarity: float = MIN_VECTOR_SIMILARITY,
) -> list[CandidateMatch]:
    index = _get_index()
    meta = _build_query_meta(query, user_context)

    if allow_exact_match and meta.attribute_hints:
        exact_matches = []
        for position, attribute in enumerate(index.attributes):
            if attribute.attribute_key not in meta.attribute_hints:
                continue
            if meta.layer_filters and attribute.layer_key not in meta.layer_filters:
                continue
            if meta.region_filters and attribute.region_key not in meta.region_filters:
                continue
            exact_matches.append(CandidateMatch(position=position, score=100.0, exact_match=True))
        if exact_matches:
            exact_matches.sort(
                key=lambda item: (
                    -item.score,
                    index.attributes[item.position].entityname,
                    index.attributes[item.position].layer,
                    index.attributes[item.position].physical_region,
                )
            )
            return exact_matches[:top_k]

    def lexical_bonus(attribute: AttributeRecord) -> float:
        score = 0.0
        query_tokens = set(_tokenize(query))
        query_terms = {token for token in query_tokens if len(token) > 2}

        def overlap_bonus(text: str, weight: float) -> float:
            text_tokens = set(_tokenize(text))
            active_terms = query_terms or query_tokens
            if not active_terms or not text_tokens:
                return 0.0
            shared_tokens = active_terms.intersection(text_tokens)
            if not shared_tokens:
                return 0.0
            overlap_ratio = len(shared_tokens) / max(len(active_terms), 1)
            return (len(shared_tokens) * weight) + (overlap_ratio * weight * 4.0)

        if meta.focus_name:
            if attribute.attribute_key == meta.focus_name or attribute.family == meta.focus_name:
                return 25.0
            if meta.focus_name in attribute.attribute_key or meta.focus_name in attribute.family:
                score += 10.0
            score += max(
                _name_similarity(meta.focus_name, attribute.attribute_key),
                _name_similarity(meta.focus_name, attribute.family),
            ) * 10.0
        score += len(query_terms.intersection(set(_tokenize(attribute.attribute)))) * 2.0
        score += len(query_terms.intersection(set(_tokenize(attribute.group or "")))) * 1.0
        score += overlap_bonus(attribute.attribute_description, 2.0)
        score += overlap_bonus(attribute.entityname, 1.5)
        score += overlap_bonus(attribute.entity_description, 0.5)

        combined_tokens = set(_tokenize(f"{attribute.attribute} {attribute.attribute_description}"))
        active_terms = query_terms or query_tokens
        shared_combined = active_terms.intersection(combined_tokens)
        if active_terms and shared_combined:
            coverage_ratio = len(shared_combined) / len(active_terms)
            score += len(shared_combined) * 3.0
            score += coverage_ratio * 18.0
        return score

    matches: list[CandidateMatch] = []
    if index.faiss_index is not None and _get_embedding_model() is not None and query.strip():
        vector = _get_embedding_model().encode([query], convert_to_numpy=True, normalize_embeddings=True).astype("float32")
        search_k = min(max(top_k * 12, 60), len(index.attributes))
        distances, indices = index.faiss_index.search(vector, search_k)

        for similarity, position in zip(distances[0], indices[0]):
            position = int(position)
            similarity = float(similarity)
            if position < 0 or similarity < min_similarity:
                continue

            attribute = index.attributes[position]
            if forced_layer and attribute.layer_key != forced_layer:
                continue
            if meta.region_filters and attribute.region_key not in meta.region_filters:
                continue

            matches.append(
                CandidateMatch(
                    position=position,
                    score=(similarity * 100.0) + lexical_bonus(attribute),
                    exact_match=meta.focus_name in {attribute.attribute_key, attribute.family},
                )
            )

    if not matches and (index.faiss_index is None or _get_embedding_model() is None):
        for position, attribute in enumerate(index.attributes):
            if forced_layer and attribute.layer_key != forced_layer:
                continue
            if meta.region_filters and attribute.region_key not in meta.region_filters:
                continue
            score = lexical_bonus(attribute)
            if score > 0:
                matches.append(CandidateMatch(position=position, score=score))

    matches.sort(key=lambda item: item.score, reverse=True)
    if matches and matches[0].score < MIN_MEANINGFUL_SCORE:
        return []
    return matches[: max(top_k, 1)]


def _candidate_payload(candidate: CandidateMatch) -> dict[str, Any]:
    attribute = _get_index().attributes[candidate.position]
    return {
        "doc_id": attribute.doc_id,
        "response_payload": {
            "entityname": attribute.entityname,
            "attribute": attribute.attribute,
            "layer": attribute.layer,
            "physical_region": attribute.physical_region,
        },
        "content": {
            "attribute_description": attribute.attribute_description,
            "entity_description": attribute.entity_description,
            "search_text": attribute.search_text,
        },
        "metadata": {
            "group": attribute.group,
            "group_normalized": attribute.group_key,
            "family": attribute.family,
        },
    }


def _select_candidates(
    query: str,
    user_context: str,
    candidates: list[CandidateMatch],
    layer_scope: str,
    cda_fallback_approved: bool,
) -> AnalyticsLLMSelection:
    if not candidates:
        return AnalyticsLLMSelection(answer=NO_MATCH_ANSWER, best_match_doc_id=None, selected_doc_ids=[], notes=[])

    shortlist = candidates[:LLM_TOP_K]
    index = _get_index()

    def refine_selected_doc_ids(doc_ids: list[str], best_match_doc_id: str | None) -> tuple[list[str], str | None]:
        if not doc_ids:
            return [], best_match_doc_id

        candidate_map = {index.attributes[candidate.position].doc_id: candidate for candidate in shortlist}
        ordered_doc_ids = [doc_id for doc_id in doc_ids if doc_id in candidate_map]
        if not ordered_doc_ids:
            return [], best_match_doc_id

        attributes = [index.attributes[candidate_map[doc_id].position] for doc_id in ordered_doc_ids]
        attribute_names = {attribute.attribute for attribute in attributes}
        if len(attribute_names) == 1:
            scored = []
            top_score = max(candidate_map[doc_id].score for doc_id in ordered_doc_ids)
            for doc_id in ordered_doc_ids:
                attribute = index.attributes[candidate_map[doc_id].position]
                score_gap = top_score - candidate_map[doc_id].score
                richness = len(_tokenize(attribute.attribute_description))
                scored.append((doc_id, score_gap, richness))

            if all(score_gap <= 2.0 for _, score_gap, _ in scored):
                ordered_doc_ids = [doc_id for doc_id, _, _ in sorted(scored, key=lambda item: item[2], reverse=True)]
            else:
                ordered_doc_ids = [doc_id for doc_id, _, _ in sorted(scored, key=lambda item: candidate_map[item[0]].score, reverse=True)]
            best_match_doc_id = ordered_doc_ids[0]

        if best_match_doc_id not in ordered_doc_ids:
            best_match_doc_id = ordered_doc_ids[0]
        elif best_match_doc_id != ordered_doc_ids[0]:
            ordered_doc_ids = [best_match_doc_id, *[doc_id for doc_id in ordered_doc_ids if doc_id != best_match_doc_id]]

        if best_match_doc_id in candidate_map:
            best_score = candidate_map[best_match_doc_id].score
            strongest_doc_id = max(ordered_doc_ids, key=lambda doc_id: candidate_map[doc_id].score)
            strongest_score = candidate_map[strongest_doc_id].score
            if strongest_score >= best_score + BEST_MATCH_PROMOTION_MARGIN:
                best_match_doc_id = strongest_doc_id
                ordered_doc_ids = [best_match_doc_id, *[doc_id for doc_id in ordered_doc_ids if doc_id != best_match_doc_id]]
        return ordered_doc_ids, best_match_doc_id

    client = _get_llm_client()
    if client is not None:
        prompt = get_analytics_prompt(
            query=query,
            user_context=user_context,
            retrieved_candidates=[_candidate_payload(candidate) for candidate in shortlist],
            layer_scope=layer_scope,
            cda_fallback_approved=cda_fallback_approved,
        )
        try:
            response = client.with_structured_output(AnalyticsLLMSelection).invoke(
                [
                    (
                        "system",
                        "You are a careful banking glossary assistant. Select only the documents that truly answer the user query.",
                    ),
                    ("human", prompt),
                ]
            )
            payload = response.model_dump() if hasattr(response, "model_dump") else response
            selection = AnalyticsLLMSelection.model_validate(payload)
            if selection.best_match_doc_id and selection.best_match_doc_id not in selection.selected_doc_ids:
                selection.selected_doc_ids = [selection.best_match_doc_id, *selection.selected_doc_ids]
            if selection.selected_doc_ids and not selection.best_match_doc_id:
                selection.best_match_doc_id = selection.selected_doc_ids[0]
            selection.selected_doc_ids, selection.best_match_doc_id = refine_selected_doc_ids(
                selection.selected_doc_ids,
                selection.best_match_doc_id,
            )
            return selection
        except Exception as exc:  # pragma: no cover
            logger.warning("Analytics LLM selection failed, using fallback selection: %s", exc)

    chosen = shortlist[: min(3, len(shortlist))]
    attributes = [index.attributes[candidate.position] for candidate in chosen]
    if len(attributes) == 1:
        answer = f"The best glossary match for '{query}' is {attributes[0].attribute} in {attributes[0].entityname}."
    else:
        answer = (
            f"Best glossary matches for '{query}' are "
            + ", ".join(f"{attribute.attribute} in {attribute.entityname}" for attribute in attributes)
            + "."
        )
    return AnalyticsLLMSelection(
        answer=answer,
        best_match_doc_id=attributes[0].doc_id,
        selected_doc_ids=[attribute.doc_id for attribute in attributes],
        notes=["Returned top FAISS matches because LLM selection was unavailable."],
    )


def _build_matches(selected_doc_ids: list[str], candidates: list[CandidateMatch], focus_name: str) -> list[AnalyticsOutputMatch]:
    index = _get_index()
    top_score = max((candidate.score for candidate in candidates), default=0.0)
    candidate_map = {index.attributes[candidate.position].doc_id: candidate for candidate in candidates}
    matches: list[AnalyticsOutputMatch] = []

    for doc_id in selected_doc_ids:
        candidate = candidate_map.get(doc_id)
        if candidate is None:
            continue

        attribute = index.attributes[candidate.position]
        similarity = max(
            _name_similarity(focus_name, attribute.attribute_key),
            _name_similarity(focus_name, attribute.family),
        )
        relative = (candidate.score / top_score) if top_score > 0 else 1.0
        if candidate.exact_match or similarity >= 0.90 or relative >= 0.90:
            score = "high"
        elif similarity >= 0.75 or relative >= 0.65:
            score = "medium"
        else:
            score = "low"

        matches.append(
            AnalyticsOutputMatch(
                entityname=attribute.entityname,
                attribute=attribute.attribute,
                layer=attribute.layer,
                physical_region=attribute.physical_region,
                attribute_description=attribute.attribute_description,
                entity_description=attribute.entity_description,
                score=score,
            )
        )
    return matches


def search_analytics(
    query: str,
    user_context: str = "",
    top_k: int = ANALYTICS_TOP_K,
    approve_cda_fallback: bool = False,
) -> AnalyticsResponse:
    top_k = ANALYTICS_TOP_K
    user_context = user_context or query
    original_query = _resolve_query(query, user_context)
    meta = _build_query_meta(original_query, user_context)
    index = _get_index()

    exact_matches = retrieve_analytics_candidates(
        query=original_query,
        user_context=user_context,
        top_k=top_k,
        allow_exact_match=True,
    )
    if exact_matches and exact_matches[0].exact_match:
        attributes = [index.attributes[candidate.position] for candidate in exact_matches]
        if len(attributes) == 1:
            answer = f"Yes, '{attributes[0].attribute}' is available in {attributes[0].entityname} ({attributes[0].layer}, {attributes[0].physical_region})."
        else:
            places = ", ".join(
                f"{attribute.entityname} ({attribute.layer}, {attribute.physical_region})"
                for attribute in attributes
            )
            answer = f"Yes, '{attributes[0].attribute}' is available in {len(attributes)} entities: {places}."
        matches = _build_matches([attribute.doc_id for attribute in attributes], exact_matches, meta.focus_name)
        return AnalyticsResponse(
            original_query=original_query,
            answer=answer,
            retrieval_mode="exact_attribute_across_entities",
            best_match=matches[0] if matches else None,
            alternate_matches=matches[1:],
            searched_layers=sorted({attribute.layer for attribute in attributes}),
            requires_cda_approval=False,
            next_action=None,
        )

    retrieval_query = original_query
    layer_order = [layer for layer in LAYER_ORDER if layer in meta.layer_filters] or list(LAYER_ORDER)
    searched_layers: list[str] = []

    layer_candidates: dict[str, list[CandidateMatch]] = {}
    for layer in [item for item in layer_order if item != "cda"]:
        candidates = retrieve_analytics_candidates(
            query=retrieval_query,
            user_context=original_query,
            top_k=top_k * 3,
            forced_layer=layer,
            allow_exact_match=False,
        )
        if not candidates:
            continue
        layer_candidates[layer] = candidates
        searched_layers.append(layer.upper())

    chosen_layer = ""
    if layer_candidates:
        if "gda" in layer_candidates and "mda" in layer_candidates:
            gda_score = layer_candidates["gda"][0].score
            mda_score = layer_candidates["mda"][0].score
            chosen_layer = "mda" if mda_score >= gda_score + MDA_WIN_MARGIN else "gda"
        else:
            chosen_layer = next(layer for layer in layer_order if layer in layer_candidates)

    cda_preview = []
    if "cda" in layer_order:
        cda_preview = retrieve_analytics_candidates(
            query=retrieval_query,
            user_context=original_query,
            top_k=top_k * 3,
            forced_layer="cda",
            allow_exact_match=False,
            min_similarity=PREVIEW_VECTOR_SIMILARITY if not approve_cda_fallback else MIN_VECTOR_SIMILARITY,
        )

    if chosen_layer and cda_preview:
        chosen_score = layer_candidates[chosen_layer][0].score
        cda_score = cda_preview[0].score
        if cda_score >= chosen_score + CDA_WIN_MARGIN:
            if not approve_cda_fallback:
                return AnalyticsResponse(
                    original_query=original_query,
                    answer=CDA_APPROVAL_MESSAGE,
                    retrieval_mode="cda_approval_required",
                    best_match=None,
                    alternate_matches=[],
                    searched_layers=searched_layers + ["CDA_PENDING_APPROVAL"],
                    requires_cda_approval=True,
                    next_action="Resubmit the same request with approve_cda_fallback=true to allow CDA layer search.",
                )
            chosen_layer = "cda"
            layer_candidates["cda"] = cda_preview

    if chosen_layer:
        candidates = layer_candidates[chosen_layer]
        selection = _select_candidates(
            query=original_query,
            user_context=user_context,
            candidates=candidates,
            layer_scope=chosen_layer.upper(),
            cda_fallback_approved=(chosen_layer == "cda"),
        )
        matches = _build_matches(selection.selected_doc_ids, candidates, meta.focus_name)
        if matches:
            if chosen_layer == "cda" and "CDA" not in searched_layers:
                searched_layers.append("CDA")
            return AnalyticsResponse(
                original_query=original_query,
                answer=selection.answer or NO_MATCH_ANSWER,
                retrieval_mode="attribute_faiss_plus_llm",
                best_match=matches[0],
                alternate_matches=matches[1:],
                searched_layers=searched_layers,
                requires_cda_approval=False,
                next_action=None,
            )

    if "cda" in layer_order:
        if not approve_cda_fallback:
            if cda_preview:
                return AnalyticsResponse(
                    original_query=original_query,
                    answer=CDA_APPROVAL_MESSAGE,
                    retrieval_mode="cda_approval_required",
                    best_match=None,
                    alternate_matches=[],
                    searched_layers=searched_layers + ["CDA_PENDING_APPROVAL"],
                    requires_cda_approval=True,
                    next_action="Resubmit the same request with approve_cda_fallback=true to allow CDA layer search.",
                )
        else:
            candidates = cda_preview or retrieve_analytics_candidates(
                query=retrieval_query,
                user_context=original_query,
                top_k=top_k * 3,
                forced_layer="cda",
                allow_exact_match=False,
            )
            if candidates:
                searched_layers.append("CDA")
                selection = _select_candidates(
                    query=original_query,
                    user_context=user_context,
                    candidates=candidates,
                    layer_scope="CDA",
                    cda_fallback_approved=True,
                )
                matches = _build_matches(selection.selected_doc_ids, candidates, meta.focus_name)
                if matches:
                    return AnalyticsResponse(
                        original_query=original_query,
                        answer=selection.answer or NO_MATCH_ANSWER,
                        retrieval_mode="attribute_faiss_plus_llm",
                        best_match=matches[0],
                        alternate_matches=matches[1:],
                        searched_layers=searched_layers,
                        requires_cda_approval=False,
                        next_action=None,
                    )

    return AnalyticsResponse(
        original_query=original_query,
        answer=NO_MATCH_ANSWER,
        retrieval_mode="no_suitable_match",
        best_match=None,
        alternate_matches=[],
        searched_layers=searched_layers,
        requires_cda_approval=False,
        next_action=None,
    )

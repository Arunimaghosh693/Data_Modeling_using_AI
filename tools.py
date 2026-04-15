from __future__ import annotations

import json
import re
from typing import Any, Dict, List

from langchain_core.tools import tool

try:
    from openai import OpenAI
except ImportError:  # pragma: no cover
    OpenAI = None

try:
    from config import get_openai_api_key, get_openai_model
    from prompts import (
        get_conceptual_prompt,
        get_logical_prompt,
        get_physical_prompt,
    )
    from rag import get_relevant_context
    from schemas import ConceptualModel, LogicalModel, PhysicalModelTemplate
except ImportError:  # pragma: no cover
    from .config import get_openai_api_key, get_openai_model
    from .prompts import (
        get_conceptual_prompt,
        get_logical_prompt,
        get_physical_prompt,
    )
    from .rag import get_relevant_context
    from .schemas import ConceptualModel, LogicalModel, PhysicalModelTemplate


def _build_client():
    api_key = get_openai_api_key()
    if not api_key or OpenAI is None:
        return None
    return OpenAI(api_key=api_key)


def _extract_json(text: str) -> Dict[str, Any]:
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            raise
        return json.loads(match.group(0))


def extract_json_from_tool_output(text: str) -> Dict[str, Any]:
    return _extract_json(text)


def _infer_entities(requirement: str, context: str) -> List[Dict[str, Any]]:
    text = f"{requirement}\n{context}".lower()
    candidates = [
        ("Customer", ["customer", "client", "borrower"]),
        ("Facility", ["facility", "loan", "credit line"]),
        ("Application", ["application", "onboarding", "origination"]),
        ("Account", ["account", "wallet", "profile"]),
        ("Transaction", ["transaction", "payment", "transfer"]),
        ("Collateral", ["collateral", "security", "pledge"]),
        ("Default", ["default", "delinquency", "past due"]),
        ("Recovery", ["recovery", "collection", "restructure"]),
    ]
    entities: List[Dict[str, Any]] = []
    for name, keywords in candidates:
        if any(keyword in text for keyword in keywords):
            entities.append(
                {
                    "name": name,
                    "description": f"Business entity inferred for {name.lower()} management.",
                    "attributes": [],
                }
            )

    if len(entities) < 2:
        entities = [
            {
                "name": "Customer",
                "description": "Borrower or business party under credit assessment.",
                "attributes": [],
            },
            {
                "name": "Facility",
                "description": "Credit product or exposure granted to the customer.",
                "attributes": [],
            },
        ]
    return entities


def _fallback_conceptual_model(requirement: str, context: str) -> Dict[str, Any]:
    entities = _infer_entities(requirement, context)
    relationships: List[Dict[str, Any]] = []
    if len(entities) >= 2:
        first = entities[0]["name"]
        second = entities[1]["name"]
        relationships.append(
            {
                "from_entity": first,
                "to_entity": second,
                "cardinality": "1:N",
                "description": f"One {first} can be associated with many {second} records.",
                "label": "has",
            }
        )

    return {
        "title": "Conceptual Credit Risk Model",
        "scope": "Business-level conceptual model inferred from the provided requirement.",
        "requirement": requirement,
        "rag_context_used": context,
        "entities": entities,
        "relationships": relationships,
        "business_rules": [
            "Cardinality should be reviewed and approved by the SME.",
            "Entity names should reflect business language, not technical table names.",
        ],
        "assumptions": [
            "The requirement text does not yet contain full attribute-level detail.",
            "This conceptual model is intended for SME validation before logical modeling.",
        ],
        "conceptual_summary": "This draft identifies the core business entities and high-level relationships for the requested use case.",
        "diagram_description": "ER diagram derived from conceptual business entities and their cardinality.",
    }


def _fallback_logical_model(conceptual_output: Dict[str, Any]) -> Dict[str, Any]:
    entities = conceptual_output.get("entities", [])
    relationships = conceptual_output.get("relationships", [])
    tables = []

    for entity in entities:
        entity_name = entity["name"]
        table_name = f"{entity_name.lower()}s"
        pk_name = f"{entity_name.lower()}_id"
        columns = [
            {"name": pk_name, "type": "INTEGER", "nullable": False},
            {"name": "name", "type": "VARCHAR(255)", "nullable": False},
        ]
        tables.append(
            {
                "table_name": table_name,
                "source_entity": entity_name,
                "columns": columns,
                "primary_key": [pk_name],
                "foreign_keys": [],
            }
        )

    for relationship in relationships:
        parent = relationship["from_entity"].lower()
        child = relationship["to_entity"].lower()
        parent_table = f"{parent}s"
        child_table = f"{child}s"
        fk_name = f"{parent}_id"
        for table in tables:
            if table["table_name"] == child_table:
                if not any(column["name"] == fk_name for column in table["columns"]):
                    table["columns"].append(
                        {"name": fk_name, "type": "INTEGER", "nullable": False}
                    )
                table["foreign_keys"].append(
                    {
                        "column": fk_name,
                        "references_table": parent_table,
                        "references_column": f"{parent}_id",
                    }
                )

    return {
        "source_entities": [entity["name"] for entity in entities],
        "tables": tables,
        "relationships": relationships,
        "normalization_notes": [
            "The draft is aligned to 3NF expectations pending SME confirmation of attributes.",
            "Repeating groups should be split into separate child tables during detailed design.",
        ],
    }


def _generate_json(prompt: str, system_message: str) -> Dict[str, Any]:
    client = _build_client()
    if client is None:
        raise RuntimeError("OpenAI client is not configured.")

    response = client.responses.create(
        model=get_openai_model(),
        input=[
            {"role": "system", "content": system_message},
            {"role": "user", "content": prompt},
        ],
    )
    return json.loads(response.output_text)


def rag_context_core(requirement: str, k: int = 3) -> str:
    return get_relevant_context(requirement, k=k)


def conceptual_model_core(requirement: str) -> Dict[str, Any]:
    context = rag_context_core(requirement)
    prompt = get_conceptual_prompt(requirement, context)
    try:
        conceptual = ConceptualModel.model_validate(
            _generate_json(
                prompt,
                "You are a senior enterprise data architect specializing in conceptual data modeling.",
            )
        )
        if not conceptual.requirement:
            conceptual.requirement = requirement
        if not conceptual.rag_context_used:
            conceptual.rag_context_used = context
        return conceptual.model_dump()
    except Exception:
        return _fallback_conceptual_model(requirement, context)


def logical_model_core(conceptual_payload: Dict[str, Any]) -> Dict[str, Any]:
    prompt = get_logical_prompt(conceptual_payload)
    try:
        logical = LogicalModel.model_validate(
            _generate_json(
                prompt,
                "You are a senior data modeler specializing in logical data modeling.",
            )
        )
        return logical.model_dump()
    except Exception:
        return _fallback_logical_model(conceptual_payload)





@tool
def rag_tool(requirement: str) -> str:
    """Retrieve relevant business context for the requirement using RAG."""
    content =  rag_context_core(requirement)
    return {"context":content}


@tool
def conceptual_tool(requirement: str) -> dict:
    """Generate the conceptual model JSON from the business requirement."""
    conceptual = conceptual_model_core(requirement)
    #return f"CONCEPTUAL_MODEL_JSON:\n{json.dumps(conceptual, indent=2)}"
    return conceptual


@tool
def logical_tool(conceptual_output: dict) -> dict:
    """Generate the logical model JSON from the conceptual model JSON."""
    return logical_model_core(conceptual_output)


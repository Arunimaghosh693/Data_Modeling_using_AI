from __future__ import annotations

import logging
logger = logging.getLogger(__name__)

import json
import re
from typing import Any, Dict, List

from langchain_core.tools import tool

try:
    from openai import OpenAI
except ImportError:  
    OpenAI = None

try:
    from config import get_openai_api_key, get_openai_model
    from prompts import (
        get_conceptual_prompt,
        get_logical_prompt,
        get_physical_prompt,
    )
    from rag import get_relevant_context
    from schemas import ConceptualModel, LogicalModel, PhysicalModel, PhysicalModelTemplate  #added by swamy
except ImportError:  # pragma: no cover
    from .config import get_openai_api_key, get_openai_model
    from .prompts import (
        get_conceptual_prompt,
        get_logical_prompt,
        get_physical_prompt,
    )
    from .rag import get_relevant_context
    from .schemas import ConceptualModel, LogicalModel, PhysicalModel, PhysicalModelTemplate  #added by swamy

  


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


#added by swamy
def _physical_name(name: str) -> str:
    name = name.strip()
    name = re.sub(r"\s+", "_", name)
    name = re.sub(r"[^a-zA-Z0-9_]", "", name)
    return name.lower()


#added by swamy
def _map_column_data_type(
    logical_type: str,
    is_primary_key: bool = False,
    is_foreign_key: bool = False,
) -> str:
    type_text = (logical_type or "").lower()

    if any(token in type_text for token in ["int", "number"]):
        return "INTEGER"
    if any(token in type_text for token in ["decimal", "numeric", "amount", "money"]):
        return "DECIMAL(18,2)"
    if "timestamp" in type_text or "datetime" in type_text:
        return "TIMESTAMP"
    if "date" in type_text:
        return "DATE"
    if "bool" in type_text:
        return "BOOLEAN"
    if "text" in type_text:
        return "TEXT"
    return "VARCHAR(255)"


#added by swamy
def _build_table_ddl(
    table: Dict[str, Any],
    column_lines: List[str],
    primary_key: List[str],
    foreign_keys: List[Dict[str, Any]],
) -> str:
    constraints = []
    table_name = table["table_name"]

    if primary_key:
        constraints.append(
            f"  CONSTRAINT pk_{table_name} PRIMARY KEY ({', '.join(primary_key)})"
        )

    for foreign_key in foreign_keys:
        column = foreign_key["column"]
        references_table = foreign_key["references_table"]
        references_column = foreign_key["references_column"]
        constraints.append(
            "  "
            f"CONSTRAINT fk_{table_name}_{column} "
            f"FOREIGN KEY ({column}) "
            f"REFERENCES {references_table} ({references_column})"
        )

    ddl_lines = column_lines + constraints
    return (
        f"CREATE TABLE {table_name} (\n"
        + ",\n".join(ddl_lines)
        + "\n);"
    )


#added by swamy
def _fallback_physical_model(logical_output: Dict[str, Any]) -> Dict[str, Any]:
    tables = logical_output.get("tables", [])
    table_name_map = {
        table.get("table_name", ""): _physical_name(table.get("table_name", ""))
        for table in tables
    }
    physical_tables = []
    all_indexes = []
    ddl = []

    for table in tables:
        logical_table_name = table.get("table_name", "")
        physical_table_name = table_name_map.get(logical_table_name, _physical_name(logical_table_name))
        primary_key = [_physical_name(column) for column in table.get("primary_key", [])]
        logical_foreign_keys = table.get("foreign_keys", [])
        foreign_key_columns = {
            _physical_name(foreign_key.get("column", ""))
            for foreign_key in logical_foreign_keys
        }
        physical_columns = []
        column_lines = []

        for column in table.get("columns", []):
            column_name = _physical_name(column.get("name", ""))
            is_primary_key = column_name in primary_key
            is_foreign_key = column_name in foreign_key_columns
            column_data_type = _map_column_data_type(
                column.get("type", ""),
                is_primary_key=is_primary_key,
                is_foreign_key=is_foreign_key,
            )
            nullable = bool(column.get("nullable", True))
            null_clause = "NULL" if nullable else "NOT NULL"
            column_lines.append(f"  {column_name} {column_data_type} {null_clause}")
            physical_columns.append(
                {
                    "name": column_name,
                    "column_data_type": column_data_type,
                    "nullable": nullable,
                    "default": None,
                    "source_logical_column": column.get("name", ""),
                    "comment": "Mapped from logical model column.",
                }
            )

        physical_foreign_keys = []
        table_indexes = []
        for foreign_key in logical_foreign_keys:
            column_name = _physical_name(foreign_key.get("column", ""))
            references_table = table_name_map.get(
                foreign_key.get("references_table", ""),
                _physical_name(foreign_key.get("references_table", "")),
            )
            references_column = _physical_name(foreign_key.get("references_column", ""))
            physical_foreign_keys.append(
                {
                    "column": column_name,
                    "references_table": references_table,
                    "references_column": references_column,
                }
            )
            index = {
                "index_name": f"idx_{physical_table_name}_{column_name}",
                "table_name": physical_table_name,
                "columns": [column_name],
                "unique": False,
            }
            table_indexes.append(index)
            all_indexes.append(index)

        physical_table = {
            "table_name": physical_table_name,
            "source_logical_table": logical_table_name,
            "columns": physical_columns,
            "primary_key": primary_key,
            "foreign_keys": physical_foreign_keys,
            "indexes": table_indexes,
            "partitioning": "",
            "storage_notes": [
                "No partitioning is applied because workload and volume details were not provided."
            ],
        }
        physical_tables.append(physical_table)
        ddl.append(
            _build_table_ddl(
                physical_table,
                column_lines,
                primary_key,
                physical_foreign_keys,
            )
        )

    for index in all_indexes:
        ddl.append(
            f"CREATE INDEX {index['index_name']} "
            f"ON {index['table_name']} "
            f"({', '.join(index['columns'])});"
        )

    return {
        "tables": physical_tables,
        "indexes": all_indexes,
        "ddl": ddl,
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
    return _extract_json(response.output_text)


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


#added by swamy
def physical_model_core(logical_payload: Dict[str, Any]) -> Dict[str, Any]:
    prompt = get_physical_prompt(logical_payload)
    try:
        physical = PhysicalModel.model_validate(
            _generate_json(
                prompt,
                "You are a senior physical data modeler specializing in DDL artifact generation.",
            )
        )
        return physical.model_dump()
    except Exception:
        fallback = _fallback_physical_model(logical_payload)
        return PhysicalModel.model_validate(fallback).model_dump()


@tool
def rag_tool(requirement: str) -> str:
    """Retrieve relevant business context for the requirement using RAG."""
    return rag_context_core(requirement)


@tool
def conceptual_tool(requirement: str) -> str:
    """Generate the conceptual model JSON from the business requirement."""
    logger.info("TOOL CALLED: conceptual_tool")
    conceptual = conceptual_model_core(requirement)
    #return conceptual
    return f"CONCEPTUAL_MODEL_JSON:\n{json.dumps(conceptual, indent=2)}"
    

@tool
def logical_tool(conceptual_json: str) -> str:
    """Generate the logical model JSON from the conceptual model JSON."""
    logger.info("TOOL CALLED: logical_tool")
    conceptual_payload = extract_json_from_tool_output(conceptual_json)
    logical = logical_model_core(conceptual_payload)
    #return logical
    return f"LOGICAL_MODEL_JSON:\n{json.dumps(logical, indent=2)}"
    

#added by swamy
@tool
def physical_tool(logical_json: str) -> str:
    """Generate the physical model JSON and DDL from the logical model JSON."""
    logger.info("TOOL CALLED: physical_tool")
    logical_payload = extract_json_from_tool_output(logical_json)
    physical = physical_model_core(logical_payload)
    return f"PHYSICAL_MODEL_JSON:\n{json.dumps(physical, indent=2)}"

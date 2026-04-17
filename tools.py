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
        get_conceptual_update_prompt,
        get_logical_prompt,
        get_physical_prompt,
    )
    from rag import get_relevant_context
    from schemas import ConceptualModel, ConceptualUpdatePatch, LogicalModel, PhysicalModel, PhysicalModelTemplate  #added by swamy
except ImportError:  # pragma: no cover
    from .config import get_openai_api_key, get_openai_model
    from .prompts import (
        get_conceptual_prompt,
        get_conceptual_update_prompt,
        get_logical_prompt,
        get_physical_prompt,
    )
    from .rag import get_relevant_context
    from .schemas import ConceptualModel, ConceptualUpdatePatch, LogicalModel, PhysicalModel, PhysicalModelTemplate  #added by swamy

  


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


#editd by mani
def _is_canonical_entity_name(entity_name: str) -> bool:
    return bool(re.fullmatch(r"[A-Z][A-Z0-9_]*", entity_name))


#editd by mani
def _business_name_from_canonical(entity_name: str) -> str:
    return entity_name.replace("_", " ").title()


#editd by mani
def _extract_context_entities(context: str) -> List[Dict[str, Any]]:
    entities_by_canonical: Dict[str, Dict[str, Any]] = {}

    for line in context.splitlines():
        line = line.strip()
        if not line.startswith("Business concept:"):
            continue

        match = re.match(
            r"Business concept:\s*(?P<term>[^.]+)\.\s*"
            r"(?:Canonical ER entity|Canonical table):\s*(?P<entity>[^.]+)\.\s*"
            r"Definition:\s*(?P<definition>.+?)\.\s*"
            r"(?:Business usage|Business purpose):",
            line,
        )
        if not match:
            continue

        canonical_entity = match.group("entity").strip()
        if not _is_canonical_entity_name(canonical_entity):
            continue

        entities_by_canonical[canonical_entity] = {
            "name": match.group("term").strip(),
            "description": match.group("definition").strip(),
            "attributes": [],
        }

    for line in context.splitlines():
        line = line.strip()
        if not line.startswith("Entity profile:"):
            continue

        match = re.match(
            r"Entity profile:\s*(?P<entity>[A-Z0-9_]+)\.\s*"
            r"(?:Business terms:\s*(?P<terms>[^.]+)\.\s*)?",
            line,
        )
        if not match:
            continue

        canonical_entity = match.group("entity").strip()
        if not _is_canonical_entity_name(canonical_entity):
            continue

        entity = entities_by_canonical.setdefault(
            canonical_entity,
            {
                "name": _business_name_from_canonical(canonical_entity),
                "description": f"Business entity grounded in glossary context for {canonical_entity}.",
                "attributes": [],
            },
        )

        terms = (match.group("terms") or "").strip()
        if terms and entity["name"] == _business_name_from_canonical(canonical_entity):
            entity["name"] = terms.split(",")[0].strip()

    for line in context.splitlines():
        line = line.strip()
        if not line.startswith("Table summary:"):
            continue

        match = re.match(
            r"Table summary:\s*(?P<entity>[A-Z0-9_]+)\s+represents\s+(?P<term>[^.]+)\.\s*",
            line,
        )
        if not match:
            continue

        canonical_entity = match.group("entity").strip()
        if not _is_canonical_entity_name(canonical_entity):
            continue

        definition_match = re.search(
            r"Business attributes:\s*(?P<attributes>.+?)\.\s*(?:Examples:|$)",
            line,
        )
        attributes = []
        if definition_match:
            for attribute_part in definition_match.group("attributes").split(";"):
                attribute_name = attribute_part.strip().split(" means ", 1)[0].strip()
                if attribute_name:
                    attributes.append(attribute_name)

        entities_by_canonical.setdefault(
            canonical_entity,
            {
                "name": match.group("term").strip(),
                "description": f"Business entity represented by {canonical_entity} in glossary context.",
                "attributes": attributes,
            },
        )

    return list(entities_by_canonical.values())


#editd by mani
def _extract_context_relationships(context: str, entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    business_name_by_canonical = {
        entity["name"].upper().replace(" ", "_"): entity["name"]
        for entity in entities
    }
    relationships_by_key: Dict[tuple[str, str], Dict[str, Any]] = {}

    for line in context.splitlines():
        line = line.strip()
        if not line.startswith("Entity profile:"):
            continue

        entity_match = re.match(r"Entity profile:\s*(?P<entity>[A-Z0-9_]+)\.", line)
        if not entity_match:
            continue

        child_canonical = entity_match.group("entity").strip()
        child_name = business_name_by_canonical.get(child_canonical)
        if not child_name:
            continue

        reference_match = re.search(
            r"Identifiers and reference attributes:\s*(?P<references>.+?)\.\s*"
            r"(?:Typical business attributes:|Notes and examples:|$)",
            line,
        )
        if not reference_match:
            continue

        reference_text = reference_match.group("references")
        for reference_part in reference_text.split(";"):
            attribute_name = reference_part.strip().split(" means ", 1)[0].strip()
            if not attribute_name.endswith("_id"):
                continue

            parent_canonical = attribute_name[:-3].upper()
            if parent_canonical == child_canonical:
                continue

            parent_name = business_name_by_canonical.get(parent_canonical)
            if not parent_name:
                continue

            relationship_key = (parent_name, child_name)
            if relationship_key in relationships_by_key:
                continue

            relationships_by_key[relationship_key] = {
                "from_entity": parent_name,
                "to_entity": child_name,
                "cardinality": "1:N",
                "description": f"One {parent_name} can be associated with many {child_name} records based on glossary reference attributes.",
                "label": "relates to",
            }

    for line in context.splitlines():
        line = line.strip()
        if not line.startswith("Relationship rule:"):
            continue

        match = re.match(
            r"Relationship rule:\s*(?P<from_entity>[A-Z0-9_]+)\s+to\s+(?P<to_entity>[A-Z0-9_]+)\.\s*"
            r"Cardinality:\s*(?P<cardinality>[^.]+)\.\s*"
            r"Business rule:\s*(?P<description>.+)",
            line,
        )
        if not match:
            continue

        from_entity = business_name_by_canonical.get(match.group("from_entity").strip(), _business_name_from_canonical(match.group("from_entity").strip()))
        to_entity = business_name_by_canonical.get(match.group("to_entity").strip(), _business_name_from_canonical(match.group("to_entity").strip()))
        cardinality = match.group("cardinality").strip().replace("1:M", "1:N")
        relationship_key = (from_entity, to_entity)
        relationships_by_key[relationship_key] = {
            "from_entity": from_entity,
            "to_entity": to_entity,
            "cardinality": cardinality,
            "description": match.group("description").strip(),
            "label": "relates to",
        }

    return list(relationships_by_key.values())


#editd by mani
def _normalized_entity_key(entity_name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", entity_name.lower())


#editd by mani
def _relationship_exists(
    relationships: List[Dict[str, Any]],
    from_entity: str,
    to_entity: str,
) -> bool:
    target_pair = {
        _normalized_entity_key(from_entity),
        _normalized_entity_key(to_entity),
    }
    for relationship in relationships:
        relationship_pair = {
            _normalized_entity_key(relationship.get("from_entity", "")),
            _normalized_entity_key(relationship.get("to_entity", "")),
        }
        if relationship_pair == target_pair:
            return True
    return False


#editd by mani
def _conceptual_entity_degrees(
    entities: List[Dict[str, Any]],
    relationships: List[Dict[str, Any]],
) -> Dict[str, int]:
    degrees = {
        _normalized_entity_key(entity.get("name", "")): 0
        for entity in entities
    }
    for relationship in relationships:
        from_key = _normalized_entity_key(relationship.get("from_entity", ""))
        to_key = _normalized_entity_key(relationship.get("to_entity", ""))
        if from_key in degrees:
            degrees[from_key] += 1
        if to_key in degrees:
            degrees[to_key] += 1
    return degrees


#editd by mani
def _preferred_connection_target(
    orphan_entity_name: str,
    entities: List[Dict[str, Any]],
    relationships: List[Dict[str, Any]],
) -> str | None:
    orphan_key = _normalized_entity_key(orphan_entity_name)
    degrees = _conceptual_entity_degrees(entities, relationships)
    preferred_names = ["Customer", "Facility", "Loan", "Account", "Loan Account"]

    for preferred_name in preferred_names:
        for entity in entities:
            entity_name = entity.get("name", "")
            if _normalized_entity_key(entity_name) == orphan_key:
                continue
            if _normalized_entity_key(entity_name) == _normalized_entity_key(preferred_name):
                return entity_name

    connected_entities = [
        entity.get("name", "")
        for entity in entities
        if _normalized_entity_key(entity.get("name", "")) != orphan_key
        and degrees.get(_normalized_entity_key(entity.get("name", "")), 0) > 0
    ]
    if connected_entities:
        return connected_entities[0]

    for entity in entities:
        entity_name = entity.get("name", "")
        if _normalized_entity_key(entity_name) != orphan_key:
            return entity_name
    return None


#editd by mani
def ensure_connected_conceptual_model(
    conceptual_output: Dict[str, Any],
    context: str = "",
) -> Dict[str, Any]:
    entities = list(conceptual_output.get("entities", []))
    relationships = [dict(relationship) for relationship in conceptual_output.get("relationships", [])]

    if len(entities) <= 1:
        normalized_output = dict(conceptual_output)
        normalized_output["relationships"] = relationships
        return normalized_output

    inferred_relationships = _extract_context_relationships(context, entities) if context else []

    while True:
        degrees = _conceptual_entity_degrees(entities, relationships)
        orphan_entities = [
            entity for entity in entities
            if degrees.get(_normalized_entity_key(entity.get("name", "")), 0) == 0
        ]
        if not orphan_entities:
            break

        added_relationship = False
        for orphan_entity in orphan_entities:
            orphan_name = orphan_entity.get("name", "")

            for inferred_relationship in inferred_relationships:
                inferred_from = inferred_relationship.get("from_entity", "")
                inferred_to = inferred_relationship.get("to_entity", "")
                if _normalized_entity_key(orphan_name) not in {
                    _normalized_entity_key(inferred_from),
                    _normalized_entity_key(inferred_to),
                }:
                    continue
                if _relationship_exists(relationships, inferred_from, inferred_to):
                    continue
                relationships.append(inferred_relationship)
                added_relationship = True
                break

            if added_relationship:
                break

            target_entity = _preferred_connection_target(orphan_name, entities, relationships)
            if not target_entity or _relationship_exists(relationships, target_entity, orphan_name):
                continue

            relationships.append(
                {
                    "from_entity": target_entity,
                    "to_entity": orphan_name,
                    "cardinality": "1:N" if _normalized_entity_key(target_entity) in {
                        _normalized_entity_key("Customer"),
                        _normalized_entity_key("Facility"),
                        _normalized_entity_key("Loan"),
                    } else "M:N",
                    "description": f"{target_entity} is associated with {orphan_name} in the conceptual business model.",
                    "label": "relates to",
                }
            )
            added_relationship = True
            break

        if not added_relationship:
            break

    normalized_output = dict(conceptual_output)
    normalized_output["relationships"] = relationships
    return normalized_output


def _fallback_conceptual_model(requirement: str, context: str) -> Dict[str, Any]:
    entities = _extract_context_entities(context)
    relationships = _extract_context_relationships(context, entities)

    return {
        "title": "Conceptual Credit Risk Model",
        "scope": "Business-level conceptual model grounded only in the retrieved glossary context.",
        "requirement": requirement,
        "rag_context_used": context,
        "entities": entities,
        "relationships": relationships,
        "business_rules": [
            "Only glossary-supported entities and relationships are included in this fallback conceptual model.",
            "Cardinality inferred from glossary reference attributes should be reviewed and approved by the SME.",
        ],
        "conceptual_summary": "This draft identifies business entities and high-level relationships using retrieved glossary context only.",
        "diagram_description": "ER diagram derived from glossary-grounded conceptual entities and inferred relationships.",
    }


#editd by mani
def _title_case_entity_name(entity_name: str) -> str:
    parts = re.split(r"[_\s]+", entity_name.strip())
    return "_".join(part.capitalize() for part in parts if part)


#editd by mani
def _fallback_conceptual_update_patch(
    conceptual_output: Dict[str, Any],
    instruction: str,
) -> Dict[str, Any]:
    existing_entities = conceptual_output.get("entities", [])
    normalized_entity_lookup = {
        re.sub(r"[^a-z0-9]", "", entity.get("name", "").lower()): entity.get("name", "")
        for entity in existing_entities
    }
    instruction_text = instruction.lower()
    entity_mentions = []

    for entity in existing_entities:
        entity_name = entity.get("name", "")
        aliases = {
            entity_name.lower(),
            entity_name.lower().replace("_", " "),
            entity_name.lower().replace(" ", "_"),
        }
        positions = [
            instruction_text.find(alias.replace("_", " "))
            for alias in aliases
            if instruction_text.find(alias.replace("_", " ")) >= 0
        ]
        for position in positions:
            entity_mentions.append((position, entity_name, False))

    for match in re.finditer(r"new\s+(?:table|entity)\s+([a-zA-Z][a-zA-Z0-9_ ]+)", instruction, re.IGNORECASE):
        raw_name = match.group(1).strip()
        raw_name = re.split(r"\s+(?:which|that|and|with)\b", raw_name, maxsplit=1)[0].strip(" ,.")
        normalized_name = re.sub(r"[^a-z0-9]", "", raw_name.lower())
        if normalized_name and normalized_name not in normalized_entity_lookup:
            entity_mentions.append((match.start(1), _title_case_entity_name(raw_name), True))

    entity_mentions.sort(key=lambda item: item[0])
    entities_to_add = []
    relationships_to_add_or_update = []
    ordered_entities = [entity_name for _, entity_name, _ in entity_mentions]

    seen_new_entities = set()
    for _, entity_name, is_new in entity_mentions:
        if is_new and entity_name not in seen_new_entities:
            seen_new_entities.add(entity_name)
            entities_to_add.append(
                {
                    "name": entity_name,
                    "description": f"Business entity added from conceptual update instruction for {entity_name}.",
                    "attributes": [],
                }
            )

    for left_entity, right_entity in zip(ordered_entities, ordered_entities[1:]):
        if left_entity == right_entity:
            continue
        relationships_to_add_or_update.append(
            {
                "from_entity": left_entity,
                "to_entity": right_entity,
                "cardinality": "M:N",
                "description": f"{left_entity} is directly related to {right_entity} at the conceptual business level.",
                "label": "relates to",
            }
        )

    return {
        "entities_to_add": entities_to_add,
        "relationships_to_add_or_update": relationships_to_add_or_update,
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

    if is_primary_key or is_foreign_key:
        return "BIGINT"
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


#editd by mani
def _normalize_logical_identifier_types(logical_output: Dict[str, Any]) -> Dict[str, Any]:
    normalized_tables = []

    for table in logical_output.get("tables", []):
        primary_keys = set(table.get("primary_key", []))
        foreign_key_columns = {
            foreign_key.get("column", "")
            for foreign_key in table.get("foreign_keys", [])
        }
        normalized_columns = []

        for column in table.get("columns", []):
            normalized_column = dict(column)
            column_name = normalized_column.get("name", "")
            if column_name in primary_keys or column_name in foreign_key_columns:
                normalized_column["type"] = "number"
                normalized_column["nullable"] = False
            normalized_columns.append(normalized_column)

        normalized_table = dict(table)
        normalized_table["columns"] = normalized_columns
        normalized_tables.append(normalized_table)

    normalized_output = dict(logical_output)
    normalized_output["tables"] = normalized_tables
    return normalized_output


#editd by mani
def _rebuild_physical_ddl(physical_output: Dict[str, Any]) -> List[str]:
    ddl = []

    for table in physical_output.get("tables", []):
        column_lines = []
        for column in table.get("columns", []):
            null_clause = "NULL" if column.get("nullable", True) else "NOT NULL"
            column_lines.append(
                f"  {column.get('name', '')} {column.get('column_data_type', 'VARCHAR(255)')} {null_clause}"
            )

        ddl.append(
            _build_table_ddl(
                table,
                column_lines,
                table.get("primary_key", []),
                table.get("foreign_keys", []),
            )
        )

    for index in physical_output.get("indexes", []):
        ddl.append(
            f"CREATE INDEX {index['index_name']} "
            f"ON {index['table_name']} "
            f"({', '.join(index['columns'])});"
        )

    return ddl


#editd by mani
def _normalize_physical_identifier_types(physical_output: Dict[str, Any]) -> Dict[str, Any]:
    normalized_tables = []

    for table in physical_output.get("tables", []):
        primary_keys = set(table.get("primary_key", []))
        foreign_key_columns = {
            foreign_key.get("column", "")
            for foreign_key in table.get("foreign_keys", [])
        }
        normalized_columns = []

        for column in table.get("columns", []):
            normalized_column = dict(column)
            column_name = normalized_column.get("name", "")
            if column_name in primary_keys or column_name in foreign_key_columns:
                normalized_column["column_data_type"] = "BIGINT"
                normalized_column["nullable"] = False
            normalized_columns.append(normalized_column)

        normalized_table = dict(table)
        normalized_table["columns"] = normalized_columns
        normalized_tables.append(normalized_table)

    normalized_output = dict(physical_output)
    normalized_output["tables"] = normalized_tables
    normalized_output["ddl"] = _rebuild_physical_ddl(normalized_output)
    return normalized_output


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


def rag_context_core(requirement: str, k: int = 12) -> str:
    return get_relevant_context(requirement, k=k)


def conceptual_model_core(requirement: str) -> Dict[str, Any]:
    context = rag_context_core(requirement)
    prompt = get_conceptual_prompt(requirement, context)
    try:
        conceptual = ConceptualModel.model_validate(
            _generate_json(
                prompt,
                "You are a senior enterprise data architect specializing in conceptual data modeling. Use only the supplied glossary context as the source of truth and do not invent unsupported entities or relationships.",
            )
        )
        if not conceptual.requirement:
            conceptual.requirement = requirement
        if not conceptual.rag_context_used:
            conceptual.rag_context_used = context
        return ensure_connected_conceptual_model(conceptual.model_dump(), context)
    except Exception:
        return ensure_connected_conceptual_model(_fallback_conceptual_model(requirement, context), context)


#editd by mani
def conceptual_update_patch_core(
    conceptual_payload: Dict[str, Any],
    instruction: str,
) -> Dict[str, Any]:
    prompt = get_conceptual_update_prompt(conceptual_payload, instruction)
    try:
        patch = ConceptualUpdatePatch.model_validate(
            _generate_json(
                prompt,
                "You are a senior enterprise data architect specializing in conceptual model change requests. Return only a minimal JSON patch for the requested conceptual update.",
            )
        )
        return patch.model_dump()
    except Exception:
        return _fallback_conceptual_update_patch(conceptual_payload, instruction)


def logical_model_core(conceptual_payload: Dict[str, Any]) -> Dict[str, Any]:
    prompt = get_logical_prompt(conceptual_payload)
    try:
        logical = LogicalModel.model_validate(
            _generate_json(
                prompt,
                "You are a senior data modeler specializing in logical data modeling.",
            )
        )
        return _normalize_logical_identifier_types(logical.model_dump())
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
        return _normalize_physical_identifier_types(physical.model_dump())
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

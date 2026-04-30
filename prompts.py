import json
from typing import Any, Dict


#editd by mani
def _compact_json(data: Dict[str, Any]) -> str:
    return json.dumps(data, separators=(",", ":"))


#editd by mani
def _logical_prompt_payload(conceptual_output: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "title": conceptual_output.get("title", ""),
        "scope": conceptual_output.get("scope", ""),
        "entities": [
            {
                "name": entity.get("name", ""),
                "description": entity.get("description", ""),
                "attributes": entity.get("attributes", []),
            }
            for entity in conceptual_output.get("entities", [])
        ],
        "relationships": [
            {
                "from_entity": relationship.get("from_entity", ""),
                "to_entity": relationship.get("to_entity", ""),
                "cardinality": relationship.get("cardinality", ""),
                "description": relationship.get("description", ""),
                "label": relationship.get("label"),
            }
            for relationship in conceptual_output.get("relationships", [])
        ],
        "business_rules": conceptual_output.get("business_rules", []),
    }


#editd by mani
def _physical_prompt_payload(logical_output: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "tables": [
            {
                "table_name": table.get("table_name", ""),
                "source_entity": table.get("source_entity", ""),
                "columns": [
                    {
                        "name": column.get("name", ""),
                        "type": column.get("type", ""),
                        "nullable": column.get("nullable", True),
                    }
                    for column in table.get("columns", [])
                ],
                "primary_key": table.get("primary_key", []),
                "foreign_keys": table.get("foreign_keys", []),
            }
            for table in logical_output.get("tables", [])
        ]
    }


#editd by mani
def _conceptual_update_prompt_payload(conceptual_output: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "title": conceptual_output.get("title", ""),
        "entities": [
            {
                "name": entity.get("name", ""),
                "description": entity.get("description", ""),
            }
            for entity in conceptual_output.get("entities", [])
        ],
        "relationships": [
            {
                "from_entity": relationship.get("from_entity", ""),
                "to_entity": relationship.get("to_entity", ""),
                "cardinality": relationship.get("cardinality", ""),
                "label": relationship.get("label"),
            }
            for relationship in conceptual_output.get("relationships", [])
        ],
    }


def get_conceptual_prompt(requirement: str, context: str) -> str:
    return f"""
You are a banking domain expert and enterprise data architect.

Business requirement:
{requirement}

Authoritative glossary context:
{context}

Return ONLY valid JSON for a conceptual model.

Rules:
- Use the glossary context as the source of truth.
- Include only glossary-supported entities and relationships.
- Stay strictly conceptual: no PK, FK, SQL, indexing, storage, or calculations.
- Keep names business-friendly and prefer domain-specific names like Loan_Default over Default.
- Use entity profiles and column hints only to understand business meaning, not to design technical schemas.
- Every conceptual entity must participate in at least one relationship. Do not return isolated or orphan entities.

Required output:
{{
  "title": "string",
  "scope": "string",
  "entities": [
    {{
      "name": "string",
      "description": "string",
      "attributes": ["optional conceptual attributes"]
    }}
  ],
  "relationships": [
    {{
      "from_entity": "string",
      "to_entity": "string",
      "cardinality": "1:1 | 1:N | M:N",
      "description": "string",
      "label": "string"
    }}
  ],
  "business_rules": ["string"],
  "conceptual_summary": "string",
  "diagram_description": "string"
}}
""".strip()


#editd by mani
def get_conceptual_update_prompt(conceptual_output: Dict[str, Any], instruction: str) -> str:
    conceptual_json = _compact_json(_conceptual_update_prompt_payload(conceptual_output))

    return f"""
You are updating an existing conceptual ER model based on a user chat instruction.

Current conceptual model:
{conceptual_json}

User update instruction:
{instruction}

Return ONLY valid JSON describing the required patch.

Rules:
- Keep the existing conceptual structure unchanged unless the instruction requests a change.
- Reuse existing entity names exactly when referring to existing entities.
- Add a new entity only when the instruction clearly asks for one.
- Add or update only the relationships needed for the instruction.
- Stay strictly conceptual: no PK, FK, SQL, or physical details.
- If a new entity is added, also include at least one relationship that connects it to an existing or newly added entity.
- Use empty arrays when no entity or relationship is required; do not return placeholder values like "string".

Required output:
{{
  "entities_to_add": [
    {{
      "name": "string",
      "description": "string",
      "attributes": []
    }}
  ],
  "relationships_to_add_or_update": [
    {{
      "from_entity": "string",
      "to_entity": "string",
      "cardinality": "1:1 | 1:N | M:N",
      "description": "string",
      "label": "string"
    }}
  ]
}}
""".strip()


def get_logical_prompt(conceptual_output: Dict[str, Any]) -> str:
    conceptual_json = _compact_json(_logical_prompt_payload(conceptual_output))

    return f"""
You are a banking domain expert and enterprise data architect.

Approved conceptual model:
{conceptual_json}

Return ONLY valid JSON for a logical model.

Rules:
- Use ONLY the provided conceptual model.
- Stay at the logical level: no physical DDL, storage, indexing, or performance tuning.
- Convert entities into tables and preserve all conceptual relationships.
- Add business-relevant columns, primary keys, and foreign keys.
- Resolve every M:N relationship with an associative table.
- Use generic types only: string, number, date, datetime, boolean.
- Keep naming consistent, especially PK/FK pairs.
- All surrogate primary key and foreign key identifier columns must use type "number", not "string".
- Identifier columns such as Customer_ID, Facility_ID, Loan_ID, and bridge-table key columns must remain numeric.

Required output:
{{
  "source_entities": ["string"],
  "tables": [
    {{
      "table_name": "string",
      "source_entity": "string",
      "columns": [
        {{
          "name": "string",
          "type": "string",
          "nullable": false
        }}
      ],
      "primary_key": ["string"],
      "foreign_keys": [
        {{
          "column": "string",
          "references_table": "string",
          "references_column": "string"
        }}
      ]
    }}
  ],
  "relationships": [
    {{
      "from_entity": "string",
      "to_entity": "string",
      "cardinality": "string",
      "description": "string"
    }}
  ],
  "normalization_notes": ["string"]
}}
""".strip()


#added by swamy
def get_physical_prompt(logical_output: Dict[str, Any]) -> str:
    logical_json = _compact_json(_physical_prompt_payload(logical_output))
    return f"""
You are a banking domain expert and senior physical data modeling agent.

Approved logical model:
{logical_json}

Return ONLY valid JSON for a physical model.

Rules:
- Use ONLY the provided logical model.
- Do NOT invent, remove, or rename approved tables or relationships.
- Do NOT add database connection, execution, or engine-specific behavior.
- Map generic logical types to generic physical types.
- Preserve PK/FK constraints and add indexes mainly for foreign keys and joins.
- Generate generic DDL suitable for review/demo use.
- Use integer-style physical types for surrogate PK/FK identifier columns, for example BIGINT.
- Do NOT use VARCHAR/TEXT for surrogate primary key or foreign key columns.

Required output:
{{
  "tables": [
    {{
      "table_name": "string",
      "columns": [
        {{
          "name": "string",
          "column_data_type": "string",
          "nullable": false
        }}
      ],
      "primary_key": ["string"],
      "foreign_keys": [
        {{
          "column": "string",
          "references_table": "string",
          "references_column": "string"
        }}
      ],
      "indexes": [
        {{
          "index_name": "string",
          "table_name": "string",
          "columns": ["string"],
          "unique": false
        }}
      ]
    }}
  ],
  "indexes": [
    {{
      "index_name": "string",
      "table_name": "string",
      "columns": ["string"],
      "unique": false
    }}
  ],
  "ddl": ["string"]
}}
""".strip()


def get_analytics_prompt(
    query: str,
    user_context: str,
    retrieved_candidates: list[dict[str, Any]],
    layer_scope: str = "",
    cda_fallback_approved: bool = False,
) -> str:
    candidates_json = _compact_json(
        {
            "original_query": query,
            "user_context": user_context,
            "retrieved_documents": retrieved_candidates,
        }
    )
    context_text = user_context or "No extra user context provided."
    layer_scope_text = layer_scope or "ANY"
    cda_approval_text = "approved" if cda_fallback_approved else "not approved"

    return f"""
You are a banking glossary assistant.

Original query:
{query}

User context:
{context_text}

Layer scope:
{layer_scope_text}

CDA fallback:
{cda_approval_text}

Retrieved candidates:
{candidates_json}

Return ONLY valid JSON.

Rules:
- Use only the retrieved documents. Do not invent entities or attributes.
- Ignore retrieval order. Judge relevance only from business meaning.
- Work only inside the current layer scope.
- If there is no strong match in this layer, return null for best_match_doc_id and an empty selected_doc_ids list.
- Prefer exact attribute matches first.
- Prefer candidates whose attribute name and attribute description cover more of the user query concepts.
- Do not overvalue generic shared words if another candidate captures the more specific concept in the query.
- For exact attribute availability questions, include all exact matches across entities.
- For broader questions, choose the smallest useful set of attributes.
- When several entities contain the same attribute, pick the best_match_doc_id from the clearest business definition and keep only the most useful supporting entities.
- Multi-line concepts like address may return sibling attributes when they are needed together.
- Keep selected_doc_ids ordered from best match to weaker match.
- If CDA fallback is not approved, do not return CDA documents.
- Keep the answer short, clear, and business-friendly.

Required output:
{{
  "answer": "string",
  "best_match_doc_id": "doc_id or null",
  "selected_doc_ids": ["doc_id"],
  "notes": ["string"]
}}
""".strip()

import json
from typing import Any, Dict


def get_conceptual_prompt(requirement: str, context: str) -> str:
    return f"""
You are a banking domain expert and enterprise data architect. A business requirement for a 
a Credit Risk use case is provided. Your task is to understand the business requirement throughly and understand 
what are the different entities, relationships are present in the business requirement and how we can generate a 
conceptual level details

Business requirement:
{requirement}

Use this context to understand meaning of different business
terms. 

Context:
{context}

Create a detailed conceptual model and return ONLY valid JSON.

Rules:
- Identify business entities and key relationships.
- Stay strictly as Business/Conceptual level
- Do NOT include primary keys or foriegn keys
- Do NOT design fact tables or dimension tables 
- Do NOT include calculations or formulas 
- Do NOT include PD, LGD, EAD, IFRS 9, or Basel calculations
- Focus ONLY on core business entities and their relationships 
- Do not invent detailed technical columns unless strongly implied.
- Keep the answer aligned to business semantics, not implementation details.

Scope: 
- End-to-End Credit Risk lifecyle 
- From customer onboarding and loan orginiation
- Through credit assesment and ongoinh monitoring
- To default and recovery 
- Applicable to both Retail and Corperate banking 

What you need to do:
  - Parse the provided business requirement text 
  - Identify core business entities involved in Credit Risk
  - Define each entity in plain, business friendly language 
  - Infer high-level relationships between entities 
  - Indicate relationship type:
      - One-to-One 
      - One-to-many
      - Many-to-Many
  - Identify the CENTRAL business entity in Credit Risk 

  Deliverables: 
  - List of conceptual entities with short business definitions 
  - High-level relationships expressed in plain English 
  - Relationship type ( One-to-One, One-to-Many, Many-to-Many)
  - Identification of the central business entity 
  - A concise conceptal summary
  - A valid and fully detailed JSON file to describe the conceptual level understand 
  - This json will be used to visulize the ER diagram 
 
  Important Rules:
  - Entity names must be business nouns (e.g., Customer, Facility, Account)
  - Definitions must be non-technical and easy to understand 
  - Relationships must be described in business language 
  - Do NOT incliude any implementation or database terminology

Example JSON structure:
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
  "assumptions": ["string"],
  "conceptual_summary": "string",
  "diagram_description": "string",
}}
""".strip()


def get_logical_prompt(conceptual_output: Dict[str, Any]) -> str:
    conceptual_json = json.dumps(conceptual_output, indent=2)
    return f"""
You are a data modeler converting an approved conceptual model into a logical model.

Approved conceptual model:
{conceptual_json}

Return ONLY valid JSON.

Rules:
- Convert entities into logical tables.
- Define primary keys and foreign keys.
- Include logical column types at a generic level.
- Mention normalization guidance.
- Preserve the approved business relationships from the conceptual model.

JSON structure:
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


def get_physical_prompt(logical_output: Dict[str, Any]) -> str:
    logical_json = json.dumps(logical_output, indent=2)
    return f"""
You are the physical data modeling agent.

This phase is not being implemented yet.
If invoked in the future, this approved logical model will be the input:
{logical_json}

Expected future responsibility:
- generate DDL
- suggest indexes
- map types to a target database engine
- propose partitioning and performance hints
""".strip()

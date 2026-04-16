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
  - Prefer domain-specific entity names like Loan_Default and Loan_Recovery instead of generic names like Default and Recovery
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
  "conceptual_summary": "string",
  "diagram_description": "string",
}}
""".strip()


def get_logical_prompt(conceptual_output: Dict[str, Any]) -> str:
    conceptual_json = json.dumps(conceptual_output, indent=2)

    return f"""
You are a banking domain expert and enterprise data architect.

You are given an APPROVED conceptual ER model for a Credit Risk system.  
Your task is to transform it into a LOGICAL data model.

-----------------------------------
CONTEXT
-----------------------------------
- Domain: Banking (Credit Risk)
- Scope: End-to-end credit lifecycle
(Origination → Assessment → Monitoring → Default → Recovery) 109

-----------------------------------
OBJECTIVE
-----------------------------------
Convert the conceptual model into a structured logical data model.

-----------------------------------
STRICT RULES
-----------------------------------
- Stay strictly at the LOGICAL level.
- Do NOT generate physical DDL (no SQL, no storage details).
- Do NOT include performance or indexing considerations.
- Do NOT classify tables as fact/dimension.
- Do NOT include financial calculations (PD, LGD, EAD, IFRS-9, Basel).
- Use ONLY the provided conceptual model (no hallucination).

-----------------------------------
WHAT YOU MUST DO
-----------------------------------
1. Convert conceptual entities into logical tables.
2. Define columns for each table (business-relevant attributes).
3. Identify PRIMARY KEYS for each table.
4. Define FOREIGN KEY relationships between tables.
5. Resolve MANY-TO-MANY relationships using associative tables.
6. Maintain all relationships from the conceptual model.
7. Implement all the relationships properly mentioned in the conceptual model. 
7. Apply basic normalization (avoid redundancy, logical grouping).
8. Include audit-style attributes where appropriate (e.g., status, effective dates).

-----------------------------------
IMPORTANT CONSTRAINTS
-----------------------------------
- Column types should be GENERIC (e.g., string, number, date).
- Do NOT use database-specific types.
- Preserve business meaning from conceptual model.

-----------------------------------
PRIMARY KEY & FOREIGN KEY CONSTRAINTS
-----------------------------------

PRIMARY KEY RULES:

- Every table MUST have a primary key.

- Primary key must uniquely identify each record.

- Primary key columns must NOT be nullable.

- Use surrogate keys for all main entities:
  → Format: <Entity_Name>_ID
  → Examples: Customer_ID, Account_ID, Transaction_ID

- Do NOT use business attributes (e.g., Name, Email, Phone) as primary keys.

- Primary keys must be stable and should not change over time.

- Ensure consistent naming convention across all tables.

- For associative (bridge) tables:
  → Use composite primary key consisting of foreign keys
  → Example: (Facility_ID, Collateral_ID)

-----------------------------------

FOREIGN KEY RULES:

- Every structural relationship between entities MUST be implemented using foreign keys.

- For every 1:N relationship:
  → Add a foreign key in the child table referencing the parent table’s primary key.

- For every 1:1 relationship:
  → Add a foreign key in the dependent entity
  → OR use shared primary key if entities are tightly coupled.

- For every M:N relationship:
  → Create an associative (bridge) table
  → Add foreign keys referencing both parent tables
  → Use these foreign keys as composite primary key

- Foreign key columns must match the referenced primary key in meaning and type (logical level).

- Tables may not contain foreign keys if they represent root or independent entities.

-----------------------------------

CONSISTENCY VALIDATION (VERY IMPORTANT)

Before returning the final JSON:
- Ensure every table has a valid primary key.
- Ensure every relationship is implemented using foreign keys or associative tables.
- Ensure no relationship from the conceptual model is missing in logical design.
- Ensure naming consistency between PK and FK (e.g., Customer_ID matches Customer table).

-----------------------------------
INPUT (APPROVED CONCEPTUAL MODEL)
-----------------------------------
{conceptual_json}

-----------------------------------
OUTPUT REQUIREMENTS
-----------------------------------
Return ONLY valid JSON (no explanation).

Example JSON structure:
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
    logical_json = json.dumps(logical_output, indent=2)
    return f"""
You are a banking domain expert and senior physical data modeling agent.

You are given an APPROVED logical data model for a Credit Risk system.
Your task is to transform it into a PHYSICAL data model with generic DDL output.

-----------------------------------
STRICT RULES
-----------------------------------
- Use ONLY the provided logical model as the source of truth.
- Do NOT invent new business entities.
- Do NOT remove approved tables or relationships.
- Do NOT generate database connection or execution steps.
- Do NOT assume a specific database engine.
- Generate generic DDL for review/demo purposes only.
- Preserve all primary keys and foreign keys from the logical model.
- Add indexes mainly for foreign keys and common relationship joins.

-----------------------------------
WHAT YOU MUST DO
-----------------------------------
1. Map generic logical types to generic physical types.
2. Generate physical tables and columns.
3. Generate primary key and foreign key constraints.
4. Suggest indexes for join and lookup performance.
5. Generate generic DDL statements.
6. Include deployment notes.

-----------------------------------
INPUT (APPROVED LOGICAL MODEL)
-----------------------------------
{logical_json}

-----------------------------------
OUTPUT REQUIREMENTS
-----------------------------------
Return ONLY valid JSON (no explanation).

Example JSON structure:
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

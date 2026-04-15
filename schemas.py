from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class EntityDefinition(BaseModel):
    name: str
    description: str
    attributes: List[str] = Field(default_factory=list)


class RelationshipDefinition(BaseModel):
    from_entity: str
    to_entity: str
    cardinality: str
    description: str
    label: Optional[str] = None


class ConceptualModel(BaseModel):
    title: str = ""
    scope: str = ""
    requirement: str = ""
    rag_context_used: str = ""
    entities: List[EntityDefinition]
    relationships: List[RelationshipDefinition]
    business_rules: List[str] = Field(default_factory=list)
    conceptual_summary: str = ""
    diagram_description: str = ""
    er_diagram_mermaid: str = ""


class LogicalColumn(BaseModel):
    name: str
    type: str
    nullable: bool


class ForeignKeyDefinition(BaseModel):
    column: str
    references_table: str
    references_column: str


class LogicalTable(BaseModel):
    table_name: str
    source_entity: str
    columns: List[LogicalColumn]
    primary_key: List[str]
    foreign_keys: List[ForeignKeyDefinition] = Field(default_factory=list)


class LogicalModel(BaseModel):
    source_entities: List[str]
    tables: List[LogicalTable]
    relationships: List[RelationshipDefinition]
    normalization_notes: List[str] = Field(default_factory=list)


class PhysicalModelTemplate(BaseModel):
    status: str
    message: str
    prompt_preview: str
    next_step_template: Dict[str, Any]
    logical_tables_received: int


#added by swamy
class PhysicalColumn(BaseModel):
    name: str
    column_data_type: str
    nullable: bool


#added by swamy
class PhysicalIndex(BaseModel):
    index_name: str
    table_name: str
    columns: List[str]
    unique: bool = False


#added by swamy
class PhysicalTable(BaseModel):
    table_name: str
    columns: List[PhysicalColumn]
    primary_key: List[str]
    foreign_keys: List[ForeignKeyDefinition] = Field(default_factory=list)
    indexes: List[PhysicalIndex] = Field(default_factory=list)


#added by swamy
class PhysicalModel(BaseModel):
    tables: List[PhysicalTable]
    indexes: List[PhysicalIndex] = Field(default_factory=list)
    ddl: List[str] = Field(default_factory=list)


class ConceptualRequest(BaseModel):
    requirement: str = Field(..., description="Business requirement or use case from the user.")


class LogicalRequest(BaseModel):
    conceptual_output: ConceptualModel


class ModelingRequest(BaseModel):
    requirement: str = Field(..., description="Business requirement or use case from the user.")


class ConceptualResponse(BaseModel):
    rag_context: str
    conceptual_model: ConceptualModel
    mermaid_diagram: str
    artifact_id: str
    view_url: str
    download_mermaid_url: str
    download_json_url: str


class OrchestratorResponse(BaseModel):
    requirement: str
    conceptual_output: Optional[ConceptualModel] = None
    logical_output: Optional[LogicalModel] = None
    physical_output: Optional[PhysicalModel] = None  #added by swamy
    agent_final_answer: str = ""
    conceptual_artifact_id: Optional[str] = None
    conceptual_view_url: Optional[str] = None
    conceptual_download_mermaid_url: Optional[str] = None
    conceptual_download_json_url: Optional[str] = None

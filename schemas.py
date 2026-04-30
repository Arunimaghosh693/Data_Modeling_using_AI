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


#editd by mani
class ConceptualUpdatePatch(BaseModel):
    entities_to_add: List[EntityDefinition] = Field(default_factory=list)
    relationships_to_add_or_update: List[RelationshipDefinition] = Field(default_factory=list)


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
    er_diagram_mermaid: str = ""


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
    er_diagram_mermaid: str = ""


class AnalyticsGlossaryContent(BaseModel):
    search_text: Optional[str] = ""
    entity_description: Optional[str] = ""


class AnalyticsGlossaryMetadata(BaseModel):
    physical_region: Optional[str] = None
    entityname_normalized: str = ""
    layer_normalized: str = ""
    category: Optional[str] = None
    source_system: Optional[str] = None
    data_classification: Optional[str] = None
    attribute_count: int = 0
    group_count: int = 0


class AnalyticsGlossaryAttribute(BaseModel):
    doc_id: str
    attribute: str
    attribute_normalized: str = ""
    group: Optional[str] = None
    group_normalized: str = ""
    family: str = ""
    attribute_description: str = ""
    search_text: str = ""
    is_pii_column: Optional[str] = None
    is_sensitive_column: Optional[str] = None
    category: Optional[str] = None
    source_system: Optional[str] = None
    data_classification: Optional[str] = None
    response_payload: Dict[str, Any] = Field(default_factory=dict)


class AnalyticsGlossaryAttributeGroup(BaseModel):
    group: str
    group_normalized: str = ""
    attributes: List[str] = Field(default_factory=list)
    attribute_count: int = 0
    search_text: str = ""


class AnalyticsGlossaryDocument(BaseModel):
    doc_id: str
    doc_type: str = "entity"
    entityname: str
    layer: str = ""
    content: AnalyticsGlossaryContent = Field(default_factory=AnalyticsGlossaryContent)
    metadata: AnalyticsGlossaryMetadata = Field(default_factory=AnalyticsGlossaryMetadata)
    attribute_groups: List[AnalyticsGlossaryAttributeGroup] = Field(default_factory=list)
    attributes: List[AnalyticsGlossaryAttribute] = Field(default_factory=list)


class AnalyticsRequest(BaseModel):
    query: str = Field(..., description="Attribute search query or natural-language glossary question.")
    approve_cda_fallback: bool = Field(
        default=False,
        description="Set to true to allow CDA-layer results when no suitable GDA or MDA result is found.",
    )


class AnalyticsDocumentResponsePayload(BaseModel):
    entityname: str
    attribute: str
    layer: str
    physical_region: Optional[str] = None


class AnalyticsDocumentContent(BaseModel):
    attribute_description: str = ""
    entity_description: str = ""
    search_text: str = ""


class AnalyticsDocumentMetadata(BaseModel):
    group: Optional[str] = None
    group_normalized: str = ""
    family: str = ""
    category: Optional[str] = None
    source_system: Optional[str] = None
    data_classification: Optional[str] = None
    is_pii_column: Optional[str] = None
    is_sensitive_column: Optional[str] = None


class AnalyticsOutputMatch(BaseModel):
    entityname: str
    attribute: str
    layer: str
    physical_region: Optional[str] = None
    attribute_description: str = ""
    entity_description: str = ""
    score: str = ""


class AnalyticsResponse(BaseModel):
    original_query: str
    answer: str
    retrieval_mode: str
    best_match: Optional[AnalyticsOutputMatch] = None
    alternate_matches: List[AnalyticsOutputMatch] = Field(default_factory=list)
    searched_layers: List[str] = Field(default_factory=list)
    requires_cda_approval: bool = False
    next_action: Optional[str] = None


class AnalyticsLLMSelection(BaseModel):
    answer: str = ""
    best_match_doc_id: Optional[str] = None
    selected_doc_ids: List[str] = Field(default_factory=list)
    notes: List[str] = Field(default_factory=list)


class ConceptualRequest(BaseModel):
    requirement: str = Field(..., description="Business requirement or use case from the user.")


class LogicalRequest(BaseModel):
    conceptual_output: ConceptualModel


class ModelingRequest(BaseModel):
    requirement: str = Field(..., description="Business requirement or use case from the user.")
    artifact_id: Optional[str] = Field(
        default=None,
        description="Existing conceptual artifact to update or approve using the same /orchestrate endpoint.",
    )
    from_entity: Optional[str] = None
    to_entity: Optional[str] = None
    cardinality: str = "M:N"
    description: Optional[str] = None
    label: Optional[str] = None


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
    conceptual_status: Optional[str] = None
    agent_final_answer: str = ""
    conceptual_artifact_id: Optional[str] = None
    conceptual_view_url: Optional[str] = None
    conceptual_download_mermaid_url: Optional[str] = None
    conceptual_download_json_url: Optional[str] = None
    logical_artifact_id: Optional[str] = None
    logical_view_url: Optional[str] = None
    logical_download_mermaid_url: Optional[str] = None
    logical_download_json_url: Optional[str] = None
    physical_artifact_id: Optional[str] = None
    physical_view_url: Optional[str] = None
    physical_download_mermaid_url: Optional[str] = None
    physical_download_json_url: Optional[str] = None





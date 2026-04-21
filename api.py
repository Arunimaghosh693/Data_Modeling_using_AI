from __future__ import annotations
import logging
import re

logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s"
)



try:
    import json

    from fastapi import FastAPI, HTTPException, Request
    from fastapi.responses import HTMLResponse, PlainTextResponse

    from artifact_store import (
        get_conceptual_artifact,
        get_logical_artifact,
        get_physical_artifact,
        set_conceptual_artifact_status,
        save_conceptual_artifact,
        save_logical_artifact,
        save_physical_artifact,
        update_conceptual_artifact,
    )
    from rag import warm_rag
    from schemas import (
        ConceptualModel,
        EntityDefinition,
        LogicalModel,
        ModelingRequest,
        OrchestratorResponse,
        PhysicalModel,
        RelationshipDefinition,
    )
    from tools import (
        conceptual_model_core,
        conceptual_update_patch_core,
        ensure_connected_conceptual_model,
        logical_model_core,
        physical_model_core,
    )
    from utils.mermaid_builder import build_logical_mermaid, build_mermaid, build_physical_mermaid
except ImportError:  # pragma: no cover - supports package-style imports
    import json

    from fastapi import FastAPI, HTTPException, Request
    from fastapi.responses import HTMLResponse, PlainTextResponse

    from .artifact_store import (
        get_conceptual_artifact,
        get_logical_artifact,
        get_physical_artifact,
        set_conceptual_artifact_status,
        save_conceptual_artifact,
        save_logical_artifact,
        save_physical_artifact,
        update_conceptual_artifact,
    )
    from .rag import warm_rag
    from .schemas import (
        ConceptualModel,
        EntityDefinition,
        LogicalModel,
        ModelingRequest,
        OrchestratorResponse,
        PhysicalModel,
        RelationshipDefinition,
    )
    from .tools import (
        conceptual_model_core,
        conceptual_update_patch_core,
        ensure_connected_conceptual_model,
        logical_model_core,
        physical_model_core,
    )
    from .utils.mermaid_builder import build_logical_mermaid, build_mermaid, build_physical_mermaid
    

app = FastAPI(
    title="Agentic Data Modeling Workflow",
    version="2.0.0",
    description=(
        "Single-entry agentic API. The user sends a requirement to /orchestrate, "
        "the orchestrator invokes the agent, and the agent decides which tools to use."
    ),
)


#editd by mani
@app.on_event("startup")
def _warm_rag_on_startup() -> None:
    warm_rag()


def _apply_generated_mermaid(conceptual: ConceptualModel) -> ConceptualModel:
    generated_mermaid = build_mermaid(conceptual)
    return conceptual.model_copy(update={"er_diagram_mermaid": generated_mermaid})


def _apply_generated_logical_mermaid(logical: LogicalModel) -> LogicalModel:
    generated_mermaid = build_logical_mermaid(logical)
    return logical.model_copy(update={"er_diagram_mermaid": generated_mermaid})


def _apply_generated_physical_mermaid(physical: PhysicalModel) -> PhysicalModel:
    generated_mermaid = build_physical_mermaid(physical)
    return physical.model_copy(update={"er_diagram_mermaid": generated_mermaid})


def _build_artifact_links(request: Request, stage: str, artifact_id: str) -> dict[str, str]:
    base_url = str(request.base_url).rstrip("/")
    return {
        "view_url": f"{base_url}/{stage}/view/{artifact_id}",
        "download_mermaid_url": f"{base_url}/{stage}/download/mermaid/{artifact_id}",
        "download_json_url": f"{base_url}/{stage}/download/json/{artifact_id}",
    }


#editd by mani
def _generation_failed(step_name: str, exc: Exception) -> None:
    logging.exception("%s generation failed. No fallback artifact will be created.", step_name)
    raise HTTPException(
        status_code=502,
        detail=f"{step_name} generation or validation failed. Please verify GEMINI_API_KEY, GEMINI_MODEL, and model output format.",
    ) from exc


#editd by mani
def _normalized_entity_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.lower())


#editd by mani
def _resolve_conceptual_entity_name(conceptual: ConceptualModel, entity_name: str) -> str | None:
    target = _normalized_entity_name(entity_name)
    for entity in conceptual.entities:
        if _normalized_entity_name(entity.name) == target:
            return entity.name
    return None


#editd by mani
def _resolve_instruction_entities(conceptual: ConceptualModel, instruction: str) -> list[str]:
    instruction_text = instruction.lower().replace("_", " ")
    matches = []
    for entity in conceptual.entities:
        aliases = {
            entity.name.lower(),
            entity.name.lower().replace("_", " "),
            entity.name.lower().replace(" ", "_"),
        }
        positions = [
            instruction_text.find(alias.replace("_", " "))
            for alias in aliases
            if instruction_text.find(alias.replace("_", " ")) >= 0
        ]
        if positions:
            matches.append((min(positions), entity.name))
    matches.sort(key=lambda item: item[0])

    ordered_entities = []
    for _, entity_name in matches:
        if entity_name not in ordered_entities:
            ordered_entities.append(entity_name)
    return ordered_entities


#editd by mani
def _upsert_conceptual_relationship(
    conceptual: ConceptualModel,
    from_entity: str,
    to_entity: str,
    cardinality: str,
    description: str | None,
    label: str | None,
) -> ConceptualModel:
    relationships = [relationship.model_copy() for relationship in conceptual.relationships]
    existing_index = None

    for index, relationship in enumerate(relationships):
        if {
            _normalized_entity_name(relationship.from_entity),
            _normalized_entity_name(relationship.to_entity),
        } == {
            _normalized_entity_name(from_entity),
            _normalized_entity_name(to_entity),
        }:
            existing_index = index
            break

    relationship_payload = RelationshipDefinition(
        from_entity=from_entity,
        to_entity=to_entity,
        cardinality=cardinality,
        description=description or f"{from_entity} is directly related to {to_entity} at the conceptual business level.",
        label=label or "relates to",
    )

    if existing_index is None:
        relationships.append(relationship_payload)
    else:
        relationships[existing_index] = relationship_payload

    return conceptual.model_copy(update={"relationships": relationships})


#editd by mani
def _upsert_conceptual_entity(
    conceptual: ConceptualModel,
    entity_name: str,
    description: str | None,
    attributes: list[str] | None,
) -> ConceptualModel:
    entities = [entity.model_copy() for entity in conceptual.entities]
    normalized_entity_name = _normalized_entity_name(entity_name)

    for entity in entities:
        if _normalized_entity_name(entity.name) == normalized_entity_name:
            return conceptual

    entities.append(
        EntityDefinition(
            name=entity_name,
            description=description or f"Business entity added from conceptual update instruction for {entity_name}.",
            attributes=attributes or [],
        )
    )
    return conceptual.model_copy(update={"entities": entities})


#editd by mani
def _is_approval_instruction(requirement: str) -> bool:
    requirement_text = requirement.strip().lower()
    return bool(re.fullmatch(r"(approve|approved|save|saved|proceed|continue)", requirement_text))


#editd by mani
def _parse_cardinality_from_text(requirement: str, fallback: str) -> str:
    requirement_text = requirement.lower()
    if "1:n" in requirement_text or "one-to-many" in requirement_text or "one to many" in requirement_text:
        return "1:N"
    if "n:1" in requirement_text or "many-to-one" in requirement_text or "many to one" in requirement_text:
        return "N:1"
    if "1:1" in requirement_text or "one-to-one" in requirement_text or "one to one" in requirement_text:
        return "1:1"
    if "m:n" in requirement_text or "many-to-many" in requirement_text or "many to many" in requirement_text:
        return "M:N"
    return fallback


def _build_mermaid_html(title: str, payload: dict[str, object], json_filename: str, mermaid_text: str) -> str:
    payload_json = json.dumps(payload, indent=2)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Conceptual ER Diagram</title>
  <script type="module">
    import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs';
    mermaid.initialize({{ startOnLoad: true, theme: 'default' }});
  </script>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 24px; background: #f7f7fb; color: #1f2937; }}
    .wrap {{ max-width: 1180px; margin: 0 auto; background: white; border-radius: 12px; padding: 24px; box-shadow: 0 8px 24px rgba(0, 0, 0, 0.08); }}
    .toolbar {{ display: flex; gap: 12px; margin-bottom: 20px; flex-wrap: wrap; }}
    button {{ border: 0; border-radius: 8px; padding: 10px 14px; background: #0f766e; color: white; cursor: pointer; font-size: 14px; }}
    pre {{ background: #111827; color: #e5e7eb; padding: 16px; border-radius: 10px; overflow-x: auto; white-space: pre-wrap; }}
    .section {{ margin-top: 24px; }}
  </style>
</head>
<body>
  <div class="wrap">
    <h1>{title}</h1>
    <div class="toolbar">
      <button onclick="downloadMermaid()">Download .mmd</button>
      <button onclick="downloadJson()">Download JSON</button>
    </div>
    <div class="mermaid">
{mermaid_text}
    </div>
    <div class="section"><h2>Mermaid Source</h2><pre id="source"></pre></div>
    <div class="section"><h2>Model JSON</h2><pre id="model-json"></pre></div>
  </div>
  <script>
    const mermaidText = {mermaid_text!r};
    const modelJson = {payload_json!r};
    document.getElementById("source").textContent = mermaidText;
    document.getElementById("model-json").textContent = modelJson;
    function downloadMermaid() {{
      const blob = new Blob([mermaidText], {{ type: "text/plain;charset=utf-8" }});
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = "er_diagram.mmd";
      link.click();
      URL.revokeObjectURL(url);
    }}
    function downloadJson() {{
      const blob = new Blob([modelJson], {{ type: "application/json;charset=utf-8" }});
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = {json_filename!r};
      link.click();
      URL.revokeObjectURL(url);
    }}
  </script>
</body>
</html>"""


#editd by mani
def _build_orchestrator_response(
    request: Request,
    requirement: str,
    conceptual: ConceptualModel | None,
    logical: LogicalModel | None,
    physical: PhysicalModel | None,
    conceptual_artifact_id: str | None,
    logical_artifact_id: str | None,
    physical_artifact_id: str | None,
    conceptual_status: str | None,
    agent_final_answer: str,
) -> OrchestratorResponse:
    conceptual_links = {
        "view_url": None,
        "download_mermaid_url": None,
        "download_json_url": None,
    }
    logical_links = {
        "view_url": None,
        "download_mermaid_url": None,
        "download_json_url": None,
    }
    physical_links = {
        "view_url": None,
        "download_mermaid_url": None,
        "download_json_url": None,
    }

    if conceptual_artifact_id:
        conceptual_links = _build_artifact_links(request, "conceptual", conceptual_artifact_id)
    if logical_artifact_id:
        logical_links = _build_artifact_links(request, "logical", logical_artifact_id)
    if physical_artifact_id:
        physical_links = _build_artifact_links(request, "physical", physical_artifact_id)

    return OrchestratorResponse(
        requirement=requirement,
        conceptual_output=conceptual,
        logical_output=logical,
        physical_output=physical,
        conceptual_status=conceptual_status,
        agent_final_answer=agent_final_answer,
        conceptual_artifact_id=conceptual_artifact_id,
        conceptual_view_url=conceptual_links["view_url"],
        conceptual_download_mermaid_url=conceptual_links["download_mermaid_url"],
        conceptual_download_json_url=conceptual_links["download_json_url"],
        logical_artifact_id=logical_artifact_id,
        logical_view_url=logical_links["view_url"],
        logical_download_mermaid_url=logical_links["download_mermaid_url"],
        logical_download_json_url=logical_links["download_json_url"],
        physical_artifact_id=physical_artifact_id,
        physical_view_url=physical_links["view_url"],
        physical_download_mermaid_url=physical_links["download_mermaid_url"],
        physical_download_json_url=physical_links["download_json_url"],
    )


@app.get("/health")
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/orchestrate", response_model=OrchestratorResponse)
def orchestrate_endpoint(payload: ModelingRequest, request: Request) -> OrchestratorResponse:
    logging.info("/orchestrate endpoint called")
    requirement = payload.requirement
    artifact_id = payload.artifact_id

    if artifact_id:
        conceptual = get_conceptual_artifact(artifact_id)
        if conceptual is None:
            raise HTTPException(status_code=404, detail="Conceptual artifact not found.")

        if _is_approval_instruction(requirement):
            conceptual = _apply_generated_mermaid(conceptual)

            try:
                logical_payload = logical_model_core(conceptual.model_dump())
            except Exception as exc:
                _generation_failed("Logical model", exc)

            logical = _apply_generated_logical_mermaid(LogicalModel.model_validate(logical_payload))

            try:
                physical_payload = physical_model_core(logical.model_dump())
            except Exception as exc:
                _generation_failed("Physical model", exc)

            physical = _apply_generated_physical_mermaid(PhysicalModel.model_validate(physical_payload))

            update_conceptual_artifact(artifact_id, conceptual)
            set_conceptual_artifact_status(artifact_id, "approved")
            logical_artifact_id = save_logical_artifact(logical)
            physical_artifact_id = save_physical_artifact(physical)

            return _build_orchestrator_response(
                request=request,
                requirement=conceptual.requirement,
                conceptual=conceptual,
                logical=logical,
                physical=physical,
                conceptual_artifact_id=artifact_id,
                logical_artifact_id=logical_artifact_id,
                physical_artifact_id=physical_artifact_id,
                conceptual_status="approved",
                agent_final_answer="Conceptual draft approved and used to generate logical and physical models.",
            )

        from_entity = payload.from_entity
        to_entity = payload.to_entity

        if from_entity:
            from_entity = _resolve_conceptual_entity_name(conceptual, from_entity)
        if to_entity:
            to_entity = _resolve_conceptual_entity_name(conceptual, to_entity)

        if not from_entity or not to_entity:
            try:
                patch = conceptual_update_patch_core(conceptual.model_dump(), requirement)
            except Exception as exc:
                _generation_failed("Conceptual update", exc)

            for entity in patch.get("entities_to_add", []):
                updated_name = entity.get("name", "")
                if not updated_name:
                    continue
                conceptual = _upsert_conceptual_entity(
                    conceptual=conceptual,
                    entity_name=updated_name,
                    description=entity.get("description"),
                    attributes=entity.get("attributes", []),
                )

            relationships = patch.get("relationships_to_add_or_update", [])
            if not relationships:
                resolved_entities = _resolve_instruction_entities(conceptual, requirement)
                if len(resolved_entities) >= 2:
                    relationships = [
                        {
                            "from_entity": resolved_entities[0],
                            "to_entity": resolved_entities[1],
                            "cardinality": _parse_cardinality_from_text(requirement, payload.cardinality),
                            "description": payload.description,
                            "label": payload.label,
                        }
                    ]

            if not relationships:
                raise HTTPException(
                    status_code=400,
                    detail="Could not understand the conceptual update request. Mention the entities to connect or the new entity to add.",
                )

            updated_conceptual = conceptual
            for relationship in relationships:
                resolved_from_entity = _resolve_conceptual_entity_name(
                    updated_conceptual,
                    relationship.get("from_entity", ""),
                ) or relationship.get("from_entity", "")
                resolved_to_entity = _resolve_conceptual_entity_name(
                    updated_conceptual,
                    relationship.get("to_entity", ""),
                ) or relationship.get("to_entity", "")

                if not resolved_from_entity or not resolved_to_entity:
                    continue

                updated_conceptual = _upsert_conceptual_relationship(
                    conceptual=updated_conceptual,
                    from_entity=resolved_from_entity,
                    to_entity=resolved_to_entity,
                    cardinality=_parse_cardinality_from_text(
                        requirement,
                        relationship.get("cardinality", payload.cardinality),
                    ),
                    description=relationship.get("description") or payload.description,
                    label=relationship.get("label") or payload.label,
                )
        else:
            updated_conceptual = _upsert_conceptual_relationship(
                conceptual=conceptual,
                from_entity=from_entity,
                to_entity=to_entity,
                cardinality=_parse_cardinality_from_text(requirement, payload.cardinality),
                description=payload.description,
                label=payload.label,
            )

        updated_conceptual = ConceptualModel.model_validate(
            ensure_connected_conceptual_model(updated_conceptual.model_dump())
        )
        updated_conceptual = _apply_generated_mermaid(updated_conceptual)
        update_conceptual_artifact(artifact_id, updated_conceptual)
        set_conceptual_artifact_status(artifact_id, "draft")

        return _build_orchestrator_response(
            request=request,
            requirement=updated_conceptual.requirement,
            conceptual=updated_conceptual,
            logical=None,
            physical=None,
            conceptual_artifact_id=artifact_id,
            logical_artifact_id=None,
            physical_artifact_id=None,
            conceptual_status="draft",
            agent_final_answer=f"Conceptual relationship updated between {from_entity} and {to_entity}. Review the revised draft and send requirement as 'approve' or 'save' with the same artifact_id when ready.",
        )

    try:
        conceptual_payload = conceptual_model_core(requirement)
    except Exception as exc:
        _generation_failed("Conceptual model", exc)

    conceptual = _apply_generated_mermaid(ConceptualModel.model_validate(conceptual_payload))
    conceptual_artifact_id = save_conceptual_artifact(conceptual, status="draft")
    return _build_orchestrator_response(
        request=request,
        requirement=requirement,
        conceptual=conceptual,
        logical=None,
        physical=None,
        conceptual_artifact_id=conceptual_artifact_id,
        logical_artifact_id=None,
        physical_artifact_id=None,
        conceptual_status="draft",
        agent_final_answer="Conceptual draft generated. Review the conceptual ER and use the same /orchestrate endpoint with artifact_id to update relationships or send 'approve' to continue.",
    )


@app.get("/conceptual/view/{artifact_id}", response_class=HTMLResponse)
def conceptual_view(artifact_id: str) -> HTMLResponse:
    conceptual = get_conceptual_artifact(artifact_id)
    if conceptual is None:
        raise HTTPException(status_code=404, detail="Conceptual artifact not found.")
    return HTMLResponse(
        content=_build_mermaid_html(
            "Conceptual ER Diagram",
            conceptual.model_dump(),
            "conceptual_model.json",
            conceptual.er_diagram_mermaid,
        )
    )


@app.get("/conceptual/download/mermaid/{artifact_id}")
def download_mermaid_artifact(artifact_id: str) -> PlainTextResponse:
    conceptual = get_conceptual_artifact(artifact_id)
    if conceptual is None:
        raise HTTPException(status_code=404, detail="Conceptual artifact not found.")
    return PlainTextResponse(
        content=conceptual.er_diagram_mermaid,
        media_type="text/plain",
        headers={"Content-Disposition": 'attachment; filename="er_diagram.mmd"'},
    )


@app.get("/conceptual/download/json/{artifact_id}")
def download_conceptual_json_artifact(artifact_id: str) -> PlainTextResponse:
    conceptual = get_conceptual_artifact(artifact_id)
    if conceptual is None:
        raise HTTPException(status_code=404, detail="Conceptual artifact not found.")
    return PlainTextResponse(
        content=json.dumps(conceptual.model_dump(), indent=2),
        media_type="application/json",
        headers={"Content-Disposition": 'attachment; filename="conceptual_model.json"'},
    )


@app.get("/logical/view/{artifact_id}", response_class=HTMLResponse)
def logical_view(artifact_id: str) -> HTMLResponse:
    logical = get_logical_artifact(artifact_id)
    if logical is None:
        raise HTTPException(status_code=404, detail="Logical artifact not found.")
    return HTMLResponse(
        content=_build_mermaid_html(
            "Logical ER Diagram",
            logical.model_dump(),
            "logical_model.json",
            logical.er_diagram_mermaid,
        )
    )


@app.get("/logical/download/mermaid/{artifact_id}")
def download_logical_mermaid_artifact(artifact_id: str) -> PlainTextResponse:
    logical = get_logical_artifact(artifact_id)
    if logical is None:
        raise HTTPException(status_code=404, detail="Logical artifact not found.")
    return PlainTextResponse(
        content=logical.er_diagram_mermaid,
        media_type="text/plain",
        headers={"Content-Disposition": 'attachment; filename="logical_er_diagram.mmd"'},
    )


@app.get("/logical/download/json/{artifact_id}")
def download_logical_json_artifact(artifact_id: str) -> PlainTextResponse:
    logical = get_logical_artifact(artifact_id)
    if logical is None:
        raise HTTPException(status_code=404, detail="Logical artifact not found.")
    return PlainTextResponse(
        content=json.dumps(logical.model_dump(), indent=2),
        media_type="application/json",
        headers={"Content-Disposition": 'attachment; filename="logical_model.json"'},
    )


@app.get("/physical/view/{artifact_id}", response_class=HTMLResponse)
def physical_view(artifact_id: str) -> HTMLResponse:
    physical = get_physical_artifact(artifact_id)
    if physical is None:
        raise HTTPException(status_code=404, detail="Physical artifact not found.")
    return HTMLResponse(
        content=_build_mermaid_html(
            "Physical ER Diagram",
            physical.model_dump(),
            "physical_model.json",
            physical.er_diagram_mermaid,
        )
    )


@app.get("/physical/download/mermaid/{artifact_id}")
def download_physical_mermaid_artifact(artifact_id: str) -> PlainTextResponse:
    physical = get_physical_artifact(artifact_id)
    if physical is None:
        raise HTTPException(status_code=404, detail="Physical artifact not found.")
    return PlainTextResponse(
        content=physical.er_diagram_mermaid,
        media_type="text/plain",
        headers={"Content-Disposition": 'attachment; filename="physical_er_diagram.mmd"'},
    )


@app.get("/physical/download/json/{artifact_id}")
def download_physical_json_artifact(artifact_id: str) -> PlainTextResponse:
    physical = get_physical_artifact(artifact_id)
    if physical is None:
        raise HTTPException(status_code=404, detail="Physical artifact not found.")
    return PlainTextResponse(
        content=json.dumps(physical.model_dump(), indent=2),
        media_type="application/json",
        headers={"Content-Disposition": 'attachment; filename="physical_model.json"'},
    )

from __future__ import annotations
import logging

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
        save_conceptual_artifact,
        save_logical_artifact,
        save_physical_artifact,
    )
    from orchestrator import DataModelingOrchestrator
    from rag import warm_rag
    from schemas import ConceptualModel, LogicalModel, ModelingRequest, OrchestratorResponse, PhysicalModel
    from utils.mermaid_builder import build_logical_mermaid, build_mermaid, build_physical_mermaid
except ImportError:  # pragma: no cover - supports package-style imports
    import json

    from fastapi import FastAPI, HTTPException, Request
    from fastapi.responses import HTMLResponse, PlainTextResponse

    from .artifact_store import (
        get_conceptual_artifact,
        get_logical_artifact,
        get_physical_artifact,
        save_conceptual_artifact,
        save_logical_artifact,
        save_physical_artifact,
    )
    from .orchestrator import DataModelingOrchestrator
    from .rag import warm_rag
    from .schemas import ConceptualModel, LogicalModel, ModelingRequest, OrchestratorResponse, PhysicalModel
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


@app.get("/health")
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/orchestrate", response_model=OrchestratorResponse)
def orchestrate_endpoint(payload: ModelingRequest, request: Request) -> OrchestratorResponse:
    logging.info("/orchestrate endpoint called")
    requirement = payload.requirement
    result = DataModelingOrchestrator().run(requirement)

    conceptual_output = result.get("conceptual_output")
    conceptual_artifact_id = None
    conceptual_links = {
        "view_url": None,
        "download_mermaid_url": None,
        "download_json_url": None,
    }
    logical_artifact_id = None
    logical_links = {
        "view_url": None,
        "download_mermaid_url": None,
        "download_json_url": None,
    }
    physical_artifact_id = None
    physical_links = {
        "view_url": None,
        "download_mermaid_url": None,
        "download_json_url": None,
    }

    if conceptual_output:
        conceptual = _apply_generated_mermaid(ConceptualModel.model_validate(conceptual_output))
        conceptual_artifact_id = save_conceptual_artifact(conceptual)
        conceptual_links = _build_artifact_links(request, "conceptual", conceptual_artifact_id)
        result["conceptual_output"] = conceptual.model_dump()

    logical_output = result.get("logical_output")
    if logical_output:
        logical = _apply_generated_logical_mermaid(LogicalModel.model_validate(logical_output))
        logical_artifact_id = save_logical_artifact(logical)
        logical_links = _build_artifact_links(request, "logical", logical_artifact_id)
        result["logical_output"] = logical.model_dump()

    physical_output = result.get("physical_output")
    if physical_output:
        physical = _apply_generated_physical_mermaid(PhysicalModel.model_validate(physical_output))
        physical_artifact_id = save_physical_artifact(physical)
        physical_links = _build_artifact_links(request, "physical", physical_artifact_id)
        result["physical_output"] = physical.model_dump()

    return OrchestratorResponse(
        requirement=requirement,
        conceptual_output=result.get("conceptual_output"),
        logical_output=result.get("logical_output"),
        physical_output=result.get("physical_output"),
        agent_final_answer=result.get("agent_final_answer", ""),
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

from __future__ import annotations

try:
    import json

    from fastapi import FastAPI, HTTPException, Request
    from fastapi.responses import HTMLResponse, PlainTextResponse

    from artifact_store import get_conceptual_artifact, save_conceptual_artifact
    from orchestrator import DataModelingOrchestrator
    from schemas import ConceptualModel, ModelingRequest, OrchestratorResponse
    from utils.mermaid_builder import build_mermaid
except ImportError:  # pragma: no cover - supports package-style imports
    import json

    from fastapi import FastAPI, HTTPException, Request
    from fastapi.responses import HTMLResponse, PlainTextResponse

    from .artifact_store import get_conceptual_artifact, save_conceptual_artifact
    from .orchestrator import DataModelingOrchestrator
    from .schemas import ConceptualModel, ModelingRequest, OrchestratorResponse
    from .utils.mermaid_builder import build_mermaid


app = FastAPI(
    title="Agentic Data Modeling Workflow",
    version="2.0.0",
    description=(
        "Single-entry agentic API. The user sends a requirement to /orchestrate, "
        "the orchestrator invokes the agent, and the agent decides which tools to use."
    ),
)


def _apply_generated_mermaid(conceptual: ConceptualModel) -> ConceptualModel:
    generated_mermaid = build_mermaid(conceptual)
    return conceptual.model_copy(update={"er_diagram_mermaid": generated_mermaid})


def _build_artifact_links(request: Request, artifact_id: str) -> dict[str, str]:
    base_url = str(request.base_url).rstrip("/")
    return {
        "view_url": f"{base_url}/conceptual/view/{artifact_id}",
        "download_mermaid_url": f"{base_url}/conceptual/download/mermaid/{artifact_id}",
        "download_json_url": f"{base_url}/conceptual/download/json/{artifact_id}",
    }


def _build_mermaid_html(conceptual: ConceptualModel, mermaid_text: str) -> str:
    conceptual_json = json.dumps(conceptual.model_dump(), indent=2)
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
    <h1>Conceptual ER Diagram</h1>
    <div class="toolbar">
      <button onclick="downloadMermaid()">Download .mmd</button>
      <button onclick="downloadJson()">Download conceptual.json</button>
    </div>
    <div class="mermaid">
{mermaid_text}
    </div>
    <div class="section"><h2>Mermaid Source</h2><pre id="source"></pre></div>
    <div class="section"><h2>Conceptual JSON</h2><pre id="conceptual-json"></pre></div>
  </div>
  <script>
    const mermaidText = {mermaid_text!r};
    const conceptualJson = {conceptual_json!r};
    document.getElementById("source").textContent = mermaidText;
    document.getElementById("conceptual-json").textContent = conceptualJson;
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
      const blob = new Blob([conceptualJson], {{ type: "application/json;charset=utf-8" }});
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = "conceptual_model.json";
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
    result = DataModelingOrchestrator().run(payload.requirement)

    conceptual_output = result.get("conceptual_output")
    artifact_id = None
    links = {
        "view_url": None,
        "download_mermaid_url": None,
        "download_json_url": None,
    }

    if conceptual_output:
        conceptual = _apply_generated_mermaid(ConceptualModel.model_validate(conceptual_output))
        artifact_id = save_conceptual_artifact(conceptual)
        links = _build_artifact_links(request, artifact_id)
        result["conceptual_output"] = conceptual.model_dump()

    return OrchestratorResponse(
        requirement=payload.requirement,
        conceptual_output=result.get("conceptual_output"),
        logical_output=result.get("logical_output"),
        physical_output=result.get("physical_output"),
        agent_final_answer=result.get("agent_final_answer", ""),
        conceptual_artifact_id=artifact_id,
        conceptual_view_url=links["view_url"],
        conceptual_download_mermaid_url=links["download_mermaid_url"],
        conceptual_download_json_url=links["download_json_url"],
    )


@app.get("/conceptual/view/{artifact_id}", response_class=HTMLResponse)
def conceptual_view(artifact_id: str) -> HTMLResponse:
    conceptual = get_conceptual_artifact(artifact_id)
    if conceptual is None:
        raise HTTPException(status_code=404, detail="Conceptual artifact not found.")
    return HTMLResponse(content=_build_mermaid_html(conceptual, conceptual.er_diagram_mermaid))


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

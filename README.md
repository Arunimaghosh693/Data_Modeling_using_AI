# Data Modeling API

This folder contains an end-to-end AI data modeling workflow built for FastAPI Swagger usage.

## Architecture

- `orchestrator.py`: stage-based router for conceptual, logical, and physical flows
- `tools.py`: RAG retrieval and generation tools
- `prompts.py`: detailed prompts for each modeling stage
- `schemas.py`: request and response contracts used by Swagger
- `api.py`: FastAPI entry point
- `rag.py`: vector retrieval plus local fallback
- `analytics_service.py`: entity-first glossary retrieval for `/analytics`

## Recommended demo path

Use Swagger at `http://127.0.0.1:8000/docs` and call:

1. `POST /orchestrate` with the business requirement
2. Review the returned conceptual JSON and Mermaid text
3. Open `GET /conceptual/view/{artifact_id}` to visualize the ER diagram
4. Use the buttons on that page to download:
   conceptual JSON
   Mermaid `.mmd`
5. Reuse the same `artifact_id` with `POST /orchestrate` and send `approve` to generate logical and physical models
6. Use `POST /analytics` for glossary attribute search

## Run

```bash
pip install -r requirements.txt
uvicorn api:app --reload
```

Create a local `.env` file in `Data_Modeling/`:

```bash
cp .env.example .env
```

Then set:

```env
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-2.5-pro
ANALYTICS_GLOSSARY_JSON_PATH=C:\Users\pilla\Desktop\HSBC_DATA_POC\DATA\Business_Glossary_Output.json
```

This repo now also includes a local `.env` file stub. Replace `your_gemini_api_key_here`
with the actual key before running against Gemini.

## Example Swagger request

```json
{
  "requirement": "Design a retail banking data model where a customer can hold multiple accounts and each account can have many transactions.",
  "requested_stage": "conceptual",
  "approved_conceptual": null
}
```

## Gemini setup

- Store `GEMINI_API_KEY` in `.env`
- Optional: set `GEMINI_MODEL` if you want a model other than the default `gemini-2.5-pro`

## Notes

- If Gemini is unavailable, the app falls back to deterministic local outputs so the flow still demos cleanly.
- `/analytics` uses entity-first retrieval, then attribute ranking inside the matched entities.
- Conceptual modeling should use a structured output schema, not a physical database schema.
- Mermaid is generated from the conceptual model structure using `utils/mermaid_builder.py`.

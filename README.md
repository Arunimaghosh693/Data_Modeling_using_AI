# Data Modeling API

This folder contains an end-to-end AI data modeling workflow built for FastAPI Swagger usage.

## Architecture

- `orchestrator.py`: stage-based router for conceptual, logical, and physical flows
- `tools.py`: RAG retrieval and generation tools
- `prompts.py`: detailed prompts for each modeling stage
- `schemas.py`: request and response contracts used by Swagger
- `api.py`: FastAPI entry point
- `rag.py`: vector retrieval plus local fallback

## Recommended demo path

Use Swagger at `http://127.0.0.1:8000/docs` and call:

1. `POST /conceptual` with the business requirement
2. Review the returned conceptual JSON and Mermaid text
3. Open `GET /conceptual/view?requirement=...` to visualize the ER diagram
4. Use the buttons on that page to download:
   conceptual JSON
   Mermaid `.mmd`
5. Pass `conceptual_model` from `/conceptual` into `POST /logical`
6. Optionally call `POST /physical`

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
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4.1
```

This repo now also includes a local `.env` file stub. Replace `paste_your_openai_api_key_here`
with the actual key before running against OpenAI.

## Example Swagger request

```json
{
  "requirement": "Design a retail banking data model where a customer can hold multiple accounts and each account can have many transactions.",
  "requested_stage": "conceptual",
  "approved_conceptual": null
}
```

## OpenAI setup

- Store `OPENAI_API_KEY` in `.env`
- Optional: set `OPENAI_MODEL` if you want a model other than the default `gpt-4.1`

## Notes

- If OpenAI is unavailable, the app falls back to deterministic local outputs so the flow still demos cleanly.
- Conceptual modeling should use a structured output schema, not a physical database schema.
- Mermaid is generated from the conceptual model structure using `utils/mermaid_builder.py`.

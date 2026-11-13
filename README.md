# PromptLab API

A small, tested REST API for managing **versioned prompt templates** — the kind
of backend work AI-engineering roles expect you to be comfortable with:
resource modeling, persistence, input validation, and automated testing.

## What it does

- **CRUD for prompt templates** (`POST/GET/PUT/DELETE /prompts`)
- **Automatic versioning** — every update creates a new immutable version;
  full history at `GET /prompts/{id}/versions`
- **Template rendering** — `POST /prompts/{id}/render` fills `{variables}`
  and errors clearly on missing ones
- **Deterministic evaluation** — `POST /evaluate` scores prompt structure
  (length, specificity, formatting) with zero paid dependencies, so tests
  are hermetic
- **SQLite storage** — zero-config, file-backed by default (`promptlab.db`)

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# run the API
uvicorn app.main:app --reload    # http://127.0.0.1:8000/docs for Swagger UI

# run the tests
python -m pytest -q
```

Set `PROMPTLAB_DB` to change the database path (`:memory:` for ephemeral).

## Example

```bash
curl -X POST localhost:8000/prompts \
  -H 'Content-Type: application/json' \
  -d '{"name":"summarizer","template":"Summarize this in 3 bullets: {text}"}'

curl -X POST localhost:8000/prompts/1/render \
  -H 'Content-Type: application/json' \
  -d '{"variables":{"text":"quarterly earnings beat expectations"}}'

curl -X POST localhost:8000/evaluate \
  -H 'Content-Type: application/json' \
  -d '{"text":"Summarize the report in exactly 5 bullet points."}'
```

## Project layout

```
app/
  main.py      # FastAPI app + routes
  models.py    # Pydantic request/response schemas
  store.py     # SQLite storage, versioning, template rendering
  evaluate.py  # deterministic prompt-scoring heuristics
tests/
  test_api.py  # 18 end-to-end tests (in-memory DB)
.github/workflows/ci.yml  # pytest on every push/PR
```

## Design notes

- The evaluator is deliberately a **mock**: real model-based scoring can
  replace `evaluate()` without changing the API contract.
- Thread-safe store with a lock; fine for a demo, would need a connection
  pool (or Postgres) for real concurrency.

# Research-to-Prototype Agent

> Autonomously transforms a research paper into a runnable, tested proof-of-concept. Five specialized agents chain reading comprehension → methodology extraction → planning → code generation → reproducibility scoring.

## Agents

| # | Agent | Output |
|---|-------|--------|
| 1 | **Paper Ingestion** | Title, abstract, sections, contributions |
| 2 | **Methodology Extraction** | Hyperparameters, architecture, ambiguities (with `is_assumption` flags) |
| 3 | **Implementation Planning** | File structure, step dependencies, sandbox requirements |
| 4 | **Code Generation** | Source, tests, Dockerfile, README — each line traced to a paper passage |
| 5 | **Reproducibility Check** | Metric-by-metric comparison: paper vs reproduced, with confidence |

## Guarantees

- **Never claims success** unless code actually runs and tests pass
- **All assumptions labeled** — `is_assumption: true` on every inferred detail
- **Traceability links** from every implementation decision to a paper equation/table/section
- **Blocking ambiguities** surface before code generation — human can approve or edit

## Quick Start

```bash
git clone https://github.com/yashaswinidinesh/research-proto-agent
cd research-proto-agent

# Add API key (optional — mock mode works without it)
echo "OPENAI_API_KEY=sk-..." > .env

docker compose up --build
```

Open **http://localhost:3000**, paste a paper, click **Run Research Pipeline**.

## Local Dev

```bash
# Backend
cd backend && python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Frontend
cd frontend && npm install && npm run dev
```

## API

| Endpoint | Description |
|----------|-------------|
| `POST /api/v1/jobs` | Submit paper text or upload file |
| `GET /api/v1/jobs/{id}` | Full job detail + steps + artifacts |
| `GET /api/v1/jobs/{id}/stream` | SSE stream of agent events |
| `GET /api/v1/jobs/{id}/artifacts/{aid}/download` | Download generated file |

## Stack

FastAPI · SQLAlchemy async · PostgreSQL · Next.js 14 · Tailwind · Docker Compose · GitHub Actions

## Author

**Yashaswini Dinesh** · [linkedin.com/in/yashaswini-dinesh-roopa](https://linkedin.com/in/yashaswini-dinesh-roopa)

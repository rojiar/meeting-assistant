# Enterprise Meeting Assistant

English UI and documentation for an AI-native meeting assistant MVP. Analyze meeting transcripts (text or audio), extract summaries and tasks, ask questions with RAG, and create Jira issues.

**Meetings DB:** SQLite (`data/meetings.db`) — transcripts, summaries, tasks. Legacy JSON in `data/meetings/` migrates on first start.

**Vector DB:** [ChromaDB](https://www.trychroma.com/) (embedded, local — `data/chroma/`).

## Prerequisites

- Python 3.11+
- Node.js 20+
- [uv](https://docs.astral.sh/uv/) for Python deps (or `pip install -r backend/requirements.txt`)
- `.env` in the repo root (copy from `.env.example`)
- *(optional)* [Pydantic Logfire](https://logfire.pydantic.dev) — org `meetingassistant` / project `starter-project` (EU)

### Environment

```bash
cp .env.example .env
# Edit: GOOGLE_API_KEY, JIRA_* (optional), LOGFIRE_TOKEN (optional)
```

### Logfire (one-time, optional)

```bash
uv sync
uv run logfire --region eu auth
uv run logfire --region eu projects use --org meetingassistant starter-project
```

Add the write token from [logfire-eu.pydantic.dev](https://logfire-eu.pydantic.dev) to `.env` as `LOGFIRE_TOKEN`.

## Tests

**Unit tests** (mocked APIs, no network):

```bash
chmod +x scripts/run-tests.sh
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 ./scripts/run-tests.sh
```

**Live tests** (real Gemini / Jira — require valid `.env`):

```bash
./scripts/run-live-tests.sh
# or both: ./scripts/run-all-tests.sh
```

**Frontend build:**

```bash
cd frontend && npm install && npm run build
```

## Run

Single terminal — backend + frontend:

```bash
chmod +x scripts/run-dev.sh
./scripts/run-dev.sh
```

Or two terminals:

```bash
./scripts/run-backend.sh    # http://127.0.0.1:8000
./scripts/run-frontend.sh   # http://localhost:4321
```

Open **http://localhost:4321**

## Documentation

Three main documents in `docs/` — matching PDFs in `docs/pdf/`:

| File | Content |
|------|---------|
| `docs/01-project-overview.html` | Project overview & vision |
| `docs/02-implementation.html` | Technical implementation |
| `docs/03-roadmap-and-future-work.html` | Roadmap & future work |

Other resources:

- `docs/README.md` — doc index
- `docs/CHANGELOG.md` — change history
- `docs/superpowers/specs/2026-05-26-meeting-assistant-design.md` — engineering spec

Regenerate PDFs and Mermaid SVGs:

```bash
./scripts/export-docs.sh
```

## Stack

| Layer | Choice |
|-------|--------|
| Backend | FastAPI, Pydantic AI agents |
| Frontend | Astro SSR (English LTR) |
| Embeddings | `gemini-embedding-001` |
| LLM | `google:gemini-3.5-flash` |
| Observability | Logfire (optional) |

## Smoke check

```bash
curl -s http://127.0.0.1:8000/api/health
# Expected: {"status":"ok", ...}
```

# Meeting Assistant MVP — Implementation Plan

> **Goal:** Demo app: Persian transcript → summary/tasks/RAG → Jira (KAN)

**Architecture:** Astro RTL frontend + FastAPI backend + Pydantic AI agents + local JSON vector store

**Tech Stack:** Astro 5, FastAPI, Pydantic AI, Gemini 2.5 Flash, gemini-embedding-001, Jira REST

---

## Status: Implemented

- [x] Backend FastAPI with ingest, RAG, Jira routes
- [x] `analysis_agent` + `rag_agent` (Pydantic AI)
- [x] 3 synthetic Persian meetings
- [x] Astro UI (home, meeting tabs, settings)
- [x] Unit tests (parser, cosine similarity)
- [x] Persian HTML docs + design spec

## Run

```bash
./scripts/run-backend.sh   # terminal 1
./scripts/run-frontend.sh  # terminal 2
```

Open http://localhost:4321 → pick synthetic meeting → test tabs.

## Verified

- `POST /api/meetings/synthetic/meeting-01-scrum` → analysis OK
- `POST /api/meetings/{id}/ask` → RAG with citation OK
- `POST /api/meetings/{id}/jira/preview` → issue payload OK

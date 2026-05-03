# 🧠 Jarvis Brain

> A persistent cognitive system with memory, planning, and learning.

## Core Philosophy
`Understand → Plan → Retrieve → Reason → Act → Learn`

## Architecture
See `docs/architecture.md` (or the SKILL.md root spec).

## Quick Start
```bash
pip install -r requirements.txt
python main.py cli         # interactive CLI
python main.py api         # FastAPI server
docker-compose -f docker/docker-compose.yml up
```

## Module Map
| Module          | Responsibility                              |
|-----------------|---------------------------------------------|
| `api/`          | HTTP surface (FastAPI)                      |
| `orchestrator/` | Core engine — session, retry, critic loop   |
| `agents/`       | Planner, Executor, Research, Critic, Memory |
| `memory/`       | Vector + structured + episodic + graph      |
| `goals/`        | Long-term goal tracking                     |
| `logs/`         | Session logs                                |
| `models/`       | Embeddings, reranker, classifier, router    |
| `tools/`        | Tool layer (memory, system, api)            |
| `reflection/`   | Learning loop — extract & score insights    |
| `config/`       | Settings, environment                       |
| `data/`         | Chroma DB, SQLite stores, logs              |
| `frontend/`     | React dashboard                             |
| `tests/`        | pytest suite                                |
| `docker/`       | Container orchestration                     |

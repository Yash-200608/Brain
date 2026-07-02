# 🧠 Brain

> A persistent cognitive system with memory, planning, and learning.

## Core Philosophy
`Understand → Plan → Retrieve → Reason → Act → Learn`

## Architecture
See the Module Map below. Runtime flow: `main.py` → `JarvisOrchestrator`
(V1-compatible facade) → `SessionManager` → per-session `SessionActor` →
`CognitivePipeline`: intent routing → memory retrieval → plan → execute
(retry under critic, agents via `AgentProtocol`) → reflect → session log.

Brain is the authoritative central server; Jarvis, Chimera and mobile nodes
are clients. See `docs/BRAIN_V2_DESIGN.md` (target architecture) and
`docs/BRAIN_V2_FOUNDATION.md` (implemented foundation + migration notes).

## Quick Start
```bash
pip install -r requirements.txt
python main.py cli         # interactive CLI
python main.py api         # FastAPI server
docker-compose -f docker/docker-compose.yml up
```

## Module Map
| Module          | Responsibility                                        |
|-----------------|-------------------------------------------------------|
| `api/`          | HTTP surface (FastAPI)                                |
| `orchestrator/` | V1-compatible facade + legacy import shims            |
| `core/`         | SessionManager, SessionActor, CognitivePipeline       |
| `agents/`       | AgentProtocol + Planner, Executor, Research, Critic, Memory |
| `services/`     | MemoryService, SessionService, GoalService            |
| `identity/`     | Principal, scopes, IdentityService (non-enforcing)    |
| `protocols/`    | Versioned Envelope — the client wire contract         |
| `events/`       | In-process typed EventBus                             |
| `modelgw/`      | ModelGateway — provider-agnostic LLM access (Ollama)  |
| `memory/`       | Vector + structured + episodic + graph, scoping       |
| `goals/`        | Long-term goal tracking                               |
| `logs/`         | Session logs                                          |
| `models/`       | Embeddings, reranker, classifier, router              |
| `tools/`        | Tool layer (memory, system, api)                      |
| `reflection/`   | Learning loop — extract & score insights              |
| `config/`       | Settings, environment                                 |
| `data/`         | Chroma DB, SQLite stores, logs                        |
| `frontend/`     | Dashboard                                             |
| `tests/`        | pytest suite                                          |
| `docker/`       | Container orchestration                               |

## System Evolution
| Version | Capability              |
|---------|-------------------------|
| V1      | basic RAG               |
| V2      | planner                 |
| V3      | multi-agent             |
| V4      | adaptive retrieval      |
| V5      | autonomous intelligence |

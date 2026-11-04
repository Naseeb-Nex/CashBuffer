---
name: project_context
description: Use this to understand the Graph2Do-AI architecture and coding conventions.
---

# Graph2Do-AI project context

## Purpose
CashBuffer is current repository product name: local-first, zero-cost financial assistant for Raspberry Pi, with multi-tenant transaction ingestion, categorization, Telegram review, dashboard/API chat, and BYO-LLM support. User identity is Kinde JWT `sub`; all domain data is tenant-scoped by `user_id`.

## Current MVP architecture
- **Runtime:** Python 3.14 target; FastAPI async API; Uvicorn; SQLAlchemy async + asyncpg; Alembic migrations.
- **Boundary:** `apps/api/main.py` creates app, routers, DB schema check, OAuth refresh daemon, and CORS. `apps/api/app/presentation/*` handles HTTP/auth dependencies; `apps/api/app/application/*` owns business logic; `apps/api/app/infrastructure/*` owns persistence/settings/crypto/providers/ingestion.
- **Data:** PostgreSQL/Neon. Core tables: users, transactions, categories, vendor rules, OAuth credentials, per-user LLM config. Transactions use parsed → needs_review → categorized states and deterministic hash dedupe.
- **Ingestion:** email/bank parsers normalize raw alerts into transaction payloads; services validate category ownership, persist tenant-scoped rows, and attempt rule-based categorization. OAuth secrets/tokens and LLM keys use Fernet encryption at rest.
- **Assistant:** `/assistant/chat` builds tenant-scoped financial context, loads per-user LiteLLM credentials, calls configured model, parses explicit action markers, then executes guarded transaction/category/rule service operations. Memory is presently vendor-rule persistence, not an external graph memory.
- **Messaging:** connector interface in `apps/api/app/infrastructure/providers/chat_connector.py`; Telegram implementation uses async `httpx`, with mock logging when unconfigured.

## Graph architecture truth
`ARCHITECTURE.md` describes intended LangGraph + LangChain orchestration: state should carry messages, `user_id`, active transactions, and financial context; dynamic per-user LiteLLM should run inside graph execution; planned nodes include memory/context, LLM, tool execution, and response/widget paths. Current code does **not** contain a `StateGraph`, compiled graph, supervisor, worker agents, or multi-agent modules: assistant execution is a service-level linear flow with deterministic action parsing. Treat graph/multi-agent claims as roadmap unless code proves otherwise.

## Conventions
- Keep async boundaries end-to-end; use `AsyncSession`, SQLAlchemy `select`, and explicit commits/refreshes.
- Pass authenticated `user_id` from API dependency into every service/repository query and mutation; filter every tenant-owned read by it.
- Reuse service functions rather than querying models from routers. Add routes in `apps/api/app/presentation`, behavior in `apps/api/app/application`, schema changes through Alembic.
- Keep external providers behind focused adapters/connectors. Keep LLM output non-authoritative: actions must be explicit, validated, tenant-scoped, and deterministic.
- Preserve encrypted-at-rest handling; never return raw keys or tokens. Use settings from `.env` through `app/core/config.py`.
- Prefer existing dependencies and patterns; run Ruff and pytest for changes.

## Things to Avoid
- Do not assume repository name or design docs equal implementation: verify current code before adding LangGraph or multi-agent abstractions.
- Do not add broad `all()` queries, accept client-supplied tenant identity, or trust LLM-generated IDs/category names without ownership validation.
- Do not put business logic in routers, duplicate categorization/transaction rules, or bypass service-layer hash dedupe/state transitions.
- Do not log, expose, or persist plaintext API keys, OAuth tokens, prompts containing secrets, or cross-tenant financial context.
- Do not add a new graph framework, memory system, provider SDK, or abstraction until an actual MVP requirement and existing seam demand it.

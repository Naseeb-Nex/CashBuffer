---
name: project-context
description: Use this to understand CashBuffer architecture and coding conventions.
disable-model-invocation: false
---

# CashBuffer Project Context

## Purpose
CashBuffer is a local-first, multi-tenant financial assistant. It ingests bank/email alerts, tracks income and expenses, learns vendor categorization rules, sends Telegram review prompts, and provides an authenticated AI financial assistant with BYO-LLM support.

## Stack
- Python async backend; FastAPI and Uvicorn.
- SQLAlchemy asyncio with asyncpg; PostgreSQL/Neon in deployment; Alembic migrations.
- Kinde JWT authentication; user ID is JWT `sub`.
- LiteLLM for per-user OpenAI/Anthropic/Gemini/Ollama providers.
- Fernet encryption for stored LLM and OAuth secrets.
- `httpx` integrations, Google OAuth/Gmail ingestion, Telegram connector.
- Ruff and pytest for validation.

## Structure
- `main.py`: app lifecycle, routers, schema startup check, OAuth refresh daemon.
- `app/api/`: HTTP routes, request/response schemas, auth and dependency wiring.
- `app/services/`: tenant-scoped business logic for transactions, categorization, assistant, LLM, export, notifications, OAuth.
- `app/db/`: async session and SQLAlchemy models.
- `app/core/`: settings and cryptography.
- `app/email/`: bank-alert parsing and email watching.
- `app/chat_connectors/`: delivery-provider interfaces and implementations.
- `alembic/`: schema migrations.

## Architectural rules
- Pass authenticated `user_id` from route dependency into every service operation. Every tenant-owned query and mutation must filter by that ID.
- Keep routes thin; reuse services. Keep external providers behind adapters.
- Use async SQLAlchemy `select` and explicit transaction boundaries. Preserve transaction hash deduplication and status transitions (`parsed`, `needs_review`, `categorized`).
- Use `Decimal` for money and never introduce new floating-point currency calculations. Preserve currency and inflow/outflow direction.
- Validate ownership of category, rule, transaction, and credential IDs before mutation.
- Keep LLM output advisory. Parse only explicit, validated actions; never let model output bypass authorization or persistence checks.
- Encrypt secrets at rest and never log or return plaintext keys, tokens, or sensitive financial context.
- Add schema changes through Alembic. Keep configuration in environment-backed settings.
- Current assistant flow is service-based; do not claim or add multi-agent/LangGraph behavior unless an approved locked check requires it.

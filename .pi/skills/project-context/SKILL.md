---
name: project-context
description: Architecture, directory boundaries, coding conventions, test execution, and constraints for CashBuffer. Use when starting tasks in CashBuffer, deciding file placement, checking tech stack rules, implementing backend services or DB queries, or verifying multi-tenant security requirements.
disable-model-invocation: false
---

# CashBuffer Project Context

## App Overview
Local-first, multi-tenant personal financial assistant:
- Ingests bank email alerts via Gmail OAuth.
- Normalizes alerts into transaction stream; auto-categorizes via tenant vendor rules.
- Review workflow via Telegram bot connector (daily catchup / alerts).
- Financial assistant powered by dynamic BYO-LLM (LiteLLM + LangGraph state machine) with native tool/function calling.
- Web dashboard interface for configuration, transaction review, generative UI reporting.

## Tech Stack
- **Backend:** Python 3.12+, FastAPI, SQLAlchemy, asyncpg / psycopg, Alembic, Pydantic v2.
- **Database:** PostgreSQL (Neon serverless in prod, local/Neon-compatible in dev).
- **LLM & Agents:** LangGraph, LangChain, LiteLLM (OpenAI, Anthropic, Gemini, Ollama), SuperMemory.
- **Security / Encryption:** `cryptography.fernet` (AES-128-CBC) for credentials & tokens at rest.
- **Auth:** Kinde JWT JWKS (cloud) / short-lived HS256 JWT + refresh cookie (self-hosted).
- **Frontend / Clients:** Next.js / React (permitted in monorepo under `apps/web` or external clients), Recharts / Tremor UI, Telegram Bot API.
- **Testing & Tooling:** pytest, pytest-asyncio, ruff.

## Current State
- Existing repository with running backend under `apps/api`.
- Database migrations configured via Alembic (`apps/api/alembic/`).
- Active test suite with locked acceptance checks (`apps/api/tests/`, `locked_checks/`).
- Web client directory designated at `apps/web` (API-first architecture).

## Strict Conventions
1. **Multi-Tenancy & Isolation:**
   - Every table and entity must bind `user_id` mapped strictly to JWT `sub`.
   - Repositories/queries must filter by `user_id`. Never trust client-supplied `user_id`.
   - Never allow unbounded queries like `db.query(Transaction).all()`.
2. **Clean Architecture Boundaries:**
   - Presentation (routers) -> Application (services/use cases) -> Infrastructure (repos/db).
   - Presentation NEVER imports Infrastructure persistence models directly.
   - Domain layer remains pure: no framework or DB dependencies.
3. **Money Precision:**
   - Always use `Decimal` for currency amounts. Never use `float`.
   - Preserve sign and currency code.
4. **Secret Storage & Encryption:**
   - Master key `ENCRYPTION_KEY` lives strictly in `.env`.
   - OAuth tokens, user BYO-LLM API keys, and sensitive credentials must pass through `FernetEncryptor` before DB write and decrypt on read.
   - Plaintext secrets in DB, command invocations, or logs forbidden.
5. **Schema & DB Migrations:**
   - DB schema modifications allowed only via Alembic migrations under `apps/api/alembic/versions/`.
6. **Transaction Invariants:**
   - Deterministic SHA-256 hash across normalized `(date, decimal_amount, vendor, account)` for deduplication.
   - Strict lifecycle: `parsed` -> `needs_review` -> `categorized`.

## Project Structure
Monorepo layout:
- `apps/api/main.py`: Entrypoint, lifecycle, schema verify, OAuth token refresh daemon.
- `apps/api/app/presentation/`: FastAPI routers (`assistant`, `auth`, `categories`, `export`, `ingestion`, `llm`, `notifications`, `rules`, `telegram`, `transactions`).
- `apps/api/app/application/`: Tenant-scoped use cases (`assistant_service.py`, `transactions_service.py`, `export_service.py`, `oauth_service.py`, `rules_service.py`).
- `apps/api/app/domain/`: Pure domain entities, tools, and invariant policies.
- `apps/api/app/infrastructure/`:
  - `persistence/`: SQLAlchemy models (`models.py`), session (`database.py`).
  - `ingestion/`: Email and bank-alert parsers (`email_parser.py`).
  - `providers/`: Adapter implementations (`chat_connector.py`, `telegram.py`).
  - `config.py` & `crypto.py`: Pydantic settings (`.env`) and Fernet encryption.
- `apps/api/alembic/`: Schema migrations. Run via `alembic upgrade head` inside `apps/api/`.
- `apps/api/tests/`: Pytest test suite.
- Frontend: Web app / dashboard permitted under `apps/web` or connected clients.

## Technical Conventions
1. **Tenant Isolation & Auth:** Extract `user_id` from JWT `sub` in routes.
   - Cloud: Kinde JWT `sub`.
   - Self-hosted: Short-lived HS256 JWT (15-min) + stateless encrypted cookie refresh token (7-day), invalidated via user `token_epoch` (see `docs/adr/001-short-lived-local-jwt-auth.md`).
   - Every query and mutation must filter by `user_id`. Never trust client-supplied `user_id`.
2. **Money Precision:** Always use `Decimal` for currency. Never cast to or store `float`. Preserve sign and currency code.
3. **Transaction Deduplication:** Compute deterministic SHA-256 hash across normalized `(date, decimal_amount, vendor, account)` for deduplication. Lifecycle: `parsed` -> `needs_review` -> `categorized`.
4. **Secret Storage:** `ENCRYPTION_KEY` and credentials live strictly in `.env`. OAuth tokens and BYO-LLM keys pass through `FernetEncryptor` before DB write and decrypt on read. Plaintext secrets in DB, command invocations, or logs forbidden.
5. **BYO-LLM & Native Tools:** LiteLLM invokes structured model function/tool calls. Model acts through declared tool handlers with tenant-scoped validation on every action.
6. **Agent Orchestration:** LangGraph and graph memory are permitted for multi-turn assistant workflows and memory persistence.

## Gotchas & Constraints
- **Layer Violations:** Presentation never imports Infrastructure persistence models directly. Flow: Route -> Application Service -> Infrastructure Repo.
- **Clean Schema:** Modify schema only via Alembic migrations in `apps/api/alembic/versions/`.
- **Environment Driven:** Pydantic loads configuration from `.env` in repository root. Do not hardcode connection strings or encryption keys in test files or command scripts.
- **Frontend / Backend Boundary:** Web UI consumes standard JSON REST/WebSocket endpoints with Bearer auth; no server-side template mixing in `apps/api`.

## Validation Loop
Ensure `.env` exists with `DATABASE_URL` and `ENCRYPTION_KEY`, then run:
```bash
pytest
```

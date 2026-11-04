# CashBuffer Feature Builder Rulebook

## Baseline rules
- Read `.pi/skills/project-context/SKILL.md` and the relevant file in `./locked_checks/` before implementation.
- Keep FastAPI routes thin; put domain behavior in `apps/api/app/application/`; use `apps/api/app/infrastructure/persistence/` for persistence and Alembic for schema changes.
- Preserve async boundaries with `AsyncSession`, SQLAlchemy `select`, explicit commits, and safe rollback/error handling.
- Treat authenticated Kinde JWT `sub` as the only tenant identity. Every tenant-owned read, write, update, delete, and export must enforce `user_id` server-side.
- Use `Decimal` for all monetary calculations. Never use binary floating point for amounts, totals, comparisons, or persisted money values. Preserve currency and inflow/outflow direction.
- Validate all untrusted input, including transaction IDs, category IDs, vendor rules, provider names, dates, amounts, and model actions.
- Preserve transaction hash deduplication and valid status transitions: `parsed`, `needs_review`, `categorized`.
- LLM output is untrusted advisory input. Execute only explicit, validated, tenant-scoped actions; never allow it to authorize access or mutate another tenant.
- Encrypt secrets at rest. Never log or return plaintext API keys, OAuth tokens, credentials, or unnecessary financial context.
- Keep provider integrations behind existing adapters. Avoid new dependencies and abstractions unless a locked check requires them.
- Maintain accessibility and useful error responses for API/UI-facing changes.
- Run the smallest relevant existing validation command, then the full project validation when practical. Report failures without hiding them.

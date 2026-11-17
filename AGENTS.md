# Project agent memory

This file is the project's committed home for project-intrinsic agent knowledge: build, test, release, architecture, and sharp-edge notes that should travel with the code.

- Architecture: Clean architecture microservices (FastAPI Core API `apps/api/`, Ingress Microservice `apps/ingress/`, FastMCP Intelligence Server `apps/mcp/`). Native psycopg 3 async pool only with numbered SQL migrations.
- Tenancy & Auth: Multi-tenant household boundary. Provider-neutral `users.idp_user_id` maps to internal `users.id` UUID. Strict tenant scoping on all queries.
- Migrations: Native numbered SQL migrations in `migrations/*.sql` executed by `app/db/native_migrations/` (`scripts/migrate.py`) with `pg_advisory_lock(847291)` and SHA-256 checksums in `schema_migrations`.
- Deployment: Composed via root `docker-compose.yml` with memory limits.

## Maintaining this file

Keep this file for knowledge useful to almost every future agent session in this project.
Do not repeat what the codebase already shows; point to the authoritative file or command instead.
Prefer rewriting or pruning existing entries over appending new ones.
When updating this file, preserve this bar for all agents and keep entries concise.

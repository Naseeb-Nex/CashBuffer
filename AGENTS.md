# Project agent memory

This file is the project's committed home for project-intrinsic agent knowledge: build, test, release, architecture, and sharp-edge notes that should travel with the code.

- Native PostgreSQL migrations: Runner lives in `app/db/native_migrations/` (`scripts/migrate.py`), executes numbered SQL migrations in `migrations/*.sql` using psycopg 3 with session advisory lock and SHA-256 checksum validation. `users.idp_user_id` stores Kinde provider subject; `users.id` is UUID.

## Maintaining this file

Keep this file for knowledge useful to almost every future agent session in this project.
Do not repeat what the codebase already shows; point to the authoritative file or command instead.
Prefer rewriting or pruning existing entries over appending new ones.
When updating this file, preserve this bar for all agents and keep entries concise.

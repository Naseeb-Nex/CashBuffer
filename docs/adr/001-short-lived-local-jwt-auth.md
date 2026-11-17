# ADR 001: Short-Lived Stateless Local JWT Authentication

## Status
Accepted

## Context
CashBuffer operates in two modes: cloud multi-tenant SaaS (Kinde JWKS verification) and self-hosted local mode (e.g. Raspberry Pi / single-server).
For self-hosted deployments without third-party identity providers:
- Long-lived bearer JWTs present severe token theft risk.
- Maintaining stateful server session/refresh token tables in Postgres adds DB overhead, cleanup cron jobs, and migration bloat.
- Non-browser clients (Telegram connectors, ingestion daemons, CLI scripts) need a uniform authentication pattern.

## Decision
1. **Stateless Token Pair**:
   - **Access Token:** Short-lived (15 minutes), signed via HS256 with `LOCAL_JWT_SECRET`. Stored only in frontend memory or client runtime. Contains `sub` (`user_id`), `exp`, and `token_epoch`.
   - **Refresh Token:** Stateless encrypted cookie (`httpOnly`, `SameSite=Strict`, `Secure`), 7-day expiry. Encrypted with `ENCRYPTION_KEY`. Payload contains `user_id`, `exp`, and `token_epoch`.
2. **User Provisioning:**
   - Local users exist as standard records in the database `users` table. Seeded via startup check or CLI script (`python scripts/seed_local_user.py`).
3. **Programmatic / Machine Clients:**
   - Telegram connectors and CLI scripts obtain access tokens programmatically via `POST /auth/login` using credentials.
4. **Stateless Invalidation (Password Change):**
   - User entity maintains `password_changed_at` epoch timestamp.
   - JWT tokens include `token_epoch`.
   - If `token_epoch < user.password_changed_at`, token is immediately rejected without requiring a server session store.

## Consequences
- **Positive:** Zero database queries on standard API calls (access token verified purely in-memory via crypto signature). No refresh token tables or cleanup crons.
- **Negative:** Revoking a specific refresh token before expiration is not possible without changing the user's password epoch or rotating `LOCAL_JWT_SECRET`.
- **Security:** 15-minute exposure window on stolen access tokens; refresh tokens shielded from browser XSS.

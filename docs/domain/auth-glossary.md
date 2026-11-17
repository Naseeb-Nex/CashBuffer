# Authentication & Identity Domain Glossary

## Entities & Value Objects

### User
- **Identifier:** `user_id` (string). In Kinde mode, maps to Kinde `sub`. In local mode, maps to local UUID.
- **Attributes:**
  - `email`: User's login identifier.
  - `password_hash`: Bcrypt hashed password (local mode only).
  - `password_changed_at`: Unix epoch timestamp tracking password updates.
- **Invariant:** All tenant transactions, categories, vendor rules, and LLM configs belong to a single `user_id`.

### Access Token
- **Format:** Signed JWT (HS256 in local mode, RS256 in Kinde cloud mode).
- **Lifetime:** 15 minutes (900 seconds).
- **Claims:**
  - `sub`: `user_id`.
  - `exp`: Expiration timestamp.
  - `token_epoch`: Issued timestamp matching or exceeding `password_changed_at`.
- **Storage:** Frontend in-memory state; non-browser client runtime variable. Never written to `localStorage`.

### Refresh Token (Local Mode)
- **Format:** Fernet-encrypted payload containing `{"user_id": ..., "token_epoch": ..., "exp": ...}`.
- **Lifetime:** 7 days.
- **Transport:** `Set-Cookie` header (`httpOnly; SameSite=Strict; Secure; Path=/auth/refresh`).
- **Storage:** Browser cookie jar. Inaccessible to JavaScript.

## State Transitions & Workflows

### 1. Login Workflow (`POST /auth/login`)
- Input: `{ email, password }`
- Validation: Look up `User` by `email`, verify bcrypt hash against `password_hash`.
- Actions:
  - Generate 15-minute Access Token.
  - Generate 7-day encrypted Refresh Token.
  - Return `{ "access_token": "...", "token_type": "bearer", "expires_in": 900 }`.
  - Set `httpOnly` cookie for Refresh Token.

### 2. Token Refresh Workflow (`POST /auth/refresh`)
- Input: Cookie `refresh_token` (browser) or JSON payload (script).
- Validation:
  - Decrypt Fernet token payload.
  - Check `exp > now()`.
  - Check `token_epoch >= user.password_changed_at`.
- Actions:
  - Issue new 15-minute Access Token.
  - Rotate: Issue new 7-day encrypted Refresh Token and update cookie.

### 3. Request Authorization Dependency (`get_current_user`)
- Input: `Authorization: Bearer <access_token>`.
- Verification:
  - Verify signature with `LOCAL_JWT_SECRET` (or Kinde JWKS if cloud).
  - Check expiration (`exp`).
  - Return `sub` as `user_id`.
- Tenant scope: Injected into every route and passed down to application services.

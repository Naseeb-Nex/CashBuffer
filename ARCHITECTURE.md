# System Architecture & Technical Design

## 1. Top-Level Ecosystem
*   **Host:** Raspberry Pi (Debian/Ubuntu).
*   **API / Core:** Python, FastAPI (with asyncio background daemons for ingestion).
*   **Database:** Neon (Serverless Postgres), accessed via SQLAlchemy & asyncpg.
*   **Authentication:** Kinde (Stateless JWT validation via JWKS).
*   **Agent Orchestration:** LangGraph + LangChain.
*   **LLM Gateway:** LiteLLM (unifies calls to OpenAI, Anthropic, Gemini, Ollama under one standard).

## 2. Multi-Tenant Data Security (Zero-Breach Tolerance)
The backend enforces mechanical multi-tenancy:
1.  **Strict Foreign Keys:** Every functional table (`transactions`, `categories`, `vendor_rules`, `llm_configs`, `oauth_credentials`, `quarantined_emails`) has a `user_id` mapped strictly to the Kinde Subject claim.
2.  **API Gateway:** FastAPI `Depends(get_current_user)` parses the JWT and forces `user_id` down to the service layer.
3.  **Service Enforcement:** No generic `db.query(Transaction).all()` exists. Repositories must receive `user_id`.

## 3. "Bring Your Own LLM" (BYO-LLM) Subsystem
To support BYO-LLM, the agent instantiation must be dynamic per-user request:
1.  **Storage:** User submits their API key via the web dashboard.
2.  **Encryption:** FastAPI encrypts the key at rest using `cryptography.fernet` (AES-128 in CBC mode) with a secret master key stored in `.env`.
3.  **Dynamic Initialization:** When LangGraph executes for `user_id=123`, the state machine fetches and decrypts their key, reads their preference (`model="claude-3-5-sonnet"`), and initializes LiteLLM specifically for that run.

## 4. The Agent Engine (LangGraph)
The financial assistant is not a chat completion - it is a graph state machine.
*   **State:** Holds `messages`, `user_id`, `active_transactions`, and `financial_context`.
*   **Memory (SuperMemory):** Instantiated with namespace `user_id`. Agent checks this *before* asking the user questions to see if a categorization rule exists.
*   **Tool Execution Node:** Exposes strict determinism:
    *   `update_transaction(user_id, tx_id, category_id)`
    *   `fetch_spending_by_category(user_id, month)`
    *   `predict_upcoming_bills(user_id)`

## 5. Interface Abstractions

### 5.1. Push (Telegram)
*   **Binding:** User signs in to the web app, generates a "Telegram Binding Token", messages the Telegram bot with it, and the DB links `telegram_chat_id` -> `kinde_user_id`. Users can also disconnect their account via the `/telegram/unlink` API.
*   **Flow:** A cron scheduler hits an internal FastAPI endpoint `POST /jobs/daily-catchup`. The system pulls `needs_review` transactions for all users, initializes their specific LLM, generates a witty prompt, and fires it via the Telegram API.

### 5.2. Pull (Generative UI Web Dashboard)
*   **Auth:** Next.js uses Kinde SDK. Passes `Bearer {token}` to FastAPI.
*   **Flow:** User asks "Where did my money go this month?".
*   **Response:** LangGraph tools fetch the data, prepare a JSON payload:
    ```json
    {
      "text": "You spent $400 mostly on dining.",
      "ui_widget": "CASHFLOW_BAR_CHART",
      "data": {"dining": 400, "rent": 1500}
    }
    ```
*   **Render:** The React frontend maps `"CASHFLOW_BAR_CHART"` to a Recharts/Tremor UI component without parsing markdown.

## 6. Database Schema Target (Phase 1)
*   `users` (id, email, telegram_chat_id)
*   `llm_configs` (user_id, provider, encrypted_key, model_name)
*   `oauth_credentials` (id, user_id, provider, encrypted_access_token, encrypted_refresh_token, expires_at, is_valid)
*   `vendor_rules` (id, user_id, vendor_regex, default_category_id)
*   `transactions` (id, user_id, amount, currency, is_inflow, date, vendor_raw, category_id, status[parsed|needs_review|categorized], tx_hash)
*   `categories` (id, user_id, name, parent_id)
*   `quarantined_emails` (id, user_id, email_text, error_reason, created_at, resolved)

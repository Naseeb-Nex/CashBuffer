# Cash Buffer — Product Requirements Document (PRD) 💰

> **Deployment:** Raspberry Pi (Local) -> Potential SaaS
> **Cost Constraint:** Zero-cost (Free tiers only)
> **Auth:** Kinde
> **AI:** Bring Your Own LLM (BYO-LLM) Supported

## 1. Product Vision
Cash Buffer is a zero-friction, multi-tenant financial assistant. It bridges the gap between passive tools (like Mint/Copilot) and active chatting. It automatically captures income and expenses via bank emails, categorizes them based on your historical memory, and proactively reaches out on your messaging apps to categorize unknowns. 

## 2. Core Features (MVP to V1)
1.  **Automated Capture:** Ingests bank transaction emails (Gmail API), parses amounts/vendors, and securely writes to the database.
2.  **Autonomous Categorization:** Matches new transactions against an ever-learning memory of your vendor rules.
3.  **Proactive Catch-ups (Push):** At a scheduled time, the agent batches uncategorized items and sends an interactive message to your Telegram to quickly resolve them.
4.  **Generative UI (Pull):** A web dashboard where chatting with your financial agent generates deterministic widgets (spend charts, upcoming bills, savings simulators) directly in the UI.
5.  **Strict Multi-Tenancy:** Mechanical isolation of user data. User A can never cross paths with User B.
6.  **Bring Your Own LLM (BYO-LLM):** Users supply their own API keys (OpenAI, Anthropic, Gemini, or Local/Ollama). Reduces SaaS overhead and puts privacy/power in the hands of the user.

## 3. Target Audience
-   **Phase 1 (Hobby):** Personal use hosted on a Raspberry Pi.
-   **Phase 2 (SaaS):** Power users, developers, and privacy-conscious individuals who want AI financial assistance without handing their data to a black-box AI provider.

## 4. Execution Roadmap
*   **Phase 1: DB & Auth:** Multi-tenant DB, Kinde JWT validation, and encrypted BYO-LLM credential storage.
*   **Phase 2: Ingestion:** Gmail API integration and Regex/LLM hybrid parsers.
*   **Phase 3: LangGraph Engine:** Dynamic LLM routing (LiteLLM), tools deployment, and SuperMemory integration.
*   **Phase 4: Interfaces:** Telegram interactive bot and Next.js Generative UI dashboard.

*(Refer to `ARCHITECTURE.md` for technical system design and mechanization).*
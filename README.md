# Cash Buffer — Personal Finance Companion Agent 💰

> **Phase 1 (MVP) Product Requirements & System Specification**  
> **Owner:** Naseeb  
> **Date:** August 11, 2026  
> **Status:** Draft v1.0  

---

## 1. Overview

### 1.1 Problem Statement
Tracking day-to-day spending is manual, scattered across bank SMS/email alerts and memory, and categorization is tedious enough that most people give up within weeks. There is no lightweight, agent-driven system that captures spend automatically, organizes it with minimal user effort, and surfaces useful financial insight over time.

### 1.2 Product Vision
**Cash Buffer** is a personal financial companion agent that automatically captures transactions (starting with bank email alerts), organizes them into categories with progressively less user input, and gives the user a clear picture of monthly spending — with the long-term goal of proactively flagging repetitive or unusual spending patterns.

### 1.3 Phase 1 (MVP) Goals
- 📬 **Automated Capture:** Capture transactions automatically from bank email alerts (starting with **Axis Bank** format).
- ✍️ **Manual Fallback:** Allow manual entry for cash or untracked expenses.
- 🤖 **Agent Categorization & Learning:** Categorize transactions via an interactive chat interface; learn and auto-apply known vendor/UPI mappings for repeat transactions.
- 📊 **Monthly Dashboard:** Display monthly spend totals, category breakdowns, and filterable transaction lists.
- ⚙️ **Settings & Setup:** Connect email accounts and manage main categories and subcategories.

### 1.4 Phase 1 Non-Goals
- Bank account or SMS aggregation beyond email (planned for Phase 2+).
- Multi-user / shared household budgeting.
- Automated bill payments or fund transfers (*Cash Buffer is strictly read-only/advisory*).
- Investment tracking, net worth calculation, or credit score tracking.
- Native mobile applications (*Phase 1 is web-first*).

---

## 2. Target User & Core Use Cases

### 2.1 Primary User
Individual professionals who receive bank transaction alerts by email and want an effortless way to understand where their money goes each month without maintaining manual spreadsheets.

### 2.2 Core Use Cases
1. **Automated Bank Email Capture:** Bank email alerts are automatically transformed into tracked transactions.
2. **Manual Expense Logging:** Manually log cash or untracked spends so financial records stay complete.
3. **Automated Vendor Categorization:** Agent automatically categorizes spends when vendor/UPI ID is recognized.
4. **Interactive Chat Categorization:** Agent asks the user via chat to categorize transactions only when vendor is unknown.
5. **Monthly Financial Dashboard:** View monthly spending metrics by category to understand spending habits.
6. **Account & Category Management:** Easily configure email integration and customize category trees in settings.

---

## 3. System Architecture & Data Flow

### 3.1 Five-Phase Pipeline
```
┌─────────────┐     ┌───────────┐     ┌──────────────┐     ┌─────────────┐     ┌─────────────┐
│   CAPTURE   │ ──> │   STORE   │ ──> │   ORGANIZE   │ ──> │   ANALYZE   │ ──> │   DISPLAY   │
└─────────────┘     └───────────┘     └──────────────┘     └─────────────┘     └─────────────┘
  Email Watcher       Raw DB           Categorization       Insight Agent       Dashboard
  Email Parser                         Category DB                              Settings UI
  Manual Entry                         Chat Interface
```

| Phase | Responsibility | Key Components |
| :--- | :--- | :--- |
| **Capture** | Ingest transaction data into system | Email Watcher, Email Parser, Manual Entry UI |
| **Store** | Persist raw transaction records | Raw Transactions DB |
| **Organize** | Assign main category & subcategory | Categorization Agent, Category Mapping DB, Chat Interface |
| **Analyze** | Surface patterns & recurring spends | Insight Agent, Insight/Context Store |
| **Display** | Present financial view to user | Dashboard, Settings UI |

### 3.2 End-to-End Data Flow
1. Bank sends transaction email alert (e.g., Axis Bank UPI debit alert).
2. **Email Watcher** receives message via IMAP / Gmail push notification.
3. **Email Parser** extracts `amount`, `currency`, `vendor/UPI ID`, `date`, and `type` (debit/credit), then writes a record to the **Raw Transactions DB**.
4. On a scheduled cron run, the **Categorization Agent** checks for uncategorized transactions.
5. For each transaction, the agent checks the **Category Mapping DB** for a known vendor/UPI ID.
   - **If matched:** Category and subcategory are auto-applied (`category_source: auto`).
   - **If unmatched:** Agent prompts the user via the **Chat Interface** (`category_source: chat`). User answer updates both the transaction and the reusable mapping DB for future automated categorization.
6. The **Insight Agent** periodically analyzes historical transactions to identify recurring expenses and generate monthly summaries.

---

## 4. Functional Requirements Summary

### 4.1 Email Capture (P0)
- **FR-1.1:** Support connecting email accounts via IMAP / Gmail API with user credentials/OAuth.
- **FR-1.2:** Filter incoming mail for bank alert patterns (sender, subject line).
- **FR-1.3:** Extract amount, currency, vendor/payee, date, and transaction type (debit/credit).
- **FR-1.4:** Support Axis Bank alert parsing at launch with extensible parser interface.
- **FR-1.5:** Deduplicate transactions to prevent double counting.
- **FR-1.6 (P1):** Queue unparseable emails for manual review.

### 4.2 Manual Entry (P0)
- **FR-2.1:** Manually create transactions (amount, vendor, date, note).
- **FR-2.2:** Route manual entries into the standard categorization agent workflow.

### 4.3 Categorization & Learning (P0 / P1)
- **FR-3.1:** Maintain vendor-to-category mapping database.
- **FR-3.2:** Cron-based identification of uncategorized transactions.
- **FR-3.3:** Auto-apply categories when vendor mappings exist.
- **FR-3.4:** Prompt user via chat interface when vendor mapping is unknown.
- **FR-3.5:** Persist chat responses to update transaction and future mappings.
- **FR-3.6 (P1):** Manage main categories and subcategories via Settings UI.
- **FR-3.7 (P1):** Allow manual recategorization of past transactions with mapping updates.

### 4.4 Dashboard (P0 / P1)
- **FR-4.1:** Current month total spend calculation.
- **FR-4.2:** Breakdown by main categories.
- **FR-4.3 (P1):** Filterable transaction list (by date range & category).
- **FR-4.4 (P1):** Historical month navigation.

### 4.5 Setup & Settings (P0 / P2)
- **FR-5.1:** Email connection setup UI.
- **FR-5.2:** Category & subcategory editor UI.
- **FR-5.3 (P2):** Cron schedule configuration (daily, weekly).

### 4.6 Insight Agent — Stretch (P2)
- **FR-6.1:** Detect recurring transactions across months.
- **FR-6.2:** Generate concise monthly spending summaries.

---

## 5. Non-Functional Requirements

- 🔒 **Security:** Encrypt stored email credentials and financial data; leverage OAuth 2.0 where available.
- 🛡️ **Privacy:** Keep transaction data private; sanitize account numbers in LLM prompts.
- ⚡ **Reliability & Latency:** Zero loss on email pipeline; sub-second dashboard rendering and efficient cron execution.
- 📈 **Auditability:** Record source of every category assignment (`auto` vs `chat`).

---

## 6. High-Level Data Schema

- **Raw Transactions:** `id`, `source` (email | manual), `raw_amount`, `currency`, `vendor_raw`, `date`, `status` (parsed | needs_review)
- **Categorized Transactions:** `transaction_id`, `category`, `subcategory`, `category_source` (auto | chat), `assigned_at`
- **Category Mapping:** `vendor_identifier` (e.g., UPI ID), `category`, `subcategory`, `created_at`, `last_used_at`
- **Insight / Context Store:** `summary_type`, `period`, `content`, `generated_at`

---

## 7. Delivery Roadmap (Phase 1)

```
[M1: Capture Core] ──> [M2: Setup UI] ──> [M3: Categorization Loop] ──> [M4: Dashboard v1] ──> [M5: Insight Agent]
```

- **M1 — Capture Core:** Email watcher, Axis Bank parser, Raw Transactions DB.
- **M2 — Setup Screen:** Email account connection and category management UI.
- **M3 — Categorization Loop:** Cron job, lookup mapping DB, chat interface for unknown vendors.
- **M4 — Dashboard v1:** Monthly totals, category charts, transaction table.
- **M5 — Insight Agent (Stretch):** Recurring spend detection & monthly summaries.

---

*For detailed implementation discussions and architecture decisions, refer to project planning documentation.*

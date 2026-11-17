-- Migration: 003_core_ledger
-- Description: Core financial ledger, accounts, categories, budgets, merchants, transactions, and LLM configuration.

CREATE TABLE IF NOT EXISTS accounts (
    id UUID DEFAULT gen_random_uuid(),
    household_id UUID NOT NULL REFERENCES households(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    type VARCHAR(30) NOT NULL DEFAULT 'checking',
    currency VARCHAR(3) DEFAULT 'INR' NOT NULL,
    current_balance NUMERIC(15, 2) DEFAULT 0.00 NOT NULL,
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    PRIMARY KEY (id, household_id)
);

CREATE TABLE IF NOT EXISTS categories (
    id SERIAL PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    household_id UUID REFERENCES households (id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    parent_id INTEGER REFERENCES categories (id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_categories_user_id ON categories (user_id);
CREATE INDEX IF NOT EXISTS idx_categories_household_id ON categories (household_id) WHERE household_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_categories_parent_id ON categories (parent_id) WHERE parent_id IS NOT NULL;

CREATE TABLE IF NOT EXISTS budgets (
    id UUID DEFAULT gen_random_uuid(),
    household_id UUID NOT NULL REFERENCES households(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    PRIMARY KEY (id, household_id)
);

CREATE TABLE IF NOT EXISTS merchants (
    id UUID DEFAULT gen_random_uuid(),
    household_id UUID NOT NULL REFERENCES households(id) ON DELETE CASCADE,
    name VARCHAR(150) NOT NULL,
    default_category_id INTEGER REFERENCES categories(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    PRIMARY KEY (id, household_id),
    CONSTRAINT uq_household_merchant UNIQUE (household_id, name)
);

CREATE TABLE IF NOT EXISTS vendor_rules (
    id SERIAL PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    household_id UUID REFERENCES households (id) ON DELETE CASCADE,
    vendor_regex TEXT NOT NULL,
    default_category_id INTEGER NOT NULL REFERENCES categories (id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_vendor_rules_user_id ON vendor_rules (user_id);
CREATE INDEX IF NOT EXISTS idx_vendor_rules_household_id ON vendor_rules (household_id) WHERE household_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_vendor_rules_default_category_id ON vendor_rules (default_category_id);

CREATE TABLE IF NOT EXISTS transactions (
    id SERIAL PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    household_id UUID REFERENCES households (id) ON DELETE CASCADE,
    amount NUMERIC(14, 2) NOT NULL,
    currency VARCHAR(10) NOT NULL DEFAULT 'USD',
    is_inflow BOOLEAN NOT NULL DEFAULT FALSE,
    record_date DATE NOT NULL,
    vendor_raw TEXT NOT NULL,
    tx_hash VARCHAR(255),
    dedupe_hash VARCHAR(64),
    category_id INTEGER REFERENCES categories (id) ON DELETE SET NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'parsed',
    raw_source VARCHAR(50) DEFAULT 'gmail_axis',
    raw_email_id VARCHAR(100),
    email_url TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_transactions_tx_hash UNIQUE (tx_hash),
    CONSTRAINT uq_transactions_dedupe_hash UNIQUE (dedupe_hash),
    CONSTRAINT chk_transaction_status CHECK (status IN ('parsed', 'needs_review', 'categorized'))
);

CREATE INDEX IF NOT EXISTS idx_transactions_user_id ON transactions (user_id);
CREATE INDEX IF NOT EXISTS idx_transactions_household_id ON transactions (household_id) WHERE household_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_transactions_category_id ON transactions (category_id) WHERE category_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_transactions_record_date ON transactions (record_date);
CREATE INDEX IF NOT EXISTS idx_transactions_user_record_date ON transactions (user_id, record_date);
CREATE INDEX IF NOT EXISTS idx_transactions_tx_hash ON transactions (tx_hash) WHERE tx_hash IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_transactions_dedupe_hash ON transactions (dedupe_hash) WHERE dedupe_hash IS NOT NULL;

CREATE TABLE IF NOT EXISTS llm_configs (
    user_id UUID PRIMARY KEY REFERENCES users (id) ON DELETE CASCADE,
    provider VARCHAR(50) NOT NULL,
    model_name VARCHAR(100) NOT NULL,
    encrypted_key TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

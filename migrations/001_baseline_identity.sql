-- Migration: 001_baseline_identity
-- Description: Baseline schema with identity management.
-- Preserves Kinde provider subject in users.idp_user_id while internal users.id is UUID.

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    idp_user_id VARCHAR(255) NOT NULL,
    email VARCHAR(255),
    telegram_chat_id VARCHAR(255),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_users_idp_user_id UNIQUE (idp_user_id),
    CONSTRAINT uq_users_email UNIQUE (email),
    CONSTRAINT uq_users_telegram_chat_id UNIQUE (telegram_chat_id)
);

CREATE INDEX IF NOT EXISTS idx_users_idp_user_id ON users (idp_user_id);
CREATE INDEX IF NOT EXISTS idx_users_email ON users (email);
CREATE INDEX IF NOT EXISTS idx_users_telegram_chat_id ON users (telegram_chat_id) WHERE telegram_chat_id IS NOT NULL;

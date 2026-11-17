-- Migration: 004_ingress
-- Description: Ingress pipelines, OAuth credentials, raw payload staging, and quarantine queue.

CREATE TABLE IF NOT EXISTS oauth_credentials (
    id SERIAL PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    source VARCHAR(50) NOT NULL,
    encrypted_access_token TEXT NOT NULL,
    encrypted_refresh_token TEXT NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    is_valid BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_oauth_credentials_user_id ON oauth_credentials (user_id);
CREATE INDEX IF NOT EXISTS idx_oauth_credentials_expires_at ON oauth_credentials (expires_at);
CREATE INDEX IF NOT EXISTS idx_oauth_credentials_user_source ON oauth_credentials (user_id, source);

CREATE TABLE IF NOT EXISTS ingress_sources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    household_id UUID REFERENCES households (id) ON DELETE CASCADE,
    source_type VARCHAR(50) NOT NULL,
    source_name VARCHAR(255) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'active',
    config JSONB NOT NULL DEFAULT '{}'::jsonb,
    last_ingested_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_ingress_source_status CHECK (status IN ('active', 'paused', 'error', 'revoked'))
);

CREATE INDEX IF NOT EXISTS idx_ingress_sources_user_id ON ingress_sources (user_id);
CREATE INDEX IF NOT EXISTS idx_ingress_sources_household_id ON ingress_sources (household_id) WHERE household_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_ingress_sources_status ON ingress_sources (status);

CREATE TABLE IF NOT EXISTS ingress_payloads (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    source_id UUID REFERENCES ingress_sources (id) ON DELETE SET NULL,
    source_type VARCHAR(50) NOT NULL,
    raw_payload TEXT NOT NULL,
    payload_hash VARCHAR(64),
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    error_reason TEXT,
    retry_count INTEGER NOT NULL DEFAULT 0,
    processed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_ingress_payload_status CHECK (status IN ('pending', 'processing', 'processed', 'quarantined', 'failed'))
);

CREATE INDEX IF NOT EXISTS idx_ingress_payloads_user_id ON ingress_payloads (user_id);
CREATE INDEX IF NOT EXISTS idx_ingress_payloads_user_status ON ingress_payloads (user_id, status);
CREATE INDEX IF NOT EXISTS idx_ingress_payloads_payload_hash ON ingress_payloads (payload_hash) WHERE payload_hash IS NOT NULL;

CREATE TABLE IF NOT EXISTS quarantined_emails (
    id SERIAL PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    ingress_payload_id UUID REFERENCES ingress_payloads (id) ON DELETE SET NULL,
    email_text TEXT NOT NULL,
    error_reason TEXT NOT NULL,
    resolved BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_quarantined_emails_user_id ON quarantined_emails (user_id);
CREATE INDEX IF NOT EXISTS idx_quarantined_emails_resolved ON quarantined_emails (resolved);
CREATE INDEX IF NOT EXISTS idx_quarantined_emails_ingress_payload_id ON quarantined_emails (ingress_payload_id) WHERE ingress_payload_id IS NOT NULL;

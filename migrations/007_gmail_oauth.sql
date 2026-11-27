-- Migration: 007_gmail_oauth
-- Description: Add household-scoped OAuth credentials for Gmail integration.

ALTER TABLE oauth_credentials
    ADD COLUMN IF NOT EXISTS account_email VARCHAR(255),
    ADD COLUMN IF NOT EXISTS scopes TEXT[],
    ADD COLUMN IF NOT EXISTS household_id UUID REFERENCES households(id) ON DELETE CASCADE;

CREATE UNIQUE INDEX IF NOT EXISTS uq_oauth_credentials_household_source
    ON oauth_credentials (household_id, source);

CREATE INDEX IF NOT EXISTS idx_oauth_credentials_household_id
    ON oauth_credentials (household_id) WHERE household_id IS NOT NULL;

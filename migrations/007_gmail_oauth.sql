-- Migration: 007_gmail_oauth
-- Description: Add household-scoped OAuth credentials for Gmail integration.

ALTER TABLE oauth_credentials
    ADD COLUMN IF NOT EXISTS account_email VARCHAR(255),
    ADD COLUMN IF NOT EXISTS scopes TEXT[],
    ADD COLUMN IF NOT EXISTS household_id UUID REFERENCES households(id) ON DELETE CASCADE;

-- Backfill household_id from household_members for pre-existing credentials
UPDATE oauth_credentials oc
SET household_id = hm.household_id
FROM household_members hm
WHERE oc.user_id = hm.user_id
  AND oc.household_id IS NULL
  AND NOT EXISTS (
      SELECT 1 FROM oauth_credentials existing
      WHERE existing.household_id = hm.household_id
        AND existing.source = oc.source
  );

CREATE UNIQUE INDEX IF NOT EXISTS uq_oauth_credentials_household_source
    ON oauth_credentials (household_id, source);

CREATE INDEX IF NOT EXISTS idx_oauth_credentials_household_id
    ON oauth_credentials (household_id) WHERE household_id IS NOT NULL;

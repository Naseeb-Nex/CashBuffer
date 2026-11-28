-- Migration: 007_gmail_oauth
-- Description: Add household-scoped OAuth credentials for Gmail integration.

ALTER TABLE oauth_credentials
    ADD COLUMN IF NOT EXISTS account_email VARCHAR(255),
    ADD COLUMN IF NOT EXISTS scopes TEXT[],
    ADD COLUMN IF NOT EXISTS household_id UUID REFERENCES households(id) ON DELETE CASCADE;

-- Deterministic, collision-safe backfill of household_id for pre-existing credentials.
-- Rule:
-- 1. For each user, select primary household prioritizing owner role, then oldest membership.
-- 2. Across all candidate credentials for a (household_id, source), pick at most one row
--    prioritizing valid credentials, then most recently updated/created.
-- 3. Users without household or competing duplicate credentials remain with household_id NULL.
WITH primary_user_households AS (
    SELECT DISTINCT ON (user_id)
        user_id,
        household_id
    FROM household_members
    ORDER BY user_id, (role = 'owner') DESC, joined_at ASC
),
ranked_creds AS (
    SELECT DISTINCT ON (puh.household_id, oc.source)
        oc.id AS cred_id,
        puh.household_id
    FROM oauth_credentials oc
    JOIN primary_user_households puh ON oc.user_id = puh.user_id
    WHERE oc.household_id IS NULL
    ORDER BY puh.household_id, oc.source, (oc.is_valid = TRUE) DESC, oc.updated_at DESC, oc.created_at DESC, oc.id ASC
)
UPDATE oauth_credentials oc
SET household_id = rc.household_id
FROM ranked_creds rc
WHERE oc.id = rc.cred_id
  AND NOT EXISTS (
      SELECT 1 FROM oauth_credentials existing
      WHERE existing.household_id = rc.household_id
        AND existing.source = oc.source
  );

CREATE UNIQUE INDEX IF NOT EXISTS uq_oauth_credentials_household_source
    ON oauth_credentials (household_id, source);

CREATE INDEX IF NOT EXISTS idx_oauth_credentials_household_id
    ON oauth_credentials (household_id) WHERE household_id IS NOT NULL;

-- Migration: 002_household
-- Description: Household structure for shared / multi-tenant financial contexts.

CREATE TABLE IF NOT EXISTS households (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    created_by UUID REFERENCES users (id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS household_members (
    household_id UUID NOT NULL REFERENCES households (id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    role VARCHAR(50) NOT NULL DEFAULT 'member',
    joined_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (household_id, user_id),
    CONSTRAINT chk_household_member_role CHECK (role IN ('owner', 'admin', 'member'))
);

CREATE INDEX IF NOT EXISTS idx_households_created_by ON households (created_by);
CREATE INDEX IF NOT EXISTS idx_household_members_user_id ON household_members (user_id);

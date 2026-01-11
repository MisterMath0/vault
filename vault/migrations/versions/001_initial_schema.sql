-- ============================================================================
-- Vault Initial Schema - Migration 001
-- ============================================================================
-- This migration creates all the core tables for Vault multi-tenant RBAC
-- Source of truth: vault_* tables (syncs to/from Supabase auth.users)
-- ============================================================================

-- ============================================================================
-- USERS (Source of Truth - syncs TO Supabase auth.users)
-- ============================================================================
CREATE TABLE IF NOT EXISTS vault_users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Core identity
    email TEXT UNIQUE NOT NULL,
    email_verified BOOLEAN DEFAULT FALSE,
    phone TEXT,
    phone_verified BOOLEAN DEFAULT FALSE,

    -- Auth provider tracking (for sync)
    supabase_auth_id UUID UNIQUE,  -- Links to auth.users.id when synced
    auth_provider TEXT DEFAULT 'email',  -- email, google, github, etc.

    -- Profile (extensible by user)
    display_name TEXT,
    avatar_url TEXT,
    metadata JSONB DEFAULT '{}',  -- User can add ANY fields here

    -- Status
    status TEXT DEFAULT 'active',  -- active, suspended, deleted
    last_sign_in_at TIMESTAMPTZ,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for fast Supabase sync lookups
CREATE INDEX IF NOT EXISTS idx_vault_users_supabase_auth_id ON vault_users(supabase_auth_id);
CREATE INDEX IF NOT EXISTS idx_vault_users_email ON vault_users(email);
CREATE INDEX IF NOT EXISTS idx_vault_users_status ON vault_users(status);

-- ============================================================================
-- ORGANIZATIONS
-- ============================================================================
CREATE TABLE IF NOT EXISTS vault_organizations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    slug TEXT UNIQUE NOT NULL,

    -- Settings (billing tier, feature flags, etc.)
    settings JSONB DEFAULT '{}',
    metadata JSONB DEFAULT '{}',

    -- Status
    status TEXT DEFAULT 'active',  -- active, suspended, deleted

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_vault_organizations_slug ON vault_organizations(slug);
CREATE INDEX IF NOT EXISTS idx_vault_organizations_status ON vault_organizations(status);

-- ============================================================================
-- ROLES (per organization)
-- ============================================================================
CREATE TABLE IF NOT EXISTS vault_roles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID REFERENCES vault_organizations(id) ON DELETE CASCADE,

    name TEXT NOT NULL,
    description TEXT,

    -- Permissions as array: ["posts:read", "posts:write", "users:*"]
    permissions TEXT[] DEFAULT '{}',

    -- Is this the default role for new members?
    is_default BOOLEAN DEFAULT FALSE,

    -- System roles can't be deleted (owner, admin)
    is_system BOOLEAN DEFAULT FALSE,

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(organization_id, name)
);

CREATE INDEX IF NOT EXISTS idx_vault_roles_org_id ON vault_roles(organization_id);
CREATE INDEX IF NOT EXISTS idx_vault_roles_is_default ON vault_roles(is_default);

-- ============================================================================
-- MEMBERSHIPS (User <-> Organization with Role)
-- ============================================================================
CREATE TABLE IF NOT EXISTS vault_memberships (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- References OUR users table, not auth.users
    user_id UUID REFERENCES vault_users(id) ON DELETE CASCADE,
    organization_id UUID REFERENCES vault_organizations(id) ON DELETE CASCADE,
    role_id UUID REFERENCES vault_roles(id) ON DELETE SET NULL,

    status TEXT DEFAULT 'active',  -- active, suspended, pending

    -- Metadata for this membership
    metadata JSONB DEFAULT '{}',

    joined_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(user_id, organization_id)
);

CREATE INDEX IF NOT EXISTS idx_vault_memberships_user_id ON vault_memberships(user_id);
CREATE INDEX IF NOT EXISTS idx_vault_memberships_org_id ON vault_memberships(organization_id);
CREATE INDEX IF NOT EXISTS idx_vault_memberships_role_id ON vault_memberships(role_id);
CREATE INDEX IF NOT EXISTS idx_vault_memberships_status ON vault_memberships(status);

-- ============================================================================
-- INVITATIONS
-- ============================================================================
CREATE TABLE IF NOT EXISTS vault_invitations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID REFERENCES vault_organizations(id) ON DELETE CASCADE,

    email TEXT NOT NULL,
    role_id UUID REFERENCES vault_roles(id),

    -- Who sent the invite (references OUR users table)
    invited_by UUID REFERENCES vault_users(id),

    -- Token for accepting
    token TEXT UNIQUE NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,

    -- Tracking
    accepted_at TIMESTAMPTZ,
    accepted_by UUID REFERENCES vault_users(id),

    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for token lookups
CREATE INDEX IF NOT EXISTS idx_vault_invitations_token ON vault_invitations(token);
CREATE INDEX IF NOT EXISTS idx_vault_invitations_org_id ON vault_invitations(organization_id);
CREATE INDEX IF NOT EXISTS idx_vault_invitations_email ON vault_invitations(email);

-- ============================================================================
-- AUDIT LOG
-- ============================================================================
CREATE TABLE IF NOT EXISTS vault_audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Context
    organization_id UUID REFERENCES vault_organizations(id),
    user_id UUID REFERENCES vault_users(id),

    -- What happened
    action TEXT NOT NULL,  -- user.created, member.added, role.assigned, etc.
    resource_type TEXT,    -- user, organization, role, etc.
    resource_id UUID,

    -- Details
    metadata JSONB DEFAULT '{}',
    ip_address INET,
    user_agent TEXT,

    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for querying by org
CREATE INDEX IF NOT EXISTS idx_vault_audit_log_org ON vault_audit_log(organization_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_vault_audit_log_user ON vault_audit_log(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_vault_audit_log_action ON vault_audit_log(action);

-- ============================================================================
-- MIGRATION TRACKING
-- ============================================================================
CREATE TABLE IF NOT EXISTS vault_migrations (
    id SERIAL PRIMARY KEY,
    version TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    applied_at TIMESTAMPTZ DEFAULT NOW()
);

-- Record this migration
INSERT INTO vault_migrations (version, name)
VALUES ('001', 'initial_schema')
ON CONFLICT (version) DO NOTHING;

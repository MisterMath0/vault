-- ============================================================================
-- Vault Webhooks and API Keys - Migration 002
-- ============================================================================
-- Adds tables for webhooks, webhook deliveries, and API keys
-- ============================================================================

-- ============================================================================
-- WEBHOOKS
-- ============================================================================
CREATE TABLE IF NOT EXISTS vault_webhooks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID REFERENCES vault_organizations(id) ON DELETE CASCADE,

    -- Webhook configuration
    url TEXT NOT NULL,
    secret TEXT NOT NULL,  -- For HMAC signature verification
    description TEXT,

    -- Events to listen for (array of event names)
    events TEXT[] DEFAULT '{}',

    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    failure_count INTEGER DEFAULT 0,
    last_triggered_at TIMESTAMPTZ,
    last_success_at TIMESTAMPTZ,
    last_failure_at TIMESTAMPTZ,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_vault_webhooks_org_id ON vault_webhooks(organization_id);
CREATE INDEX IF NOT EXISTS idx_vault_webhooks_is_active ON vault_webhooks(is_active);

-- ============================================================================
-- WEBHOOK DELIVERIES (for tracking delivery attempts)
-- ============================================================================
CREATE TABLE IF NOT EXISTS vault_webhook_deliveries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    webhook_id UUID REFERENCES vault_webhooks(id) ON DELETE CASCADE,
    event TEXT NOT NULL,

    -- Request details
    request_url TEXT NOT NULL,
    request_headers JSONB DEFAULT '{}',
    request_body JSONB DEFAULT '{}',

    -- Response details
    response_status INTEGER,
    response_body TEXT,
    response_time_ms INTEGER,

    -- Status
    success BOOLEAN DEFAULT FALSE,
    error_message TEXT,
    attempt_number INTEGER DEFAULT 1,

    -- Timestamp
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_vault_webhook_deliveries_webhook_id ON vault_webhook_deliveries(webhook_id);
CREATE INDEX IF NOT EXISTS idx_vault_webhook_deliveries_created_at ON vault_webhook_deliveries(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_vault_webhook_deliveries_success ON vault_webhook_deliveries(success);

-- ============================================================================
-- API KEYS (for service-to-service authentication)
-- ============================================================================
CREATE TABLE IF NOT EXISTS vault_api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID REFERENCES vault_organizations(id) ON DELETE CASCADE,

    -- Key identification
    name TEXT NOT NULL,
    description TEXT,
    key_prefix TEXT NOT NULL,  -- First 8 chars of key for identification
    key_hash TEXT NOT NULL,    -- bcrypt hash of the full key

    -- Permissions
    scopes TEXT[] DEFAULT '{}',  -- Allowed permissions for this key

    -- Rate limiting
    rate_limit INTEGER,  -- Requests per minute (NULL = unlimited)

    -- Status and tracking
    is_active BOOLEAN DEFAULT TRUE,
    last_used_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(organization_id, name)
);

CREATE INDEX IF NOT EXISTS idx_vault_api_keys_org_id ON vault_api_keys(organization_id);
CREATE INDEX IF NOT EXISTS idx_vault_api_keys_key_prefix ON vault_api_keys(key_prefix);
CREATE INDEX IF NOT EXISTS idx_vault_api_keys_is_active ON vault_api_keys(is_active);

-- ============================================================================
-- API KEY USAGE LOG (for tracking key usage)
-- ============================================================================
CREATE TABLE IF NOT EXISTS vault_api_key_usage (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    api_key_id UUID REFERENCES vault_api_keys(id) ON DELETE CASCADE,

    -- Request details
    endpoint TEXT,
    method TEXT,
    ip_address INET,
    user_agent TEXT,

    -- Response
    response_status INTEGER,

    -- Timestamp
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_vault_api_key_usage_key_id ON vault_api_key_usage(api_key_id);
CREATE INDEX IF NOT EXISTS idx_vault_api_key_usage_created_at ON vault_api_key_usage(created_at DESC);

-- Record this migration
INSERT INTO vault_migrations (version, name)
VALUES ('002', 'webhooks_and_api_keys')
ON CONFLICT (version) DO NOTHING;

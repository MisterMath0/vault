# Vault: Multi-tenant Organization Auth Library

## Vision
An open-source Python library that provides dead-simple multi-tenant RBAC (Role-Based Access Control) for organizations. Uses Supabase as the auth provider but keeps YOUR data in YOUR tables. Users shouldn't need to know Postgres, write SQL, or understand Supabase internals.

---

## Core Philosophy: Data Sovereignty

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         VAULT TABLES (Source of Truth)                      │
│                     User owns this data - fully portable                    │
│                                                                             │
│  ┌──────────────┐  ┌──────────────────┐  ┌─────────────┐  ┌─────────────┐  │
│  │ vault_users  │  │ vault_orgs       │  │ vault_roles │  │ vault_perms │  │
│  │              │  │                  │  │             │  │             │  │
│  │ - id visibil │  │ - id             │  │ - id        │  │ - id        │  │
│  │ - email      │  │ - name           │  │ - name      │  │ - action    │  │
│  │ - metadata   │  │ - slug           │  │ - org_id    │  │ - resource  │  │
│  │ - status     │  │ - settings       │  │ - perms[]   │  │             │  │
│  │ - provider_* │  │                  │  │             │  │             │  │
│  └──────┬───────┘  └──────────────────┘  └─────────────┘  └─────────────┘  │
│         │                                                                   │
│         │  ┌───────────────────┐  ┌─────────────────┐                       │
│         │  │ vault_memberships │  │ vault_invites   │                       │
│         └──│ - user_id ────────│  │ - email         │                       │
│            │ - org_id          │  │ - org_id        │                       │
│            │ - role_id         │  │ - role_id       │                       │
│            └───────────────────┘  └─────────────────┘                       │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ SYNC LAYER (bidirectional)
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    SUPABASE AUTH (Provider Layer)                           │
│              Handles: sessions, OAuth, magic links, MFA                     │
│                                                                             │
│  auth.users ◄──── synced from vault_users                                   │
│  auth.sessions    (managed by Supabase)                                     │
│                                                                             │
│  On OAuth/Magic Link login ───► sync back to vault_users                    │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Why This Approach?

1. **Portability** - Switch from Supabase to Auth0, Firebase, or self-hosted tomorrow
2. **Extensibility** - Add any columns you want to `vault_users` (phone, avatar, preferences, etc.)
3. **No vendor lock-in** - Your user data isn't trapped in Supabase's schema
4. **Easy migrations** - Export `vault_*` tables and you have everything
5. **Framework agnostic** - Works the same whether you use Supabase Cloud or self-hosted

---

## Core Problems We're Solving

1. **Auth providers own your user data** - you're locked into their schema
2. **Multi-tenant RBAC is complex** - most solutions are proprietary (WorkOS, Auth0 Organizations)
3. **Too much boilerplate** - invites, permissions, roles all require custom flows
4. **No CLI tooling** - everything requires dashboard or raw SQL
5. **Hard to migrate** - switching auth providers means rewriting everything

---

## Key Decisions

### 1. Database Schema: Vault-First with Sync

- `vault_users` is the source of truth for user data
- Syncs TO `auth.users` for Supabase auth to work
- Syncs FROM `auth.users` when OAuth/external login happens
- All relationships reference `vault_users.id`, not `auth.users.id`

### 2. Permission Model

**Option A: Simple RBAC**
```
Organization -> Roles -> Permissions
User -> Membership -> Role(s)
```

**Option B: Hierarchical RBAC (Recommended)**
```
Organization (can have sub-orgs/teams)
  -> Roles (inheritable)
    -> Permissions (resource:action format)
User -> Membership(s) -> Role(s)
```

**Option C: ABAC (Attribute-Based)**
- More flexible but more complex
- Probably overkill for v1

**Recommendation:** Start with Option A, design for Option B

### 3. Framework Integration

**Option A: Framework Agnostic (Recommended for v1)**
- Pure Python, works anywhere
- Provide decorators that work with any ASGI/WSGI
- Users bring their own web framework

**Option B: Framework-Specific Packages**
- `vault-fastapi`, `vault-flask`, `vault-django`
- More ergonomic but more maintenance

**Recommendation:** Core library agnostic, optional framework adapters later

### 4. CLI vs Programmatic

**Both.** CLI for admin tasks, library for runtime.

---

## Proposed Architecture

```
vault/
├── vault/
│   ├── __init__.py
│   ├── client.py              # Main Vault client
│   ├── config.py              # Configuration management
│   │
│   ├── auth/
│   │   ├── __init__.py
│   │   ├── users.py           # User management
│   │   ├── sessions.py        # Session handling
│   │   └── providers.py       # OAuth provider configs
│   │
│   ├── organizations/
│   │   ├── __init__.py
│   │   ├── orgs.py            # Organization CRUD
│   │   ├── members.py         # Membership management
│   │   └── invites.py         # Invitation system
│   │
│   ├── rbac/
│   │   ├── __init__.py
│   │   ├── roles.py           # Role management
│   │   ├── permissions.py     # Permission definitions
│   │   └── policies.py        # Policy evaluation
│   │
│   ├── decorators/
│   │   ├── __init__.py
│   │   ├── auth.py            # @require_auth
│   │   ├── permissions.py     # @require_permission("read:posts")
│   │   └── org.py             # @require_org_member, @require_org_role
│   │
│   ├── migrations/
│   │   ├── __init__.py
│   │   ├── manager.py         # Migration runner
│   │   └── versions/          # SQL migration files
│   │
│   ├── cli/
│   │   ├── __init__.py
│   │   ├── main.py            # CLI entry point
│   │   ├── commands/
│   │   │   ├── init.py        # vault init
│   │   │   ├── migrate.py     # vault migrate
│   │   │   ├── users.py       # vault users list/create/delete
│   │   │   ├── orgs.py        # vault orgs create/list
│   │   │   ├── roles.py       # vault roles create/assign
│   │   │   └── invites.py     # vault invite send
│   │
│   └── utils/
│       ├── __init__.py
│       └── supabase.py        # Supabase client wrapper
│
├── tests/
├── pyproject.toml
├── README.md
└── docs/
```

---

## Database Schema (Vault-First)

```sql
-- ============================================================================
-- USERS (Source of Truth - syncs TO Supabase auth.users)
-- ============================================================================
CREATE TABLE vault_users (
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
CREATE INDEX idx_vault_users_supabase_auth_id ON vault_users(supabase_auth_id);

-- ============================================================================
-- ORGANIZATIONS
-- ============================================================================
CREATE TABLE vault_organizations (
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

-- ============================================================================
-- ROLES (per organization)
-- ============================================================================
CREATE TABLE vault_roles (
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

-- ============================================================================
-- MEMBERSHIPS (User <-> Organization with Role)
-- ============================================================================
CREATE TABLE vault_memberships (
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

-- ============================================================================
-- INVITATIONS
-- ============================================================================
CREATE TABLE vault_invitations (
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
CREATE INDEX idx_vault_invitations_token ON vault_invitations(token);

-- ============================================================================
-- AUDIT LOG
-- ============================================================================
CREATE TABLE vault_audit_log (
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
CREATE INDEX idx_vault_audit_log_org ON vault_audit_log(organization_id, created_at DESC);
```

---

## Sync Layer: How It Works

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              SYNC SCENARIOS                                  │
└─────────────────────────────────────────────────────────────────────────────┘

1. USER CREATED VIA VAULT (email/password signup)
   ────────────────────────────────────────────────
   vault.users.create(email, password)
        │
        ├──► INSERT into vault_users (our table)
        │
        └──► supabase.auth.admin.create_user(email, password)
                  │
                  └──► UPDATE vault_users SET supabase_auth_id = auth.users.id


2. USER SIGNS IN VIA OAUTH (Google, GitHub, etc.)
   ────────────────────────────────────────────────
   supabase.auth.sign_in_with_oauth('google')
        │
        └──► Supabase creates auth.users record
                  │
        ┌─────────┴─────────┐
        │  Webhook/Trigger  │  (on auth.users INSERT)
        └─────────┬─────────┘
                  │
                  └──► UPSERT into vault_users
                       - email from auth.users
                       - supabase_auth_id = auth.users.id
                       - auth_provider = 'google'


3. USER UPDATED VIA VAULT
   ────────────────────────────────────────────────
   vault.users.update(user_id, display_name="New Name")
        │
        ├──► UPDATE vault_users (our table)
        │
        └──► supabase.auth.admin.update_user(
                supabase_auth_id,
                user_metadata={display_name: "New Name"}
             )


4. SESSION VALIDATION
   ────────────────────────────────────────────────
   @require_auth decorator
        │
        ├──► Validate JWT with Supabase
        │         (supabase.auth.get_user(token))
        │
        └──► Fetch full user from vault_users
             WHERE supabase_auth_id = jwt.sub
```

---

## API Design (What Users Will Write)

### Initialization
```python
from vault import Vault

vault = Vault(
    supabase_url="https://xxx.supabase.co",
    supabase_key="your-service-key",
    # or from env vars automatically
)
```

### User Management
```python
# Create user with org
user = await vault.users.create(
    email="user@example.com",
    password="secure123",
    organization="acme-corp",
    role="admin"
)

# Invite user
await vault.invites.send(
    email="newuser@example.com",
    organization="acme-corp",
    role="member",
    message="Welcome to our team!"  # Custom message
)

# List users in org
users = await vault.users.list(organization="acme-corp")
```

### Organizations
```python
# Create org
org = await vault.orgs.create(
    name="Acme Corp",
    slug="acme-corp"
)

# Add member
await vault.orgs.add_member(
    organization="acme-corp",
    user_id=user.id,
    role="editor"
)
```

### RBAC
```python
# Define roles
await vault.roles.create(
    organization="acme-corp",
    name="editor",
    permissions=["read:posts", "write:posts", "read:comments"]
)

# Check permission
can_write = await vault.can(user, "write:posts", org="acme-corp")
```

### Decorators (FastAPI example)
```python
from vault.decorators import require_auth, require_permission, require_org_role

@app.get("/posts")
@require_auth
async def list_posts(user: VaultUser):
    return {"posts": [...]}

@app.post("/posts")
@require_permission("write:posts")
async def create_post(user: VaultUser, post: Post):
    return {"created": True}

@app.delete("/org/{org_id}")
@require_org_role("admin")
async def delete_org(user: VaultUser, org_id: str):
    return {"deleted": True}
```

---

## CLI Commands

```bash
# Initialize vault in project
vault init

# Run migrations
vault migrate

# User management
vault users list --org acme-corp
vault users create --email user@example.com --org acme-corp --role admin
vault users delete user@example.com

# Organization management
vault orgs create "Acme Corp" --slug acme-corp
vault orgs list
vault orgs members acme-corp

# Role management
vault roles create editor --org acme-corp --permissions "read:*,write:posts"
vault roles list --org acme-corp
vault roles assign user@example.com editor --org acme-corp

# Invitations
vault invite user@example.com --org acme-corp --role member
vault invites list --org acme-corp --pending
```

---

## Things You'll Need to Learn/Use

### Must Have
1. **Supabase Python SDK** (`supabase-py`) - for auth and database
2. **Click or Typer** - for CLI (recommend Typer, more modern)
3. **Pydantic** - for data validation and settings
4. **Python async/await** - Supabase SDK is async

### Good to Know
5. **PostgreSQL basics** - for writing migrations
6. **JWT tokens** - understanding how Supabase auth works
7. **RBAC patterns** - for good permission design

### For Quality
8. **pytest + pytest-asyncio** - testing
9. **Ruff** - linting/formatting
10. **GitHub Actions** - CI/CD

---

## Implementation Phases

### Phase 1: Foundation
- [ ] Project setup (pyproject.toml, structure)
- [ ] Configuration management (env vars, config file)
- [ ] Supabase client wrapper
- [ ] Migration system
- [ ] Basic CLI (`vault init`, `vault migrate`)

### Phase 2: Core Auth
- [ ] User CRUD (create, read, update, delete)
- [ ] Session management
- [ ] Basic decorators (@require_auth)
- [ ] CLI commands for users

### Phase 3: Organizations
- [ ] Organization CRUD
- [ ] Membership management
- [ ] CLI commands for orgs

### Phase 4: RBAC
- [ ] Role management
- [ ] Permission system
- [ ] Permission checking decorators
- [ ] Policy evaluation

### Phase 5: Advanced Features
- [ ] Invitation system with email
- [ ] Audit logging
- [ ] Webhooks
- [ ] API keys for service-to-service

### Phase 6: Polish
- [ ] Documentation
- [ ] Framework-specific adapters (FastAPI, Flask)
- [ ] Examples and tutorials
- [ ] PyPI publishing

---

## Open Questions

1. **Sync vs Async?** - Should the library be async-first or support both?
   - Recommendation: Async-first with sync wrappers

2. **Email sending?** - Should we handle email for invites or let users bring their own?
   - Recommendation: Let Supabase handle it via their email templates, we just trigger

3. **Token storage?** - Where do we store refresh tokens?
   - Recommendation: Leave to the user's framework (cookies, localStorage, etc.)

4. **Multi-database?** - Should we support multiple Supabase projects?
   - Recommendation: Not for v1, one project per Vault instance

---

## Similar Projects to Study

1. **Ory (Kratos, Keto)** - Open source identity, good permission model
2. **Casbin** - Permission library, good policy patterns
3. **Django-organizations** - Django-specific but good UX patterns
4. **Permit.io** - Commercial but good API design inspiration

---

## Next Steps

1. Set up the project structure
2. Create the pyproject.toml with dependencies
3. Implement the configuration system
4. Build the migration system
5. Start with `vault init` CLI command

Ready to start coding?

# Vault

**Multi-tenant RBAC library with Supabase integration** - Keep YOUR data in YOUR tables.

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Why Vault?

Most auth providers lock your user data into their schema. Vault gives you:

- **Data Sovereignty** - Your users live in `vault_users`, not hidden in auth provider tables
- **Multi-tenant RBAC** - Organizations, roles, and permissions out of the box
- **No Vendor Lock-in** - Switch from Supabase to Auth0 or self-hosted tomorrow
- **Simple API** - No SQL, no complex configs, just Python

```python
from vault import Vault

async with await Vault.create() as vault:
    # Create a user
    user = await vault.users.create(
        email="user@example.com",
        password="secure123"
    )

    # Create an organization
    org = await vault.orgs.create(
        name="Acme Corp",
        slug="acme-corp"
    )

    # Add user with a role
    await vault.memberships.create(user.id, org.id, role_id=admin_role.id)

    # Check permissions
    can_write = await vault.permissions.check(user.id, org.id, "posts:write")
```

## Installation

```bash
pip install vault
```

## Quick Start

### 1. Initialize Vault

```bash
# Create .env file with Supabase credentials
vault init
```

### 2. Run Migrations

Apply the schema to your Supabase database:

```bash
vault migrate
```

### 3. Start Using Vault

```python
from vault import Vault

async def main():
    vault = await Vault.create()

    # Create your first user
    user = await vault.users.create(
        email="admin@example.com",
        password="secure-password",
        display_name="Admin User"
    )

    # Create an organization
    org = await vault.orgs.create(
        name="My Company",
        slug="my-company"
    )

    # Initialize system roles (Owner, Admin, Member)
    await vault.roles.create_system_roles(org.id)

    # Add user as owner
    owner_role = await vault.roles.get_by_name(org.id, "Owner")
    await vault.memberships.create(user.id, org.id, role_id=owner_role.id)

    await vault.close()
```

## Features

### User Management

```python
# Create users
user = await vault.users.create(
    email="user@example.com",
    password="secure123",
    display_name="John Doe",
    metadata={"department": "Engineering"}
)

# Authentication
session = await vault.sessions.sign_in_with_password(
    email="user@example.com",
    password="secure123"
)

# Get current user from token
user = await vault.sessions.get_user_from_token(session.access_token)
```

### Organizations & Memberships

```python
# Create organization
org = await vault.orgs.create(
    name="Acme Corp",
    slug="acme-corp",
    settings={"billing_tier": "pro"}
)

# Add members
await vault.memberships.create(
    user_id=user.id,
    organization_id=org.id,
    role_id=member_role.id
)

# List members
members = await vault.memberships.list_by_organization(org.id)
```

### Roles & Permissions

```python
# Create custom role
editor_role = await vault.roles.create(
    organization_id=org.id,
    name="Editor",
    permissions=["posts:read", "posts:write", "comments:*"]
)

# Check permissions
can_edit = await vault.permissions.check(user.id, org.id, "posts:write")
can_any = await vault.permissions.check_any(user.id, org.id, ["posts:write", "posts:delete"])

# Wildcard support
# "posts:*" matches posts:read, posts:write, posts:delete
# "*:read" matches posts:read, users:read, etc.
```

### Invitations

```python
# Send invitation
invite = await vault.invites.create(
    organization_id=org.id,
    email="newuser@example.com",
    role_id=member_role.id,
    invited_by=admin_user.id
)

# Accept invitation
await vault.invites.accept(
    token=invite.token,
    user_id=new_user.id
)
```

### Audit Logging

```python
from vault import AuditAction, ResourceType

# Log an action
await vault.audit.log(
    action=AuditAction.USER_CREATED,
    user_id=admin.id,
    organization_id=org.id,
    resource_type=ResourceType.USER,
    resource_id=new_user.id,
    metadata={"email": new_user.email}
)

# Query audit log
entries = await vault.audit.list_by_organization(
    organization_id=org.id,
    action=AuditAction.USER_CREATED,
    since=datetime(2024, 1, 1)
)
```

### Webhooks

```python
from vault import WebhookEvent

# Register webhook
webhook = await vault.webhooks.create(
    url="https://example.com/webhooks/vault",
    events=[WebhookEvent.USER_CREATED, WebhookEvent.MEMBER_ADDED],
    organization_id=org.id
)

# Trigger webhook (automatic on events, or manual)
await vault.webhooks.trigger(
    event=WebhookEvent.USER_CREATED,
    organization_id=org.id,
    data={"user_id": str(user.id), "email": user.email}
)
```

### API Keys

```python
# Create API key for service-to-service auth
key = await vault.api_keys.create(
    name="backend-service",
    organization_id=org.id,
    scopes=["users:read", "orgs:read"],
    rate_limit=1000  # requests per minute
)
# IMPORTANT: Save key.key - it's only shown once!

# Validate API key
result = await vault.api_keys.validate(
    key="vk_xxxxx...",
    required_scopes=["users:read"]
)
if result.valid:
    print(f"Key belongs to org: {result.api_key.organization_id}")
```

## Decorators (FastAPI Example)

```python
from fastapi import FastAPI, Depends
from vault.decorators import require_auth, require_permission, require_org_role

app = FastAPI()

# Require authentication
@app.get("/me")
@require_auth
async def get_me(user: VaultUser):
    return {"email": user.email}

# Require specific permission
@app.post("/posts")
@require_permission("posts:write")
async def create_post(user: VaultUser, post: PostCreate):
    return {"created": True}

# Require organization role
@app.delete("/org/{org_id}")
@require_org_role("Owner")
async def delete_org(user: VaultUser, org_id: str):
    return {"deleted": True}
```

## CLI Reference

```bash
# Project setup
vault init              # Initialize Vault in your project
vault migrate           # Run database migrations
vault status            # Show migration status

# User management
vault users create --email user@example.com --password secret
vault users list
vault users get <user-id>
vault users delete <user-id>

# Organization management
vault orgs create "Acme Corp" --slug acme-corp
vault orgs list
vault orgs get <slug>
vault orgs members <org-id>
vault orgs add-member --org <org-id> --user <user-id>
vault orgs remove-member --org <org-id> --user <user-id>

# Role management
vault roles create "Editor" --org <org-id> --permissions "posts:*,comments:read"
vault roles list --org <org-id>
vault roles init-system --org <org-id>  # Create Owner, Admin, Member
vault roles assign <user-email> <role-name> --org <org-id>

# Invitations
vault invites send user@example.com --org <org-id> --role <role-id>
vault invites list --org <org-id>
vault invites revoke <invite-id>

# API Keys
vault api-keys create "backend-service" --org <org-id> --scopes "users:read,orgs:read"
vault api-keys list --org <org-id>
vault api-keys revoke <key-id>
vault api-keys rotate <key-id>
```

## Architecture

Vault uses a "vault-first" architecture where your data lives in `vault_*` tables:

```text
┌─────────────────────────────────────────────────────────────┐
│                    VAULT TABLES (Source of Truth)           │
│                                                             │
│  vault_users ─────┬───── vault_organizations                │
│       │           │             │                           │
│       └───────────┼─────────────┼──── vault_memberships     │
│                   │             │                           │
│              vault_roles ───────┴──── vault_invitations     │
└─────────────────────────────────────────────────────────────┘
                              │
                              │ SYNC
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    SUPABASE AUTH                            │
│              (sessions, OAuth, magic links)                 │
└─────────────────────────────────────────────────────────────┘
```

## Configuration

Vault loads configuration from environment variables or `.env` file:

```bash
VAULT_SUPABASE_URL=https://xxx.supabase.co
VAULT_SUPABASE_KEY=your-service-role-key

# Optional
VAULT_SCHEMA=public          # PostgreSQL schema
VAULT_AUTO_MIGRATE=false     # Auto-run migrations
```

Or configure programmatically:

```python
vault = await Vault.create(
    supabase_url="https://xxx.supabase.co",
    supabase_key="your-service-role-key"
)
```

## Database Schema

Vault creates these tables in your database:

| Table                       | Purpose                        |
| --------------------------- | ------------------------------ |
| `vault_users`               | User profiles (source of truth)|
| `vault_organizations`       | Multi-tenant organizations     |
| `vault_roles`               | Roles per organization         |
| `vault_memberships`         | User-org relationships         |
| `vault_invitations`         | Pending invitations            |
| `vault_audit_log`           | Audit trail                    |
| `vault_webhooks`            | Webhook configurations         |
| `vault_webhook_deliveries`  | Webhook delivery history       |
| `vault_api_keys`            | API key configurations         |
| `vault_api_key_usage`       | API key usage tracking         |
| `vault_migrations`          | Migration tracking             |

## Development

```bash
# Clone the repository
git clone https://github.com/yourusername/vault
cd vault

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Format code
ruff check --fix .
black .
```

## License

MIT License - see [LICENSE](LICENSE) for details.

## Contributing

Contributions are welcome! Please read our contributing guidelines before submitting a PR.

"""
FastAPI application example with Vault integration.

This example demonstrates how to use Vault with FastAPI:
- Authentication via JWT tokens
- Permission-based route protection
- Role-based access control
- API key authentication

Run with:
    uvicorn examples.fastapi_app:app --reload
"""

from typing import Optional
from uuid import UUID

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel

from vault import Vault
from vault.auth.models import VaultUser
from vault.integrations.fastapi import VaultFastAPI, get_current_user, get_vault

# =================================================================
# FastAPI App Setup
# =================================================================

app = FastAPI(
    title="Vault Example API",
    description="Example API demonstrating Vault integration",
    version="1.0.0",
)

# Initialize Vault integration
vault_integration = VaultFastAPI(app)


# =================================================================
# Request/Response Models
# =================================================================


class UserCreate(BaseModel):
    email: str
    password: str
    display_name: Optional[str] = None


class UserResponse(BaseModel):
    id: UUID
    email: str
    display_name: Optional[str] = None


class OrgCreate(BaseModel):
    name: str
    slug: str


class OrgResponse(BaseModel):
    id: UUID
    name: str
    slug: str


class PostCreate(BaseModel):
    title: str
    content: str


class PostResponse(BaseModel):
    id: str
    title: str
    content: str
    author_id: UUID


# =================================================================
# Public Routes (No Auth Required)
# =================================================================


@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "ok", "service": "vault-example"}


@app.post("/auth/signup", response_model=UserResponse)
async def signup(user: UserCreate, vault: Vault = Depends(get_vault)):
    """Create a new user account."""
    new_user = await vault.users.create(
        email=user.email,
        password=user.password,
        display_name=user.display_name,
    )
    return UserResponse(
        id=new_user.id,
        email=new_user.email,
        display_name=new_user.display_name,
    )


@app.post("/auth/login")
async def login(email: str, password: str, vault: Vault = Depends(get_vault)):
    """Sign in and get access token."""
    try:
        session = await vault.sessions.sign_in_with_password(email, password)
        return {
            "access_token": session.access_token,
            "refresh_token": session.refresh_token,
            "expires_at": session.expires_at,
        }
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid credentials")


# =================================================================
# Protected Routes (Auth Required)
# =================================================================


@app.get("/me", response_model=UserResponse)
async def get_me(user: VaultUser = Depends(vault_integration.require_auth())):
    """Get current user profile."""
    return UserResponse(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
    )


@app.get("/users")
async def list_users(
    user: VaultUser = Depends(vault_integration.require_auth()),
    vault: Vault = Depends(get_vault),
):
    """List all users (requires authentication)."""
    users = await vault.users.list(limit=50)
    return [
        UserResponse(id=u.id, email=u.email, display_name=u.display_name)
        for u in users
    ]


# =================================================================
# Organization Routes
# =================================================================


@app.post("/orgs", response_model=OrgResponse)
async def create_org(
    org: OrgCreate,
    user: VaultUser = Depends(vault_integration.require_auth()),
    vault: Vault = Depends(get_vault),
):
    """Create a new organization."""
    new_org = await vault.orgs.create(name=org.name, slug=org.slug)

    # Initialize system roles
    await vault.roles.create_system_roles(new_org.id)

    # Make creating user the owner
    owner_role = await vault.roles.get_by_name(new_org.id, "Owner")
    await vault.memberships.create(
        user_id=user.id,
        organization_id=new_org.id,
        role_id=owner_role.id,
    )

    return OrgResponse(id=new_org.id, name=new_org.name, slug=new_org.slug)


@app.get("/orgs/{org_id}")
async def get_org(
    org_id: UUID,
    user: VaultUser = Depends(vault_integration.require_org_member()),
    vault: Vault = Depends(get_vault),
):
    """Get organization details (requires membership)."""
    org = await vault.orgs.get(org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    return OrgResponse(id=org.id, name=org.name, slug=org.slug)


@app.get("/orgs/{org_id}/members")
async def list_members(
    org_id: UUID,
    user: VaultUser = Depends(vault_integration.require_org_member()),
    vault: Vault = Depends(get_vault),
):
    """List organization members."""
    members = await vault.memberships.list_by_organization(org_id)
    result = []
    for m in members:
        member_user = await vault.users.get(m.user_id)
        if member_user:
            result.append(
                {
                    "user_id": m.user_id,
                    "email": member_user.email,
                    "role_id": m.role_id,
                    "joined_at": m.joined_at,
                }
            )
    return result


@app.delete("/orgs/{org_id}")
async def delete_org(
    org_id: UUID,
    user: VaultUser = Depends(vault_integration.require_role("Owner")),
    vault: Vault = Depends(get_vault),
):
    """Delete organization (Owner only)."""
    await vault.orgs.delete(org_id, soft_delete=False)
    return {"deleted": True}


# =================================================================
# Permission-Protected Routes
# =================================================================


@app.get("/orgs/{org_id}/posts")
async def list_posts(
    org_id: UUID,
    user: VaultUser = Depends(vault_integration.require_permission("posts:read")),
):
    """List posts (requires posts:read permission)."""
    # In a real app, you'd fetch from your posts table
    return [
        PostResponse(id="1", title="First Post", content="Hello!", author_id=user.id),
        PostResponse(id="2", title="Second Post", content="World!", author_id=user.id),
    ]


@app.post("/orgs/{org_id}/posts")
async def create_post(
    org_id: UUID,
    post: PostCreate,
    user: VaultUser = Depends(vault_integration.require_permission("posts:write")),
):
    """Create a post (requires posts:write permission)."""
    # In a real app, you'd insert into your posts table
    return PostResponse(
        id="new-post-id",
        title=post.title,
        content=post.content,
        author_id=user.id,
    )


@app.delete("/orgs/{org_id}/posts/{post_id}")
async def delete_post(
    org_id: UUID,
    post_id: str,
    user: VaultUser = Depends(vault_integration.require_permission("posts:delete")),
):
    """Delete a post (requires posts:delete permission)."""
    return {"deleted": True, "post_id": post_id}


# =================================================================
# API Key Protected Routes
# =================================================================


@app.get("/api/data")
async def get_api_data(
    api_key=Depends(vault_integration.require_api_key("data:read")),
):
    """Get data using API key authentication."""
    return {
        "data": [1, 2, 3, 4, 5],
        "api_key_name": api_key.name,
        "organization_id": str(api_key.organization_id),
    }


@app.post("/api/webhook")
async def receive_webhook(
    api_key=Depends(vault_integration.require_api_key("webhooks:receive")),
):
    """Receive webhook (API key auth)."""
    return {"received": True}


# =================================================================
# Admin Routes
# =================================================================


@app.get("/orgs/{org_id}/audit")
async def get_audit_log(
    org_id: UUID,
    user: VaultUser = Depends(vault_integration.require_role("Admin", "Owner")),
    vault: Vault = Depends(get_vault),
):
    """Get audit log (Admin or Owner only)."""
    entries = await vault.audit.list_by_organization(org_id, limit=100)
    return [
        {
            "id": e.id,
            "action": e.action,
            "user_id": e.user_id,
            "created_at": e.created_at,
        }
        for e in entries
    ]


@app.post("/orgs/{org_id}/invite")
async def send_invite(
    org_id: UUID,
    email: str,
    user: VaultUser = Depends(vault_integration.require_role("Admin", "Owner")),
    vault: Vault = Depends(get_vault),
):
    """Send invitation (Admin or Owner only)."""
    member_role = await vault.roles.get_by_name(org_id, "Member")

    invite = await vault.invites.create(
        organization_id=org_id,
        email=email,
        role_id=member_role.id if member_role else None,
        invited_by=user.id,
    )

    return {
        "id": invite.id,
        "email": invite.email,
        "token": invite.token,
        "expires_at": invite.expires_at,
    }

# Vault Development Guide

## Golden Rule

> **Never assume how supabase-py or supabase-auth works. Always read the actual package code in `venv/lib/python3.14/site-packages/` before implementing any feature.**

This is non-negotiable. The official docs can be outdated, incomplete, or wrong. The code is the truth.

---

## Package Locations

All installed packages live in:
```
venv/lib/python3.14/site-packages/
```

### Key Packages to Reference

| Package | Path | What It Contains |
|---------|------|------------------|
| `supabase` | `venv/.../supabase/` | Main client - combines auth, db, storage, realtime |
| `supabase_auth` | `venv/.../supabase_auth/` | Auth (GoTrue) - sign up, sign in, admin, MFA |
| `postgrest` | `venv/.../postgrest/` | Database queries via PostgREST |
| `storage3` | `venv/.../storage3/` | File storage |
| `realtime` | `venv/.../realtime/` | Realtime subscriptions |

---

## Package Structure (Actual)

### supabase_auth/ (The auth package we're wrapping)

```
supabase_auth/
├── __init__.py
├── types.py                      # ALL type definitions - CRITICAL FILE
├── errors.py                     # Exception classes
├── helpers.py                    # Utility functions
├── constants.py                  # Config constants
├── timer.py                      # Token refresh timer
│
├── _async/                       # ASYNC implementations (use these)
│   ├── __init__.py
│   ├── gotrue_client.py          # Main client: sign_up, sign_in_with_password, etc.
│   ├── gotrue_admin_api.py       # Admin API: create_user, delete_user, invite_user_by_email
│   ├── gotrue_base_api.py        # Base HTTP request handling
│   ├── gotrue_mfa_api.py         # MFA: enroll, challenge, verify
│   ├── gotrue_admin_mfa_api.py   # Admin MFA operations
│   ├── gotrue_admin_oauth_api.py # OAuth client management
│   └── storage.py                # Session storage (AsyncMemoryStorage)
│
└── _sync/                        # Sync wrappers (mirror of _async)
    └── ... (same structure)
```

### supabase/ (Main package that combines everything)

```
supabase/
├── __init__.py                   # Exports create_client, Client
├── client.py                     # Sync client wrapper
├── types.py                      # Re-exports
│
├── _async/
│   ├── client.py                 # AsyncClient - the main entry point
│   └── auth_client.py            # AsyncSupabaseAuthClient wrapper
│
├── _sync/
│   └── ... (mirrors _async)
│
└── lib/
    └── client_options.py         # ClientOptions config
```

---

## Critical Files to Read First

Before writing ANY code, read these files in order:

### 1. `supabase_auth/types.py` (1062 lines)
Contains ALL types used in auth:
- `User`, `Session`, `UserResponse` - Core models
- `AdminUserAttributes` - For creating users via admin API
- `SignUpWithPasswordCredentials` - For sign_up
- `SignInWithPasswordCredentials` - For sign_in
- `Provider` - Literal type of all OAuth providers
- All MFA types, OAuth types, etc.

### 2. `supabase_auth/_async/gotrue_admin_api.py` (353 lines)
Admin operations we'll wrap heavily:
- `create_user(attributes: AdminUserAttributes) -> UserResponse`
- `list_users(page, per_page) -> List[User]`
- `get_user_by_id(uid: str) -> UserResponse`
- `update_user_by_id(uid, attributes) -> UserResponse`
- `delete_user(id, should_soft_delete) -> None`
- `invite_user_by_email(email, options) -> UserResponse`
- `generate_link(params) -> GenerateLinkResponse`

### 3. `supabase_auth/_async/gotrue_client.py` (1288 lines)
Client operations (user-facing):
- `sign_up(credentials) -> AuthResponse`
- `sign_in_with_password(credentials) -> AuthResponse`
- `sign_in_with_oauth(credentials) -> OAuthResponse`
- `sign_in_with_otp(credentials) -> AuthOtpResponse`
- `sign_out(options) -> None`
- `get_session() -> Optional[Session]`
- `get_user(jwt) -> Optional[UserResponse]`
- `update_user(attributes, options) -> UserResponse`
- `refresh_session(refresh_token) -> AuthResponse`
- MFA methods: `mfa.enroll`, `mfa.challenge`, `mfa.verify`

### 4. `supabase_auth/errors.py`
Exception classes to handle:
- `AuthApiError`
- `AuthInvalidCredentialsError`
- `AuthSessionMissingError`
- `AuthRetryableError`
- `AuthImplicitGrantRedirectError`

### 5. `supabase/_async/client.py` (383 lines)
How the main client is structured:
- `AsyncClient` class
- `create_client(url, key, options)` factory function
- How `auth` property is initialized
- How auth events trigger updates to other clients

---

## Before Implementing Any Feature

### Step 1: Identify which module handles it

| Task | Module | File |
|------|--------|------|
| Create user (admin) | supabase_auth | `_async/gotrue_admin_api.py` |
| Sign up user | supabase_auth | `_async/gotrue_client.py` |
| Sign in | supabase_auth | `_async/gotrue_client.py` |
| Delete user | supabase_auth | `_async/gotrue_admin_api.py` |
| Invite user | supabase_auth | `_async/gotrue_admin_api.py` |
| MFA enroll | supabase_auth | `_async/gotrue_client.py` (via mfa) |
| DB query | postgrest | `_async/...` |

### Step 2: Find the EXACT method signature

Open the file, find the method, document:
```python
# From gotrue_admin_api.py line 119
async def create_user(self, attributes: AdminUserAttributes) -> UserResponse:
```

### Step 3: Find the type definitions

Open `types.py`, find the types used:
```python
# AdminUserAttributes (line 249)
class AdminUserAttributes(UserAttributes, TypedDict):
    user_metadata: NotRequired[Any]
    app_metadata: NotRequired[Any]
    email_confirm: NotRequired[bool]
    phone_confirm: NotRequired[bool]
    ban_duration: NotRequired[Union[str, Literal["none"]]]
    role: NotRequired[str]
    password_hash: NotRequired[str]
    id: NotRequired[str]
```

### Step 4: Only then write your wrapper

---

## Example Workflow

**Task:** Implement `vault.users.create(email, password)`

**Step 1:** This is user creation → admin API

**Step 2:** Open `venv/lib/python3.14/site-packages/supabase_auth/_async/gotrue_admin_api.py`

**Step 3:** Find `create_user` method, read it:
```python
# Actually read what's there - don't assume!
async def create_user(self, attributes: AdminUserAttributes) -> UserResponse:
    ...
```

**Step 4:** Note:
- Takes `AdminUserAttributes` not raw email/password
- Returns `UserResponse`
- Check `types.py` for what `AdminUserAttributes` contains

**Step 5:** Now implement our wrapper knowing exactly what's underneath

---

## File Reading Commands

Quick reference for exploring packages:

```bash
# List all files in a package
ls -la venv/lib/python3.14/site-packages/supabase_auth/

# See structure
find venv/lib/python3.14/site-packages/supabase_auth -name "*.py" | head -20

# Search for a method
grep -r "def create_user" venv/lib/python3.14/site-packages/

# Search for a class
grep -r "class AdminUserAttributes" venv/lib/python3.14/site-packages/
```

---

## What NOT To Do

❌ Copy code from tutorials or Stack Overflow without verifying
❌ Assume method signatures from memory
❌ Trust that the README matches the implementation
❌ Use deprecated methods because old examples use them

## What TO Do

✅ Read the source file before writing any integration
✅ Check `types.py` for data structures
✅ Check `errors.py` for exception handling
✅ Verify async vs sync variants
✅ Note version-specific behavior in comments

---

## Package Version Tracking

Document which versions we're building against:

```bash
# Check installed versions
pip show supabase supabase-auth postgrest
```

Record in this section when starting:
- `supabase`: [version]
- `supabase-auth`: [version]
- `postgrest`: [version]

---

## Implementation Checklist

Before marking any feature complete:

- [ ] Read the underlying supabase package code
- [ ] Documented which files/methods we're wrapping
- [ ] Handled all relevant exceptions from `errors.py`
- [ ] Used correct types from `types.py`
- [ ] Tested with both async and sync (if applicable)
- [ ] Added reference comment pointing to source file

---

## Adding This Comment to Every Wrapper

Every function that wraps supabase should include:

```python
async def create_user(self, email: str, password: str) -> VaultUser:
    """
    Create a new user in Vault and sync to Supabase.

    Wraps: supabase_auth._async.gotrue_admin_api.GoTrueAdminAPI.create_user
    Source: venv/lib/python3.14/site-packages/supabase_auth/_async/gotrue_admin_api.py
    """
    ...
```

This creates a traceable link between our code and the underlying implementation.

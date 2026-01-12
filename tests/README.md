# Vault Test Suite

This directory contains comprehensive tests for the Vault package.

## Test Structure

The test suite is organized by module:

- `test_config.py` - Tests for configuration management (VaultConfig, load_config)
- `test_client.py` - Tests for the main Vault client initialization and lifecycle
- `test_auth.py` - Tests for authentication (UserManager, SessionManager)
- `test_organizations.py` - Tests for organizations and memberships
- `test_rbac.py` - Tests for RBAC (roles and permissions)
- `test_invitations.py` - Tests for invitation management
- `test_webhooks.py` - Tests for webhook management
- `test_apikeys.py` - Tests for API key management
- `test_audit.py` - Tests for audit logging
- `test_utils.py` - Tests for utility modules

## Test Fixtures

The `conftest.py` file provides shared fixtures:

- `mock_supabase_client` - Mock Supabase client
- `mock_vault_supabase_client` - Mock VaultSupabaseClient wrapper
- `vault_config` - Test VaultConfig instance
- `vault` - Test Vault instance with mocked dependencies
- Sample data fixtures for users, organizations, roles, memberships, etc.

## Running Tests

Run all tests:
```bash
pytest
```

Run with coverage:
```bash
pytest --cov=vault --cov-report=term-missing
```

Run specific test file:
```bash
pytest tests/test_auth.py
```

Run specific test:
```bash
pytest tests/test_auth.py::TestUserManager::test_create_user
```

## Test Coverage

The test suite covers:

- ✅ Configuration loading and validation
- ✅ Client initialization and lifecycle
- ✅ User CRUD operations
- ✅ Session management (sign in, sign out, refresh)
- ✅ Organization CRUD operations
- ✅ Membership management
- ✅ Role CRUD operations
- ✅ Permission checking (exact match, wildcards, multiple permissions)
- ✅ Invitation creation, acceptance, revocation
- ✅ Webhook creation, triggering, delivery tracking
- ✅ API key creation, validation, rotation
- ✅ Audit logging and querying
- ✅ Error handling and edge cases

## Mocking Strategy

The tests use extensive mocking of the Supabase client to avoid requiring a real Supabase instance. All database operations are mocked, allowing tests to run quickly and in isolation.

## Notes

- All tests use `pytest.mark.asyncio` for async test functions
- Tests are designed to be independent and can run in any order
- Mock responses are configured per-test to match expected behavior
- Edge cases and error conditions are tested alongside happy paths


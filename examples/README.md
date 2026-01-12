# Vault Examples

This directory contains example scripts demonstrating how to use Vault.

## Prerequisites

1. Install Vault:
   ```bash
   pip install vault
   ```

2. Set up environment variables (create `.env` in project root):
   ```bash
   VAULT_SUPABASE_URL=https://your-project.supabase.co
   VAULT_SUPABASE_KEY=your-service-role-key
   ```

3. Run migrations:
   ```bash
   vault migrate
   ```

## Examples

### Basic Usage

Demonstrates core Vault features: users, organizations, roles, and permissions.

```bash
python examples/basic_usage.py
```

### FastAPI Integration

A complete FastAPI application with Vault integration.

```bash
# Install FastAPI
pip install fastapi uvicorn

# Run the server
uvicorn examples.fastapi_app:app --reload

# Test endpoints
curl http://localhost:8000/
curl -X POST http://localhost:8000/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "password123"}'
```

### Webhooks

Demonstrates the webhook system for event notifications.

```bash
python examples/webhooks_example.py
```

### API Keys

Shows how to use API keys for service-to-service authentication.

```bash
python examples/api_keys_example.py
```

## Running All Examples

```bash
# Run each example
python examples/basic_usage.py
python examples/webhooks_example.py
python examples/api_keys_example.py
```

## Notes

- Examples create and delete test data automatically
- Comment out cleanup sections to keep data for inspection
- Use a test Supabase project, not production

"""
API Keys example demonstrating service-to-service authentication.

This example shows how to:
- Create API keys with scopes
- Validate API keys
- Rate limiting
- Key rotation

Run with:
    python examples/api_keys_example.py
"""

import asyncio

from vault import Vault


async def main():
    vault = await Vault.create()

    try:
        # =================================================================
        # Setup: Create organization
        # =================================================================
        print("Setting up organization...")

        org = await vault.orgs.create(
            name="API Key Test Org",
            slug="api-key-test-org",
        )
        print(f"  Created org: {org.slug}")

        # =================================================================
        # 1. Create API Key
        # =================================================================
        print("\nCreating API key...")

        # Create a key with specific scopes
        key = await vault.api_keys.create(
            name="backend-service",
            organization_id=org.id,
            description="API key for backend microservice",
            scopes=["users:read", "users:write", "orgs:read"],
            rate_limit=100,  # 100 requests per minute
            expires_in_days=90,  # Expires in 90 days
        )

        print(f"  Key ID: {key.id}")
        print(f"  Name: {key.name}")
        print(f"  Prefix: {key.key_prefix}")
        print(f"  Scopes: {key.scopes}")
        print(f"  Rate Limit: {key.rate_limit}/min")
        print(f"  Expires: {key.expires_at}")
        print()
        print("  " + "=" * 50)
        print(f"  API KEY: {key.key}")
        print("  " + "=" * 50)
        print("  IMPORTANT: Save this key! It cannot be retrieved again.")

        # Store the key for later use
        api_key_value = key.key

        # =================================================================
        # 2. Create Key Without Expiration
        # =================================================================
        print("\nCreating key without expiration...")

        permanent_key = await vault.api_keys.create(
            name="internal-service",
            organization_id=org.id,
            description="Internal service key (no expiration)",
            scopes=["*:*"],  # All permissions
        )
        print(f"  Created: {permanent_key.name}")
        print(f"  Scopes: {permanent_key.scopes}")
        print(f"  Expires: {permanent_key.expires_at or 'Never'}")

        # =================================================================
        # 3. List API Keys
        # =================================================================
        print("\nListing API keys...")

        keys = await vault.api_keys.list_by_organization(org.id)
        for k in keys:
            print(f"  - {k.name} ({k.key_prefix}) - Active: {k.is_active}")

        # =================================================================
        # 4. Validate API Key
        # =================================================================
        print("\nValidating API key...")

        result = await vault.api_keys.validate(
            key=api_key_value,
            required_scopes=["users:read"],
            log_usage=True,
            endpoint="/api/users",
            method="GET",
        )

        if result.valid:
            print(f"  ✓ Key is valid")
            print(f"  Organization: {result.api_key.organization_id}")
            print(f"  Remaining requests: {result.remaining_requests}")
        else:
            print(f"  ✗ Key is invalid: {result.error}")

        # =================================================================
        # 5. Test Scope Validation
        # =================================================================
        print("\nTesting scope validation...")

        # This should succeed (users:read is in scopes)
        result1 = await vault.api_keys.validate(
            key=api_key_value,
            required_scopes=["users:read"],
            log_usage=False,
        )
        print(f"  users:read - {'✓ Allowed' if result1.valid else '✗ Denied'}")

        # This should fail (posts:write is not in scopes)
        result2 = await vault.api_keys.validate(
            key=api_key_value,
            required_scopes=["posts:write"],
            log_usage=False,
        )
        print(f"  posts:write - {'✓ Allowed' if result2.valid else '✗ Denied'}")

        # Wildcard key should pass all scope checks
        result3 = await vault.api_keys.validate(
            key=permanent_key.key,
            required_scopes=["anything:goes"],
            log_usage=False,
        )
        print(f"  anything:goes (wildcard) - {'✓ Allowed' if result3.valid else '✗ Denied'}")

        # =================================================================
        # 6. Test Rate Limiting
        # =================================================================
        print("\nTesting rate limiting...")
        print("  (Making multiple requests to show rate limit tracking)")

        for i in range(5):
            result = await vault.api_keys.validate(
                key=api_key_value,
                log_usage=True,
                endpoint=f"/api/test/{i}",
                method="GET",
            )
            print(f"  Request {i + 1}: {result.remaining_requests} remaining")

        # =================================================================
        # 7. Get Usage History
        # =================================================================
        print("\nGetting usage history...")

        usage = await vault.api_keys.get_usage(key.id, limit=10)
        print(f"  Total usage records: {len(usage)}")
        for u in usage[:5]:
            print(f"  - {u.method} {u.endpoint} at {u.created_at}")

        # =================================================================
        # 8. Update API Key
        # =================================================================
        print("\nUpdating API key...")

        updated = await vault.api_keys.update(
            key.id,
            description="Updated: Backend service key",
            scopes=["users:read", "users:write", "orgs:*"],  # Added orgs:*
            rate_limit=200,  # Increased rate limit
        )
        print(f"  New scopes: {updated.scopes}")
        print(f"  New rate limit: {updated.rate_limit}/min")

        # =================================================================
        # 9. Rotate API Key
        # =================================================================
        print("\nRotating API key...")
        print("  (Generates new key, keeps settings)")

        rotated = await vault.api_keys.rotate(key.id)
        print(f"  Old prefix: {key.key_prefix}")
        print(f"  New prefix: {rotated.key_prefix}")
        print(f"  New key: {rotated.key}")
        print("  Old key is now invalid!")

        # Verify old key is invalid
        old_result = await vault.api_keys.validate(api_key_value, log_usage=False)
        print(f"  Old key valid: {old_result.valid}")

        # Verify new key works
        new_result = await vault.api_keys.validate(rotated.key, log_usage=False)
        print(f"  New key valid: {new_result.valid}")

        # =================================================================
        # 10. Revoke API Key
        # =================================================================
        print("\nRevoking API key...")

        await vault.api_keys.revoke(key.id)
        revoke_result = await vault.api_keys.validate(rotated.key, log_usage=False)
        print(f"  Key valid after revoke: {revoke_result.valid}")
        print(f"  Error: {revoke_result.error}")

        # =================================================================
        # 11. Cleanup
        # =================================================================
        print("\nCleaning up...")

        await vault.api_keys.delete(key.id)
        await vault.api_keys.delete(permanent_key.id)
        print("  Deleted API keys")

        await vault.orgs.delete(org.id, soft_delete=False)
        print("  Deleted organization")

        print("\nDone!")

    finally:
        await vault.close()


if __name__ == "__main__":
    asyncio.run(main())

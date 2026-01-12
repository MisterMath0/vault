"""
Basic Vault usage example.

This example demonstrates the core features of Vault:
- User creation and authentication
- Organization management
- Role-based access control

Run with:
    python examples/basic_usage.py
"""

import asyncio

from vault import Vault


async def main():
    # Create Vault client (loads config from .env)
    vault = await Vault.create()

    try:
        # =================================================================
        # 1. Create Users
        # =================================================================
        print("Creating users...")

        admin_user = await vault.users.create(
            email="admin@example.com",
            password="admin-password-123",
            display_name="Admin User",
            email_confirm=True,  # Auto-confirm email
        )
        print(f"  Created admin: {admin_user.email} (ID: {admin_user.id})")

        regular_user = await vault.users.create(
            email="user@example.com",
            password="user-password-123",
            display_name="Regular User",
            email_confirm=True,
        )
        print(f"  Created user: {regular_user.email} (ID: {regular_user.id})")

        # =================================================================
        # 2. Create Organization
        # =================================================================
        print("\nCreating organization...")

        org = await vault.orgs.create(
            name="Acme Corporation",
            slug="acme-corp",
            settings={"billing_tier": "pro", "max_users": 100},
        )
        print(f"  Created org: {org.name} (slug: {org.slug})")

        # =================================================================
        # 3. Initialize System Roles
        # =================================================================
        print("\nInitializing system roles...")

        roles = await vault.roles.create_system_roles(org.id)
        for role in roles:
            print(f"  Created role: {role.name}")

        # Get specific roles
        owner_role = await vault.roles.get_by_name(org.id, "Owner")
        admin_role = await vault.roles.get_by_name(org.id, "Admin")
        member_role = await vault.roles.get_by_name(org.id, "Member")

        # =================================================================
        # 4. Create Custom Role
        # =================================================================
        print("\nCreating custom role...")

        editor_role = await vault.roles.create(
            organization_id=org.id,
            name="Editor",
            description="Can read and write posts",
            permissions=["posts:read", "posts:write", "comments:*"],
        )
        print(f"  Created role: {editor_role.name}")
        print(f"  Permissions: {editor_role.permissions}")

        # =================================================================
        # 5. Add Members to Organization
        # =================================================================
        print("\nAdding members to organization...")

        # Admin user gets Owner role
        await vault.memberships.create(
            user_id=admin_user.id,
            organization_id=org.id,
            role_id=owner_role.id,
        )
        print(f"  Added {admin_user.email} as Owner")

        # Regular user gets Editor role
        await vault.memberships.create(
            user_id=regular_user.id,
            organization_id=org.id,
            role_id=editor_role.id,
        )
        print(f"  Added {regular_user.email} as Editor")

        # =================================================================
        # 6. Check Permissions
        # =================================================================
        print("\nChecking permissions...")

        # Check if regular user can write posts
        can_write_posts = await vault.permissions.check(
            regular_user.id, org.id, "posts:write"
        )
        print(f"  {regular_user.email} can write posts: {can_write_posts}")

        # Check if regular user can delete posts (should be False)
        can_delete_posts = await vault.permissions.check(
            regular_user.id, org.id, "posts:delete"
        )
        print(f"  {regular_user.email} can delete posts: {can_delete_posts}")

        # Check if admin is owner
        is_owner = await vault.permissions.is_owner(admin_user.id, org.id)
        print(f"  {admin_user.email} is owner: {is_owner}")

        # =================================================================
        # 7. Authentication
        # =================================================================
        print("\nTesting authentication...")

        session = await vault.sessions.sign_in_with_password(
            email="user@example.com",
            password="user-password-123",
        )
        print(f"  Signed in: {regular_user.email}")
        print(f"  Access token: {session.access_token[:20]}...")

        # Get user from token
        user_from_token = await vault.sessions.get_user_from_token(
            session.access_token
        )
        print(f"  User from token: {user_from_token.email}")

        # =================================================================
        # 8. List Resources
        # =================================================================
        print("\nListing resources...")

        users = await vault.users.list(limit=10)
        print(f"  Total users: {len(users)}")

        orgs = await vault.orgs.list(limit=10)
        print(f"  Total organizations: {len(orgs)}")

        members = await vault.memberships.list_by_organization(org.id)
        print(f"  Members in {org.slug}: {len(members)}")

        # =================================================================
        # 9. Cleanup (optional - comment out to keep data)
        # =================================================================
        print("\nCleaning up...")

        # Delete memberships (automatic with user/org deletion)
        await vault.users.delete(regular_user.id, soft_delete=False)
        await vault.users.delete(admin_user.id, soft_delete=False)
        print("  Deleted users")

        await vault.orgs.delete(org.id, soft_delete=False)
        print("  Deleted organization")

        print("\nDone!")

    finally:
        await vault.close()


if __name__ == "__main__":
    asyncio.run(main())

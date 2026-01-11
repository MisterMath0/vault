"""
Migration manager for Vault database schema.

Handles applying SQL migrations to the Supabase/PostgreSQL database.
"""

import os
from pathlib import Path
from typing import List, Optional

from ..utils.supabase import VaultSupabaseClient


class Migration:
    """Represents a single database migration."""

    def __init__(self, version: str, name: str, path: Path) -> None:
        """
        Initialize a migration.

        Args:
            version: Migration version (e.g., "001")
            name: Migration name (e.g., "initial_schema")
            path: Path to the SQL file
        """
        self.version = version
        self.name = name
        self.path = path

    @classmethod
    def from_file(cls, path: Path) -> "Migration":
        """
        Create a Migration from a file path.

        Args:
            path: Path to migration file (e.g., "001_initial_schema.sql")

        Returns:
            Migration instance

        Example:
            >>> Migration.from_file(Path("001_initial_schema.sql"))
            Migration(version="001", name="initial_schema")
        """
        # Parse filename: "001_initial_schema.sql" -> version="001", name="initial_schema"
        filename = path.stem  # removes .sql extension
        parts = filename.split("_", 1)

        if len(parts) != 2:
            raise ValueError(f"Invalid migration filename: {path.name}. Expected format: 001_name.sql")

        version, name = parts
        return cls(version=version, name=name, path=path)

    def read_sql(self) -> str:
        """
        Read the SQL content of the migration.

        Returns:
            SQL content as string
        """
        return self.path.read_text()

    def __repr__(self) -> str:
        return f"Migration(version={self.version}, name={self.name})"


class MigrationManager:
    """
    Manages database migrations for Vault.

    Discovers and applies SQL migrations from the migrations/versions directory.
    """

    def __init__(self, client: VaultSupabaseClient) -> None:
        """
        Initialize the migration manager.

        Args:
            client: Vault Supabase client
        """
        self.client = client
        self.migrations_dir = Path(__file__).parent / "versions"

    def discover_migrations(self) -> List[Migration]:
        """
        Discover all migration files in the versions directory.

        Returns:
            List of Migration objects, sorted by version

        Example:
            >>> manager = MigrationManager(client)
            >>> migrations = manager.discover_migrations()
            [Migration(version="001", name="initial_schema")]
        """
        if not self.migrations_dir.exists():
            return []

        migrations = []
        for path in self.migrations_dir.glob("*.sql"):
            try:
                migration = Migration.from_file(path)
                migrations.append(migration)
            except ValueError as e:
                print(f"Warning: Skipping invalid migration file: {e}")

        # Sort by version
        migrations.sort(key=lambda m: m.version)
        return migrations

    async def get_applied_migrations(self) -> List[str]:
        """
        Get list of already applied migration versions.

        Returns:
            List of applied migration versions

        Example:
            >>> applied = await manager.get_applied_migrations()
            ['001', '002']
        """
        try:
            result = await self.client.table("vault_migrations").select("version").execute()
            return [row["version"] for row in result.data]
        except Exception:
            # Table doesn't exist yet - no migrations applied
            return []

    async def apply_migration(self, migration: Migration) -> None:
        """
        Apply a single migration to the database.

        Args:
            migration: Migration to apply

        Raises:
            Exception: If migration fails to apply

        Example:
            >>> migration = Migration.from_file(Path("001_initial_schema.sql"))
            >>> await manager.apply_migration(migration)
        """
        print(f"Applying migration {migration.version}: {migration.name}")

        sql = migration.read_sql()

        # Execute the SQL via Supabase RPC
        # Note: We need to use the postgrest client directly for raw SQL
        # Split the SQL into individual statements and execute them
        # For now, we'll use a simple approach - in production, you might want
        # to use a proper SQL parser or psycopg2
        try:
            # Execute via raw SQL using the PostgREST client
            # Note: This is a simplified approach. For production, consider using
            # psycopg2 or the Supabase SQL editor API
            await self._execute_sql(sql)
            print(f"✓ Migration {migration.version} applied successfully")
        except Exception as e:
            print(f"✗ Migration {migration.version} failed: {e}")
            raise

    async def _execute_sql(self, sql: str) -> None:
        """
        Execute raw SQL against the database.

        This is a helper method that handles executing SQL migrations.
        In Supabase, we need to use the underlying PostgreSQL connection.

        Args:
            sql: SQL to execute

        Note:
            This is a simplified implementation. For production use,
            consider using psycopg2 or the Supabase Management API.
        """
        # For now, we'll use the RPC endpoint approach
        # In a real implementation, you'd want to:
        # 1. Use psycopg2 with the database connection string
        # 2. Or use Supabase Management API
        # 3. Or have users run migrations via Supabase dashboard initially

        # Since this is v1 and we want to keep it simple, we'll document
        # that users should run the initial migration manually or via
        # the Supabase dashboard, and we'll use this for tracking only

        # For now, just execute via RPC (requires creating a migration function)
        # This is a placeholder - we'll need to implement proper SQL execution
        raise NotImplementedError(
            "Direct SQL execution not yet implemented. "
            "Please run migrations manually via Supabase dashboard or psql. "
            "Migration SQL files are in vault/migrations/versions/"
        )

    async def migrate(self, target: Optional[str] = None) -> None:
        """
        Run all pending migrations up to the target version.

        Args:
            target: Target migration version (default: latest)

        Example:
            >>> # Run all pending migrations
            >>> await manager.migrate()
            >>>
            >>> # Run up to specific version
            >>> await manager.migrate(target="003")
        """
        # Discover all available migrations
        migrations = self.discover_migrations()

        if not migrations:
            print("No migrations found")
            return

        # Get already applied migrations
        applied = await self.get_applied_migrations()

        # Filter to pending migrations
        pending = [m for m in migrations if m.version not in applied]

        if target:
            # Only run migrations up to target
            pending = [m for m in pending if m.version <= target]

        if not pending:
            print("No pending migrations")
            return

        print(f"Found {len(pending)} pending migration(s)")

        # Apply each pending migration
        for migration in pending:
            await self.apply_migration(migration)

        print(f"\n✓ All migrations applied successfully")

    async def status(self) -> None:
        """
        Show migration status.

        Displays which migrations are applied and which are pending.

        Example:
            >>> await manager.status()
            Migration Status:
            [✓] 001_initial_schema
            [✓] 002_add_teams
            [ ] 003_add_webhooks
        """
        migrations = self.discover_migrations()
        applied = await self.get_applied_migrations()

        print("Migration Status:")
        print("-" * 50)

        for migration in migrations:
            status = "✓" if migration.version in applied else " "
            print(f"[{status}] {migration.version}_{migration.name}")

        pending_count = len([m for m in migrations if m.version not in applied])
        print("-" * 50)
        print(f"Total: {len(migrations)} migrations")
        print(f"Applied: {len(applied)}")
        print(f"Pending: {pending_count}")

"""
vault migrate command - Run database migrations.

Applies pending SQL migrations to your Supabase database.
"""

import asyncio
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from ...config import load_config
from ...migrations.manager import MigrationManager
from ...utils.supabase import VaultSupabaseClient

console = Console()


def migrate_command(
    target: Optional[str] = typer.Argument(
        None,
        help="Target migration version (default: latest)",
    ),
) -> None:
    """
    Run database migrations.

    Applies all pending migrations to your Supabase database.

    Example:
        $ vault migrate           # Run all pending migrations
        $ vault migrate 003       # Run migrations up to version 003
    """
    console.print("\n[bold cyan]Vault Migration[/bold cyan]\n")

    try:
        # Load configuration
        config = load_config()
        console.print("[green]✓[/green] Configuration loaded")

    except Exception as e:
        console.print(f"[red]Error loading configuration:[/red] {e}")
        console.print("\nRun [cyan]vault init[/cyan] to set up your configuration")
        raise typer.Exit(1)

    # Run migrations asynchronously
    asyncio.run(_run_migrations(config, target))


async def _run_migrations(config, target: Optional[str]) -> None:
    """
    Internal function to run migrations asynchronously.

    Args:
        config: Vault configuration
        target: Optional target migration version
    """
    try:
        # Create Supabase client
        client = await VaultSupabaseClient.create(config)
        console.print("[green]✓[/green] Connected to Supabase")

        # Create migration manager
        manager = MigrationManager(client)

        # Run migrations
        console.print()
        await manager.migrate(target=target)

    except NotImplementedError as e:
        console.print(f"\n[yellow]Note:[/yellow] {e}")
        console.print("\n[bold]Manual Migration Required[/bold]")
        console.print("For now, please apply migrations manually:")
        console.print("1. Open your Supabase dashboard")
        console.print("2. Go to SQL Editor")
        console.print("3. Copy and run the SQL from: [cyan]vault/migrations/versions/001_initial_schema.sql[/cyan]")
        console.print("\nOr use psql:")
        console.print("[cyan]psql <your-db-url> < vault/migrations/versions/001_initial_schema.sql[/cyan]")

    except Exception as e:
        console.print(f"\n[red]Error:[/red] {e}")
        raise typer.Exit(1)


def status_command() -> None:
    """
    Show migration status.

    Displays which migrations have been applied and which are pending.

    Example:
        $ vault status
    """
    console.print("\n[bold cyan]Vault Migration Status[/bold cyan]\n")

    try:
        # Load configuration
        config = load_config()

    except Exception as e:
        console.print(f"[red]Error loading configuration:[/red] {e}")
        console.print("\nRun [cyan]vault init[/cyan] to set up your configuration")
        raise typer.Exit(1)

    # Run status check asynchronously
    asyncio.run(_show_status(config))


async def _show_status(config) -> None:
    """
    Internal function to show migration status.

    Args:
        config: Vault configuration
    """
    try:
        # Create Supabase client
        client = await VaultSupabaseClient.create(config)

        # Create migration manager
        manager = MigrationManager(client)

        # Get migrations
        migrations = manager.discover_migrations()
        applied = await manager.get_applied_migrations()

        # Create a table for display
        table = Table(title="Migration Status")
        table.add_column("Status", style="cyan", width=8)
        table.add_column("Version", style="magenta")
        table.add_column("Name", style="green")

        for migration in migrations:
            status = "✓" if migration.version in applied else "pending"
            status_style = "green" if migration.version in applied else "yellow"

            table.add_row(
                f"[{status_style}]{status}[/{status_style}]",
                migration.version,
                migration.name,
            )

        console.print(table)

        # Summary
        pending_count = len([m for m in migrations if m.version not in applied])
        console.print(f"\nTotal: {len(migrations)} migrations")
        console.print(f"[green]Applied: {len(applied)}[/green]")
        console.print(f"[yellow]Pending: {pending_count}[/yellow]\n")

        if pending_count > 0:
            console.print("Run [cyan]vault migrate[/cyan] to apply pending migrations\n")

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)

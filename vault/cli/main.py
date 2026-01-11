"""
Vault CLI - Command-line interface for multi-tenant RBAC management.

Usage:
    vault init              Initialize Vault in your project
    vault migrate           Run database migrations
    vault status            Show migration status
"""

import typer
from rich.console import Console

from .commands import init, migrate

# Create the main Typer app
app = typer.Typer(
    name="vault",
    help="Multi-tenant RBAC library with Supabase integration",
    add_completion=False,
)

# Create a Rich console for pretty output
console = Console()

# Register commands
app.command(name="init")(init.init_command)
app.command(name="migrate")(migrate.migrate_command)
app.command(name="status")(migrate.status_command)


@app.callback()
def callback() -> None:
    """
    Vault - Multi-tenant RBAC for Python.

    Keep YOUR data in YOUR tables while using Supabase for auth.
    """
    pass


def main() -> None:
    """Entry point for the CLI."""
    app()


if __name__ == "__main__":
    main()

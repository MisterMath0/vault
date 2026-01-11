"""
Vault CLI - Command-line interface for multi-tenant RBAC management.

Usage:
    vault init              Initialize Vault in your project
    vault migrate           Run database migrations
    vault status            Show migration status
    vault users             Manage users
    vault orgs              Manage organizations
"""

import typer
from rich.console import Console

from .commands import init, migrate, orgs, users

# Create the main Typer app
app = typer.Typer(
    name="vault",
    help="Multi-tenant RBAC library with Supabase integration",
    add_completion=False,
)

# Create a Rich console for pretty output
console = Console()

# Register top-level commands
app.command(name="init")(init.init_command)
app.command(name="migrate")(migrate.migrate_command)
app.command(name="status")(migrate.status_command)

# Create users subcommand group
users_app = typer.Typer(help="Manage users")
users_app.command(name="create")(users.users_create_command)
users_app.command(name="list")(users.users_list_command)
users_app.command(name="get")(users.users_get_command)
users_app.command(name="delete")(users.users_delete_command)
app.add_typer(users_app, name="users")

# Create orgs subcommand group
orgs_app = typer.Typer(help="Manage organizations")
orgs_app.command(name="create")(orgs.orgs_create_command)
orgs_app.command(name="list")(orgs.orgs_list_command)
orgs_app.command(name="get")(orgs.orgs_get_command)
orgs_app.command(name="members")(orgs.orgs_members_command)
orgs_app.command(name="add-member")(orgs.orgs_add_member_command)
orgs_app.command(name="remove-member")(orgs.orgs_remove_member_command)
app.add_typer(orgs_app, name="orgs")


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

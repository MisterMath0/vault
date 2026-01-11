"""
vault users command - User management CLI.

Create, list, update, and delete users via command line.
"""

import asyncio
from typing import Optional
from uuid import UUID

import typer
from rich.console import Console
from rich.table import Table

from ...config import load_config
from ...client import Vault

console = Console()


def users_create_command(
    email: str = typer.Argument(..., help="User email address"),
    password: Optional[str] = typer.Option(
        None,
        "--password",
        "-p",
        help="User password (will prompt if not provided)",
        prompt=True,
        hide_input=True,
    ),
    display_name: Optional[str] = typer.Option(
        None,
        "--name",
        "-n",
        help="User display name",
    ),
    confirm: bool = typer.Option(
        False,
        "--confirm",
        "-c",
        help="Auto-confirm email (skip verification)",
    ),
) -> None:
    """
    Create a new user.

    Example:
        $ vault users create user@example.com --name "John Doe" --confirm
        $ vault users create admin@example.com -p mypassword -n "Admin User"
    """
    console.print("\n[bold cyan]Creating User[/bold cyan]\n")

    asyncio.run(_create_user(email, password, display_name, confirm))


async def _create_user(
    email: str,
    password: Optional[str],
    display_name: Optional[str],
    confirm: bool,
) -> None:
    """Internal async function to create user."""
    try:
        config = load_config()
        vault = await Vault.create()

        user = await vault.users.create(
            email=email,
            password=password,
            display_name=display_name,
            email_confirm=confirm,
        )

        console.print(f"[green]✓[/green] User created successfully!")
        console.print(f"\nID: [cyan]{user.id}[/cyan]")
        console.print(f"Email: [cyan]{user.email}[/cyan]")
        console.print(f"Display Name: [cyan]{user.display_name or 'N/A'}[/cyan]")
        console.print(f"Status: [cyan]{user.status}[/cyan]")
        console.print(f"Email Verified: [cyan]{user.email_verified}[/cyan]\n")

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


def users_list_command(
    limit: int = typer.Option(50, "--limit", "-l", help="Maximum users to return"),
    offset: int = typer.Option(0, "--offset", "-o", help="Number of users to skip"),
    status: Optional[str] = typer.Option(
        None,
        "--status",
        "-s",
        help="Filter by status (active, suspended, deleted)",
    ),
) -> None:
    """
    List all users.

    Example:
        $ vault users list
        $ vault users list --limit 10
        $ vault users list --status active
    """
    console.print("\n[bold cyan]Users[/bold cyan]\n")

    asyncio.run(_list_users(limit, offset, status))


async def _list_users(limit: int, offset: int, status: Optional[str]) -> None:
    """Internal async function to list users."""
    try:
        config = load_config()
        vault = await Vault.create()

        users = await vault.users.list(limit=limit, offset=offset, status=status)

        if not users:
            console.print("[yellow]No users found[/yellow]\n")
            return

        # Create table
        table = Table(title=f"Users (showing {len(users)})")
        table.add_column("Email", style="cyan")
        table.add_column("Display Name", style="green")
        table.add_column("Status", style="magenta")
        table.add_column("Verified", style="yellow")
        table.add_column("Created", style="blue")

        for user in users:
            table.add_row(
                user.email,
                user.display_name or "—",
                user.status,
                "✓" if user.email_verified else "✗",
                user.created_at.strftime("%Y-%m-%d"),
            )

        console.print(table)
        console.print()

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


def users_get_command(
    email: str = typer.Argument(..., help="User email address"),
) -> None:
    """
    Get a user by email.

    Example:
        $ vault users get user@example.com
    """
    console.print("\n[bold cyan]User Details[/bold cyan]\n")

    asyncio.run(_get_user(email))


async def _get_user(email: str) -> None:
    """Internal async function to get user."""
    try:
        config = load_config()
        vault = await Vault.create()

        user = await vault.users.get_by_email(email)

        if not user:
            console.print(f"[red]User not found:[/red] {email}\n")
            raise typer.Exit(1)

        console.print(f"ID: [cyan]{user.id}[/cyan]")
        console.print(f"Email: [cyan]{user.email}[/cyan]")
        console.print(f"Display Name: [cyan]{user.display_name or 'N/A'}[/cyan]")
        console.print(f"Status: [cyan]{user.status}[/cyan]")
        console.print(f"Email Verified: [cyan]{user.email_verified}[/cyan]")
        console.print(f"Auth Provider: [cyan]{user.auth_provider}[/cyan]")
        console.print(f"Created: [cyan]{user.created_at}[/cyan]")
        console.print(f"Updated: [cyan]{user.updated_at}[/cyan]")

        if user.last_sign_in_at:
            console.print(f"Last Sign In: [cyan]{user.last_sign_in_at}[/cyan]")

        if user.metadata:
            console.print(f"\nMetadata:")
            for key, value in user.metadata.items():
                console.print(f"  {key}: [cyan]{value}[/cyan]")

        console.print()

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


def users_delete_command(
    email: str = typer.Argument(..., help="User email address"),
    hard: bool = typer.Option(
        False,
        "--hard",
        help="Permanently delete (cannot be undone)",
    ),
    yes: bool = typer.Option(
        False,
        "--yes",
        "-y",
        help="Skip confirmation",
    ),
) -> None:
    """
    Delete a user.

    By default, performs a soft delete (marks as deleted).
    Use --hard for permanent deletion.

    Example:
        $ vault users delete user@example.com
        $ vault users delete user@example.com --hard --yes
    """
    console.print("\n[bold cyan]Delete User[/bold cyan]\n")

    asyncio.run(_delete_user(email, hard, yes))


async def _delete_user(email: str, hard: bool, yes: bool) -> None:
    """Internal async function to delete user."""
    try:
        config = load_config()
        vault = await Vault.create()

        user = await vault.users.get_by_email(email)

        if not user:
            console.print(f"[red]User not found:[/red] {email}\n")
            raise typer.Exit(1)

        # Confirm deletion
        if not yes:
            delete_type = "permanently delete" if hard else "soft delete"
            confirm = typer.confirm(
                f"Are you sure you want to {delete_type} {email}?"
            )
            if not confirm:
                console.print("[yellow]Cancelled[/yellow]\n")
                raise typer.Exit(0)

        await vault.users.delete(user.id, soft_delete=not hard)

        delete_msg = "permanently deleted" if hard else "marked as deleted"
        console.print(f"[green]✓[/green] User {delete_msg}: {email}\n")

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)

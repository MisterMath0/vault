"""
vault orgs command - Organization management CLI.

Create, list, and manage organizations via command line.
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


def orgs_create_command(
    name: str = typer.Argument(..., help="Organization name"),
    slug: str = typer.Argument(..., help="Unique organization slug (lowercase, hyphens)"),
    settings: Optional[str] = typer.Option(
        None,
        "--settings",
        "-s",
        help="Settings JSON (e.g., '{\"billing_tier\": \"pro\"}')",
    ),
    metadata: Optional[str] = typer.Option(
        None,
        "--metadata",
        "-m",
        help="Metadata JSON (e.g., '{\"industry\": \"tech\"}')",
    ),
) -> None:
    """
    Create a new organization.

    Example:
        $ vault orgs create "Acme Corp" acme-corp
        $ vault orgs create "My Org" my-org --settings '{"tier": "pro"}'
    """
    console.print("\n[bold cyan]Creating Organization[/bold cyan]\n")

    asyncio.run(_create_org(name, slug, settings, metadata))


async def _create_org(
    name: str,
    slug: str,
    settings: Optional[str],
    metadata: Optional[str],
) -> None:
    """Internal async function to create organization."""
    import json

    try:
        config = load_config()
        vault = await Vault.create()

        # Parse JSON strings if provided
        settings_dict = json.loads(settings) if settings else {}
        metadata_dict = json.loads(metadata) if metadata else {}

        org = await vault.orgs.create(
            name=name,
            slug=slug,
            settings=settings_dict,
            metadata=metadata_dict,
        )

        console.print(f"[green]✓[/green] Organization created successfully!")
        console.print(f"\nID: [cyan]{org.id}[/cyan]")
        console.print(f"Name: [cyan]{org.name}[/cyan]")
        console.print(f"Slug: [cyan]{org.slug}[/cyan]")
        console.print(f"Status: [cyan]{org.status}[/cyan]")

        if org.settings:
            console.print(f"Settings: [cyan]{org.settings}[/cyan]")
        if org.metadata:
            console.print(f"Metadata: [cyan]{org.metadata}[/cyan]")

        console.print(f"Created: [cyan]{org.created_at}[/cyan]\n")

    except json.JSONDecodeError as e:
        console.print(f"[red]Error:[/red] Invalid JSON: {e}")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


def orgs_list_command(
    limit: int = typer.Option(50, "--limit", "-l", help="Maximum orgs to return"),
    offset: int = typer.Option(0, "--offset", "-o", help="Number of orgs to skip"),
    status: Optional[str] = typer.Option(
        None,
        "--status",
        "-s",
        help="Filter by status (active, suspended, deleted)",
    ),
) -> None:
    """
    List all organizations.

    Example:
        $ vault orgs list
        $ vault orgs list --limit 10
        $ vault orgs list --status active
    """
    console.print("\n[bold cyan]Organizations[/bold cyan]\n")

    asyncio.run(_list_orgs(limit, offset, status))


async def _list_orgs(limit: int, offset: int, status: Optional[str]) -> None:
    """Internal async function to list organizations."""
    try:
        config = load_config()
        vault = await Vault.create()

        orgs = await vault.orgs.list(limit=limit, offset=offset, status=status)

        if not orgs:
            console.print("[yellow]No organizations found[/yellow]\n")
            return

        # Create table
        table = Table(title=f"Organizations (showing {len(orgs)})")
        table.add_column("Name", style="cyan")
        table.add_column("Slug", style="green")
        table.add_column("Status", style="magenta")
        table.add_column("Created", style="blue")

        for org in orgs:
            table.add_row(
                org.name,
                org.slug,
                org.status,
                org.created_at.strftime("%Y-%m-%d"),
            )

        console.print(table)
        console.print()

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


def orgs_get_command(
    slug: str = typer.Argument(..., help="Organization slug"),
) -> None:
    """
    Get an organization by slug.

    Example:
        $ vault orgs get acme-corp
    """
    console.print("\n[bold cyan]Organization Details[/bold cyan]\n")

    asyncio.run(_get_org(slug))


async def _get_org(slug: str) -> None:
    """Internal async function to get organization."""
    try:
        config = load_config()
        vault = await Vault.create()

        org = await vault.orgs.get_by_slug(slug)

        if not org:
            console.print(f"[red]Organization not found:[/red] {slug}\n")
            raise typer.Exit(1)

        console.print(f"ID: [cyan]{org.id}[/cyan]")
        console.print(f"Name: [cyan]{org.name}[/cyan]")
        console.print(f"Slug: [cyan]{org.slug}[/cyan]")
        console.print(f"Status: [cyan]{org.status}[/cyan]")
        console.print(f"Created: [cyan]{org.created_at}[/cyan]")
        console.print(f"Updated: [cyan]{org.updated_at}[/cyan]")

        if org.settings:
            console.print(f"\nSettings:")
            for key, value in org.settings.items():
                console.print(f"  {key}: [cyan]{value}[/cyan]")

        if org.metadata:
            console.print(f"\nMetadata:")
            for key, value in org.metadata.items():
                console.print(f"  {key}: [cyan]{value}[/cyan]")

        console.print()

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


def orgs_members_command(
    slug: str = typer.Argument(..., help="Organization slug"),
    limit: int = typer.Option(50, "--limit", "-l", help="Maximum members to return"),
    offset: int = typer.Option(0, "--offset", "-o", help="Number of members to skip"),
    status: Optional[str] = typer.Option(
        None,
        "--status",
        "-s",
        help="Filter by status (active, suspended, pending)",
    ),
) -> None:
    """
    List members of an organization.

    Example:
        $ vault orgs members acme-corp
        $ vault orgs members acme-corp --status active
    """
    console.print(f"\n[bold cyan]Members of {slug}[/bold cyan]\n")

    asyncio.run(_list_members(slug, limit, offset, status))


async def _list_members(
    slug: str,
    limit: int,
    offset: int,
    status: Optional[str],
) -> None:
    """Internal async function to list organization members."""
    try:
        config = load_config()
        vault = await Vault.create()

        # Get organization first
        org = await vault.orgs.get_by_slug(slug)
        if not org:
            console.print(f"[red]Organization not found:[/red] {slug}\n")
            raise typer.Exit(1)

        # List memberships
        memberships = await vault.memberships.list_by_organization(
            org.id,
            limit=limit,
            offset=offset,
            status=status,
        )

        if not memberships:
            console.print("[yellow]No members found[/yellow]\n")
            return

        # Create table
        table = Table(title=f"Members (showing {len(memberships)})")
        table.add_column("User ID", style="cyan")
        table.add_column("Role ID", style="green")
        table.add_column("Status", style="magenta")
        table.add_column("Joined", style="blue")

        for membership in memberships:
            table.add_row(
                str(membership.user_id),
                str(membership.role_id) if membership.role_id else "—",
                membership.status,
                membership.joined_at.strftime("%Y-%m-%d"),
            )

        console.print(table)
        console.print()

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


def orgs_add_member_command(
    slug: str = typer.Argument(..., help="Organization slug"),
    user_email: str = typer.Argument(..., help="User email to add"),
    role_id: Optional[str] = typer.Option(
        None,
        "--role",
        "-r",
        help="Role ID (UUID)",
    ),
) -> None:
    """
    Add a member to an organization.

    Example:
        $ vault orgs add-member acme-corp user@example.com
        $ vault orgs add-member acme-corp user@example.com --role <role-uuid>
    """
    console.print(f"\n[bold cyan]Adding Member to {slug}[/bold cyan]\n")

    asyncio.run(_add_member(slug, user_email, role_id))


async def _add_member(
    slug: str,
    user_email: str,
    role_id: Optional[str],
) -> None:
    """Internal async function to add member to organization."""
    try:
        config = load_config()
        vault = await Vault.create()

        # Get organization
        org = await vault.orgs.get_by_slug(slug)
        if not org:
            console.print(f"[red]Organization not found:[/red] {slug}\n")
            raise typer.Exit(1)

        # Get user
        user = await vault.users.get_by_email(user_email)
        if not user:
            console.print(f"[red]User not found:[/red] {user_email}\n")
            raise typer.Exit(1)

        # Create membership
        role_uuid = UUID(role_id) if role_id else None
        membership = await vault.memberships.create(
            user_id=user.id,
            organization_id=org.id,
            role_id=role_uuid,
        )

        console.print(f"[green]✓[/green] Member added successfully!")
        console.print(f"\nMembership ID: [cyan]{membership.id}[/cyan]")
        console.print(f"User: [cyan]{user_email}[/cyan]")
        console.print(f"Organization: [cyan]{slug}[/cyan]")
        console.print(f"Role ID: [cyan]{membership.role_id or 'None'}[/cyan]")
        console.print(f"Status: [cyan]{membership.status}[/cyan]\n")

    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


def orgs_remove_member_command(
    slug: str = typer.Argument(..., help="Organization slug"),
    user_email: str = typer.Argument(..., help="User email to remove"),
    yes: bool = typer.Option(
        False,
        "--yes",
        "-y",
        help="Skip confirmation",
    ),
) -> None:
    """
    Remove a member from an organization.

    Example:
        $ vault orgs remove-member acme-corp user@example.com
        $ vault orgs remove-member acme-corp user@example.com --yes
    """
    console.print(f"\n[bold cyan]Removing Member from {slug}[/bold cyan]\n")

    asyncio.run(_remove_member(slug, user_email, yes))


async def _remove_member(
    slug: str,
    user_email: str,
    yes: bool,
) -> None:
    """Internal async function to remove member from organization."""
    try:
        config = load_config()
        vault = await Vault.create()

        # Get organization
        org = await vault.orgs.get_by_slug(slug)
        if not org:
            console.print(f"[red]Organization not found:[/red] {slug}\n")
            raise typer.Exit(1)

        # Get user
        user = await vault.users.get_by_email(user_email)
        if not user:
            console.print(f"[red]User not found:[/red] {user_email}\n")
            raise typer.Exit(1)

        # Confirm removal
        if not yes:
            confirm = typer.confirm(
                f"Remove {user_email} from {slug}?"
            )
            if not confirm:
                console.print("[yellow]Cancelled[/yellow]\n")
                raise typer.Exit(0)

        # Remove membership
        await vault.memberships.delete_by_user_and_org(
            user_id=user.id,
            organization_id=org.id,
        )

        console.print(f"[green]✓[/green] Member removed: {user_email}\n")

    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)

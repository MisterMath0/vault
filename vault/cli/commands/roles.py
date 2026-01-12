"""
vault roles command - Role management CLI.

Create, list, and manage roles via command line.
"""

import asyncio
import json
from typing import List, Optional
from uuid import UUID

import typer
from rich.console import Console
from rich.table import Table

from ...client import Vault

console = Console()


def roles_create_command(
    org_slug: str = typer.Argument(..., help="Organization slug"),
    name: str = typer.Argument(..., help="Role name"),
    permissions: Optional[str] = typer.Option(
        None,
        "--permissions",
        "-p",
        help='Permissions JSON array (e.g., \'["posts:read", "posts:write"]\')',
    ),
    description: Optional[str] = typer.Option(
        None,
        "--description",
        "-d",
        help="Role description",
    ),
    default: bool = typer.Option(
        False,
        "--default",
        help="Set as default role for new members",
    ),
) -> None:
    """
    Create a new role.

    Example:
        $ vault roles create acme-corp Editor --permissions '["posts:read", "posts:write"]'
        $ vault roles create acme-corp Viewer --permissions '["read:*"]' --default
        $ vault roles create acme-corp Admin --permissions '["admin:*"]' -d "Administrator"
    """
    console.print("\n[bold cyan]Creating Role[/bold cyan]\n")

    asyncio.run(_create_role(org_slug, name, permissions, description, default))


async def _create_role(
    org_slug: str,
    name: str,
    permissions: Optional[str],
    description: Optional[str],
    default: bool,
) -> None:
    """Internal async function to create role."""
    try:
        vault = await Vault.create()

        # Get organization first
        org = await vault.orgs.get_by_slug(org_slug)
        if not org:
            console.print(f"[red]Organization not found:[/red] {org_slug}\n")
            raise typer.Exit(1)

        # Parse permissions
        perms: List[str] = []
        if permissions:
            perms = json.loads(permissions)

        role = await vault.roles.create(
            organization_id=org.id,
            name=name,
            permissions=perms,
            description=description,
            is_default=default,
        )

        console.print(f"[green]✓[/green] Role created successfully!")
        console.print(f"\nID: [cyan]{role.id}[/cyan]")
        console.print(f"Name: [cyan]{role.name}[/cyan]")
        console.print(f"Organization: [cyan]{org_slug}[/cyan]")
        if role.description:
            console.print(f"Description: [cyan]{role.description}[/cyan]")
        console.print(f"Permissions: [cyan]{role.permissions}[/cyan]")
        console.print(f"Default: [cyan]{role.is_default}[/cyan]")
        console.print(f"System: [cyan]{role.is_system}[/cyan]")
        console.print(f"Created: [cyan]{role.created_at}[/cyan]\n")

    except json.JSONDecodeError as e:
        console.print(f"[red]Error:[/red] Invalid JSON: {e}")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


def roles_list_command(
    org_slug: str = typer.Argument(..., help="Organization slug"),
    limit: int = typer.Option(50, "--limit", "-l", help="Maximum roles to return"),
    offset: int = typer.Option(0, "--offset", "-o", help="Number of roles to skip"),
    all_roles: bool = typer.Option(
        True,
        "--all/--custom-only",
        help="Include system roles",
    ),
) -> None:
    """
    List roles for an organization.

    Example:
        $ vault roles list acme-corp
        $ vault roles list acme-corp --custom-only
        $ vault roles list acme-corp --limit 10
    """
    console.print(f"\n[bold cyan]Roles for {org_slug}[/bold cyan]\n")

    asyncio.run(_list_roles(org_slug, limit, offset, all_roles))


async def _list_roles(
    org_slug: str,
    limit: int,
    offset: int,
    include_system: bool,
) -> None:
    """Internal async function to list roles."""
    try:
        vault = await Vault.create()

        # Get organization first
        org = await vault.orgs.get_by_slug(org_slug)
        if not org:
            console.print(f"[red]Organization not found:[/red] {org_slug}\n")
            raise typer.Exit(1)

        roles = await vault.roles.list_by_organization(
            org.id,
            limit=limit,
            offset=offset,
            include_system=include_system,
        )

        if not roles:
            console.print("[yellow]No roles found[/yellow]\n")
            return

        # Create table
        table = Table(title=f"Roles (showing {len(roles)})")
        table.add_column("Name", style="cyan")
        table.add_column("Description", style="white")
        table.add_column("Permissions", style="green")
        table.add_column("Default", style="magenta")
        table.add_column("System", style="blue")

        for role in roles:
            perms_str = ", ".join(role.permissions[:3])
            if len(role.permissions) > 3:
                perms_str += f" (+{len(role.permissions) - 3} more)"

            table.add_row(
                role.name,
                role.description or "—",
                perms_str or "—",
                "✓" if role.is_default else "—",
                "✓" if role.is_system else "—",
            )

        console.print(table)
        console.print()

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


def roles_get_command(
    org_slug: str = typer.Argument(..., help="Organization slug"),
    name: str = typer.Argument(..., help="Role name"),
) -> None:
    """
    Get a role by name.

    Example:
        $ vault roles get acme-corp Editor
        $ vault roles get acme-corp Admin
    """
    console.print("\n[bold cyan]Role Details[/bold cyan]\n")

    asyncio.run(_get_role(org_slug, name))


async def _get_role(org_slug: str, name: str) -> None:
    """Internal async function to get role."""
    try:
        vault = await Vault.create()

        # Get organization first
        org = await vault.orgs.get_by_slug(org_slug)
        if not org:
            console.print(f"[red]Organization not found:[/red] {org_slug}\n")
            raise typer.Exit(1)

        role = await vault.roles.get_by_name(org.id, name)

        if not role:
            console.print(f"[red]Role not found:[/red] {name}\n")
            raise typer.Exit(1)

        console.print(f"ID: [cyan]{role.id}[/cyan]")
        console.print(f"Name: [cyan]{role.name}[/cyan]")
        console.print(f"Organization: [cyan]{org_slug}[/cyan]")
        if role.description:
            console.print(f"Description: [cyan]{role.description}[/cyan]")
        console.print(f"Default: [cyan]{role.is_default}[/cyan]")
        console.print(f"System: [cyan]{role.is_system}[/cyan]")
        console.print(f"Created: [cyan]{role.created_at}[/cyan]")
        console.print(f"Updated: [cyan]{role.updated_at}[/cyan]")

        console.print("\n[bold]Permissions:[/bold]")
        if role.permissions:
            for perm in role.permissions:
                console.print(f"  • [green]{perm}[/green]")
        else:
            console.print("  [yellow]No permissions[/yellow]")

        console.print()

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


def roles_update_command(
    org_slug: str = typer.Argument(..., help="Organization slug"),
    name: str = typer.Argument(..., help="Role name"),
    new_name: Optional[str] = typer.Option(
        None,
        "--name",
        "-n",
        help="New role name",
    ),
    permissions: Optional[str] = typer.Option(
        None,
        "--permissions",
        "-p",
        help='Permissions JSON array (replaces existing)',
    ),
    description: Optional[str] = typer.Option(
        None,
        "--description",
        "-d",
        help="New description",
    ),
    default: Optional[bool] = typer.Option(
        None,
        "--default/--no-default",
        help="Set as default role",
    ),
) -> None:
    """
    Update a role.

    Example:
        $ vault roles update acme-corp Editor --permissions '["posts:*"]'
        $ vault roles update acme-corp Editor --name "Content Editor"
        $ vault roles update acme-corp Viewer --default
    """
    console.print("\n[bold cyan]Updating Role[/bold cyan]\n")

    asyncio.run(_update_role(org_slug, name, new_name, permissions, description, default))


async def _update_role(
    org_slug: str,
    name: str,
    new_name: Optional[str],
    permissions: Optional[str],
    description: Optional[str],
    default: Optional[bool],
) -> None:
    """Internal async function to update role."""
    try:
        vault = await Vault.create()

        # Get organization first
        org = await vault.orgs.get_by_slug(org_slug)
        if not org:
            console.print(f"[red]Organization not found:[/red] {org_slug}\n")
            raise typer.Exit(1)

        # Get role
        role = await vault.roles.get_by_name(org.id, name)
        if not role:
            console.print(f"[red]Role not found:[/red] {name}\n")
            raise typer.Exit(1)

        # Parse permissions
        perms: Optional[List[str]] = None
        if permissions:
            perms = json.loads(permissions)

        updated = await vault.roles.update(
            role_id=role.id,
            name=new_name,
            permissions=perms,
            description=description,
            is_default=default,
        )

        console.print(f"[green]✓[/green] Role updated successfully!")
        console.print(f"\nID: [cyan]{updated.id}[/cyan]")
        console.print(f"Name: [cyan]{updated.name}[/cyan]")
        if updated.description:
            console.print(f"Description: [cyan]{updated.description}[/cyan]")
        console.print(f"Permissions: [cyan]{updated.permissions}[/cyan]")
        console.print(f"Default: [cyan]{updated.is_default}[/cyan]")
        console.print(f"Updated: [cyan]{updated.updated_at}[/cyan]\n")

    except json.JSONDecodeError as e:
        console.print(f"[red]Error:[/red] Invalid JSON: {e}")
        raise typer.Exit(1)
    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


def roles_delete_command(
    org_slug: str = typer.Argument(..., help="Organization slug"),
    name: str = typer.Argument(..., help="Role name"),
    yes: bool = typer.Option(
        False,
        "--yes",
        "-y",
        help="Skip confirmation",
    ),
) -> None:
    """
    Delete a role.

    System roles (Owner, Admin, Member) cannot be deleted.

    Example:
        $ vault roles delete acme-corp Editor
        $ vault roles delete acme-corp Editor --yes
    """
    console.print("\n[bold cyan]Deleting Role[/bold cyan]\n")

    asyncio.run(_delete_role(org_slug, name, yes))


async def _delete_role(org_slug: str, name: str, yes: bool) -> None:
    """Internal async function to delete role."""
    try:
        vault = await Vault.create()

        # Get organization first
        org = await vault.orgs.get_by_slug(org_slug)
        if not org:
            console.print(f"[red]Organization not found:[/red] {org_slug}\n")
            raise typer.Exit(1)

        # Get role
        role = await vault.roles.get_by_name(org.id, name)
        if not role:
            console.print(f"[red]Role not found:[/red] {name}\n")
            raise typer.Exit(1)

        if role.is_system:
            console.print(f"[red]Error:[/red] Cannot delete system role: {name}\n")
            raise typer.Exit(1)

        # Confirm deletion
        if not yes:
            confirm = typer.confirm(
                f"Delete role '{name}' from {org_slug}? Members with this role will lose it."
            )
            if not confirm:
                console.print("[yellow]Cancelled[/yellow]\n")
                raise typer.Exit(0)

        await vault.roles.delete(role.id)

        console.print(f"[green]✓[/green] Role deleted: {name}\n")

    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


def roles_add_permission_command(
    org_slug: str = typer.Argument(..., help="Organization slug"),
    name: str = typer.Argument(..., help="Role name"),
    permission: str = typer.Argument(..., help="Permission to add (e.g., 'posts:write')"),
) -> None:
    """
    Add a permission to a role.

    Example:
        $ vault roles add-permission acme-corp Editor "posts:delete"
        $ vault roles add-permission acme-corp Moderator "comments:*"
    """
    console.print("\n[bold cyan]Adding Permission[/bold cyan]\n")

    asyncio.run(_add_permission(org_slug, name, permission))


async def _add_permission(org_slug: str, name: str, permission: str) -> None:
    """Internal async function to add permission."""
    try:
        vault = await Vault.create()

        # Get organization first
        org = await vault.orgs.get_by_slug(org_slug)
        if not org:
            console.print(f"[red]Organization not found:[/red] {org_slug}\n")
            raise typer.Exit(1)

        # Get role
        role = await vault.roles.get_by_name(org.id, name)
        if not role:
            console.print(f"[red]Role not found:[/red] {name}\n")
            raise typer.Exit(1)

        updated = await vault.roles.add_permissions(role.id, [permission])

        console.print(f"[green]✓[/green] Permission added: {permission}")
        console.print(f"\nCurrent permissions for '{name}':")
        for perm in updated.permissions:
            console.print(f"  • [green]{perm}[/green]")
        console.print()

    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


def roles_remove_permission_command(
    org_slug: str = typer.Argument(..., help="Organization slug"),
    name: str = typer.Argument(..., help="Role name"),
    permission: str = typer.Argument(..., help="Permission to remove"),
) -> None:
    """
    Remove a permission from a role.

    Example:
        $ vault roles remove-permission acme-corp Editor "posts:delete"
    """
    console.print("\n[bold cyan]Removing Permission[/bold cyan]\n")

    asyncio.run(_remove_permission(org_slug, name, permission))


async def _remove_permission(org_slug: str, name: str, permission: str) -> None:
    """Internal async function to remove permission."""
    try:
        vault = await Vault.create()

        # Get organization first
        org = await vault.orgs.get_by_slug(org_slug)
        if not org:
            console.print(f"[red]Organization not found:[/red] {org_slug}\n")
            raise typer.Exit(1)

        # Get role
        role = await vault.roles.get_by_name(org.id, name)
        if not role:
            console.print(f"[red]Role not found:[/red] {name}\n")
            raise typer.Exit(1)

        if permission not in role.permissions:
            console.print(f"[yellow]Permission not found on role:[/yellow] {permission}\n")
            raise typer.Exit(1)

        updated = await vault.roles.remove_permissions(role.id, [permission])

        console.print(f"[green]✓[/green] Permission removed: {permission}")
        console.print(f"\nCurrent permissions for '{name}':")
        if updated.permissions:
            for perm in updated.permissions:
                console.print(f"  • [green]{perm}[/green]")
        else:
            console.print("  [yellow]No permissions[/yellow]")
        console.print()

    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


def roles_init_system_command(
    org_slug: str = typer.Argument(..., help="Organization slug"),
) -> None:
    """
    Initialize system roles for an organization.

    Creates the default Owner, Admin, and Member roles.

    Example:
        $ vault roles init-system acme-corp
    """
    console.print("\n[bold cyan]Initializing System Roles[/bold cyan]\n")

    asyncio.run(_init_system_roles(org_slug))


async def _init_system_roles(org_slug: str) -> None:
    """Internal async function to initialize system roles."""
    try:
        vault = await Vault.create()

        # Get organization first
        org = await vault.orgs.get_by_slug(org_slug)
        if not org:
            console.print(f"[red]Organization not found:[/red] {org_slug}\n")
            raise typer.Exit(1)

        # Check if system roles already exist
        existing = await vault.roles.list_by_organization(org.id, include_system=True)
        system_roles = [r for r in existing if r.is_system]

        if system_roles:
            console.print(f"[yellow]System roles already exist for {org_slug}:[/yellow]")
            for role in system_roles:
                console.print(f"  • {role.name}")
            console.print()
            raise typer.Exit(1)

        roles = await vault.roles.create_system_roles(org.id)

        console.print(f"[green]✓[/green] System roles created!")
        console.print()

        for role in roles:
            console.print(f"[bold]{role.name}[/bold]")
            console.print(f"  Description: {role.description}")
            console.print(f"  Permissions: {role.permissions}")
            console.print(f"  Default: {role.is_default}")
            console.print()

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


def roles_assign_command(
    org_slug: str = typer.Argument(..., help="Organization slug"),
    user_email: str = typer.Argument(..., help="User email"),
    role_name: str = typer.Argument(..., help="Role name to assign"),
) -> None:
    """
    Assign a role to a user.

    Updates the user's membership in the organization with the specified role.

    Example:
        $ vault roles assign acme-corp user@example.com Admin
        $ vault roles assign acme-corp user@example.com Editor
    """
    console.print("\n[bold cyan]Assigning Role[/bold cyan]\n")

    asyncio.run(_assign_role(org_slug, user_email, role_name))


async def _assign_role(org_slug: str, user_email: str, role_name: str) -> None:
    """Internal async function to assign role."""
    try:
        vault = await Vault.create()

        # Get organization first
        org = await vault.orgs.get_by_slug(org_slug)
        if not org:
            console.print(f"[red]Organization not found:[/red] {org_slug}\n")
            raise typer.Exit(1)

        # Get user
        user = await vault.users.get_by_email(user_email)
        if not user:
            console.print(f"[red]User not found:[/red] {user_email}\n")
            raise typer.Exit(1)

        # Get role
        role = await vault.roles.get_by_name(org.id, role_name)
        if not role:
            console.print(f"[red]Role not found:[/red] {role_name}\n")
            raise typer.Exit(1)

        # Get membership
        membership = await vault.memberships.get_by_user_and_org(user.id, org.id)
        if not membership:
            console.print(f"[red]User is not a member of {org_slug}[/red]\n")
            raise typer.Exit(1)

        # Update membership with role
        updated = await vault.memberships.update(
            membership_id=membership.id,
            role_id=role.id,
        )

        console.print(f"[green]✓[/green] Role assigned!")
        console.print(f"\nUser: [cyan]{user_email}[/cyan]")
        console.print(f"Organization: [cyan]{org_slug}[/cyan]")
        console.print(f"Role: [cyan]{role_name}[/cyan]")
        console.print(f"Permissions: [cyan]{role.permissions}[/cyan]\n")

    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)

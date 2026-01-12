"""
CLI commands for API key management.
"""

import asyncio
from typing import Optional
from uuid import UUID

import typer
from rich.console import Console
from rich.table import Table

from ...client import Vault

console = Console()
app = typer.Typer(help="Manage API keys for service authentication")


def run_async(coro):
    """Run async function in sync context."""
    return asyncio.get_event_loop().run_until_complete(coro)


@app.command("create")
def apikeys_create_command(
    name: str = typer.Argument(..., help="Name for the API key"),
    org_id: str = typer.Option(..., "--org", "-o", help="Organization ID"),
    description: Optional[str] = typer.Option(None, "--description", "-d"),
    scopes: Optional[str] = typer.Option(None, "--scopes", "-s", help="Comma-separated scopes"),
    rate_limit: Optional[int] = typer.Option(None, "--rate-limit", "-r", help="Requests per minute"),
    expires: Optional[int] = typer.Option(None, "--expires", "-e", help="Days until expiration"),
) -> None:
    """Create a new API key."""

    async def _create():
        vault = await Vault.create()
        try:
            scope_list = scopes.split(",") if scopes else None

            key = await vault.api_keys.create(
                name=name,
                organization_id=UUID(org_id),
                description=description,
                scopes=scope_list,
                rate_limit=rate_limit,
                expires_in_days=expires,
            )

            console.print(f"[green]✓[/green] API key created: {name}")
            console.print()
            console.print("[bold red]IMPORTANT:[/bold red] Save this key now. It cannot be retrieved again!")
            console.print()
            console.print(f"[bold cyan]API Key:[/bold cyan] {key.key}")
            console.print()
            console.print(f"  ID: {key.id}")
            console.print(f"  Prefix: {key.key_prefix}")
            if key.scopes:
                console.print(f"  Scopes: {', '.join(key.scopes)}")
            if key.rate_limit:
                console.print(f"  Rate Limit: {key.rate_limit}/min")
            if key.expires_at:
                console.print(f"  Expires: {key.expires_at}")
        finally:
            await vault.close()

    run_async(_create())


@app.command("list")
def apikeys_list_command(
    org_id: str = typer.Option(..., "--org", "-o", help="Organization ID"),
    all_keys: bool = typer.Option(False, "--all", "-a", help="Include inactive keys"),
    limit: int = typer.Option(50, "--limit", "-l", help="Maximum results"),
) -> None:
    """List API keys for an organization."""

    async def _list():
        vault = await Vault.create()
        try:
            keys = await vault.api_keys.list_by_organization(
                organization_id=UUID(org_id),
                active_only=not all_keys,
                limit=limit,
            )

            if not keys:
                console.print("[yellow]No API keys found[/yellow]")
                return

            table = Table(title="API Keys")
            table.add_column("Name", style="cyan")
            table.add_column("Prefix", style="yellow")
            table.add_column("Status", style="green")
            table.add_column("Scopes", style="blue")
            table.add_column("Last Used", style="dim")
            table.add_column("ID", style="dim")

            for key in keys:
                status = "Active" if key.is_active else "Inactive"
                scopes_str = ", ".join(key.scopes[:2])
                if len(key.scopes) > 2:
                    scopes_str += f"... (+{len(key.scopes) - 2})"

                last_used = key.last_used_at.strftime("%Y-%m-%d") if key.last_used_at else "Never"

                table.add_row(
                    key.name,
                    key.key_prefix,
                    status,
                    scopes_str or "-",
                    last_used,
                    str(key.id)[:8],
                )

            console.print(table)
        finally:
            await vault.close()

    run_async(_list())


@app.command("get")
def apikeys_get_command(
    key_id: str = typer.Argument(..., help="API key ID"),
) -> None:
    """Get details of an API key."""

    async def _get():
        vault = await Vault.create()
        try:
            key = await vault.api_keys.get(UUID(key_id))

            if not key:
                console.print(f"[red]Error:[/red] API key {key_id} not found")
                raise typer.Exit(1)

            console.print(f"[bold]{key.name}[/bold]")
            console.print(f"  ID: {key.id}")
            console.print(f"  Prefix: {key.key_prefix}")
            console.print(f"  Status: {'Active' if key.is_active else 'Inactive'}")
            if key.description:
                console.print(f"  Description: {key.description}")
            if key.scopes:
                console.print(f"  Scopes: {', '.join(key.scopes)}")
            if key.rate_limit:
                console.print(f"  Rate Limit: {key.rate_limit}/min")
            if key.last_used_at:
                console.print(f"  Last Used: {key.last_used_at}")
            if key.expires_at:
                console.print(f"  Expires: {key.expires_at}")
            console.print(f"  Created: {key.created_at}")
        finally:
            await vault.close()

    run_async(_get())


@app.command("revoke")
def apikeys_revoke_command(
    key_id: str = typer.Argument(..., help="API key ID to revoke"),
) -> None:
    """Revoke (deactivate) an API key."""

    async def _revoke():
        vault = await Vault.create()
        try:
            await vault.api_keys.revoke(UUID(key_id))
            console.print(f"[green]✓[/green] API key {key_id[:8]}... revoked")
        except ValueError as e:
            console.print(f"[red]Error:[/red] {e}")
            raise typer.Exit(1)
        finally:
            await vault.close()

    run_async(_revoke())


@app.command("delete")
def apikeys_delete_command(
    key_id: str = typer.Argument(..., help="API key ID to delete"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
) -> None:
    """Permanently delete an API key."""
    if not force:
        confirm = typer.confirm(f"Permanently delete API key {key_id[:8]}...?")
        if not confirm:
            raise typer.Abort()

    async def _delete():
        vault = await Vault.create()
        try:
            await vault.api_keys.delete(UUID(key_id))
            console.print(f"[green]✓[/green] API key {key_id[:8]}... deleted")
        finally:
            await vault.close()

    run_async(_delete())


@app.command("rotate")
def apikeys_rotate_command(
    key_id: str = typer.Argument(..., help="API key ID to rotate"),
    expires: Optional[int] = typer.Option(None, "--expires", "-e", help="Days until expiration"),
) -> None:
    """Rotate an API key (generate new secret, keep settings)."""

    async def _rotate():
        vault = await Vault.create()
        try:
            key = await vault.api_keys.rotate(UUID(key_id), expires_in_days=expires)

            console.print(f"[green]✓[/green] API key rotated: {key.name}")
            console.print()
            console.print("[bold red]IMPORTANT:[/bold red] Save this key now. It cannot be retrieved again!")
            console.print()
            console.print(f"[bold cyan]New API Key:[/bold cyan] {key.key}")
            console.print()
            console.print(f"  New Prefix: {key.key_prefix}")
        except ValueError as e:
            console.print(f"[red]Error:[/red] {e}")
            raise typer.Exit(1)
        finally:
            await vault.close()

    run_async(_rotate())


@app.command("validate")
def apikeys_validate_command(
    key: str = typer.Argument(..., help="API key to validate"),
) -> None:
    """Validate an API key."""

    async def _validate():
        vault = await Vault.create()
        try:
            result = await vault.api_keys.validate(key, log_usage=False)

            if result.valid:
                console.print(f"[green]✓[/green] API key is valid")
                console.print(f"  Name: {result.api_key.name}")
                console.print(f"  Organization: {result.api_key.organization_id}")
                if result.api_key.scopes:
                    console.print(f"  Scopes: {', '.join(result.api_key.scopes)}")
                if result.remaining_requests is not None:
                    console.print(f"  Remaining requests: {result.remaining_requests}")
            else:
                console.print(f"[red]✗[/red] API key is invalid: {result.error}")
                raise typer.Exit(1)
        finally:
            await vault.close()

    run_async(_validate())

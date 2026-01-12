"""
CLI commands for invitation management.
"""

import asyncio
from datetime import datetime
from typing import Optional
from uuid import UUID

import typer
from rich.console import Console
from rich.table import Table

from ...client import Vault

console = Console()
app = typer.Typer(help="Manage organization invitations")


def run_async(coro):
    """Run async function in sync context."""
    return asyncio.get_event_loop().run_until_complete(coro)


@app.command("send")
def invites_send_command(
    email: str = typer.Argument(..., help="Email address to invite"),
    org_id: str = typer.Option(..., "--org", "-o", help="Organization ID"),
    role_id: Optional[str] = typer.Option(None, "--role", "-r", help="Role ID to assign"),
    expires: int = typer.Option(7, "--expires", "-e", help="Days until expiration"),
    no_email: bool = typer.Option(False, "--no-email", help="Don't send email"),
) -> None:
    """Send an invitation to join an organization."""

    async def _send():
        vault = await Vault.create()
        try:
            invite = await vault.invites.create(
                organization_id=UUID(org_id),
                email=email,
                role_id=UUID(role_id) if role_id else None,
                expires_in_days=expires,
                send_email=not no_email,
            )
            console.print(f"[green]✓[/green] Invitation sent to {email}")
            console.print(f"  ID: {invite.id}")
            console.print(f"  Token: {invite.token}")
            console.print(f"  Expires: {invite.expires_at}")
        finally:
            await vault.close()

    run_async(_send())


@app.command("list")
def invites_list_command(
    org_id: str = typer.Option(..., "--org", "-o", help="Organization ID"),
    pending: bool = typer.Option(False, "--pending", "-p", help="Only pending invites"),
    limit: int = typer.Option(50, "--limit", "-l", help="Maximum results"),
) -> None:
    """List invitations for an organization."""

    async def _list():
        vault = await Vault.create()
        try:
            invites = await vault.invites.list_by_organization(
                organization_id=UUID(org_id),
                pending_only=pending,
                limit=limit,
            )

            if not invites:
                console.print("[yellow]No invitations found[/yellow]")
                return

            table = Table(title="Invitations")
            table.add_column("Email", style="cyan")
            table.add_column("Status", style="green")
            table.add_column("Expires", style="yellow")
            table.add_column("ID", style="dim")

            for invite in invites:
                status = "Accepted" if invite.accepted_at else "Pending"
                if not invite.accepted_at and invite.expires_at < datetime.utcnow():
                    status = "Expired"

                table.add_row(
                    invite.email,
                    status,
                    invite.expires_at.strftime("%Y-%m-%d"),
                    str(invite.id)[:8],
                )

            console.print(table)
        finally:
            await vault.close()

    run_async(_list())


@app.command("revoke")
def invites_revoke_command(
    invite_id: str = typer.Argument(..., help="Invitation ID to revoke"),
) -> None:
    """Revoke (delete) a pending invitation."""

    async def _revoke():
        vault = await Vault.create()
        try:
            await vault.invites.revoke(UUID(invite_id))
            console.print(f"[green]✓[/green] Invitation {invite_id[:8]}... revoked")
        except ValueError as e:
            console.print(f"[red]Error:[/red] {e}")
            raise typer.Exit(1)
        finally:
            await vault.close()

    run_async(_revoke())


@app.command("resend")
def invites_resend_command(
    invite_id: str = typer.Argument(..., help="Invitation ID to resend"),
) -> None:
    """Resend an invitation email and extend expiration."""

    async def _resend():
        vault = await Vault.create()
        try:
            invite = await vault.invites.resend(UUID(invite_id))
            console.print(f"[green]✓[/green] Invitation resent to {invite.email}")
            console.print(f"  New token: {invite.token}")
            console.print(f"  New expiration: {invite.expires_at}")
        except ValueError as e:
            console.print(f"[red]Error:[/red] {e}")
            raise typer.Exit(1)
        finally:
            await vault.close()

    run_async(_resend())


@app.command("accept")
def invites_accept_command(
    token: str = typer.Argument(..., help="Invitation token"),
    user_id: str = typer.Option(..., "--user", "-u", help="User ID accepting"),
) -> None:
    """Accept an invitation using its token."""

    async def _accept():
        vault = await Vault.create()
        try:
            invite = await vault.invites.accept(token, UUID(user_id))
            console.print(f"[green]✓[/green] Invitation accepted")
            console.print(f"  Organization: {invite.organization_id}")
            console.print(f"  User: {user_id[:8]}...")
        except ValueError as e:
            console.print(f"[red]Error:[/red] {e}")
            raise typer.Exit(1)
        finally:
            await vault.close()

    run_async(_accept())


@app.command("cleanup")
def invites_cleanup_command() -> None:
    """Delete all expired invitations."""

    async def _cleanup():
        vault = await Vault.create()
        try:
            deleted = await vault.invites.cleanup_expired()
            console.print(f"[green]✓[/green] Cleaned up {deleted} expired invitations")
        finally:
            await vault.close()

    run_async(_cleanup())

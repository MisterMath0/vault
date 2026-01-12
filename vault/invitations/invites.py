"""
Invitation management for Vault.

Handles creating, accepting, and managing organization invitations.
Uses Supabase invite_user_by_email for email delivery when available,
or generates custom invite tokens for manual handling.

Wraps: supabase_auth._async.gotrue_admin_api.AsyncGoTrueAdminAPI.invite_user_by_email
Source: venv/lib/python3.14/site-packages/supabase_auth/_async/gotrue_admin_api.py:81
"""

import secrets
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, List, Optional
from uuid import UUID

from .models import VaultInvitation

if TYPE_CHECKING:
    from ..client import Vault


class InvitationManager:
    """
    Manages organization invitation operations.

    The invitation flow:
    1. Create invitation with email, org, and optional role
    2. Generate unique token and store in vault_invitations
    3. Optionally trigger Supabase email via invite_user_by_email
    4. User accepts invitation via token
    5. Create membership and mark invitation as accepted
    """

    def __init__(self, vault: "Vault") -> None:
        """
        Initialize InvitationManager.

        Args:
            vault: Main Vault client instance
        """
        self.vault = vault
        self.client = vault.client

    def _generate_token(self, length: int = 32) -> str:
        """Generate a secure random token for invitations."""
        return secrets.token_urlsafe(length)

    async def create(
        self,
        organization_id: UUID,
        email: str,
        role_id: Optional[UUID] = None,
        invited_by: Optional[UUID] = None,
        expires_in_days: int = 7,
        send_email: bool = True,
        redirect_to: Optional[str] = None,
    ) -> VaultInvitation:
        """
        Create an invitation to join an organization.

        Wraps: supabase_auth._async.gotrue_admin_api.AsyncGoTrueAdminAPI.invite_user_by_email
        Source: venv/lib/python3.14/site-packages/supabase_auth/_async/gotrue_admin_api.py:81

        Args:
            organization_id: Organization to invite user to
            email: Email address to invite
            role_id: Role to assign when invitation is accepted
            invited_by: User ID of person sending the invitation
            expires_in_days: Days until invitation expires (1-30)
            send_email: Whether to send invitation email via Supabase
            redirect_to: URL to redirect to after accepting (for email link)

        Returns:
            VaultInvitation instance

        Raises:
            ValueError: If organization doesn't exist or user already member

        Example:
            ```python
            invite = await vault.invites.create(
                organization_id=org.id,
                email="newuser@example.com",
                role_id=member_role.id,
                invited_by=admin_user.id
            )
            print(f"Invitation token: {invite.token}")
            ```
        """
        # Verify organization exists
        org = await self.vault.orgs.get(organization_id)
        if not org:
            raise ValueError(f"Organization {organization_id} not found")

        # Check if user already exists and is a member
        existing_user = await self.vault.users.get_by_email(email)
        if existing_user:
            existing_membership = (
                await self.client.table("vault_memberships")
                .select("id")
                .eq("user_id", str(existing_user.id))
                .eq("organization_id", str(organization_id))
                .execute()
            )
            if existing_membership.data:
                raise ValueError(f"User {email} is already a member of this organization")

        # Check for existing pending invitation
        existing_invite = (
            await self.client.table("vault_invitations")
            .select("id")
            .eq("email", email)
            .eq("organization_id", str(organization_id))
            .is_("accepted_at", "null")
            .execute()
        )
        if existing_invite.data:
            # Revoke existing invitation before creating new one
            await self.client.table("vault_invitations").delete().eq(
                "id", existing_invite.data[0]["id"]
            ).execute()

        # Generate token and expiration
        token = self._generate_token()
        expires_at = datetime.utcnow() + timedelta(days=expires_in_days)

        # Create invitation record
        invitation_data = {
            "organization_id": str(organization_id),
            "email": email,
            "role_id": str(role_id) if role_id else None,
            "invited_by": str(invited_by) if invited_by else None,
            "token": token,
            "expires_at": expires_at.isoformat(),
            "created_at": datetime.utcnow().isoformat(),
        }

        result = await self.client.table("vault_invitations").insert(
            invitation_data
        ).execute()

        invitation = VaultInvitation(**result.data[0])

        # Optionally send email via Supabase
        if send_email:
            try:
                options = {
                    "data": {
                        "organization_id": str(organization_id),
                        "organization_name": org.name,
                        "invitation_token": token,
                        "role_id": str(role_id) if role_id else None,
                    }
                }
                if redirect_to:
                    options["redirect_to"] = redirect_to

                await self.client.auth.admin.invite_user_by_email(email, options)
            except Exception:
                # Email sending is best-effort - invitation still valid
                # User can accept via token manually
                pass

        return invitation

    async def get(self, invitation_id: UUID) -> Optional[VaultInvitation]:
        """
        Get an invitation by ID.

        Args:
            invitation_id: Invitation UUID

        Returns:
            VaultInvitation instance or None if not found
        """
        result = await self.client.table("vault_invitations").select("*").eq(
            "id", str(invitation_id)
        ).execute()

        if not result.data:
            return None

        return VaultInvitation(**result.data[0])

    async def get_by_token(self, token: str) -> Optional[VaultInvitation]:
        """
        Get an invitation by its token.

        Args:
            token: Invitation token

        Returns:
            VaultInvitation instance or None if not found
        """
        result = await self.client.table("vault_invitations").select("*").eq(
            "token", token
        ).execute()

        if not result.data:
            return None

        return VaultInvitation(**result.data[0])

    async def list_by_organization(
        self,
        organization_id: UUID,
        pending_only: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> List[VaultInvitation]:
        """
        List invitations for an organization.

        Args:
            organization_id: Organization UUID
            pending_only: Only return pending (unaccepted) invitations
            limit: Maximum number of invitations to return
            offset: Number of invitations to skip

        Returns:
            List of VaultInvitation instances
        """
        query = self.client.table("vault_invitations").select("*").eq(
            "organization_id", str(organization_id)
        )

        if pending_only:
            query = query.is_("accepted_at", "null")

        result = await query.limit(limit).offset(offset).order(
            "created_at", desc=True
        ).execute()

        return [VaultInvitation(**inv) for inv in result.data]

    async def list_by_email(
        self,
        email: str,
        pending_only: bool = True,
    ) -> List[VaultInvitation]:
        """
        List invitations for an email address.

        Args:
            email: Email address
            pending_only: Only return pending (unaccepted) invitations

        Returns:
            List of VaultInvitation instances
        """
        query = self.client.table("vault_invitations").select("*").eq("email", email)

        if pending_only:
            query = query.is_("accepted_at", "null")

        result = await query.order("created_at", desc=True).execute()

        return [VaultInvitation(**inv) for inv in result.data]

    async def accept(
        self,
        token: str,
        user_id: UUID,
    ) -> VaultInvitation:
        """
        Accept an invitation and create organization membership.

        Args:
            token: Invitation token
            user_id: ID of user accepting the invitation

        Returns:
            Updated VaultInvitation instance

        Raises:
            ValueError: If invitation not found, expired, or already accepted

        Example:
            ```python
            # User accepts invitation
            invitation = await vault.invites.accept(
                token="abc123xyz",
                user_id=user.id
            )
            ```
        """
        invitation = await self.get_by_token(token)

        if not invitation:
            raise ValueError("Invitation not found")

        if invitation.accepted_at:
            raise ValueError("Invitation has already been accepted")

        if invitation.expires_at < datetime.utcnow():
            raise ValueError("Invitation has expired")

        # Verify user exists
        user = await self.vault.users.get(user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")

        # Verify email matches (if user exists with different email, that's OK)
        # This allows accepting invites for an existing user who was invited

        # Check if user is already a member
        existing_membership = (
            await self.client.table("vault_memberships")
            .select("id")
            .eq("user_id", str(user_id))
            .eq("organization_id", str(invitation.organization_id))
            .execute()
        )
        if existing_membership.data:
            raise ValueError("User is already a member of this organization")

        # Create membership
        await self.vault.memberships.create(
            user_id=user_id,
            organization_id=invitation.organization_id,
            role_id=invitation.role_id,
        )

        # Mark invitation as accepted
        now = datetime.utcnow()
        result = await self.client.table("vault_invitations").update({
            "accepted_at": now.isoformat(),
            "accepted_by": str(user_id),
        }).eq("id", str(invitation.id)).execute()

        return VaultInvitation(**result.data[0])

    async def revoke(self, invitation_id: UUID) -> None:
        """
        Revoke (delete) an invitation.

        Args:
            invitation_id: Invitation UUID

        Raises:
            ValueError: If invitation not found or already accepted

        Example:
            ```python
            await vault.invites.revoke(invitation_id)
            ```
        """
        invitation = await self.get(invitation_id)

        if not invitation:
            raise ValueError(f"Invitation {invitation_id} not found")

        if invitation.accepted_at:
            raise ValueError("Cannot revoke an accepted invitation")

        await self.client.table("vault_invitations").delete().eq(
            "id", str(invitation_id)
        ).execute()

    async def resend(
        self,
        invitation_id: UUID,
        redirect_to: Optional[str] = None,
    ) -> VaultInvitation:
        """
        Resend an invitation email and extend expiration.

        Args:
            invitation_id: Invitation UUID
            redirect_to: URL to redirect to after accepting

        Returns:
            Updated VaultInvitation instance

        Raises:
            ValueError: If invitation not found or already accepted
        """
        invitation = await self.get(invitation_id)

        if not invitation:
            raise ValueError(f"Invitation {invitation_id} not found")

        if invitation.accepted_at:
            raise ValueError("Cannot resend an accepted invitation")

        # Generate new token and extend expiration
        new_token = self._generate_token()
        new_expires_at = datetime.utcnow() + timedelta(days=7)

        result = await self.client.table("vault_invitations").update({
            "token": new_token,
            "expires_at": new_expires_at.isoformat(),
        }).eq("id", str(invitation_id)).execute()

        updated_invitation = VaultInvitation(**result.data[0])

        # Get org for email metadata
        org = await self.vault.orgs.get(invitation.organization_id)

        # Resend email
        try:
            options = {
                "data": {
                    "organization_id": str(invitation.organization_id),
                    "organization_name": org.name if org else None,
                    "invitation_token": new_token,
                    "role_id": str(invitation.role_id) if invitation.role_id else None,
                }
            }
            if redirect_to:
                options["redirect_to"] = redirect_to

            await self.client.auth.admin.invite_user_by_email(
                invitation.email, options
            )
        except Exception:
            # Email sending is best-effort
            pass

        return updated_invitation

    async def count_by_organization(
        self,
        organization_id: UUID,
        pending_only: bool = False,
    ) -> int:
        """
        Count invitations for an organization.

        Args:
            organization_id: Organization UUID
            pending_only: Only count pending (unaccepted) invitations

        Returns:
            Count of invitations
        """
        query = self.client.table("vault_invitations").select(
            "id", count="exact"
        ).eq("organization_id", str(organization_id))

        if pending_only:
            query = query.is_("accepted_at", "null")

        result = await query.execute()
        return result.count or 0

    async def cleanup_expired(self) -> int:
        """
        Delete all expired unaccepted invitations.

        Returns:
            Number of invitations deleted

        Example:
            ```python
            deleted = await vault.invites.cleanup_expired()
            print(f"Cleaned up {deleted} expired invitations")
            ```
        """
        now = datetime.utcnow().isoformat()

        # Get count first
        count_result = await self.client.table("vault_invitations").select(
            "id", count="exact"
        ).is_("accepted_at", "null").lt("expires_at", now).execute()

        count = count_result.count or 0

        if count > 0:
            # Delete expired invitations
            await self.client.table("vault_invitations").delete().is_(
                "accepted_at", "null"
            ).lt("expires_at", now).execute()

        return count

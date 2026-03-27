"""Team management service with RBAC."""

import re
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from ..models.subscription import Plan, Subscription
from ..models.team import Team, TeamInvite, TeamMember
from ..models.user import User

ROLE_HIERARCHY = {"owner": 4, "admin": 3, "member": 2, "viewer": 1}


class TeamService:
    def __init__(self, db: Session):
        self.db = db

    def check_permission(self, user_id, team_id, required_role: str) -> bool:
        """Check if user has at least the required role in the team."""
        member = (
            self.db.query(TeamMember)
            .filter(
                TeamMember.team_id == team_id,
                TeamMember.user_id == user_id,
            )
            .first()
        )
        if not member:
            return False
        return ROLE_HIERARCHY.get(member.role, 0) >= ROLE_HIERARCHY.get(
            required_role, 0
        )

    def get_member_role(self, user_id, team_id) -> str | None:
        """Get the user's role in a team, or None if not a member."""
        member = (
            self.db.query(TeamMember)
            .filter(
                TeamMember.team_id == team_id,
                TeamMember.user_id == user_id,
            )
            .first()
        )
        return member.role if member else None

    def create_team(self, owner: User, name: str, brand_color: str | None = None) -> Team:
        """Create a team and add the owner as first member.

        Checks that the owner's plan allows team creation (team_seats > 1).
        """
        # Check plan allows teams
        plan = self._get_user_plan(owner)
        if plan and plan.team_seats <= 1:
            raise PermissionError(
                "Your plan does not support teams. Upgrade to create a team."
            )

        slug = self._generate_slug(name)
        team = Team(
            name=name,
            slug=slug,
            owner_id=owner.id,
            brand_color=brand_color,
            max_members=plan.team_seats if plan else 10,
        )
        self.db.add(team)
        self.db.flush()

        # Owner is automatically a member
        self.db.add(
            TeamMember(
                team_id=team.id,
                user_id=owner.id,
                role="owner",
            )
        )
        self.db.commit()
        self.db.refresh(team)
        return team

    def invite_member(
        self, team: Team, email: str, role: str, invited_by: User
    ) -> TeamInvite:
        """Create a team invite. Checks seat limits."""
        # Check seat limit
        current_members = (
            self.db.query(TeamMember)
            .filter(TeamMember.team_id == team.id)
            .count()
        )
        if current_members >= team.max_members:
            raise PermissionError(
                f"Team seat limit reached ({team.max_members}). "
                "Upgrade the team owner's plan to add more members."
            )

        # Check for existing pending invite
        existing = (
            self.db.query(TeamInvite)
            .filter(
                TeamInvite.team_id == team.id,
                TeamInvite.email == email,
                TeamInvite.accepted_at.is_(None),
                TeamInvite.expires_at > datetime.now(timezone.utc),
            )
            .first()
        )
        if existing:
            raise ValueError(f"A pending invite already exists for {email}")

        # Check if user is already a member
        existing_user = self.db.query(User).filter(User.email == email).first()
        if existing_user:
            existing_member = (
                self.db.query(TeamMember)
                .filter(
                    TeamMember.team_id == team.id,
                    TeamMember.user_id == existing_user.id,
                )
                .first()
            )
            if existing_member:
                raise ValueError(f"{email} is already a member of this team")

        token = secrets.token_urlsafe(32)
        invite = TeamInvite(
            team_id=team.id,
            email=email,
            role=role,
            invited_by=invited_by.id,
            token=token,
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        )
        self.db.add(invite)
        self.db.commit()
        self.db.refresh(invite)
        return invite

    def accept_invite(self, token: str, user: User) -> TeamMember:
        """Accept a team invitation."""
        invite = (
            self.db.query(TeamInvite)
            .filter(
                TeamInvite.token == token,
                TeamInvite.accepted_at.is_(None),
                TeamInvite.expires_at > datetime.now(timezone.utc),
            )
            .first()
        )
        if not invite:
            raise ValueError("Invalid or expired invite")

        # Check if already a member
        existing = (
            self.db.query(TeamMember)
            .filter(
                TeamMember.team_id == invite.team_id,
                TeamMember.user_id == user.id,
            )
            .first()
        )
        if existing:
            raise ValueError("You are already a member of this team")

        member = TeamMember(
            team_id=invite.team_id,
            user_id=user.id,
            role=invite.role,
            invited_by=invite.invited_by,
        )
        self.db.add(member)
        invite.accepted_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(member)
        return member

    def remove_member(self, team_id, user_id, removed_by) -> None:
        """Remove a member from a team. Cannot remove the owner."""
        member = (
            self.db.query(TeamMember)
            .filter(
                TeamMember.team_id == team_id,
                TeamMember.user_id == user_id,
            )
            .first()
        )
        if not member:
            raise ValueError("Member not found")

        if member.role == "owner":
            raise PermissionError("Cannot remove the team owner")

        # The remover must have higher or equal role (admin+)
        remover_role = self.get_member_role(removed_by, team_id)
        if not remover_role or ROLE_HIERARCHY.get(remover_role, 0) < ROLE_HIERARCHY.get(
            "admin", 0
        ):
            raise PermissionError("Admin role required to remove members")

        self.db.delete(member)
        self.db.commit()

    def update_member_role(self, team_id, user_id, new_role: str, updated_by) -> TeamMember:
        """Update a member's role. Cannot change the owner's role."""
        member = (
            self.db.query(TeamMember)
            .filter(
                TeamMember.team_id == team_id,
                TeamMember.user_id == user_id,
            )
            .first()
        )
        if not member:
            raise ValueError("Member not found")

        if member.role == "owner":
            raise PermissionError("Cannot change the owner's role")

        # The updater must be admin+
        updater_role = self.get_member_role(updated_by, team_id)
        if not updater_role or ROLE_HIERARCHY.get(updater_role, 0) < ROLE_HIERARCHY.get(
            "admin", 0
        ):
            raise PermissionError("Admin role required to update roles")

        # Cannot promote to a role higher than your own
        if ROLE_HIERARCHY.get(new_role, 0) > ROLE_HIERARCHY.get(updater_role, 0):
            raise PermissionError("Cannot assign a role higher than your own")

        member.role = new_role
        self.db.commit()
        self.db.refresh(member)
        return member

    def _generate_slug(self, name: str) -> str:
        """Generate a URL-safe slug from team name."""
        slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
        # Ensure uniqueness
        base_slug = slug
        counter = 1
        while self.db.query(Team).filter(Team.slug == slug).first():
            slug = f"{base_slug}-{counter}"
            counter += 1
        return slug

    def _get_user_plan(self, user: User) -> Plan | None:
        """Get the user's current plan."""
        sub = (
            self.db.query(Subscription)
            .filter(Subscription.user_id == user.id)
            .first()
        )
        return sub.plan if sub else None

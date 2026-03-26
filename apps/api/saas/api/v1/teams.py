"""Teams API endpoints — CRUD, members, invites, usage analytics."""

from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from ...api.deps import get_current_user, get_db
from ...models.channel import YouTubeChannel
from ...models.job import Job
from ...models.team import Team, TeamMember
from ...models.user import User
from ...models.video import Video
from ...schemas.common import ErrorDetail, ErrorResponse
from ...schemas.job import JobResponse
from ...schemas.team import (
    InviteMemberRequest,
    InviteResponse,
    TeamCreate,
    TeamMemberResponse,
    TeamResponse,
    TeamUpdate,
    TeamUsageResponse,
    UpdateMemberRoleRequest,
)
from ...services.team_service import TeamService

router = APIRouter()


def _build_team_response(team: Team, db: Session) -> dict:
    """Build a team response dict with computed counts."""
    members_count = (
        db.query(TeamMember).filter(TeamMember.team_id == team.id).count()
    )
    channels_count = (
        db.query(YouTubeChannel)
        .filter(YouTubeChannel.team_id == team.id, YouTubeChannel.is_active == True)  # noqa: E712
        .count()
    )
    return {
        "id": team.id,
        "name": team.name,
        "slug": team.slug,
        "owner_id": team.owner_id,
        "brand_color": team.brand_color,
        "logo_url": team.logo_url,
        "custom_domain": team.custom_domain,
        "max_members": team.max_members,
        "members_count": members_count,
        "channels_count": channels_count,
        "is_active": team.is_active,
        "created_at": team.created_at,
    }


@router.get("/teams")
def list_teams(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all teams the current user belongs to."""
    memberships = (
        db.query(TeamMember)
        .filter(TeamMember.user_id == user.id)
        .all()
    )
    team_ids = [m.team_id for m in memberships]
    teams = db.query(Team).filter(Team.id.in_(team_ids), Team.is_active == True).all()  # noqa: E712
    return {
        "items": [_build_team_response(t, db) for t in teams]
    }


@router.post("/teams", status_code=201)
def create_team(
    body: TeamCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new team. Requires a plan that supports teams."""
    service = TeamService(db)
    try:
        team = service.create_team(
            owner=user,
            name=body.name,
            brand_color=body.brand_color,
        )
    except PermissionError as e:
        raise HTTPException(
            status_code=403,
            detail=ErrorResponse(
                error=ErrorDetail(
                    code="PLAN_LIMIT_EXCEEDED",
                    message=str(e),
                )
            ).model_dump(),
        )
    return _build_team_response(team, db)


@router.get("/teams/{team_id}")
def get_team(
    team_id: UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get team details. User must be a member."""
    service = TeamService(db)
    if not service.check_permission(user.id, team_id, "viewer"):
        raise HTTPException(status_code=403, detail="Not a member of this team")

    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    return _build_team_response(team, db)


@router.patch("/teams/{team_id}")
def update_team(
    team_id: UUID,
    body: TeamUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update team settings. Requires admin+ role."""
    service = TeamService(db)
    if not service.check_permission(user.id, team_id, "admin"):
        raise HTTPException(status_code=403, detail="Admin role required")

    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(team, field, value)

    db.commit()
    db.refresh(team)
    return _build_team_response(team, db)


@router.delete("/teams/{team_id}", status_code=200)
def delete_team(
    team_id: UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a team. Owner only."""
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    if team.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Only the team owner can delete the team")

    team.is_active = False
    db.commit()
    return {"status": "ok"}


@router.get("/teams/{team_id}/members")
def list_members(
    team_id: UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List team members. Any member can view."""
    service = TeamService(db)
    if not service.check_permission(user.id, team_id, "viewer"):
        raise HTTPException(status_code=403, detail="Not a member of this team")

    members = (
        db.query(TeamMember)
        .filter(TeamMember.team_id == team_id)
        .all()
    )
    result = []
    for m in members:
        member_user = db.query(User).filter(User.id == m.user_id).first()
        result.append(
            TeamMemberResponse(
                id=m.id,
                user_id=m.user_id,
                email=member_user.email if member_user else "",
                display_name=member_user.display_name if member_user else None,
                avatar_url=member_user.avatar_url if member_user else None,
                role=m.role,
                joined_at=m.joined_at,
            )
        )
    return {"items": result}


@router.post("/teams/{team_id}/members/invite", status_code=201)
def invite_member(
    team_id: UUID,
    body: InviteMemberRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Invite a new member to the team. Requires admin+ role."""
    service = TeamService(db)
    if not service.check_permission(user.id, team_id, "admin"):
        raise HTTPException(status_code=403, detail="Admin role required to invite members")

    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    try:
        invite = service.invite_member(
            team=team,
            email=body.email,
            role=body.role,
            invited_by=user,
        )
    except PermissionError as e:
        raise HTTPException(
            status_code=403,
            detail=ErrorResponse(
                error=ErrorDetail(
                    code="PLAN_LIMIT_EXCEEDED",
                    message=str(e),
                )
            ).model_dump(),
        )
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))

    return InviteResponse(
        invite_id=invite.id,
        email=invite.email,
        role=invite.role,
        expires_at=invite.expires_at,
    )


@router.patch("/teams/{team_id}/members/{member_user_id}")
def update_member_role(
    team_id: UUID,
    member_user_id: UUID,
    body: UpdateMemberRoleRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update a team member's role. Requires admin+ role."""
    service = TeamService(db)
    try:
        member = service.update_member_role(
            team_id=team_id,
            user_id=member_user_id,
            new_role=body.role,
            updated_by=user.id,
        )
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    member_user = db.query(User).filter(User.id == member.user_id).first()
    return TeamMemberResponse(
        id=member.id,
        user_id=member.user_id,
        email=member_user.email if member_user else "",
        display_name=member_user.display_name if member_user else None,
        avatar_url=member_user.avatar_url if member_user else None,
        role=member.role,
        joined_at=member.joined_at,
    )


@router.delete("/teams/{team_id}/members/{member_user_id}")
def remove_member(
    team_id: UUID,
    member_user_id: UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Remove a member from the team. Requires admin+ role."""
    service = TeamService(db)
    try:
        service.remove_member(
            team_id=team_id,
            user_id=member_user_id,
            removed_by=user.id,
        )
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return {"status": "ok"}


@router.get("/teams/{team_id}/jobs")
def list_team_jobs(
    team_id: UUID,
    status: str | None = Query(None, pattern="^(queued|running|completed|failed|canceled)$"),
    limit: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List jobs belonging to a team. Any member can view."""
    service = TeamService(db)
    if not service.check_permission(user.id, team_id, "viewer"):
        raise HTTPException(status_code=403, detail="Not a member of this team")

    query = db.query(Job).filter(Job.team_id == team_id)
    if status:
        query = query.filter(Job.status == status)

    jobs = query.order_by(Job.created_at.desc()).limit(limit).all()
    return {
        "items": [JobResponse.model_validate(j) for j in jobs]
    }


def _calculate_period_start(period: str) -> datetime:
    """Calculate the start of a period for analytics."""
    now = datetime.now(timezone.utc)
    if period == "week":
        return now - timedelta(days=7)
    elif period == "quarter":
        return now - timedelta(days=90)
    else:  # month (default)
        return now - timedelta(days=30)


@router.get("/teams/{team_id}/usage")
def team_usage(
    team_id: UUID,
    period: str = Query("month", pattern="^(week|month|quarter)$"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get team usage analytics. Requires admin+ role."""
    service = TeamService(db)
    if not service.check_permission(user.id, team_id, "admin"):
        raise HTTPException(status_code=403, detail="Admin role required for analytics")

    period_start = _calculate_period_start(period)

    # Aggregate team usage
    stats = (
        db.query(
            func.count(Job.id).label("total_jobs"),
            func.sum(Job.cost_usd).label("total_cost"),
        )
        .filter(
            Job.team_id == team_id,
            Job.created_at >= period_start,
        )
        .first()
    )

    completed_count = (
        db.query(func.count(Job.id))
        .filter(
            Job.team_id == team_id,
            Job.created_at >= period_start,
            Job.status == "completed",
        )
        .scalar()
    )

    failed_count = (
        db.query(func.count(Job.id))
        .filter(
            Job.team_id == team_id,
            Job.created_at >= period_start,
            Job.status == "failed",
        )
        .scalar()
    )

    # Per-member breakdown
    member_stats = (
        db.query(
            User.display_name,
            User.email,
            func.count(Job.id).label("jobs_created"),
        )
        .join(Job, Job.user_id == User.id)
        .filter(
            Job.team_id == team_id,
            Job.created_at >= period_start,
        )
        .group_by(User.id)
        .all()
    )

    # Per-channel breakdown
    channel_stats = (
        db.query(
            YouTubeChannel.channel_title,
            func.count(Video.id).label("videos_uploaded"),
        )
        .join(Video, Video.channel_id == YouTubeChannel.id)
        .filter(
            YouTubeChannel.team_id == team_id,
            Video.created_at >= period_start,
        )
        .group_by(YouTubeChannel.id)
        .all()
    )

    return TeamUsageResponse(
        period=period,
        period_start=period_start.isoformat(),
        total_jobs=stats.total_jobs or 0 if stats else 0,
        completed_jobs=completed_count or 0,
        failed_jobs=failed_count or 0,
        total_cost_usd=float(stats.total_cost or 0) if stats else 0.0,
        members=[
            {"name": m.display_name, "email": m.email, "jobs": m.jobs_created}
            for m in member_stats
        ],
        channels=[
            {"name": c.channel_title, "uploads": c.videos_uploaded}
            for c in channel_stats
        ],
    )

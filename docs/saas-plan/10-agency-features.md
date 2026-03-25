# 10 — Agency Features (Day-1 First-Class Support)

## Overview

Agency features are NOT an afterthought — they're built into the core data model from
day one. Every job, video, and channel has an optional `team_id` foreign key. The
permission system handles both individual and team contexts seamlessly.

---

## Core Agency Capabilities

### 1. Team Management

**Team Roles:**

| Role | Permissions |
|------|------------|
| **Owner** | Full access. Manage billing, delete team, manage all members. |
| **Admin** | Manage members (invite/remove), manage channels, create/delete jobs |
| **Member** | Create jobs, view team videos, upload to shared channels |
| **Viewer** | View-only access to team's videos and job history |

**Role Hierarchy:**
```
Owner > Admin > Member > Viewer
```

Each role can do everything the role below it can do, plus its own permissions.

```python
# saas/services/team_service.py

ROLE_HIERARCHY = {"owner": 4, "admin": 3, "member": 2, "viewer": 1}

class TeamService:
    def check_permission(self, user_id: str, team_id: str, required_role: str) -> bool:
        """Check if user has at least the required role in the team."""
        member = self.db.query(TeamMember).filter(
            TeamMember.team_id == team_id,
            TeamMember.user_id == user_id,
        ).first()

        if not member:
            return False

        return ROLE_HIERARCHY.get(member.role, 0) >= ROLE_HIERARCHY.get(required_role, 0)

    def create_team(self, owner: User, name: str, brand_color: str = None) -> Team:
        """Create a team and add the owner as first member."""
        # Check team seat limit
        usage = UsageService(self.db)
        can_create, reason = usage.check_team_seats_for_new_team(owner)
        if not can_create:
            raise PermissionError(reason)

        slug = self._generate_slug(name)
        team = Team(
            name=name,
            slug=slug,
            owner_id=owner.id,
            brand_color=brand_color,
        )
        self.db.add(team)
        self.db.flush()

        # Owner is automatically a member
        self.db.add(TeamMember(
            team_id=team.id,
            user_id=owner.id,
            role="owner",
        ))
        self.db.commit()
        return team

    def invite_member(self, team: Team, email: str, role: str, invited_by: User) -> TeamInvite:
        """Create a team invite (sends email)."""
        # Check team seat limit
        usage = UsageService(self.db)
        can_add, reason = usage.check_team_seats(team)
        if not can_add:
            raise PermissionError(reason)

        import secrets
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

        # TODO: Send invite email
        # send_invite_email(email, team.name, invited_by.display_name, token)

        return invite

    def accept_invite(self, token: str, user: User) -> TeamMember:
        """Accept a team invitation."""
        invite = self.db.query(TeamInvite).filter(
            TeamInvite.token == token,
            TeamInvite.accepted_at.is_(None),
            TeamInvite.expires_at > datetime.now(timezone.utc),
        ).first()

        if not invite:
            raise ValueError("Invalid or expired invite")

        member = TeamMember(
            team_id=invite.team_id,
            user_id=user.id,
            role=invite.role,
            invited_by=invite.invited_by,
        )
        self.db.add(member)
        invite.accepted_at = datetime.now(timezone.utc)
        self.db.commit()
        return member
```

### 2. Shared YouTube Channels

Agencies connect YouTube channels that team members can use:

```python
# When connecting a channel, optionally assign to team
@router.post("/channels/connect")
async def connect_channel(
    request: ChannelConnectRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # If team_id provided, verify user is admin+ on that team
    if request.team_id:
        team_service = TeamService(db)
        if not team_service.check_permission(user.id, request.team_id, "admin"):
            raise HTTPException(403, "Admin role required to connect team channels")

    # Start YouTube OAuth flow with team_id in state
    state = json.dumps({"user_id": str(user.id), "team_id": str(request.team_id) if request.team_id else None})
    auth_url = generate_youtube_oauth_url(state=state)
    return {"auth_url": auth_url}
```

Team members with `member` role or above can create jobs targeting shared channels:

```python
# In job creation
@router.post("/jobs")
async def create_job(request: JobCreateRequest, user: User = Depends(get_current_user)):
    if request.channel_id:
        channel = db.query(YouTubeChannel).filter(YouTubeChannel.id == request.channel_id).first()

        # Personal channel: must be owner
        if not channel.team_id and channel.user_id != user.id:
            raise HTTPException(403, "Not your channel")

        # Team channel: must be member+
        if channel.team_id:
            if not team_service.check_permission(user.id, channel.team_id, "member"):
                raise HTTPException(403, "Must be a team member to use this channel")
```

### 3. Team-Scoped Jobs and Videos

When a team member creates a job, it's tagged with both `user_id` (who created it)
and `team_id` (which team it belongs to):

```python
# Job creation with team context
@router.post("/jobs")
async def create_job(request: JobCreateRequest, user: User = Depends(get_current_user)):
    job = Job(
        user_id=user.id,
        team_id=request.team_id,       # Optional: assigns to team
        channel_id=request.channel_id,
        topic=request.topic,
        # ... other fields
    )
```

**Visibility rules:**
- Personal jobs (no team_id): only visible to the user who created them
- Team jobs: visible to ALL team members (any role)
- Team admin/owner: can see all team jobs + individual member jobs within the team

```python
# List jobs with team context
@router.get("/jobs")
async def list_jobs(
    team_id: UUID | None = None,
    user: User = Depends(get_current_user),
):
    query = db.query(Job)

    if team_id:
        # Team context: show all team jobs
        if not team_service.check_permission(user.id, team_id, "viewer"):
            raise HTTPException(403)
        query = query.filter(Job.team_id == team_id)
    else:
        # Personal context: show only user's own jobs
        query = query.filter(Job.user_id == user.id, Job.team_id.is_(None))

    return query.order_by(Job.created_at.desc()).all()
```

### 4. Team Analytics

```python
# saas/api/v1/teams.py

@router.get("/teams/{team_id}/usage")
async def team_usage(
    team_id: UUID,
    period: str = "month",   # week, month, quarter
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not team_service.check_permission(user.id, team_id, "admin"):
        raise HTTPException(403, "Admin role required for analytics")

    # Aggregate team usage
    from sqlalchemy import func

    period_start = _calculate_period_start(period)

    stats = db.query(
        func.count(Job.id).label("total_jobs"),
        func.count(Job.id).filter(Job.status == "completed").label("completed_jobs"),
        func.count(Job.id).filter(Job.status == "failed").label("failed_jobs"),
        func.sum(Job.cost_usd).label("total_cost"),
    ).filter(
        Job.team_id == team_id,
        Job.created_at >= period_start,
    ).first()

    # Per-member breakdown
    member_stats = db.query(
        User.display_name,
        User.email,
        func.count(Job.id).label("jobs_created"),
    ).join(Job, Job.user_id == User.id).filter(
        Job.team_id == team_id,
        Job.created_at >= period_start,
    ).group_by(User.id).all()

    # Per-channel breakdown
    channel_stats = db.query(
        YouTubeChannel.channel_title,
        func.count(Video.id).label("videos_uploaded"),
    ).join(Video, Video.channel_id == YouTubeChannel.id).filter(
        YouTubeChannel.team_id == team_id,
        Video.created_at >= period_start,
    ).group_by(YouTubeChannel.id).all()

    return {
        "period": period,
        "period_start": period_start.isoformat(),
        "total_jobs": stats.total_jobs,
        "completed_jobs": stats.completed_jobs,
        "failed_jobs": stats.failed_jobs,
        "total_cost_usd": float(stats.total_cost or 0),
        "members": [{"name": m.display_name, "email": m.email, "jobs": m.jobs_created} for m in member_stats],
        "channels": [{"name": c.channel_title, "uploads": c.videos_uploaded} for c in channel_stats],
    }
```

### 5. White-Label Support (Agency Tier)

Agency plan includes basic white-label capabilities:

```python
# teams table has:
# - brand_color (VARCHAR 7, hex)
# - custom_domain (VARCHAR 255)
# - logo_url (VARCHAR 500)
```

**What white-label provides:**
- Custom brand color applied to the dashboard when viewing as team
- Team logo in sidebar and emails
- Custom domain mapping (e.g., `shorts.agency.com` → their ShortFactory dashboard)
- Branded email notifications (job complete, invite, etc.)
- Removal of "Powered by ShortFactory" from generated thumbnails (if any)

**Implementation (custom domain):**
- DNS: Agency points CNAME to `custom.shortfactory.io`
- Caddy/nginx: wildcard SSL + reverse proxy
- Frontend: detect domain → load team branding from API
- API: `GET /branding?domain=shorts.agency.com` returns team config

### 6. Bulk Operations

Agencies often need to produce many videos at once:

```python
# POST /jobs/bulk
@router.post("/jobs/bulk")
async def create_bulk_jobs(
    request: BulkJobCreateRequest,    # topics: list[str], shared settings
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create multiple video generation jobs at once (max 20)."""
    if len(request.topics) > 20:
        raise HTTPException(400, "Maximum 20 jobs per bulk request")

    # Check quota for all jobs
    usage_service = UsageService(db)
    for _ in request.topics:
        can_create, reason = usage_service.check_can_create_job(user)
        if not can_create:
            raise HTTPException(402, reason)

    jobs = []
    for topic in request.topics:
        job = Job(
            user_id=user.id,
            team_id=request.team_id,
            channel_id=request.channel_id,
            topic=topic,
            language=request.language or user.default_lang,
            # ... shared settings
        )
        db.add(job)
        jobs.append(job)

    db.commit()

    # Enqueue all jobs
    queue = _get_queue_for_user(db, user.id)
    for job in jobs:
        run_video_pipeline.apply_async(args=[str(job.id)], queue=queue)

    return {"jobs": [{"id": str(j.id), "topic": j.topic, "status": "queued"} for j in jobs]}
```

### 7. Content Calendar / Scheduling

Agencies plan content ahead:

```python
# POST /jobs with scheduled_at
{
  "topic": "Monday motivation tips",
  "channel_id": "uuid",
  "auto_upload": true,
  "scheduled_at": "2026-03-31T09:00:00Z"   # Generate + upload at this time
}
```

The `process_scheduled_jobs` beat task (from 07-task-queue.md) picks these up when due.

**Calendar API:**

```python
@router.get("/teams/{team_id}/calendar")
async def team_calendar(
    team_id: UUID,
    start_date: date,
    end_date: date,
    user: User = Depends(get_current_user),
):
    """Get scheduled and completed jobs as calendar events."""
    jobs = db.query(Job).filter(
        Job.team_id == team_id,
        or_(
            and_(Job.scheduled_at >= start_date, Job.scheduled_at <= end_date),
            and_(Job.created_at >= start_date, Job.created_at <= end_date),
        ),
    ).all()

    return {
        "events": [
            {
                "id": str(j.id),
                "title": j.topic[:50],
                "date": (j.scheduled_at or j.created_at).isoformat(),
                "status": j.status,
                "channel": j.channel.channel_title if j.channel else None,
                "created_by": j.user.display_name,
            }
            for j in jobs
        ]
    }
```

---

## Agency-Specific Frontend Pages

### Team Dashboard (`/dashboard/teams/{id}`)

Shows:
- Team overview (member count, channel count, total videos)
- Recent team activity (who created what)
- Usage vs. plan limits
- Quick actions (invite, connect channel, bulk create)

### Content Calendar (`/dashboard/teams/{id}/calendar`)

- Monthly/weekly calendar view
- Scheduled jobs shown as future events
- Completed jobs shown as past events
- Drag-and-drop to reschedule
- Color-coded by channel

### Team Activity Feed (`/dashboard/teams/{id}/activity`)

- Real-time feed of team actions
- "Jane created a video about SpaceX"
- "Bob uploaded 'AI Revolution' to Tech Daily channel"
- "3 scheduled videos are due this week"

---

## Billing for Teams

The team **owner's** subscription determines team limits. The owner pays for
everything — team members don't need their own paid subscriptions.

```
Agency plan ($149/mo) gives the TEAM:
- 500 videos/month (shared across all members)
- Unlimited channels
- 10 team seats
- White-label
- Priority queue
- API access
```

If the team exceeds 500 videos, overage is billed to the team owner's Stripe account
at $0.40/video.

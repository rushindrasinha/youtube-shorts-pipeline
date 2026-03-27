from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, text
from sqlalchemy.orm import Session

from ...models.job import Job
from ...models.subscription import Subscription
from ...models.user import User
from ..deps import get_current_user, get_db

router = APIRouter()


def _require_admin(user: User = Depends(get_current_user)) -> User:
    """Dependency that ensures the current user is an admin."""
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


@router.get("/admin/stats")
def admin_stats(
    admin: User = Depends(_require_admin),
    db: Session = Depends(get_db),
):
    """Aggregate system statistics."""
    total_users = db.query(func.count(User.id)).scalar() or 0
    total_jobs = db.query(func.count(Job.id)).scalar() or 0
    completed_jobs = (
        db.query(func.count(Job.id)).filter(Job.status == "completed").scalar() or 0
    )
    failed_jobs = (
        db.query(func.count(Job.id)).filter(Job.status == "failed").scalar() or 0
    )
    running_jobs = (
        db.query(func.count(Job.id)).filter(Job.status == "running").scalar() or 0
    )
    total_cost = db.query(func.sum(Job.cost_usd)).filter(Job.status == "completed").scalar() or 0

    return {
        "total_users": total_users,
        "total_jobs": total_jobs,
        "completed_jobs": completed_jobs,
        "failed_jobs": failed_jobs,
        "active_jobs": running_jobs,
        "total_cost": float(total_cost),
    }


@router.get("/admin/users")
def admin_list_users(
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
    admin: User = Depends(_require_admin),
    db: Session = Depends(get_db),
):
    """Paginated user list for admin."""
    total = db.query(func.count(User.id)).scalar() or 0
    users = (
        db.query(User)
        .order_by(User.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    return {
        "total": total,
        "offset": offset,
        "limit": limit,
        "users": [
            {
                "id": str(u.id),
                "email": u.email,
                "display_name": u.display_name,
                "role": u.role,
                "is_active": u.is_active,
                "created_at": u.created_at.isoformat() if u.created_at else None,
            }
            for u in users
        ],
    }


@router.patch("/admin/users/{user_id}")
def admin_update_user(
    user_id: str,
    role: str | None = None,
    is_active: bool | None = None,
    admin: User = Depends(_require_admin),
    db: Session = Depends(get_db),
):
    """Admin can ban a user (is_active=False) or change their role/plan."""
    from uuid import UUID

    try:
        uid = UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user ID")

    target = db.query(User).filter(User.id == uid).first()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    if role is not None:
        if role not in ("user", "admin"):
            raise HTTPException(status_code=400, detail="Invalid role")
        target.role = role

    if is_active is not None:
        target.is_active = is_active

    db.commit()
    db.refresh(target)

    return {
        "id": str(target.id),
        "email": target.email,
        "role": target.role,
        "is_active": target.is_active,
    }

from fastapi import APIRouter

from . import (
    admin,
    auth,
    billing,
    channels,
    health,
    jobs,
    provider_keys,
    teams,
    topics,
    users,
    videos,
    webhooks,
)

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(jobs.router, tags=["jobs"])
api_router.include_router(teams.router, tags=["teams"])
api_router.include_router(channels.router, tags=["channels"])
api_router.include_router(topics.router, tags=["topics"])
api_router.include_router(billing.router, prefix="/billing", tags=["billing"])
api_router.include_router(webhooks.router, prefix="/webhooks", tags=["webhooks"])
api_router.include_router(videos.router, prefix="/videos", tags=["videos"])
api_router.include_router(
    provider_keys.router,
    prefix="/users/me/provider-keys",
    tags=["provider-keys"],
)
api_router.include_router(health.router, tags=["health"])
api_router.include_router(admin.router, tags=["admin"])

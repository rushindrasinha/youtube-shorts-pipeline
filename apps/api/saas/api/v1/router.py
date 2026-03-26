from fastapi import APIRouter

from . import auth, health, jobs, users

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(jobs.router, tags=["jobs"])
api_router.include_router(health.router, tags=["health"])

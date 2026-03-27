from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .settings import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    settings.validate_production()
    yield
    # Shutdown


def create_app() -> FastAPI:
    app = FastAPI(
        title="ShortFactory API",
        version="0.1.0",
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS.split(","),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    # Include routers
    from .api.v1.router import api_router

    app.include_router(api_router, prefix="/api/v1")
    return app


app = create_app()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from services.api.app.api.routes import router
from services.api.app.api.sources import router as sources_router
from services.api.app.core.config import get_settings
from services.api.app.core.logging import configure_logging

settings = get_settings()
configure_logging(settings.log_level)
app = FastAPI(
    title="GradJobs API",
    version="0.1.0",
    description="Early-career discovery from supported public employer job boards.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["GET", "POST", "PATCH"],
    allow_headers=["Content-Type"],
)
app.include_router(router)
app.include_router(sources_router)

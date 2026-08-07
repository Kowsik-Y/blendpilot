"""
BlendPilot AI — FastAPI Application Entry Point

Main entry point for the BlendPilot backend API. Exposes workflow control,
SSE real-time streaming, asset export, and health check endpoints.
"""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.api.export import router as export_router
from backend.api.workflow import router as workflow_router
from backend.routers.copilot import router as copilot_router
from backend.config import settings

# Configure root logger
logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("blendpilot.backend")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown lifecycles."""
    logger.info("Starting %s (v%s)...", settings.app_name, settings.app_version)
    os.makedirs(settings.output_dir, exist_ok=True)
    os.makedirs(settings.checkpoints_dir, exist_ok=True)
    yield
    logger.info("Shutting down %s...", settings.app_name)


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Agentic AI Copilot for Autonomous 3D Modeling in Blender",
    lifespan=lifespan,
)

# ── CORS Middleware ─────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Include Routers ─────────────────────────────────────────
app.include_router(workflow_router)
app.include_router(export_router)
app.include_router(copilot_router)

@app.get("/api/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {
        "status": "healthy",
        "app": settings.app_name,
        "version": settings.app_version,
    }


# ── Static Files for Output Artifacts Previews ──────────────
if os.path.exists(settings.output_dir):
    app.mount("/static", StaticFiles(directory=settings.output_dir), name="static")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host=settings.host, port=settings.port, reload=settings.debug)

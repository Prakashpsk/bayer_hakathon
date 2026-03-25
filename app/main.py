"""
FastAPI application for Autonomous Incident Commander.
Serves the dashboard UI and API endpoints.
"""
from __future__ import annotations

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.routes.investigate import router as investigate_router
from app.routes.health import router as health_router

app = FastAPI(
    title="Autonomous Incident Commander",
    description="Multi-Agent AI System for Diagnosing Cloud System Failures",
    version="1.0.0",
)

# Templates
templates_dir = os.path.join(os.path.dirname(__file__), "templates")
templates = Jinja2Templates(directory=templates_dir)

# Routes
app.include_router(health_router)
app.include_router(investigate_router)


@app.get("/")
async def root():
    """Redirect to dashboard."""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/dashboard")

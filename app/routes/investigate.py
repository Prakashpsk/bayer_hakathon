"""
Investigation routes - Trigger alerts and get RCA reports.
"""
from __future__ import annotations

import asyncio
import uuid
from datetime import datetime

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

import os
from models.schemas import Alert, Severity, RCAReport
from agents.commander_agent import commander_agent, CommanderDeps
from config import MODEL_NAME

router = APIRouter()

templates_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")
templates = Jinja2Templates(directory=templates_dir)

# In-memory store for reports (use S3 in production)
reports_store: dict[str, dict] = {}


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Serve the main dashboard UI."""
    try:
        print(f"DEBUG: Serving dashboard. Reports in store: {len(reports_store)}")
        return templates.TemplateResponse(
            request=request,
            name="dashboard.html",
            context={"request": request, "reports": list(reports_store.values())}
        )
    except Exception as e:
        print(f"DEBUG ERROR in dashboard: {str(e)}")
        import traceback
        traceback.print_exc()
        raise e


@router.post("/investigate")
async def trigger_investigation():
    """Trigger the full multi-agent investigation. Returns RCA report."""
    investigation_id = str(uuid.uuid4())[:8]

    # Create the demo alert
    alert = Alert(
        alert_id=f"ALERT-{investigation_id}",
        service="checkout-service",
        title="P99 Latency Critical - Checkout Service",
        description=(
            "Checkout Service p99 latency has spiked to 2000ms "
            "(threshold: 500ms). Error rate at 73%. "
            "Multiple HTTP 500 responses reported. "
            "Approximately 450 users affected."
        ),
        severity=Severity.CRITICAL,
        timestamp="2026-03-25T10:00:00Z",
        metric_value=2001.0,
        threshold=500.0,
    )

    # Run Commander Agent
    deps = CommanderDeps(
        alert_service=alert.service,
        alert_description=alert.description,
        incident_time=alert.timestamp,
    )

    result = await commander_agent.run(
        (
            f"INCIDENT ALERT:\n"
            f"  Alert ID: {alert.alert_id}\n"
            f"  Service: {alert.service}\n"
            f"  Title: {alert.title}\n"
            f"  Description: {alert.description}\n"
            f"  Severity: {alert.severity.value}\n"
            f"  Time: {alert.timestamp}\n"
            f"  Metric Value: {alert.metric_value}ms (threshold: {alert.threshold}ms)\n\n"
            f"Conduct a full investigation using all three specialist agents. "
            f"Follow the reasoning loop: DETECT -> PLAN -> INVESTIGATE -> DECIDE -> ACT -> REPORT. "
            f"Cross-correlate findings to identify the root cause."
        ),
        deps=deps,
        model=MODEL_NAME,
    )

    report = result.output
    usage = result.usage()

    # Store report
    report_data = {
        "id": investigation_id,
        "timestamp": datetime.utcnow().isoformat(),
        "alert": alert.model_dump(),
        "report": report.model_dump(),
        "usage": {
            "requests": usage.requests,
            "input_tokens": usage.input_tokens,
            "output_tokens": usage.output_tokens,
        },
    }
    reports_store[investigation_id] = report_data

    return report_data


@router.get("/report/{report_id}")
async def get_report(report_id: str):
    """Get a saved RCA report by ID."""
    if report_id in reports_store:
        return reports_store[report_id]
    return {"error": f"Report {report_id} not found"}


@router.get("/reports")
async def list_reports():
    """List all saved reports."""
    return {"reports": list(reports_store.values())}

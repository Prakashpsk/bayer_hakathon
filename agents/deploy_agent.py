"""
Deploy Intelligence Agent — The Historian.

Maps real-time errors against the timeline of CI/CD deployments
and service configuration changes using Pydantic AI with tool-use.
"""
from __future__ import annotations

from dataclasses import dataclass

from pydantic_ai import Agent, RunContext

from data.mock_deployments import (
    get_recent_deployments,
    get_deployment_diff,
    check_rollback_available,
)
from models.schemas import DeployAnalysisResult


@dataclass
class DeployDeps:
    """Dependencies for the Deploy Intelligence Agent."""
    incident_time: str = "2026-03-25T10:00:00Z"
    lookback_hours: int = 24


# ── Agent Definition ──────────────────────────────────────────────────────
# Model is NOT set here — pass it at runtime via agent.run(model=...)

deploy_agent = Agent(
    deps_type=DeployDeps,
    output_type=DeployAnalysisResult,
    instructions=(
        "You are the DEPLOY INTELLIGENCE AGENT — a historian who maps errors "
        "against CI/CD deployment timelines.\n\n"
        "Your job is to:\n"
        "1. List all recent deployments around the incident time\n"
        "2. Identify deployments that happened BEFORE the incident\n"
        "3. Check config changes in suspicious deployments (especially those "
        "   that changed database or infrastructure settings)\n"
        "4. Flag deployments that correlate with the incident timeline\n"
        "5. Check if rollback is available for suspicious deployments\n\n"
        "A deployment is suspicious if it happened within 1 hour BEFORE the incident "
        "and involved configuration changes to infrastructure or database services."
    ),
)


@deploy_agent.tool
async def tool_get_recent_deployments(
    ctx: RunContext[DeployDeps],
) -> str:
    """List all deployments from the last 24 hours around the incident time."""
    results = get_recent_deployments(hours_back=ctx.deps.lookback_hours)
    if not results:
        return "No deployments found in the time window."
    lines = ["Recent deployments:"]
    for d in results:
        flag = "⚠️ " if d["config_changes"] else "  "
        lines.append(
            f"{flag}[{d['timestamp']}] {d['deploy_id']} | {d['service']} | "
            f"{d['version']} | by {d['deployer']}"
        )
        lines.append(f"    Summary: {d['change_summary']}")
        if d["config_changes"]:
            lines.append(f"    ⚠️  CONFIG CHANGES DETECTED: {d['config_changes']}")
    return "\n".join(lines)


@deploy_agent.tool
async def tool_get_deployment_diff(
    ctx: RunContext[DeployDeps],
    deploy_id: str,
) -> str:
    """Get detailed configuration changes for a specific deployment.

    Args:
        deploy_id: The deployment ID to inspect (e.g., 'deploy-cfg-2026-0325')
    """
    diff = get_deployment_diff(deploy_id)
    if "error" in diff:
        return diff["error"]
    lines = [
        f"Deployment: {diff['deploy_id']}",
        f"Time: {diff['timestamp']}",
        f"Service: {diff['service']}",
        f"Deployer: {diff['deployer']}",
        f"Summary: {diff['change_summary']}",
    ]
    if diff["config_changes"]:
        lines.append("Configuration Changes:")
        for key, val in diff["config_changes"].items():
            lines.append(f"  {key}: {val['old']} → {val['new']}")
    else:
        lines.append("No configuration changes (code-only deployment)")
    lines.append(f"Rollback available: {diff['rollback_available']}")
    return "\n".join(lines)


@deploy_agent.tool
async def tool_check_rollback(
    ctx: RunContext[DeployDeps],
    deploy_id: str,
) -> str:
    """Check if a rollback is available for a specific deployment.

    Args:
        deploy_id: The deployment ID to check rollback for
    """
    result = check_rollback_available(deploy_id)
    if "error" in result and result.get("rollback_available") is False:
        return result["error"]
    return (
        f"Deployment: {result['deploy_id']}\n"
        f"Service: {result['service']}\n"
        f"Rollback available: {result['rollback_available']}\n"
        f"Rollback target: {result['rollback_to_version']}"
    )

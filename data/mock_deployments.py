"""
Mock CI/CD deployment history with the ROOT CAUSE deployment injected.

Simulates the demo scenario:
  - A configuration deployment at 09:45 reduced max_connections from 100 → 10
  - This is the root cause of the checkout-service latency spike at 10:00
"""
from models.schemas import Deployment


def get_mock_deployments() -> list[Deployment]:
    """Return simulated deployment history."""
    return [
        # Normal deployment — 2 days ago
        Deployment(
            deploy_id="deploy-app-2026-0323",
            timestamp="2026-03-23T14:00:00Z",
            service="checkout-service",
            version="v2.14.1",
            deployer="ci-bot",
            change_summary="Bug fix: corrected tax calculation rounding",
            config_changes=None,
            rollback_available=True,
        ),
        # Normal deployment — yesterday
        Deployment(
            deploy_id="deploy-app-2026-0324",
            timestamp="2026-03-24T11:00:00Z",
            service="payment-service",
            version="v3.8.0",
            deployer="ci-bot",
            change_summary="Added support for new payment provider API v2",
            config_changes=None,
            rollback_available=True,
        ),

        # ══════════════════════════════════════════════════════════════
        # ██  ROOT CAUSE DEPLOYMENT — 15 minutes before incident  ██
        # ══════════════════════════════════════════════════════════════
        Deployment(
            deploy_id="deploy-cfg-2026-0325",
            timestamp="2026-03-25T09:45:00Z",
            service="database-primary",
            version="config-v1.2.3",
            deployer="admin@bayer.com",
            change_summary="Database configuration update: connection pool tuning for cost optimization",
            config_changes={
                "max_connections": {"old": 100, "new": 10},
                "idle_timeout_ms": {"old": 30000, "new": 5000},
                "connection_max_lifetime_ms": {"old": 3600000, "new": 600000},
            },
            rollback_available=True,
        ),

        # Another normal deployment — after incident
        Deployment(
            deploy_id="deploy-app-2026-0325b",
            timestamp="2026-03-25T10:30:00Z",
            service="api-gateway",
            version="v1.5.2",
            deployer="ci-bot",
            change_summary="Updated rate limiting rules",
            config_changes=None,
            rollback_available=True,
        ),
    ]


def get_recent_deployments(hours_back: int = 24) -> list[dict]:
    """Get deployments within the last N hours from incident time."""
    deployments = get_mock_deployments()
    # For the demo, return all deployments within the time window
    results = []
    for d in deployments:
        if d.timestamp >= "2026-03-24T10:00:00Z":
            results.append(d.model_dump())
    return results


def get_deployment_diff(deploy_id: str) -> dict:
    """Get detailed config changes for a specific deployment."""
    for d in get_mock_deployments():
        if d.deploy_id == deploy_id:
            return {
                "deploy_id": d.deploy_id,
                "timestamp": d.timestamp,
                "service": d.service,
                "deployer": d.deployer,
                "change_summary": d.change_summary,
                "config_changes": d.config_changes or {},
                "rollback_available": d.rollback_available,
            }
    return {"error": f"Deployment {deploy_id} not found"}


def check_rollback_available(deploy_id: str) -> dict:
    """Check if a rollback is available for a deployment."""
    for d in get_mock_deployments():
        if d.deploy_id == deploy_id:
            return {
                "deploy_id": d.deploy_id,
                "rollback_available": d.rollback_available,
                "service": d.service,
                "rollback_to_version": "config-v1.2.2" if d.config_changes else d.version,
            }
    return {"error": f"Deployment {deploy_id} not found", "rollback_available": False}

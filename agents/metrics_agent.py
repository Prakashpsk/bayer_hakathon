"""
Metrics Agent — The Telemetry Analyst.

Monitors performance counters (CPU, p99 Latency, Memory Leak patterns)
to spot anomalies using Pydantic AI with tool-use.
"""
from __future__ import annotations

from dataclasses import dataclass

from pydantic_ai import Agent, RunContext

from data.mock_metrics import get_metrics_for_service, detect_anomalies
from models.schemas import MetricsAnalysisResult


@dataclass
class MetricsDeps:
    """Dependencies for the Metrics Agent."""
    target_service: str
    time_start: str = "2026-03-25T09:00:00Z"
    time_end: str = "2026-03-25T11:00:00Z"


# ── Agent Definition ──────────────────────────────────────────────────────
# Model is NOT set here — pass it at runtime via agent.run(model=...)

metrics_agent = Agent(
    deps_type=MetricsDeps,
    output_type=MetricsAnalysisResult,
    instructions=(
        "You are the METRICS AGENT — a telemetry analyst specializing in "
        "performance counters and anomaly detection.\n\n"
        "Your job is to:\n"
        "1. Retrieve metrics for the affected service (latency, error rate)\n"
        "2. Check related infrastructure metrics (CPU, memory, connection pool)\n"
        "3. Detect anomalies by comparing against baselines\n"
        "4. Identify the timeline of metric degradation\n\n"
        "Focus on: p99 latency, CPU%, memory%, connection pool utilization, error rate.\n"
        "Always note the EXACT timestamps when anomalies started."
    ),
)


@metrics_agent.tool
async def tool_get_metrics(
    ctx: RunContext[MetricsDeps],
    service: str,
    metric_name: str,
) -> str:
    """Retrieve metric time-series data for a service.

    Args:
        service: Service name (e.g., 'checkout-service', 'database-primary')
        metric_name: Metric name (e.g., 'p99_latency_ms', 'cpu_percent',
                     'conn_pool_usage_percent', 'error_rate_percent', 'memory_percent')
    """
    results = get_metrics_for_service(service, metric_name)
    if not results:
        return f"No metrics found for {service}/{metric_name}"
    lines = [f"Metrics for {service} — {metric_name}:"]
    for r in results:
        lines.append(f"  {r['timestamp']}: {r['value']}{r['unit']}")
    return "\n".join(lines)


@metrics_agent.tool
async def tool_detect_anomalies(
    ctx: RunContext[MetricsDeps],
    service: str,
) -> str:
    """Detect anomalous metric values that exceed established baselines.

    Args:
        service: Service name to check for anomalies
    """
    anomalies = detect_anomalies(service=service)
    if not anomalies:
        return f"No anomalies detected for {service}"
    lines = [f"Anomalies detected for {service}:"]
    for a in anomalies:
        lines.append(
            f"  [{a['timestamp']}] {a['metric']}: {a['value']}{a['unit']} "
            f"(baseline: {a['baseline']}{a['unit']}, +{a['deviation_percent']}% deviation)"
        )
    return "\n".join(lines)


@metrics_agent.tool
async def tool_compare_baseline(
    ctx: RunContext[MetricsDeps],
    service: str,
) -> str:
    """Compare current metric values against baselines for all metrics.

    Args:
        service: Service to compare
    """
    all_anomalies = detect_anomalies(service=service)
    if not all_anomalies:
        return f"All metrics for {service} are within baseline ranges."

    # Group by metric
    by_metric: dict[str, list] = {}
    for a in all_anomalies:
        by_metric.setdefault(a["metric"], []).append(a)

    lines = [f"Baseline comparison for {service}:"]
    for metric, entries in by_metric.items():
        baseline = entries[0]["baseline"]
        latest = entries[-1]
        lines.append(
            f"  {metric}: baseline={baseline}{latest['unit']} → "
            f"current={latest['value']}{latest['unit']} "
            f"(+{latest['deviation_percent']}% deviation) ⚠️ ANOMALY"
        )
    return "\n".join(lines)

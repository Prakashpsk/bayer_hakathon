"""
Logs Agent — The Forensic Expert.

Deep-scans distributed application logs to find specific stack traces
and error correlations using Pydantic AI with tool-use.
"""
from __future__ import annotations

from dataclasses import dataclass

from pydantic_ai import Agent, RunContext

from data.mock_logs import search_logs, find_stack_traces, get_error_correlations
from models.schemas import LogAnalysisResult


@dataclass
class LogsDeps:
    """Dependencies for the Logs Agent."""
    target_service: str
    time_start: str = "2026-03-25T09:00:00Z"
    time_end: str = "2026-03-25T11:00:00Z"


# ── Agent Definition ──────────────────────────────────────────────────────
# Model is NOT set here — pass it at runtime via agent.run(model=...)
# This allows TestModel to work without an API key.

logs_agent = Agent(
    deps_type=LogsDeps,
    output_type=LogAnalysisResult,
    instructions=(
        "You are the LOGS AGENT — a forensic expert in distributed application logs. "
        "Your job is to deep-scan logs to find error patterns, stack traces, and "
        "correlations across services.\n\n"
        "PROCEDURE:\n"
        "1. Search for ERROR and CRITICAL logs in the target service\n"
        "2. Find all stack traces to identify root error types\n"
        "3. Look for error correlations across services\n"
        "4. Summarize your findings with specific evidence\n\n"
        "Be specific about timestamps, error types, and affected services."
    ),
)


@logs_agent.tool
async def tool_search_logs(
    ctx: RunContext[LogsDeps],
    service: str,
    severity: str,
) -> str:
    """Search application logs for a specific service and severity level.

    Args:
        service: Service name to search (e.g., 'checkout-service', 'database-primary')
        severity: Log severity to filter (INFO, WARN, ERROR, CRITICAL)
    """
    results = search_logs(
        service=service,
        severity=severity,
        time_start=ctx.deps.time_start,
        time_end=ctx.deps.time_end,
    )
    if not results:
        return f"No {severity} logs found for {service}"
    lines = []
    for r in results:
        lines.append(f"[{r['timestamp']}] [{r['level']}] {r['service']}: {r['message']}")
    return "\n".join(lines)


@logs_agent.tool
async def tool_find_stack_traces(
    ctx: RunContext[LogsDeps],
    service: str,
) -> str:
    """Find all log entries with stack traces for a service.

    Args:
        service: Service name to search for stack traces
    """
    results = find_stack_traces(service=service)
    if not results:
        return f"No stack traces found for {service}"
    lines = []
    for r in results:
        lines.append(f"=== {r['timestamp']} | {r['service']} | {r['level']} ===")
        lines.append(f"Message: {r['message']}")
        lines.append(f"Stack Trace:\n{r['stack_trace']}")
        lines.append("")
    return "\n".join(lines)


@logs_agent.tool
async def tool_correlate_errors(ctx: RunContext[LogsDeps]) -> str:
    """Find error correlations across all services. Call this to understand
    how errors in one service relate to errors in other services."""
    correlations = get_error_correlations()
    if not correlations:
        return "No error correlations found"
    lines = []
    for c in correlations:
        lines.append(f"Pattern: {c['pattern']}")
        lines.append(f"  Services: {', '.join(c['services'])}")
        lines.append(f"  First seen: {c['first_seen']}")
        lines.append(f"  Count: {c['count']}")
        lines.append(f"  Correlation: {c['correlation']}")
        lines.append("")
    return "\n".join(lines)

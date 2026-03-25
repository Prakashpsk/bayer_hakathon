"""
Commander Agent — The Orchestrator.

Processes initial alerts, develops an investigation plan, and
coordinates the three specialized investigator agents using
Pydantic AI's agent delegation pattern.

This is the central multi-agent orchestrator that implements the
reasoning loop: DETECT → PLAN → INVESTIGATE → DECIDE → ACT → REPORT
"""
from __future__ import annotations

from dataclasses import dataclass

from pydantic_ai import Agent, RunContext

from models.schemas import RCAReport

from agents.logs_agent import logs_agent, LogsDeps
from agents.metrics_agent import metrics_agent, MetricsDeps
from agents.deploy_agent import deploy_agent, DeployDeps


@dataclass
class CommanderDeps:
    """Dependencies for the Commander Agent."""
    alert_service: str
    alert_description: str
    incident_time: str = "2026-03-25T10:00:00Z"


# ── Agent Definition ──────────────────────────────────────────────────────
# Model is NOT set here — pass it at runtime via agent.run(model=...)

commander_agent = Agent(
    deps_type=CommanderDeps,
    output_type=RCAReport,
    instructions=(
        "You are the COMMANDER AGENT — the lead incident responder and orchestrator.\n\n"
        "You have been triggered by an alert. Your mission is to conduct a thorough "
        "Root Cause Analysis (RCA) by coordinating three specialist agents:\n\n"
        "1. LOGS AGENT — call `investigate_logs` to deep-scan application logs\n"
        "2. METRICS AGENT — call `analyze_metrics` to check performance counters\n"
        "3. DEPLOY INTELLIGENCE — call `check_deployments` to review CI/CD history\n\n"
        "REASONING LOOP:\n"
        "  DETECT → You've received the alert. Note what is happening.\n"
        "  PLAN → Decide which agents to dispatch and in what order.\n"
        "  INVESTIGATE → Call the specialist agents to gather evidence.\n"
        "  DECIDE → Correlate findings across all agents to identify root cause.\n"
        "  ACT → Recommend a specific remediation action.\n"
        "  REPORT → Compile the final RCA report.\n\n"
        "IMPORTANT:\n"
        "- Call ALL THREE agents to gather comprehensive evidence\n"
        "- Cross-correlate: look for time-based correlations between deployments, "
        "  metric changes, and log errors\n"
        "- Be specific about the root cause and evidence\n"
        "- Recommend a concrete action (e.g., rollback deployment X)\n"
        "- Include confidence level based on evidence strength"
    ),
)


# ── Agent Delegation Tools ────────────────────────────────────────────────
# These tools allow the Commander to delegate to sub-agents.
# This is the core Pydantic AI multi-agent pattern: agent delegation.

@commander_agent.tool
async def investigate_logs(ctx: RunContext[CommanderDeps]) -> str:
    """Dispatch the Logs Agent to deep-scan application logs and find error
    patterns, stack traces, and cross-service correlations.
    Call this to understand WHAT errors are happening."""
    deps = LogsDeps(
        target_service=ctx.deps.alert_service,
        time_start="2026-03-25T09:00:00Z",
        time_end="2026-03-25T11:00:00Z",
    )
    result = await logs_agent.run(
        f"Investigate logs for service '{ctx.deps.alert_service}'. "
        f"The alert says: {ctx.deps.alert_description}. "
        f"Incident time: {ctx.deps.incident_time}. "
        f"Search for errors, stack traces, and correlations.",
        deps=deps,
        model=ctx.model,
        usage=ctx.usage,
    )
    output = result.output
    report_lines = [
        "=== LOGS AGENT REPORT ===",
        f"Summary: {output.summary}",
        f"Error count: {output.error_count}",
        f"Top error patterns: {', '.join(output.top_error_patterns)}",
        f"Correlated services: {', '.join(output.correlated_services)}",
        "",
        "Findings:",
    ]
    for f in output.findings:
        report_lines.append(f"  [{f.severity.value}] {f.summary}")
        for e in f.evidence:
            report_lines.append(f"    Evidence: {e}")
    return "\n".join(report_lines)


@commander_agent.tool
async def analyze_metrics(ctx: RunContext[CommanderDeps]) -> str:
    """Dispatch the Metrics Agent to analyze performance counters and
    detect anomalies in latency, CPU, memory, and connection pools.
    Call this to see HOW BAD the impact is and WHEN it started."""
    deps = MetricsDeps(
        target_service=ctx.deps.alert_service,
        time_start="2026-03-25T09:00:00Z",
        time_end="2026-03-25T11:00:00Z",
    )
    result = await metrics_agent.run(
        f"Analyze metrics for service '{ctx.deps.alert_service}' and related infrastructure. "
        f"The alert says: {ctx.deps.alert_description}. "
        f"Incident time: {ctx.deps.incident_time}. "
        f"Check latency, CPU, memory, connection pools, and error rates. "
        f"Also check 'database-primary' metrics.",
        deps=deps,
        model=ctx.model,
        usage=ctx.usage,
    )
    output = result.output
    report_lines = [
        "=== METRICS AGENT REPORT ===",
        f"Summary: {output.summary}",
        f"Anomalies detected: {output.anomalies_detected}",
        f"Affected metrics: {', '.join(output.affected_metrics)}",
        "",
        "Findings:",
    ]
    for f in output.findings:
        report_lines.append(f"  [{f.severity.value}] {f.summary}")
        for e in f.evidence:
            report_lines.append(f"    Evidence: {e}")
    return "\n".join(report_lines)


@commander_agent.tool
async def check_deployments(ctx: RunContext[CommanderDeps]) -> str:
    """Dispatch the Deploy Intelligence Agent to check CI/CD deployment
    history and configuration changes around the incident time.
    Call this to find out WHY the issue started — look for deployments
    that happened before the incident."""
    deps = DeployDeps(
        incident_time=ctx.deps.incident_time,
        lookback_hours=24,
    )
    result = await deploy_agent.run(
        f"Check all deployments around the incident time {ctx.deps.incident_time}. "
        f"The affected service is '{ctx.deps.alert_service}'. "
        f"Look for configuration changes in database or infrastructure "
        f"services that happened BEFORE the incident. "
        f"Check if rollback is available for suspicious deployments.",
        deps=deps,
        model=ctx.model,
        usage=ctx.usage,
    )
    output = result.output
    report_lines = [
        "=== DEPLOY INTELLIGENCE REPORT ===",
        f"Summary: {output.summary}",
        f"Suspicious deployments: {', '.join(output.suspicious_deployments)}",
        f"Recommended rollbacks: {', '.join(output.recommended_rollbacks)}",
        "",
        "Findings:",
    ]
    for f in output.findings:
        report_lines.append(f"  [{f.severity.value}] {f.summary}")
        for e in f.evidence:
            report_lines.append(f"    Evidence: {e}")
    return "\n".join(report_lines)

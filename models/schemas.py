"""
Pydantic schemas for the Autonomous Incident Commander.

All data models used across agents, state management, and reporting.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# ── Enums ──────────────────────────────────────────────────────────────────

class Severity(str, Enum):
    INFO = "INFO"
    WARN = "WARN"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class ReasoningPhase(str, Enum):
    DETECT = "DETECT"
    PLAN = "PLAN"
    INVESTIGATE = "INVESTIGATE"
    DECIDE = "DECIDE"
    ACT = "ACT"
    REPORT = "REPORT"


# ── Raw Data Models ───────────────────────────────────────────────────────

class Alert(BaseModel):
    """Incoming alert that triggers the investigation."""
    alert_id: str = Field(description="Unique alert identifier")
    service: str = Field(description="Affected service name")
    title: str = Field(description="Short alert title")
    description: str = Field(description="Detailed alert description")
    severity: Severity = Field(default=Severity.CRITICAL)
    timestamp: str = Field(description="ISO timestamp when alert fired")
    metric_value: Optional[float] = Field(default=None, description="Metric value that triggered alert")
    threshold: Optional[float] = Field(default=None, description="Threshold that was breached")


class LogEntry(BaseModel):
    """A single application log line."""
    timestamp: str
    service: str
    level: Severity
    message: str
    stack_trace: Optional[str] = None
    request_id: Optional[str] = None


class MetricPoint(BaseModel):
    """A single metric data point."""
    timestamp: str
    service: str
    metric_name: str
    value: float
    unit: str = ""


class Deployment(BaseModel):
    """A CI/CD deployment record."""
    deploy_id: str
    timestamp: str
    service: str
    version: str
    deployer: str
    change_summary: str
    config_changes: Optional[dict] = None
    rollback_available: bool = True


# ── Agent Output Models ───────────────────────────────────────────────────

class Finding(BaseModel):
    """A single finding from any agent."""
    agent: str = Field(description="Which agent produced this finding")
    category: str = Field(description="Category: error_pattern / anomaly / deployment_change / correlation")
    summary: str = Field(description="Human-readable summary of the finding")
    severity: Severity = Field(default=Severity.INFO)
    evidence: list[str] = Field(default_factory=list, description="Supporting evidence lines")
    timestamp_range: Optional[str] = Field(default=None, description="Time range of the finding")


class LogAnalysisResult(BaseModel):
    """Output from the Logs Agent."""
    findings: list[Finding] = Field(default_factory=list)
    error_count: int = Field(default=0)
    top_error_patterns: list[str] = Field(default_factory=list)
    correlated_services: list[str] = Field(default_factory=list)
    summary: str = Field(description="Overall log analysis summary")


class MetricsAnalysisResult(BaseModel):
    """Output from the Metrics Agent."""
    findings: list[Finding] = Field(default_factory=list)
    anomalies_detected: int = Field(default=0)
    affected_metrics: list[str] = Field(default_factory=list)
    summary: str = Field(description="Overall metrics analysis summary")


class DeployAnalysisResult(BaseModel):
    """Output from the Deploy Intelligence Agent."""
    findings: list[Finding] = Field(default_factory=list)
    suspicious_deployments: list[str] = Field(default_factory=list)
    recommended_rollbacks: list[str] = Field(default_factory=list)
    summary: str = Field(description="Overall deployment analysis summary")


# ── Investigation State ───────────────────────────────────────────────────

class InvestigationState(BaseModel):
    """Tracks the state of the investigation through the reasoning loop."""
    phase: ReasoningPhase = Field(default=ReasoningPhase.DETECT)
    alert: Optional[Alert] = None
    findings: list[Finding] = Field(default_factory=list)
    chain_of_thought: list[str] = Field(default_factory=list, description="Agent reasoning steps")
    root_cause: Optional[str] = None
    recommended_action: Optional[str] = None

    def add_thought(self, thought: str):
        self.chain_of_thought.append(f"[{self.phase.value}] {thought}")

    def advance_phase(self):
        phases = list(ReasoningPhase)
        idx = phases.index(self.phase)
        if idx < len(phases) - 1:
            self.phase = phases[idx + 1]


# ── Final RCA Report ─────────────────────────────────────────────────────

class RCAReport(BaseModel):
    """Root Cause Analysis report — the final deliverable."""
    title: str = Field(description="Report title")
    incident_summary: str = Field(description="What happened")
    root_cause: str = Field(description="Identified root cause")
    evidence: list[str] = Field(default_factory=list, description="Key evidence supporting the conclusion")
    timeline: list[str] = Field(default_factory=list, description="Chronological timeline of events")
    impact: str = Field(description="Impact assessment")
    recommended_action: str = Field(description="Recommended remediation action")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence level 0-1")
    chain_of_thought: list[str] = Field(default_factory=list, description="Agent reasoning trace")

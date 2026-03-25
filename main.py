"""
Autonomous Incident Commander - Main Entry Point.

Runs the complete demo scenario:
  TRIGGER: Checkout Service latency spikes to 2000ms
  INVESTIGATION: Multi-agent reasoning loop
  OUTCOME: RCA report identifying config deployment as root cause

Usage:
    set OPENAI_API_KEY=your-key-here
    python main.py
"""
from __future__ import annotations

import asyncio
import sys
import os

# Load .env file FIRST (before any agent imports that need API keys)
from dotenv import load_dotenv
load_dotenv()

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Force UTF-8 for Windows console
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")

from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.table import Table

from models.schemas import Alert, Severity
from agents.commander_agent import commander_agent, CommanderDeps
from config import MODEL_NAME

console = Console(force_terminal=True)


def create_demo_alert() -> Alert:
    """Create the simulated alert that triggers the investigation."""
    return Alert(
        alert_id="ALERT-2026-0325-001",
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


def print_rca_report(report) -> None:
    """Pretty-print the RCA report using Rich."""
    console.print()
    console.print(Panel.fit(
        f"[bold red]ALERT: {report.title}[/bold red]",
        border_style="red",
    ))

    # Summary
    console.print(Panel(
        f"[bold]Incident Summary:[/bold]\n{report.incident_summary}",
        title="Summary",
        border_style="yellow",
    ))

    # Root Cause
    console.print(Panel(
        f"[bold red]{report.root_cause}[/bold red]",
        title="Root Cause",
        border_style="red",
    ))

    # Evidence
    evidence_table = Table(title="Evidence", show_lines=True)
    evidence_table.add_column("#", style="dim", width=3)
    evidence_table.add_column("Evidence", style="cyan")
    for i, e in enumerate(report.evidence, 1):
        evidence_table.add_row(str(i), e)
    console.print(evidence_table)

    # Timeline
    if report.timeline:
        timeline_table = Table(title="Timeline", show_lines=True)
        timeline_table.add_column("Event", style="green")
        for t in report.timeline:
            timeline_table.add_row(t)
        console.print(timeline_table)

    # Impact
    console.print(Panel(
        f"{report.impact}",
        title="Impact",
        border_style="magenta",
    ))

    # Recommended Action
    console.print(Panel(
        f"[bold green]{report.recommended_action}[/bold green]",
        title="Recommended Action",
        border_style="green",
    ))

    # Confidence
    conf_pct = int(report.confidence * 100)
    bar = "#" * (conf_pct // 5) + "-" * ((100 - conf_pct) // 5)
    console.print(Panel(
        f"[bold]{conf_pct}%[/bold]  [{bar}]",
        title="Confidence",
        border_style="blue",
    ))

    # Chain of Thought
    if report.chain_of_thought:
        console.print()
        console.print("[bold cyan]Agent Chain of Thought:[/bold cyan]")
        for i, thought in enumerate(report.chain_of_thought, 1):
            console.print(f"  {i}. {thought}")

    console.print()


async def run_investigation():
    """Run the full autonomous incident investigation."""
    # -- DETECT --
    alert = create_demo_alert()

    console.print(Panel.fit(
        "[bold white on red] AUTONOMOUS INCIDENT COMMANDER [/bold white on red]",
        border_style="bright_red",
    ))
    console.print()
    console.print(f"[bold yellow]>> ALERT RECEIVED:[/bold yellow] {alert.title}")
    console.print(f"   Service: {alert.service}")
    console.print(f"   Severity: {alert.severity.value}")
    console.print(f"   Description: {alert.description}")
    console.print(f"   Time: {alert.timestamp}")
    console.print()
    console.print("[bold cyan]>> Starting multi-agent investigation...[/bold cyan]")
    console.print("   Dispatching: Logs Agent, Metrics Agent, Deploy Intelligence")
    console.print()

    # -- INVESTIGATE (Commander orchestrates sub-agents) --
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

    # -- REPORT --
    print_rca_report(result.output)

    # Print usage stats
    usage = result.usage()
    console.print(Panel(
        f"Requests: {usage.requests} | "
        f"Input tokens: {usage.input_tokens} | "
        f"Output tokens: {usage.output_tokens}",
        title="LLM Usage",
        border_style="dim",
    ))


def main():
    """Entry point."""
    try:
        asyncio.run(run_investigation())
    except KeyboardInterrupt:
        console.print("\n[yellow]Investigation cancelled.[/yellow]")
    except Exception as e:
        console.print(f"\n[red]Error: {e}[/red]")
        console.print("[dim]Make sure OPENAI_API_KEY is set: set OPENAI_API_KEY=your-key[/dim]")
        raise


if __name__ == "__main__":
    main()

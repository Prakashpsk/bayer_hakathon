# Autonomous Incident Commander
### Bayer AI Hackathon 2026 — Multi-Agent Incident Response System

> **Agentic AI System** that autonomously diagnoses complex cloud system failures
> using **Pydantic AI** with multi-agent reasoning.

---

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run tests (NO API key needed - uses TestModel)
python test_demo.py

# Run live demo (requires OpenAI API key)
set OPENAI_API_KEY=your-key-here
python main.py
```

---

## Architecture

```
ALERT TRIGGER
     │
     ▼
┌─────────────────────────────────┐
│       COMMANDER AGENT           │  ← The Orchestrator
│   (Pydantic AI + Agent Delegation)│
│                                   │
│  Reasoning Loop:                  │
│  DETECT → PLAN → INVESTIGATE     │
│  → DECIDE → ACT → REPORT        │
└──────┬──────────┬──────────┬─────┘
       │          │          │
       ▼          ▼          ▼
┌──────────┐ ┌──────────┐ ┌──────────────┐
│ LOGS     │ │ METRICS  │ │ DEPLOY       │
│ AGENT    │ │ AGENT    │ │ INTELLIGENCE │
│          │ │          │ │              │
│ 3 Tools: │ │ 3 Tools: │ │ 3 Tools:     │
│ •search  │ │ •get     │ │ •get deploys │
│ •traces  │ │ •anomaly │ │ •get diff    │
│ •correlate│ │ •compare │ │ •rollback    │
└──────────┘ └──────────┘ └──────────────┘
       │          │          │
       ▼          ▼          ▼
┌─────────────────────────────────┐
│    MOCK DATA (Artificial Errors) │
│  • Logs: DB timeouts, 500s      │
│  • Metrics: latency 2000ms      │
│  • Deploys: max_conn 100→10     │
└─────────────────────────────────┘
       │
       ▼
   RCA REPORT
```

---

## Project Structure

```
bayer_hakathon/
├── config.py                  # Model config, env loading
├── requirements.txt           # Dependencies
├── main.py                    # Live demo entry point (needs API key)
├── test_demo.py               # 11 tests, NO API key needed
├── models/
│   └── schemas.py             # All Pydantic data models
├── data/
│   ├── mock_logs.py           # Simulated logs with errors
│   ├── mock_metrics.py        # Simulated metrics with anomalies
│   └── mock_deployments.py    # Simulated CI/CD history
└── agents/
    ├── logs_agent.py          # Forensic Expert (3 tools)
    ├── metrics_agent.py       # Telemetry Analyst (3 tools)
    ├── deploy_agent.py        # Deployment Historian (3 tools)
    └── commander_agent.py     # Orchestrator (3 delegation tools)
```

---

## How Pydantic AI is Used

### 1. Agent Definition with Typed Dependencies & Output
```python
from pydantic_ai import Agent, RunContext

logs_agent = Agent(
    deps_type=LogsDeps,              # Typed dependencies
    output_type=LogAnalysisResult,   # Structured Pydantic output
    instructions="You are the LOGS AGENT...",
)
```

### 2. Tool Registration with @agent.tool
```python
@logs_agent.tool
async def tool_search_logs(
    ctx: RunContext[LogsDeps],   # Access deps via ctx.deps
    service: str,
    severity: str,
) -> str:
    """Search logs for a service and severity."""
    results = search_logs(service=service, severity=severity)
    return format_results(results)
```

### 3. Agent Delegation (Multi-Agent Pattern)
```python
@commander_agent.tool
async def investigate_logs(ctx: RunContext[CommanderDeps]) -> str:
    """Commander delegates to Logs Agent."""
    result = await logs_agent.run(
        "Investigate logs...",
        deps=LogsDeps(target_service=ctx.deps.alert_service),
        model=ctx.model,       # Propagate model through chain
        usage=ctx.usage,       # Track token usage across agents
    )
    return format_report(result.output)
```

### 4. Testing with TestModel (No API Key)
```python
from pydantic_ai.models.test import TestModel

result = await commander_agent.run(
    "Investigate incident...",
    deps=deps,
    model=TestModel(),  # No LLM call, generates mock structured output
)
```

---

## Demo Scenario

| Step | Time | Event |
|------|------|-------|
| 1 | 09:45 | Config deployment reduces `max_connections: 100 → 10` |
| 2 | 09:50 | DB connection pool utilization rises to 90% |
| 3 | 10:00 | **ALERT**: Checkout service p99 latency spikes to 2000ms |
| 4 | 10:00 | Commander Agent dispatches 3 specialist agents |
| 5 | — | Logs Agent finds `ConnectionPoolExhausted` stack traces |
| 6 | — | Metrics Agent detects latency, CPU, pool anomalies |
| 7 | — | Deploy Agent finds the config change 15 min prior |
| 8 | — | Commander correlates findings → identifies root cause |
| 9 | — | **RCA Report**: Recommends immediate rollback |

---

## Test Results

```
RESULTS: 11/11 passed, 0 failed

Tests:
 1. Mock Logs - Artificial errors present          ✓
 2. Mock Metrics - Anomalies present               ✓
 3. Mock Deployments - Root cause exists            ✓
 4. Pydantic Models - Alert validation              ✓
 5. Pydantic Models - State transitions             ✓
 6. Pydantic Models - RCA Report                    ✓
 7. Logs Agent - TestModel                          ✓
 8. Metrics Agent - TestModel                       ✓
 9. Deploy Agent - TestModel                        ✓
10. Commander Agent - Full orchestration            ✓
11. End-to-End Pipeline                             ✓
```

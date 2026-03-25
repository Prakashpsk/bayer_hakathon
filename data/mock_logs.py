"""
Mock application logs with ARTIFICIAL ERRORS injected.

Simulates the demo scenario:
  - Checkout service starts throwing DB connection timeout errors
  - Errors begin ~15 minutes after a configuration deployment
  - Stack traces show ConnectionPoolExhausted and TimeoutError
"""
from models.schemas import LogEntry, Severity


def get_mock_logs() -> list[LogEntry]:
    """Return simulated application logs with injected errors."""
    return [
        # ── Normal logs before the incident ─────────────────────────
        LogEntry(
            timestamp="2026-03-25T09:30:00Z",
            service="checkout-service",
            level=Severity.INFO,
            message="Health check passed. All systems nominal.",
        ),
        LogEntry(
            timestamp="2026-03-25T09:35:00Z",
            service="checkout-service",
            level=Severity.INFO,
            message="Processing order #78432. Latency: 180ms.",
        ),
        LogEntry(
            timestamp="2026-03-25T09:40:00Z",
            service="database-primary",
            level=Severity.INFO,
            message="Connection pool stats: active=12, idle=88, max=100.",
        ),

        # ── Configuration deployment happens at 09:45 ──────────────
        LogEntry(
            timestamp="2026-03-25T09:45:00Z",
            service="deploy-pipeline",
            level=Severity.INFO,
            message="Deployment deploy-cfg-2026-0325 completed. Service: database-primary. Config updated.",
        ),
        LogEntry(
            timestamp="2026-03-25T09:46:00Z",
            service="database-primary",
            level=Severity.INFO,
            message="Configuration reloaded. max_connections changed from 100 to 10.",
        ),

        # ── Initial warnings as pool shrinks ────────────────────────
        LogEntry(
            timestamp="2026-03-25T09:50:00Z",
            service="database-primary",
            level=Severity.WARN,
            message="Connection pool utilization high: active=9, idle=1, max=10.",
        ),
        LogEntry(
            timestamp="2026-03-25T09:52:00Z",
            service="checkout-service",
            level=Severity.WARN,
            message="Slow query detected. DB response time: 850ms (threshold: 500ms).",
        ),

        # ══════════════════════════════════════════════════════════════
        # ██  ARTIFICIAL ERRORS BEGIN — Incident starts at 10:00  ██
        # ══════════════════════════════════════════════════════════════

        LogEntry(
            timestamp="2026-03-25T10:00:00Z",
            service="checkout-service",
            level=Severity.ERROR,
            message="Failed to process order #78501. DB connection timeout after 2000ms.",
            stack_trace=(
                "Traceback (most recent call last):\n"
                "  File \"/app/checkout/handler.py\", line 142, in process_order\n"
                "    conn = await db_pool.acquire(timeout=2.0)\n"
                "  File \"/app/lib/db/pool.py\", line 87, in acquire\n"
                "    raise ConnectionPoolExhausted('No connections available in pool')\n"
                "ConnectionPoolExhausted: No connections available in pool (max=10, active=10, waiting=23)"
            ),
            request_id="req-a1b2c3",
        ),
        LogEntry(
            timestamp="2026-03-25T10:00:15Z",
            service="checkout-service",
            level=Severity.ERROR,
            message="HTTP 500 returned to client. Order #78502 failed. Latency: 2001ms.",
            request_id="req-d4e5f6",
        ),
        LogEntry(
            timestamp="2026-03-25T10:00:30Z",
            service="database-primary",
            level=Severity.CRITICAL,
            message="Connection pool EXHAUSTED. All 10 connections in use. 35 requests queued.",
            stack_trace=(
                "CRITICAL: ConnectionPoolExhausted\n"
                "  Pool stats: max=10, active=10, idle=0, waiting=35\n"
                "  Longest wait: 2340ms\n"
                "  Config source: deploy-cfg-2026-0325"
            ),
        ),
        LogEntry(
            timestamp="2026-03-25T10:01:00Z",
            service="checkout-service",
            level=Severity.ERROR,
            message="Cascade failure: 15 orders failed in last 60 seconds. Circuit breaker OPEN.",
            stack_trace=(
                "Traceback (most recent call last):\n"
                "  File \"/app/checkout/handler.py\", line 98, in handle_request\n"
                "    result = await self.process_order(order)\n"
                "  File \"/app/checkout/handler.py\", line 142, in process_order\n"
                "    conn = await db_pool.acquire(timeout=2.0)\n"
                "TimeoutError: Connection acquisition timed out after 2000ms"
            ),
            request_id="req-g7h8i9",
        ),
        LogEntry(
            timestamp="2026-03-25T10:02:00Z",
            service="payment-service",
            level=Severity.ERROR,
            message="Upstream checkout-service returning 500s. Payment processing halted.",
        ),
        LogEntry(
            timestamp="2026-03-25T10:03:00Z",
            service="checkout-service",
            level=Severity.CRITICAL,
            message="Service degraded. p99 latency: 2150ms. Error rate: 73%. Affected users: ~450.",
        ),
        LogEntry(
            timestamp="2026-03-25T10:05:00Z",
            service="api-gateway",
            level=Severity.WARN,
            message="High error rate from checkout-service. Routing 50% traffic to fallback.",
        ),
    ]


def search_logs(service: str | None = None, severity: str | None = None,
                time_start: str | None = None, time_end: str | None = None) -> list[dict]:
    """Search and filter mock logs. Returns dicts for tool consumption."""
    logs = get_mock_logs()
    results = []
    for log in logs:
        if service and service.lower() not in log.service.lower():
            continue
        if severity and log.level.value != severity.upper():
            continue
        if time_start and log.timestamp < time_start:
            continue
        if time_end and log.timestamp > time_end:
            continue
        results.append(log.model_dump())
    return results


def find_stack_traces(service: str | None = None) -> list[dict]:
    """Find all log entries with stack traces."""
    logs = get_mock_logs()
    results = []
    for log in logs:
        if log.stack_trace:
            if service and service.lower() not in log.service.lower():
                continue
            results.append({
                "timestamp": log.timestamp,
                "service": log.service,
                "level": log.level.value,
                "message": log.message,
                "stack_trace": log.stack_trace,
            })
    return results


def get_error_correlations() -> list[dict]:
    """Find error correlations across services."""
    return [
        {
            "pattern": "ConnectionPoolExhausted",
            "services": ["checkout-service", "database-primary"],
            "first_seen": "2026-03-25T10:00:00Z",
            "count": 47,
            "correlation": "DB connection pool exhausted → checkout timeouts → payment failures",
        },
        {
            "pattern": "TimeoutError",
            "services": ["checkout-service"],
            "first_seen": "2026-03-25T10:01:00Z",
            "count": 32,
            "correlation": "Connection acquisition timeout (2000ms) matches p99 latency spike",
        },
        {
            "pattern": "Config change → Pool exhaustion",
            "services": ["database-primary", "deploy-pipeline"],
            "first_seen": "2026-03-25T09:45:00Z",
            "count": 1,
            "correlation": "max_connections reduced 100→10 at 09:45, pool exhausted by 10:00",
        },
    ]

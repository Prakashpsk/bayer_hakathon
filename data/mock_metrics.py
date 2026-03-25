"""
Mock metrics data with ARTIFICIAL ANOMALIES injected.

Simulates the demo scenario:
  - p99 latency spike from 200ms → 2000ms on checkout-service
  - CPU spike on database server
  - DB connection pool hitting 100% capacity
"""
from models.schemas import MetricPoint


def get_mock_metrics() -> list[MetricPoint]:
    """Return simulated time-series metrics with injected anomalies."""
    return [
        # ── Baseline metrics (normal) ───────────────────────────────
        # Checkout service latency — normal
        MetricPoint(timestamp="2026-03-25T09:30:00Z", service="checkout-service",
                    metric_name="p99_latency_ms", value=195.0, unit="ms"),
        MetricPoint(timestamp="2026-03-25T09:35:00Z", service="checkout-service",
                    metric_name="p99_latency_ms", value=201.0, unit="ms"),
        MetricPoint(timestamp="2026-03-25T09:40:00Z", service="checkout-service",
                    metric_name="p99_latency_ms", value=198.0, unit="ms"),
        MetricPoint(timestamp="2026-03-25T09:45:00Z", service="checkout-service",
                    metric_name="p99_latency_ms", value=210.0, unit="ms"),
        MetricPoint(timestamp="2026-03-25T09:50:00Z", service="checkout-service",
                    metric_name="p99_latency_ms", value=450.0, unit="ms"),
        MetricPoint(timestamp="2026-03-25T09:55:00Z", service="checkout-service",
                    metric_name="p99_latency_ms", value=890.0, unit="ms"),

        # ██ ANOMALY: Latency spikes to 2000ms ██
        MetricPoint(timestamp="2026-03-25T10:00:00Z", service="checkout-service",
                    metric_name="p99_latency_ms", value=2001.0, unit="ms"),
        MetricPoint(timestamp="2026-03-25T10:05:00Z", service="checkout-service",
                    metric_name="p99_latency_ms", value=2150.0, unit="ms"),

        # ── Database CPU — normal then spike ────────────────────────
        MetricPoint(timestamp="2026-03-25T09:30:00Z", service="database-primary",
                    metric_name="cpu_percent", value=25.0, unit="%"),
        MetricPoint(timestamp="2026-03-25T09:40:00Z", service="database-primary",
                    metric_name="cpu_percent", value=28.0, unit="%"),
        MetricPoint(timestamp="2026-03-25T09:50:00Z", service="database-primary",
                    metric_name="cpu_percent", value=65.0, unit="%"),
        # ██ ANOMALY: CPU spike ██
        MetricPoint(timestamp="2026-03-25T10:00:00Z", service="database-primary",
                    metric_name="cpu_percent", value=92.0, unit="%"),
        MetricPoint(timestamp="2026-03-25T10:05:00Z", service="database-primary",
                    metric_name="cpu_percent", value=95.0, unit="%"),

        # ── DB Connection Pool Utilization ──────────────────────────
        MetricPoint(timestamp="2026-03-25T09:30:00Z", service="database-primary",
                    metric_name="conn_pool_usage_percent", value=12.0, unit="%"),
        MetricPoint(timestamp="2026-03-25T09:40:00Z", service="database-primary",
                    metric_name="conn_pool_usage_percent", value=15.0, unit="%"),
        MetricPoint(timestamp="2026-03-25T09:46:00Z", service="database-primary",
                    metric_name="conn_pool_usage_percent", value=60.0, unit="%"),
        MetricPoint(timestamp="2026-03-25T09:50:00Z", service="database-primary",
                    metric_name="conn_pool_usage_percent", value=90.0, unit="%"),
        # ██ ANOMALY: Pool at 100% ██
        MetricPoint(timestamp="2026-03-25T10:00:00Z", service="database-primary",
                    metric_name="conn_pool_usage_percent", value=100.0, unit="%"),
        MetricPoint(timestamp="2026-03-25T10:05:00Z", service="database-primary",
                    metric_name="conn_pool_usage_percent", value=100.0, unit="%"),

        # ── Memory usage (database) ─────────────────────────────────
        MetricPoint(timestamp="2026-03-25T09:30:00Z", service="database-primary",
                    metric_name="memory_percent", value=45.0, unit="%"),
        MetricPoint(timestamp="2026-03-25T10:00:00Z", service="database-primary",
                    metric_name="memory_percent", value=78.0, unit="%"),

        # ── Error rate ──────────────────────────────────────────────
        MetricPoint(timestamp="2026-03-25T09:30:00Z", service="checkout-service",
                    metric_name="error_rate_percent", value=0.1, unit="%"),
        MetricPoint(timestamp="2026-03-25T09:50:00Z", service="checkout-service",
                    metric_name="error_rate_percent", value=5.0, unit="%"),
        # ██ ANOMALY: Error rate spike ██
        MetricPoint(timestamp="2026-03-25T10:00:00Z", service="checkout-service",
                    metric_name="error_rate_percent", value=73.0, unit="%"),
        MetricPoint(timestamp="2026-03-25T10:05:00Z", service="checkout-service",
                    metric_name="error_rate_percent", value=71.0, unit="%"),
    ]


def get_metrics_for_service(service: str, metric_name: str | None = None) -> list[dict]:
    """Get metrics filtered by service and optionally metric name."""
    metrics = get_mock_metrics()
    results = []
    for m in metrics:
        if service.lower() not in m.service.lower():
            continue
        if metric_name and metric_name.lower() not in m.metric_name.lower():
            continue
        results.append(m.model_dump())
    return results


def detect_anomalies(service: str | None = None) -> list[dict]:
    """Detect anomalous metric patterns (values exceeding baselines)."""
    baselines = {
        ("checkout-service", "p99_latency_ms"): 300.0,
        ("database-primary", "cpu_percent"): 50.0,
        ("database-primary", "conn_pool_usage_percent"): 70.0,
        ("checkout-service", "error_rate_percent"): 5.0,
        ("database-primary", "memory_percent"): 60.0,
    }

    anomalies = []
    for m in get_mock_metrics():
        if service and service.lower() not in m.service.lower():
            continue
        baseline = baselines.get((m.service, m.metric_name))
        if baseline and m.value > baseline:
            anomalies.append({
                "timestamp": m.timestamp,
                "service": m.service,
                "metric": m.metric_name,
                "value": m.value,
                "baseline": baseline,
                "deviation_percent": round(((m.value - baseline) / baseline) * 100, 1),
                "unit": m.unit,
            })
    return anomalies

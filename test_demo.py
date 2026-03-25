"""
Test file for Autonomous Incident Commander.

Runs ALL tests using Pydantic AI's TestModel - NO API KEY NEEDED.
This demonstrates the complete system working end-to-end.

Usage:
    cd d:\\bayer_agent\\bayer_hakathon
    python test_demo.py

The TestModel returns structured mock responses so we can verify
the agent tools, delegation, and pipeline work correctly.
"""
from __future__ import annotations

import asyncio
import sys
import os
import traceback
import io

# Load .env file
from dotenv import load_dotenv
load_dotenv()

# Fix Windows console encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pydantic_ai import Agent
from pydantic_ai.models.test import TestModel

from models.schemas import (
    Alert, Severity, Finding, LogAnalysisResult,
    MetricsAnalysisResult, DeployAnalysisResult, RCAReport,
    InvestigationState, ReasoningPhase,
)
from data.mock_logs import search_logs, find_stack_traces, get_error_correlations
from data.mock_metrics import get_metrics_for_service, detect_anomalies
from data.mock_deployments import get_recent_deployments, get_deployment_diff, check_rollback_available


# ======================================================================
# Test Utilities
# ======================================================================

passed = 0
failed = 0
total = 0


def test(name: str):
    """Decorator to register and run a test."""
    def decorator(func):
        func._test_name = name
        return func
    return decorator


def assert_true(condition: bool, msg: str = ""):
    if not condition:
        raise AssertionError(f"Assertion failed: {msg}")


def assert_eq(actual, expected, msg: str = ""):
    if actual != expected:
        raise AssertionError(f"Expected {expected!r}, got {actual!r}. {msg}")


def assert_gt(actual, threshold, msg: str = ""):
    if not actual > threshold:
        raise AssertionError(f"Expected {actual} > {threshold}. {msg}")


# ======================================================================
# TEST 1: Mock Data - Artificial Errors
# ======================================================================

@test("Mock Logs — Artificial errors are present")
def test_mock_logs():
    """Verify that the mock logs contain injected errors."""
    # Search for ERROR logs in checkout-service
    error_logs = search_logs(service="checkout-service", severity="ERROR")
    assert_gt(len(error_logs), 0, "Should have ERROR logs for checkout-service")
    print(f"  [OK] Found {len(error_logs)} ERROR logs for checkout-service")

    # Search for CRITICAL logs
    critical_logs = search_logs(severity="CRITICAL")
    assert_gt(len(critical_logs), 0, "Should have CRITICAL logs")
    print(f"  [OK] Found {len(critical_logs)} CRITICAL logs")

    # Check stack traces exist
    traces = find_stack_traces(service="checkout-service")
    assert_gt(len(traces), 0, "Should have stack traces")
    # Verify ConnectionPoolExhausted is in the traces
    trace_text = " ".join([t["stack_trace"] for t in traces])
    assert_true("ConnectionPoolExhausted" in trace_text, "Should contain ConnectionPoolExhausted")
    print(f"  [OK] Found {len(traces)} stack traces with ConnectionPoolExhausted")

    # Check correlations
    correlations = get_error_correlations()
    assert_gt(len(correlations), 0, "Should have error correlations")
    print(f"  [OK] Found {len(correlations)} error correlations")


@test("Mock Metrics - Anomalies are present")
def test_mock_metrics():
    """Verify that the mock metrics contain injected anomalies."""
    # Check checkout-service latency
    latency = get_metrics_for_service("checkout-service", "p99_latency_ms")
    assert_gt(len(latency), 0, "Should have latency metrics")
    max_latency = max(m["value"] for m in latency)
    assert_gt(max_latency, 2000, "Max p99 latency should exceed 2000ms")
    print(f"  [OK] p99 latency spike detected: {max_latency}ms")

    # Check anomaly detection
    anomalies = detect_anomalies(service="checkout-service")
    assert_gt(len(anomalies), 0, "Should detect anomalies for checkout-service")
    print(f"  [OK] Detected {len(anomalies)} anomalies for checkout-service")

    # Check database anomalies
    db_anomalies = detect_anomalies(service="database-primary")
    assert_gt(len(db_anomalies), 0, "Should detect database anomalies")
    print(f"  [OK] Detected {len(db_anomalies)} anomalies for database-primary")

    # Verify connection pool at 100%
    pool_metrics = get_metrics_for_service("database-primary", "conn_pool_usage_percent")
    max_pool = max(m["value"] for m in pool_metrics)
    assert_eq(max_pool, 100.0, "Connection pool should hit 100%")
    print(f"  [OK] Connection pool reached {max_pool}%")


@test("Mock Deployments - Root cause deployment exists")
def test_mock_deployments():
    """Verify that the root cause deployment is in the mock data."""
    deployments = get_recent_deployments()
    assert_gt(len(deployments), 0, "Should have recent deployments")
    print(f"  [OK] Found {len(deployments)} recent deployments")

    # Check the root cause deployment
    diff = get_deployment_diff("deploy-cfg-2026-0325")
    assert_true("error" not in diff, "Root cause deployment should exist")
    assert_true(diff["config_changes"] is not None, "Should have config changes")
    assert_eq(
        diff["config_changes"]["max_connections"]["old"], 100,
        "Old max_connections should be 100"
    )
    assert_eq(
        diff["config_changes"]["max_connections"]["new"], 10,
        "New max_connections should be 10"
    )
    print(f"  [OK] Root cause: max_connections changed {diff['config_changes']['max_connections']['old']} -> {diff['config_changes']['max_connections']['new']}")

    # Check rollback
    rollback = check_rollback_available("deploy-cfg-2026-0325")
    assert_true(rollback["rollback_available"], "Rollback should be available")
    print(f"  [OK] Rollback available: {rollback['rollback_available']}")


# ======================================================================
# TEST 2: Pydantic Models - Validation
# ======================================================================

@test("Pydantic Models - Alert validation")
def test_alert_model():
    """Verify Alert model works correctly."""
    alert = Alert(
        alert_id="TEST-001",
        service="checkout-service",
        title="Test Alert",
        description="Test description",
        severity=Severity.CRITICAL,
        timestamp="2026-03-25T10:00:00Z",
        metric_value=2001.0,
        threshold=500.0,
    )
    assert_eq(alert.severity, Severity.CRITICAL)
    assert_eq(alert.service, "checkout-service")
    print(f"  [OK] Alert model validated: {alert.alert_id}")


@test("Pydantic Models - InvestigationState transitions")
def test_investigation_state():
    """Verify state machine transitions work."""
    state = InvestigationState()
    assert_eq(state.phase, ReasoningPhase.DETECT)
    print(f"  [OK] Initial phase: {state.phase.value}")

    # Walk through all phases
    phases = ["DETECT", "PLAN", "INVESTIGATE", "DECIDE", "ACT", "REPORT"]
    for i, expected in enumerate(phases):
        assert_eq(state.phase.value, expected)
        state.add_thought(f"Completed {expected} phase")
        if i < len(phases) - 1:
            state.advance_phase()

    assert_eq(len(state.chain_of_thought), 6)
    print(f"  [OK] All 6 phases traversed: {' -> '.join(phases)}")
    print(f"  [OK] Chain of thought has {len(state.chain_of_thought)} entries")


@test("Pydantic Models - RCAReport validation")
def test_rca_report_model():
    """Verify RCAReport model works."""
    report = RCAReport(
        title="Test RCA Report",
        incident_summary="Checkout service latency spike",
        root_cause="Configuration change reduced DB connection pool",
        evidence=["p99 latency > 2000ms", "max_connections: 100 -> 10"],
        timeline=["09:45 Config deployed", "10:00 Latency spike"],
        impact="~450 users affected, 73% error rate",
        recommended_action="Rollback deploy-cfg-2026-0325",
        confidence=0.95,
        chain_of_thought=["Detected alert", "Investigated logs"],
    )
    assert_eq(report.confidence, 0.95)
    assert_eq(len(report.evidence), 2)
    assert_eq(len(report.timeline), 2)
    print(f"  [OK] RCA Report validated: {report.title}")
    print(f"  [OK] Confidence: {report.confidence}")


# ======================================================================
# TEST 3: Pydantic AI Agents - Using TestModel (NO API KEY)
# ======================================================================

@test("Logs Agent - Runs with TestModel")
async def test_logs_agent():
    """Test Logs Agent with TestModel (no real LLM call)."""
    from agents.logs_agent import logs_agent, LogsDeps

    # Override model with TestModel
    test_model = TestModel()

    deps = LogsDeps(target_service="checkout-service")
    result = await logs_agent.run(
        "Investigate logs for checkout-service. Find errors and stack traces.",
        deps=deps,
        model=test_model,
    )

    # TestModel auto-generates structured output matching LogAnalysisResult
    assert_true(result.output is not None, "Should have output")
    assert_true(isinstance(result.output, LogAnalysisResult), "Should be LogAnalysisResult")
    print(f"  [OK] Logs Agent returned LogAnalysisResult")
    print(f"  [OK] Summary: {result.output.summary[:80]}...")
    print(f"  [OK] Usage: {result.usage()}")


@test("Metrics Agent - Runs with TestModel")
async def test_metrics_agent():
    """Test Metrics Agent with TestModel (no real LLM call)."""
    from agents.metrics_agent import metrics_agent, MetricsDeps

    test_model = TestModel()

    deps = MetricsDeps(target_service="checkout-service")
    result = await metrics_agent.run(
        "Analyze metrics for checkout-service. Detect anomalies.",
        deps=deps,
        model=test_model,
    )

    assert_true(result.output is not None, "Should have output")
    assert_true(isinstance(result.output, MetricsAnalysisResult), "Should be MetricsAnalysisResult")
    print(f"  [OK] Metrics Agent returned MetricsAnalysisResult")
    print(f"  [OK] Summary: {result.output.summary[:80]}...")
    print(f"  [OK] Usage: {result.usage()}")


@test("Deploy Agent - Runs with TestModel")
async def test_deploy_agent():
    """Test Deploy Intelligence Agent with TestModel (no real LLM call)."""
    from agents.deploy_agent import deploy_agent, DeployDeps

    test_model = TestModel()

    deps = DeployDeps(incident_time="2026-03-25T10:00:00Z")
    result = await deploy_agent.run(
        "Check deployments around the incident. Find suspicious config changes.",
        deps=deps,
        model=test_model,
    )

    assert_true(result.output is not None, "Should have output")
    assert_true(isinstance(result.output, DeployAnalysisResult), "Should be DeployAnalysisResult")
    print(f"  [OK] Deploy Agent returned DeployAnalysisResult")
    print(f"  [OK] Summary: {result.output.summary[:80]}...")
    print(f"  [OK] Usage: {result.usage()}")


@test("Commander Agent - Full orchestration with TestModel")
async def test_commander_agent():
    """Test Commander Agent end-to-end with TestModel (no real LLM call).
    This tests the full multi-agent delegation pipeline."""
    from agents.commander_agent import commander_agent, CommanderDeps

    test_model = TestModel()

    deps = CommanderDeps(
        alert_service="checkout-service",
        alert_description="P99 latency spike to 2000ms, error rate 73%",
        incident_time="2026-03-25T10:00:00Z",
    )

    result = await commander_agent.run(
        (
            "INCIDENT ALERT: Checkout service latency spike to 2000ms. "
            "Error rate 73%. ~450 users affected. "
            "Investigate using all three specialist agents."
        ),
        deps=deps,
        model=test_model,
    )

    assert_true(result.output is not None, "Should have output")
    assert_true(isinstance(result.output, RCAReport), "Should be RCAReport")
    print(f"  [OK] Commander Agent returned RCAReport")
    print(f"  [OK] Title: {result.output.title[:60]}...")
    print(f"  [OK] Root cause: {result.output.root_cause[:60]}...")
    print(f"  [OK] Recommended action: {result.output.recommended_action[:60]}...")
    print(f"  [OK] Confidence: {result.output.confidence}")
    print(f"  [OK] Total usage: {result.usage()}")


# ======================================================================
# TEST 4: End-to-End Pipeline
# ======================================================================

@test("End-to-End - Full incident response pipeline")
async def test_e2e_pipeline():
    """Test the complete pipeline: Alert -> Commander -> Sub-agents -> RCA Report."""
    from agents.commander_agent import commander_agent, CommanderDeps

    test_model = TestModel()

    # Step 1: Create the alert (simulating the demo scenario)
    alert = Alert(
        alert_id="ALERT-2026-0325-001",
        service="checkout-service",
        title="P99 Latency Critical - Checkout Service",
        description=(
            "Checkout Service p99 latency has spiked to 2000ms "
            "(threshold: 500ms). Error rate at 73%."
        ),
        severity=Severity.CRITICAL,
        timestamp="2026-03-25T10:00:00Z",
        metric_value=2001.0,
        threshold=500.0,
    )
    print(f"  [OK] Alert created: {alert.alert_id}")

    # Step 2: Verify mock data has the evidence
    error_logs = search_logs(service="checkout-service", severity="ERROR")
    anomalies = detect_anomalies(service="checkout-service")
    root_deploy = get_deployment_diff("deploy-cfg-2026-0325")
    assert_gt(len(error_logs), 0, "Mock data should have errors")
    assert_gt(len(anomalies), 0, "Mock data should have anomalies")
    assert_true("config_changes" in root_deploy, "Mock data should have root cause deploy")
    print(f"  [OK] Mock data verified: {len(error_logs)} errors, {len(anomalies)} anomalies")

    # Step 3: Run Commander (delegates to sub-agents)
    deps = CommanderDeps(
        alert_service=alert.service,
        alert_description=alert.description,
        incident_time=alert.timestamp,
    )
    result = await commander_agent.run(
        f"Alert: {alert.title}. {alert.description}",
        deps=deps,
        model=test_model,
    )
    print(f"  [OK] Commander completed investigation")
    print(f"  [OK] RCA Report generated: {result.output.title[:50]}...")

    # Step 4: Verify report structure
    report = result.output
    assert_true(len(report.title) > 0, "Report should have title")
    assert_true(len(report.incident_summary) > 0, "Report should have summary")
    assert_true(len(report.root_cause) > 0, "Report should have root cause")
    assert_true(len(report.recommended_action) > 0, "Report should have action")
    assert_true(0 <= report.confidence <= 1, "Confidence should be 0-1")
    print(f"  [OK] Report structure validated")
    print(f"  [OK] Pipeline complete: Alert -> Investigation -> RCA Report")


# ======================================================================
# Test Runner
# ======================================================================

async def run_all_tests():
    """Run all tests and report results."""
    global passed, failed, total

    print("=" * 70)
    print("  AUTONOMOUS INCIDENT COMMANDER - TEST SUITE")
    print("  Using Pydantic AI TestModel (NO API KEY REQUIRED)")
    print("=" * 70)
    print()

    # Collect all test functions
    tests = [
        test_mock_logs,
        test_mock_metrics,
        test_mock_deployments,
        test_alert_model,
        test_investigation_state,
        test_rca_report_model,
        test_logs_agent,
        test_metrics_agent,
        test_deploy_agent,
        test_commander_agent,
        test_e2e_pipeline,
    ]

    for test_func in tests:
        name = getattr(test_func, "_test_name", test_func.__name__)
        total += 1
        print("-" * 60)
        print(f"TEST {total}: {name}")
        print("-" * 60)
        try:
            if asyncio.iscoroutinefunction(test_func):
                await test_func()
            else:
                test_func()
            passed += 1
            print(f"  >>> PASSED\n")
        except Exception as e:
            failed += 1
            print(f"  >>> FAILED: {e}")
            traceback.print_exc()
            print()

    # Summary
    print("=" * 70)
    print(f"  RESULTS: {passed}/{total} passed, {failed} failed")
    print("=" * 70)

    if failed > 0:
        print("\n[WARNING] Some tests failed. Check errors above.")
        sys.exit(1)
    else:
        print("\n>>> All tests passed! The system is working correctly.")
        print("   Run 'python main.py' with OPENAI_API_KEY set for the live demo.")
        sys.exit(0)


if __name__ == "__main__":
    asyncio.run(run_all_tests())

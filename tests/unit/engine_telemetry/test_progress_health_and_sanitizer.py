"""
tests/unit/engine_telemetry/test_progress_health_and_sanitizer.py
===================================================================
Unit tests for ProgressTracker, HealthEvaluator, and TelemetrySanitizer.
"""

import pytest
from akaalEngine.telemetry import (
    UNKNOWN_TOTAL,
    HealthState,
    TelemetryAuthority,
    TelemetrySanitizer,
)


def test_truthful_progress_tracker_unknown_totals():
    """Proves ProgressTracker strictly reports UNKNOWN (None) for remaining, percentage, and ETA when totals are unknown."""
    telemetry = TelemetryAuthority()
    snap1 = telemetry.initialize_migration_progress("mig-unk", rows_total=UNKNOWN_TOTAL)

    assert snap1.rows_total == UNKNOWN_TOTAL
    assert snap1.rows_remaining is None
    assert snap1.percentage is None
    assert snap1.eta_seconds is None

    # Update progress
    snap2 = telemetry.update_progress("mig-unk", add_rows=1000)
    assert snap2.rows_processed == 1000
    assert snap2.rows_remaining is None
    assert snap2.percentage is None
    assert snap2.eta_seconds is None

    # Override with known total
    snap3 = telemetry.update_progress("mig-unk", add_rows=1000, rows_total_override=4000)
    assert snap3.rows_processed == 2000
    assert snap3.rows_total == 4000
    assert snap3.rows_remaining == 2000
    assert snap3.percentage == 50.0
    assert snap3.eta_seconds is not None


def test_health_evaluator_aggregate_states():
    """Proves HealthEvaluator evaluates component health and derives truthful system-wide health snapshots."""
    telemetry = TelemetryAuthority()

    telemetry.update_component_health("connection_pool", HealthState.HEALTHY)
    telemetry.update_component_health("schema_engine", HealthState.HEALTHY)
    snap1 = telemetry.get_health_snapshot()
    assert snap1.overall_state == HealthState.HEALTHY

    telemetry.update_component_health("worker_heartbeat", HealthState.DEGRADED, reason="Heartbeat delayed")
    snap2 = telemetry.get_health_snapshot()
    assert snap2.overall_state == HealthState.DEGRADED

    telemetry.update_component_health("durability_spool", HealthState.UNHEALTHY, reason="Disk quota exhausted")
    snap3 = telemetry.get_health_snapshot()
    assert snap3.overall_state == HealthState.UNHEALTHY


def test_telemetry_sanitizer_redacts_secrets_preserves_position_tokens():
    """Proves TelemetrySanitizer scrubs passwords, bearer tokens, and secrets while preserving fencing and attempt tokens."""
    data = {
        "db_password": "super_secret_pass",
        "auth_header": "Bearer token_abc_123",
        "fencing_token": "fencing-token-valid-123",
        "attempt_token": "attempt-token-valid-456",
        "normal_field": "public_data",
    }

    sanitized = TelemetrySanitizer.sanitize_mapping(data)
    assert sanitized["db_password"] == "[REDACTED]"
    assert sanitized["auth_header"] == "[REDACTED]"
    assert sanitized["fencing_token"] == "fencing-token-valid-123"
    assert sanitized["attempt_token"] == "attempt-token-valid-456"
    assert sanitized["normal_field"] == "public_data"

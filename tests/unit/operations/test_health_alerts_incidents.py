"""
Unit Tests for Health Engine, Alerts, and Incident Lifecycle.
"""

import pytest
from akaal.operations.health.engine import OperationsHealthEngine
from akaal.operations.alerts.engine import AlertEngine
from akaal.operations.incidents.lifecycle import IncidentLifecycleManager, IncidentState


def test_health_engine_weighted_scoring():
    engine = OperationsHealthEngine()
    engine.update_score("Platform1", 50.0)
    engine.update_score("Platform2", 50.0)

    # 50*0.25 + 50*0.25 + 100*0.20 + 100*0.15 + 100*0.15 = 12.5+12.5+20+15+15 = 75.0
    overall = engine.compute_overall_health()
    assert overall == 75.0


def test_alert_engine_deduplication_and_suppression():
    alerts = AlertEngine()
    
    # 1. Raise alert
    a1 = alerts.raise_alert("CPU_High", "CPU > 90%", "HIGH")
    a2 = alerts.raise_alert("CPU_High", "CPU > 90%", "HIGH")
    assert a1.alert_id == a2.alert_id  # Deduplicated

    # 2. Maintenance mode suppression
    alerts.set_maintenance_mode(True)
    a3 = alerts.raise_alert("RAM_High", "RAM > 95%", "CRITICAL")
    assert a3.status == "SUPPRESSED"


def test_incident_lifecycle_state_machine():
    mgr = IncidentLifecycleManager()
    inc = mgr.create_incident("Database Connection Failure", "CRITICAL")
    
    assert inc.state == IncidentState.DETECTED

    # Valid transition sequence
    mgr.transition_incident(inc.incident_id, IncidentState.CLASSIFIED)
    assert inc.state == IncidentState.CLASSIFIED

    # Invalid transition directly to RESOLVED without MITIGATING/VERIFYING
    with pytest.raises(ValueError):
        inc.transition_to(IncidentState.RESOLVED)

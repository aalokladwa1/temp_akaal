"""Tests for Knowledge Base, State Machine, Incident Timeline, and Dashboard Models."""

import pytest
from akaal.reliability.knowledge.knowledge_base import ReliabilityKnowledgeBase
from akaal.reliability.state.machine import ReliabilityStateMachine, ReliabilityState
from akaal.reliability.timeline.incident_timeline import IncidentTimelineEngine
from akaal.reliability.dashboard.reliability_summary import ReliabilitySummary, HealthSnapshot, SLASnapshot


def test_knowledge_base_and_recommendations():
    kb = ReliabilityKnowledgeBase()
    kb.record_incident("inc_001", "database_primary", "TIMEOUT", "CHECKPOINT_RESUME", True, 2.5)
    kb.record_incident("inc_002", "database_primary", "TIMEOUT", "CHECKPOINT_RESUME", True, 1.8)
    kb.record_incident("inc_003", "database_primary", "TIMEOUT", "SERVICE_RESTART", False, 10.0)

    recs = kb.get_recommendations("database_primary", "TIMEOUT")
    assert len(recs) >= 1
    assert recs[0]["strategy"] == "CHECKPOINT_RESUME"
    assert recs[0]["effectiveness_score"] == 100.0


def test_state_machine_transitions():
    sm = ReliabilityStateMachine(ReliabilityState.HEALTHY)
    assert sm.get_current_state() == ReliabilityState.HEALTHY

    # Valid transition: HEALTHY -> DEGRADED
    assert sm.transition_to(ReliabilityState.DEGRADED, "Lag spike") is True
    assert sm.get_current_state() == ReliabilityState.DEGRADED

    # Valid transition: DEGRADED -> RECOVERING
    assert sm.transition_to(ReliabilityState.RECOVERING, "Recovery active") is True
    assert sm.get_current_state() == ReliabilityState.RECOVERING

    # Invalid transition: RECOVERING -> HEALTHY (must go through RECOVERED)
    assert sm.transition_to(ReliabilityState.HEALTHY, "Direct skip") is False
    assert sm.get_current_state() == ReliabilityState.RECOVERING

    # Valid transition: RECOVERING -> RECOVERED
    assert sm.transition_to(ReliabilityState.RECOVERED, "Recovery done") is True
    assert sm.get_current_state() == ReliabilityState.RECOVERED


def test_incident_timeline_engine():
    timeline = IncidentTimelineEngine()
    timeline.record_event("inc_100", "FAILURE_DETECTED", {"component": "auth_service"})
    timeline.record_event("inc_100", "RECOVERY_STARTED", {"strategy": "AUTO_HEAL"})
    timeline.record_event("inc_100", "RECOVERY_COMPLETED", {"status": "SUCCESS"})

    events = timeline.get_timeline("inc_100")
    assert len(events) == 3
    assert events[0].event_type == "FAILURE_DETECTED"
    assert events[2].event_type == "RECOVERY_COMPLETED"


def test_dashboard_models():
    summary = ReliabilitySummary()
    assert summary.health.overall_health_score == 100.0
    assert summary.sla.availability_pct == 99.99
    assert summary.active_profile == "ENTERPRISE"

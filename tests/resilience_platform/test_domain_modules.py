"""Tests: Resilience Platform — All 6 Domain Modules."""

import pytest
import asyncio
from akaal.resilience_eng.domain.chaos_domain import ChaosDomain
from akaal.resilience_eng.domain.experiment_domain import ExperimentDomain
from akaal.resilience_eng.domain.safety_domain import SafetyDomain
from akaal.resilience_eng.domain.learning_domain import LearningDomain
from akaal.resilience_eng.domain.recovery_validation_domain import RecoveryValidationDomain
from akaal.resilience_eng.domain.governance_domain import GovernanceDomain
from akaal.resilience_eng.core.models import ResilienceEngStatus, ResilienceEngOutcome


def run_async(coro):
    return asyncio.run(coro)



class MockContext:
    validation_platform = object()
    self_healing_platform = object()
    replication_platform = object()
    reliability_platform = object()


ctx = MockContext()


class TestChaosDomain:
    def test_capabilities_count(self):
        d = ChaosDomain()
        assert len(d.capabilities) == 10

    def test_execute_domain(self):
        d = ChaosDomain()
        result = run_async(d.execute_domain(ctx))
        assert result.status == ResilienceEngStatus.COMPLETED
        assert result.total_actions == 9
        assert result.failed_actions == 0


class TestExperimentDomain:
    def test_capabilities_count(self):
        d = ExperimentDomain()
        assert len(d.capabilities) == 3

    def test_execute_domain(self):
        d = ExperimentDomain()
        result = run_async(d.execute_domain(ctx))
        assert result.status == ResilienceEngStatus.COMPLETED
        assert result.total_actions == 3


class TestSafetyDomain:
    def test_capabilities_count(self):
        d = SafetyDomain()
        assert len(d.capabilities) == 3

    def test_execute_domain(self):
        d = SafetyDomain()
        result = run_async(d.execute_domain(ctx))
        assert result.status == ResilienceEngStatus.COMPLETED
        assert result.total_actions == 3


class TestLearningDomain:
    def test_capabilities_count(self):
        d = LearningDomain()
        assert len(d.capabilities) == 4

    def test_execute_domain(self):
        d = LearningDomain()
        result = run_async(d.execute_domain(ctx))
        assert result.status == ResilienceEngStatus.COMPLETED
        assert result.total_actions == 4


class TestRecoveryValidationDomain:
    def test_capabilities_count(self):
        d = RecoveryValidationDomain()
        assert len(d.capabilities) == 3

    def test_execute_domain(self):
        d = RecoveryValidationDomain()
        result = run_async(d.execute_domain(ctx))
        assert result.status == ResilienceEngStatus.COMPLETED
        assert result.outcome == ResilienceEngOutcome.CERTIFIED


class TestGovernanceDomain:
    def test_capabilities_count(self):
        d = GovernanceDomain()
        assert len(d.capabilities) == 6

    def test_execute_domain(self):
        d = GovernanceDomain()
        result = run_async(d.execute_domain(ctx))
        assert result.status == ResilienceEngStatus.COMPLETED
        assert result.total_actions == 6
        assert result.confidence_score == 100.0

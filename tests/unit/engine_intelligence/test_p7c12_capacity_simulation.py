"""tests/unit/engine_intelligence/test_p7c12_capacity_simulation.py
=======================================================================
P7C.12 Capacity, Cutover, Scheduling & Scenario Simulation: real deterministic
throughput arithmetic, prediction honesty (ranges not fake guaranteed ETAs), CDC
backlog convergence math, what-if worker-count comparison, and cutover feasibility.
"""

from __future__ import annotations

import sqlite3

import pytest

from akaalEngine.intelligence.api import IntelligenceKernel
from akaalEngine.intelligence.lifecycle.store import IntelligenceArtifactStore
from akaalEngine.intelligence.models.context import IntelligenceContext
from akaalEngine.intelligence.models.errors import IntelligenceValidationError
from akaalEngine.intelligence.models.request import IntelligenceRequest, IntelligenceTask
from akaalEngine.intelligence.producers.capacity_simulation import (
    estimate_bulk_duration_seconds,
    estimate_cdc_catchup_seconds,
    evaluate_scenario,
    make_capacity_simulation_producer,
)


@pytest.fixture
def conn():
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    connection.execute(
        """
        CREATE TABLE intelligence_artifacts (
            artifact_id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, workspace_id TEXT,
            project_id TEXT, subject_type TEXT NOT NULL, subject_id TEXT NOT NULL,
            subject_version TEXT NOT NULL, task TEXT NOT NULL, algorithm_version TEXT NOT NULL,
            policy_version TEXT NOT NULL, canonical_state_fingerprint TEXT NOT NULL,
            fingerprint TEXT NOT NULL, result TEXT NOT NULL, lifecycle_state TEXT NOT NULL,
            created_at TEXT NOT NULL, requested_by TEXT NOT NULL, model_provider TEXT,
            model_id TEXT, model_version TEXT, expires_at TEXT, superseded_by TEXT, updated_at TEXT
        )
        """
    )
    yield connection
    connection.close()


class TestBulkDurationMath:
    def test_doubling_workers_halves_duration(self):
        _, point1, _ = estimate_bulk_duration_seconds(1_000_000_000, 10_000_000, 1)
        _, point2, _ = estimate_bulk_duration_seconds(1_000_000_000, 10_000_000, 2)
        assert point2 == pytest.approx(point1 / 2)

    def test_range_brackets_point_estimate(self):
        low, point, high = estimate_bulk_duration_seconds(1_000_000_000, 10_000_000, 4)
        assert low < point < high

    def test_rejects_zero_workers(self):
        with pytest.raises(Exception):
            estimate_bulk_duration_seconds(1_000_000_000, 10_000_000, 0)


class TestCDCBacklogHonesty:
    def test_hostile_backlog_never_converges_returns_none_not_fake_eta(self):
        """Apply rate <= generation rate: the backlog mathematically never
        shrinks. Must return None, never a fabricated finish time."""
        result = estimate_cdc_catchup_seconds(backlog_bytes=1000, generation_rate_bytes_per_sec=100, apply_rate_bytes_per_sec=100)
        assert result is None

        result2 = estimate_cdc_catchup_seconds(backlog_bytes=1000, generation_rate_bytes_per_sec=150, apply_rate_bytes_per_sec=100)
        assert result2 is None

    def test_convergent_backlog_produces_positive_estimate(self):
        result = estimate_cdc_catchup_seconds(backlog_bytes=1000, generation_rate_bytes_per_sec=50, apply_rate_bytes_per_sec=150)
        assert result is not None
        low, point, high = result
        assert point == pytest.approx(1000 / 100)


class TestScenarioFeasibility:
    def test_feasible_scenario_within_window(self):
        scenario = evaluate_scenario(
            label="test", dataset_size_bytes=1_000_000, worker_throughput_bytes_per_sec=1_000_000,
            worker_count=4, validation_throughput_bytes_per_sec=1_000_000, cutover_window_seconds=100,
        )
        assert scenario.is_feasible is True

    def test_infeasible_scenario_exceeds_window(self):
        scenario = evaluate_scenario(
            label="test", dataset_size_bytes=1_000_000_000_000, worker_throughput_bytes_per_sec=1_000,
            worker_count=1, validation_throughput_bytes_per_sec=1_000, cutover_window_seconds=10,
        )
        assert scenario.is_feasible is False

    def test_never_converging_backlog_is_never_marked_feasible(self):
        """Hostile: an infeasible-by-construction backlog scenario must not be
        marked feasible merely because bulk+validation alone would fit."""
        scenario = evaluate_scenario(
            label="test", dataset_size_bytes=1_000, worker_throughput_bytes_per_sec=1_000_000,
            worker_count=4, validation_throughput_bytes_per_sec=1_000_000, cutover_window_seconds=1_000_000,
            cdc_backlog_bytes=1_000_000, cdc_generation_rate_bytes_per_sec=200, cdc_apply_rate_bytes_per_sec=100,
        )
        assert scenario.cdc_catchup_duration is None
        assert scenario.is_feasible is False
        assert scenario.total_point_seconds is None


class TestProducerEndToEnd:
    def _kernel(self) -> IntelligenceKernel:
        kernel = IntelligenceKernel(store=IntelligenceArtifactStore())
        kernel.register_producer(IntelligenceTask.SIMULATE, make_capacity_simulation_producer(), capability="capacity_scenario")
        return kernel

    def _req(self, **params) -> IntelligenceRequest:
        return IntelligenceRequest(
            task=IntelligenceTask.SIMULATE, tenant_id="tenant-a", subject_type="migration_plan",
            subject_id="plan-1", subject_version="v1", requested_by="user-1", parameters=params,
            capability="capacity_scenario",
        )

    def _ctx(self) -> IntelligenceContext:
        return IntelligenceContext(tenant_id="tenant-a", subject_type="migration_plan", subject_id="plan-1", subject_version="v1")

    def test_missing_required_parameters_raises(self, conn):
        with pytest.raises(IntelligenceValidationError):
            self._kernel().submit_request(self._req(), self._ctx(), conn)

    def test_what_if_worker_count_comparison(self, conn):
        artifact = self._kernel().submit_request(
            self._req(
                dataset_size_bytes=10_000_000_000,
                worker_throughput_bytes_per_sec=10_000_000,
                validation_throughput_bytes_per_sec=20_000_000,
                cutover_window_seconds=2000,
                worker_counts=[4, 8, 16],
            ),
            self._ctx(),
            conn,
        )
        scenarios = artifact.result["data"]["scenarios"]
        assert len(scenarios) == 3
        durations = [s["total_point_seconds"] for s in scenarios]
        # more workers strictly reduces total duration for this fixed dataset
        assert durations[0] > durations[1] > durations[2]
        assert artifact.result["epistemic_type"] == "PREDICTION"

    def test_predictions_carry_explicit_range_never_bare_point(self, conn):
        artifact = self._kernel().submit_request(
            self._req(
                dataset_size_bytes=10_000_000_000,
                worker_throughput_bytes_per_sec=10_000_000,
                validation_throughput_bytes_per_sec=20_000_000,
                cutover_window_seconds=2000,
            ),
            self._ctx(),
            conn,
        )
        predictions = artifact.result["predictions"]
        assert len(predictions) == 1
        assert predictions[0]["low"] < predictions[0]["value"] < predictions[0]["high"]

    def test_never_converging_cdc_backlog_scenario_flagged_not_hidden(self, conn):
        artifact = self._kernel().submit_request(
            self._req(
                dataset_size_bytes=1_000_000,
                worker_throughput_bytes_per_sec=10_000_000,
                validation_throughput_bytes_per_sec=20_000_000,
                cutover_window_seconds=2000,
                cdc_backlog_bytes=1_000_000,
                cdc_generation_rate_bytes_per_sec=500,
                cdc_apply_rate_bytes_per_sec=400,
            ),
            self._ctx(),
            conn,
        )
        scenario = artifact.result["data"]["scenarios"][0]
        assert scenario["backlog_never_converges"] is True
        assert scenario["is_feasible"] is False
        assert "never converges" in artifact.result["summary"]

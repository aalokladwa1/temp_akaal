"""tests/unit/engine_intelligence/test_p7c9_cross_migration_patterns.py
===========================================================================
Cross-migration pattern intelligence: real frequency analysis, epistemic type
is INFERENCE (never FACT), and historical similarity never masquerades as proof.
"""

from __future__ import annotations

import sqlite3

import pytest

from akaalEngine.intelligence.api import IntelligenceKernel
from akaalEngine.intelligence.lifecycle.store import IntelligenceArtifactStore
from akaalEngine.intelligence.models.context import IntelligenceContext
from akaalEngine.intelligence.models.errors import IntelligenceValidationError
from akaalEngine.intelligence.models.request import IntelligenceRequest, IntelligenceTask
from akaalEngine.intelligence.producers.cross_migration_patterns import (
    detect_recurring_finding_patterns,
    make_cross_migration_pattern_producer,
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


class TestPatternDetection:
    def test_recurring_code_across_threshold_detected(self):
        findings = {
            "mig-1": ["RISK:LOSSY_TYPES", "RISK:UNSUPPORTED"],
            "mig-2": ["RISK:LOSSY_TYPES"],
            "mig-3": ["RISK:LOSSY_TYPES"],
            "mig-4": ["RISK:UNSUPPORTED"],
        }
        patterns = detect_recurring_finding_patterns(findings, min_occurrences=3)
        assert len(patterns) == 1
        assert patterns[0]["finding_code"] == "RISK:LOSSY_TYPES"
        assert patterns[0]["occurrence_count"] == 3
        assert patterns[0]["migration_ids"] == ["mig-1", "mig-2", "mig-3"]

    def test_below_threshold_not_reported(self):
        findings = {"mig-1": ["RISK:X"], "mig-2": ["RISK:X"]}
        patterns = detect_recurring_finding_patterns(findings, min_occurrences=3)
        assert patterns == []

    def test_rejects_min_occurrences_below_two(self):
        with pytest.raises(IntelligenceValidationError):
            detect_recurring_finding_patterns({"mig-1": ["X"]}, min_occurrences=1)

    def test_deterministic_ordering(self):
        findings = {f"mig-{i}": ["RISK:B"] for i in range(3)}
        findings.update({f"mig-b{i}": ["RISK:A"] for i in range(5)})
        patterns = detect_recurring_finding_patterns(findings, min_occurrences=3)
        assert patterns[0]["finding_code"] == "RISK:A"  # higher occurrence count first


class TestProducerEndToEnd:
    def _kernel(self) -> IntelligenceKernel:
        kernel = IntelligenceKernel(store=IntelligenceArtifactStore())
        kernel.register_producer(IntelligenceTask.COMPARE, make_cross_migration_pattern_producer(), capability="cross_migration_patterns")
        return kernel

    def test_epistemic_type_is_inference_never_fact(self, conn):
        kernel = self._kernel()
        req = IntelligenceRequest(
            task=IntelligenceTask.COMPARE, tenant_id="tenant-a", subject_type="portfolio",
            subject_id="portfolio-1", subject_version="v1", requested_by="user-1", capability="cross_migration_patterns",
            parameters={"prior_migration_findings": {"mig-1": ["X"], "mig-2": ["X"], "mig-3": ["X"]}},
        )
        ctx = IntelligenceContext(tenant_id="tenant-a", subject_type="portfolio", subject_id="portfolio-1", subject_version="v1")
        artifact = kernel.submit_request(req, ctx, conn)
        assert artifact.result["epistemic_type"] == "INFERENCE"
        assert "not proof" in artifact.result["explanation"]["assumptions"][0]

    def test_missing_parameter_raises(self, conn):
        kernel = self._kernel()
        req = IntelligenceRequest(
            task=IntelligenceTask.COMPARE, tenant_id="tenant-a", subject_type="portfolio",
            subject_id="portfolio-1", subject_version="v1", requested_by="user-1", capability="cross_migration_patterns",
        )
        ctx = IntelligenceContext(tenant_id="tenant-a", subject_type="portfolio", subject_id="portfolio-1", subject_version="v1")
        with pytest.raises(IntelligenceValidationError):
            kernel.submit_request(req, ctx, conn)

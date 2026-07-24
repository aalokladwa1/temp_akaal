"""Tests for Infrastructure Services (Merkle, Evidence, Replay, Explainability, Observability)."""

import pytest
from akaal.validation.services.merkle import MerkleService
from akaal.validation.services.evidence import EvidenceService
from akaal.validation.services.replay import ReplayService
from akaal.validation.services.explainability import ExplainabilityService
from akaal.validation.services.observability import ObservabilityService
from akaal.validation.core.models import ValidationResult, ValidationStatus, ValidationIssue, SeverityLevel


def test_merkle_service():
    service = MerkleService()
    root1, hash1 = service.build_tree(["a", "b", "c"])
    root2, hash2 = service.build_tree(["a", "b", "c"])
    root3, hash3 = service.build_tree(["a", "b", "d"])

    assert hash1 == hash2
    assert hash1 != hash3

    is_same, diffs = service.compare_trees(root1, root2)
    assert is_same is True

    is_same, diffs = service.compare_trees(root1, root3)
    assert is_same is False
    assert len(diffs) > 0


def test_evidence_service():
    service = EvidenceService()
    res = ValidationResult(
        domain_name="D1",
        capabilities_tested=["Cap 1"],
        status=ValidationStatus.PASSED,
        passed_count=10,
    )
    package = service.generate_evidence_package(session_id="s123", results=[res])
    assert package is not None
    assert package.signature is not None
    json_out = service.export_evidence_json(package)
    assert "package_id" in json_out


def test_replay_service():
    service = ReplayService()
    chk_id = service.save_checkpoint("s1", "step1", {"key": "val"})
    chk = service.load_checkpoint(chk_id)
    assert chk is not None
    assert chk["payload"]["key"] == "val"
    replayed = service.replay_session("s1")
    assert len(replayed) == 1


def test_explainability_service():
    service = ExplainabilityService()
    issue = ValidationIssue(
        issue_id="i1",
        capability_id="Cap 1",
        severity=SeverityLevel.ERROR,
        table_name="users",
        column_name="email",
        row_identifier=42,
        message="NOT NULL constraint failed",
    )
    ctx = service.analyze_issue(issue)
    assert ctx is not None
    assert ctx.root_cause_category == "NULL_CONSTRAINT_VIOLATION"
    assert "UPDATE users SET email" in ctx.repair_command_recommendation


def test_observability_service():
    service = ObservabilityService()
    service.record_rows(100)
    service.record_latency("D1", 12.5)
    snap = service.get_telemetry_snapshot()
    assert snap["total_rows_validated"] == 100
    assert snap["domain_latencies_ms"]["D1"] == 12.5

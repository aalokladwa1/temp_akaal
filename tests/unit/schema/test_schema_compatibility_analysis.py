"""
Unit tests for Feature 3 — Schema Compatibility Analysis.
"""

import pytest

from akaal.schema.compatibility.analyzer import CompatibilityAnalyzer
from akaal.schema.compatibility.comparator import SchemaComparator
from akaal.schema.compatibility.risk import RiskClassifier
from akaal.schema.domain.enums import RiskLevel
from akaal.schema.domain.identifiers import SnapshotID, VersionID
from akaal.schema.versioning.snapshot import SchemaSnapshot


def test_schema_comparator_added_removed_modified():
    src = SchemaSnapshot(
        snapshot_id=SnapshotID.generate(),
        version_id=VersionID.generate(),
        tables={"t_old": {}, "t_keep": {"columns": [{"name": "c1", "type": "INT"}]}},
    )
    tgt = SchemaSnapshot(
        snapshot_id=SnapshotID.generate(),
        version_id=VersionID.generate(),
        tables={"t_new": {}, "t_keep": {"columns": [{"name": "c1", "type": "BIGINT"}]}},
    )

    comp = SchemaComparator()
    diff = comp.compare(src, tgt)

    assert len(diff.added_objects) == 1
    assert diff.added_objects[0]["name"] == "t_new"
    assert len(diff.removed_objects) == 1
    assert diff.removed_objects[0]["name"] == "t_old"
    assert len(diff.modified_objects) == 1
    assert diff.modified_objects[0]["name"] == "t_keep"


def test_risk_classifier_breaking_change_detection():
    src = SchemaSnapshot(
        snapshot_id=SnapshotID.generate(),
        version_id=VersionID.generate(),
        tables={"t1": {}},
    )
    tgt = SchemaSnapshot(
        snapshot_id=SnapshotID.generate(),
        version_id=VersionID.generate(),
        tables={},
    )

    analyzer = CompatibilityAnalyzer()
    report = analyzer.analyze(src, tgt)

    assert report.risk_level in (RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.CRITICAL)
    assert report.compatibility_score < 100.0
    assert len(report.breaking_changes) == 1
    assert len(report.advisories) > 0

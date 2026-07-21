"""
Unit tests for Feature 1 — Metadata Version Control & Version Graph DAG.
"""

import pytest

from akaal.schema.domain.errors import MetadataError
from akaal.schema.domain.identifiers import SnapshotID, VersionID
from akaal.schema.versioning.graph import VersionDAG, VersionNode
from akaal.schema.versioning.manager import MetadataVersionManager
from akaal.schema.versioning.merge import VersionMergeEngine
from akaal.schema.versioning.repository import VersionRepository
from akaal.schema.versioning.snapshot import SchemaSnapshot


def test_schema_snapshot_checksum_and_integrity():
    snap = SchemaSnapshot(
        snapshot_id=SnapshotID.generate(),
        version_id=VersionID.generate(),
        tables={"users": {"columns": [{"name": "id", "type": "INT"}]}},
    )
    assert snap.verify_integrity() is True

    # Tamper test
    snap.tables["users"]["columns"].append({"name": "email", "type": "VARCHAR"})
    assert snap.verify_integrity() is False


def test_schema_snapshot_compression():
    snap = SchemaSnapshot(
        snapshot_id=SnapshotID.generate(),
        version_id=VersionID.generate(),
        tables={"orders": {"columns": [{"name": "id", "type": "BIGINT"}]}},
    )
    compressed = snap.compress()
    assert isinstance(compressed, bytes)

    decompressed = SchemaSnapshot.decompress(compressed)
    assert str(decompressed.snapshot_id) == str(snap.snapshot_id)
    assert decompressed.tables == snap.tables


def test_version_dag_and_lca():
    dag = VersionDAG()
    v1 = VersionID.generate()
    v2 = VersionID.generate()
    v3 = VersionID.generate()

    dag.add_version(VersionNode(version_id=v1, timestamp=1.0))
    dag.add_version(VersionNode(version_id=v2, parent_ids=[v1], timestamp=2.0))
    dag.add_version(VersionNode(version_id=v3, parent_ids=[v1], timestamp=3.0))

    lca = dag.find_lca(v2, v3)
    assert lca == v1


def test_version_merge_engine_success_and_conflict():
    dag = VersionDAG()
    v_base = VersionID.generate()
    v_a = VersionID.generate()
    v_b = VersionID.generate()

    snap_base = SchemaSnapshot(snapshot_id=SnapshotID.generate(), version_id=v_base, tables={"users": {"col": "int"}})
    snap_a = SchemaSnapshot(snapshot_id=SnapshotID.generate(), version_id=v_a, tables={"users": {"col": "varchar"}, "orders": {"col": "int"}})
    snap_b = SchemaSnapshot(snapshot_id=SnapshotID.generate(), version_id=v_b, tables={"users": {"col": "bigint"}})

    merger = VersionMergeEngine(dag)
    res = merger.merge(snap_a, snap_b, base_snapshot=snap_base)
    assert res.is_success is False
    assert len(res.conflicts) == 1
    assert res.conflicts[0].object_name == "users"


def test_metadata_version_manager_workflow():
    vm = MetadataVersionManager()
    snap1 = vm.create_snapshot(tables={"t1": {"col": "int"}}, author="alice")
    snap2 = vm.create_snapshot(tables={"t1": {"col": "int"}, "t2": {"col": "text"}}, parent_version_ids=[snap1.version_id], author="bob")

    diff = vm.diff_versions(snap1.version_id, snap2.version_id)
    assert "t2" in diff.added_tables
    assert len(diff.removed_tables) == 0

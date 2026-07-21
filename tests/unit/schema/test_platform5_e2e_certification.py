"""
AKAAL Platform 5 — Final End-to-End Enterprise Certification Test Suite

Certifies all 8 features of Platform 5 — Live Schema Evolution working together via SchemaEvolutionPlatformV5 facade.
"""

import pytest

from akaal.schema.domain.changes import AddColumn, AddTable, DDLStatement
from akaal.schema.domain.enums import TransactionState
from akaal.schema.domain.identifiers import SchemaIdentifier
from akaal.schema.facade.platform5 import SchemaEvolutionPlatformV5


class CertificationMockDB:
    def __init__(self) -> None:
        self.executed_statements = []

    def execute_statement(self, sql: str) -> None:
        self.executed_statements.append(sql)


def test_platform5_e2e_certification_workflow():
    platform = SchemaEvolutionPlatformV5()
    db = CertificationMockDB()

    # 1. Metadata Refresh & Snapshot creation
    snap1 = platform.refresh_metadata(source="cert_test")
    assert snap1 is not None

    # 2. Add sample table to create Version 2
    tbl = SchemaIdentifier("public", "audit_log")
    ch_add_table = AddTable(tbl, columns=[{"name": "id", "type": "INT"}, {"name": "message", "type": "TEXT"}])

    tx = platform.execute_evolution([ch_add_table], db_context=db)
    assert tx.state == TransactionState.COMMITTED
    assert len(db.executed_statements) == 1

    # 3. Create second snapshot
    snap2 = platform.version_manager.create_snapshot(
        tables={"audit_log": {"columns": [{"name": "id", "type": "INT"}, {"name": "message", "type": "TEXT"}]}},
        parent_version_ids=[snap1.version_id],
    )

    # 4. Compare schemas and analyze compatibility
    diff = platform.compare_schemas(snap1.version_id, snap2.version_id)
    assert any(obj["name"] == "audit_log" for obj in diff.added_objects)

    report = platform.analyze_compatibility(snap1.version_id, snap2.version_id)
    assert report.compatibility_score == 100.0

    # 5. Evaluate Type Evolution (INT -> BIGINT)
    type_plan = platform.evaluate_type_evolution(tbl, "id", "INT", "BIGINT")
    assert type_plan.safety.value == "SAFE_WIDENING"

    # 6. Propagate DDL with Retry
    stmt = DDLStatement(sql="ALTER TABLE audit_log ADD COLUMN created_at TIMESTAMP;", target_object="audit_log")
    prop_res = platform.propagate_ddl([stmt], db_context=db)
    assert prop_res is True

    # 7. Evolve Constraints
    ch_add_col = AddColumn(tbl, column_name="status", data_type="VARCHAR(20)")
    const_res = platform.evolve_constraints([ch_add_col], db_context=db)
    assert len(const_res) == 1

    # 8. Replay Journal
    replay_rep = platform.replay_journal(db_context=db)
    assert replay_rep is not None

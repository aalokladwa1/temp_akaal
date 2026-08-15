"""
AKAAL P3.2.1 — Hostile CDC Capture Miners & Reconstruction Engine Acceptance Suite
====================================================================================
Adversarial test suite verifying transaction reconstruction safety, hard queue memory limits,
cross-run identity isolation, position advancement safety, and prerequisite failure injection.
"""

import unittest
from typing import Dict, Any

from akaal.cdc.sources.postgres import PostgresWALMiner
from akaal.cdc.sources.mysql import MySQLBinlogMiner
from akaal.cdc.sources.oracle import OracleRedoMiner
from akaal.cdc.sources.sqlserver import MSSQLCDCMiner
from akaal.cdc.sources.mongodb import MongoDBOplogMiner
from akaal.cdc.sources.reconstruction import TransactionReconstructor
from akaal.cdc.sources.coordinator import CDCCaptureCoordinator

from akaal.cdc.domain.positions import PostgresLSNPosition
from akaal.cdc.domain.events import CDCEventIdentity, CDCOperationType, CDCTransactionBoundary
from akaal.cdc.domain.errors import CDCExecutionError, CDCFailureType
from akaal.gateway.engine_gateway import EngineGateway


class TestP321CDCCaptureHostileAudit(unittest.TestCase):
    """Hostile Acceptance Suite for P3.2 Capture Miners & Flow Control (15 Adversarial Attacks)."""

    def setUp(self):
        self.ident_a = CDCEventIdentity("mig-A", "job-A", "run-A", "sess-A")
        self.ident_b = CDCEventIdentity("mig-A", "job-A", "run-B", "sess-A")  # Different run!
        self.gateway = EngineGateway()

    # -------------------------------------------------------------------------
    # 1. TRANSACTION RECONSTRUCTION ATTACKS
    # -------------------------------------------------------------------------
    def test_attack_01_rolled_back_transaction_never_emitted(self):
        """ATTACK: Uncommitted / aborted transactions must NEVER be emitted in committed_transactions."""
        reconstructor = TransactionReconstructor(self.ident_a)
        pos = PostgresLSNPosition("0/1000000")

        # Begin & insert
        reconstructor.process_native_record("tx-abort-99", "POSTGRESQL", "db", "sch", "tbl", CDCOperationType.INSERT, pos, CDCTransactionBoundary.BEGIN)
        reconstructor.process_native_record("tx-abort-99", "POSTGRESQL", "db", "sch", "tbl", CDCOperationType.INSERT, pos, CDCTransactionBoundary.EVENT, after_image={"x": 1})
        # Abort
        reconstructor.process_native_record("tx-abort-99", "POSTGRESQL", "db", "sch", "tbl", CDCOperationType.INSERT, pos, CDCTransactionBoundary.ABORT)

        committed = reconstructor.pop_committed_transactions()
        self.assertEqual(len(committed), 0)

    def test_attack_02_interleaved_transactions_never_mix(self):
        """ATTACK: Interleaved events from tx-1 and tx-2 must remain strictly segregated."""
        reconstructor = TransactionReconstructor(self.ident_a)
        pos = PostgresLSNPosition("0/1000000")

        reconstructor.process_native_record("tx-1", "POSTGRESQL", "db", "sch", "tbl", CDCOperationType.INSERT, pos, CDCTransactionBoundary.EVENT, after_image={"id": 1})
        reconstructor.process_native_record("tx-2", "POSTGRESQL", "db", "sch", "tbl", CDCOperationType.INSERT, pos, CDCTransactionBoundary.EVENT, after_image={"id": 2})

        # Commit tx-1 only
        tx1 = reconstructor.process_native_record("tx-1", "POSTGRESQL", "db", "sch", "tbl", CDCOperationType.INSERT, pos, CDCTransactionBoundary.COMMIT, after_image={"id": 1})
        self.assertIsNotNone(tx1)
        self.assertEqual(tx1.tx_id, "tx-1")
        self.assertEqual(len(tx1.events), 2)

        # tx-2 remains uncommitted in active transactions
        self.assertIn("tx-2", reconstructor.active_transactions)

    def test_attack_03_cross_run_identity_contamination_rejected(self):
        """ATTACK: Processing an event with run-B identity inside a run-A reconstructor must raise CDCExecutionError."""
        reconstructor = TransactionReconstructor(self.ident_a)
        pos = PostgresLSNPosition("0/1000000")

        with self.assertRaises(CDCExecutionError) as ctx:
            reconstructor.process_native_record(
                tx_id="tx-cross-1",
                source_engine="POSTGRESQL",
                source_database="db",
                source_schema="sch",
                source_table="tbl",
                operation=CDCOperationType.INSERT,
                position=pos,
                boundary=CDCTransactionBoundary.EVENT,
                record_identity=self.ident_b,  # Run-B!
            )
        self.assertEqual(ctx.exception.failure.failure_type, CDCFailureType.TRANSACTION_CORRUPTION)

    def test_attack_04_hard_memory_limit_exceeded(self):
        """ATTACK: Buffer accumulation exceeding hard_event_limit must raise CDCExecutionError (DURABLE_BUFFER_FAILURE)."""
        reconstructor = TransactionReconstructor(self.ident_a, max_buffered_events=10)
        pos = PostgresLSNPosition("0/1000000")

        # Max is 10, hard limit is 20
        for i in range(20):
            reconstructor.process_native_record(
                tx_id=f"tx-overflow-{i}",
                source_engine="POSTGRESQL",
                source_database="db",
                source_schema="sch",
                source_table="tbl",
                operation=CDCOperationType.INSERT,
                position=pos,
                boundary=CDCTransactionBoundary.EVENT,
                after_image={"val": i},
            )

        # 21st record must hit hard limit exception
        with self.assertRaises(CDCExecutionError) as ctx:
            reconstructor.process_native_record(
                tx_id="tx-overflow-21",
                source_engine="POSTGRESQL",
                source_database="db",
                source_schema="sch",
                source_table="tbl",
                operation=CDCOperationType.INSERT,
                position=pos,
                boundary=CDCTransactionBoundary.EVENT,
                after_image={"val": 999},
            )
        self.assertEqual(ctx.exception.failure.failure_type, CDCFailureType.DURABLE_BUFFER_FAILURE)

    # -------------------------------------------------------------------------
    # 2. POSITION ADVANCEMENT & RESUME SAFETY
    # -------------------------------------------------------------------------
    def test_attack_05_capture_miner_cannot_advance_applied_position(self):
        """ATTACK: Verify that miners only update captured position on boundary, not applied or acknowledged."""
        coord = CDCCaptureCoordinator()
        init_res = coord.initialize_cdc_capture("POSTGRESQL", "mig-A", "job-A", "run-A", "sess-pos-test", {"engine": "POSTGRESQL", "lsn": "0/1000000"})
        coord.start_cdc_capture("sess-pos-test")
        coord.poll_cdc_transactions("sess-pos-test")

        boundary = coord.consistency_boundaries["sess-pos-test"]
        self.assertIsNotNone(boundary.last_durably_captured_position)
        # Applied & Acknowledged positions must remain None until apply stage (P3.3+)
        self.assertIsNone(boundary.last_durably_applied_position)
        self.assertIsNone(boundary.last_acknowledged_position)

    # -------------------------------------------------------------------------
    # 3. PREREQUISITE FAILURE INJECTION ATTACKS
    # -------------------------------------------------------------------------
    def test_attack_06_postgres_wal_level_replica_fails_closed(self):
        miner = PostgresWALMiner()
        with self.assertRaises(CDCExecutionError) as ctx:
            miner.validate_prerequisites({"wal_level": "replica"})
        self.assertEqual(ctx.exception.failure.failure_type, CDCFailureType.CDC_PREREQUISITE_MISSING)

    def test_attack_07_mysql_binlog_off_fails_closed(self):
        miner = MySQLBinlogMiner()
        with self.assertRaises(CDCExecutionError) as ctx:
            miner.validate_prerequisites({"log_bin": "OFF", "binlog_format": "ROW"})
        self.assertEqual(ctx.exception.failure.failure_type, CDCFailureType.CDC_PREREQUISITE_MISSING)

    def test_attack_08_oracle_no_archivelog_fails_closed(self):
        miner = OracleRedoMiner()
        with self.assertRaises(CDCExecutionError) as ctx:
            miner.validate_prerequisites({"archivelog_mode": False})
        self.assertEqual(ctx.exception.failure.failure_type, CDCFailureType.CDC_PREREQUISITE_MISSING)

    def test_attack_09_mssql_cdc_disabled_fails_closed(self):
        miner = MSSQLCDCMiner()
        with self.assertRaises(CDCExecutionError) as ctx:
            miner.validate_prerequisites({"is_cdc_enabled": False})
        self.assertEqual(ctx.exception.failure.failure_type, CDCFailureType.CDC_PREREQUISITE_MISSING)

    def test_attack_10_mongodb_standalone_fails_closed(self):
        miner = MongoDBOplogMiner()
        with self.assertRaises(CDCExecutionError) as ctx:
            miner.validate_prerequisites({"is_replica_set": False})
        self.assertEqual(ctx.exception.failure.failure_type, CDCFailureType.CDC_PREREQUISITE_MISSING)

    # -------------------------------------------------------------------------
    # 4. GATEWAY & TELEMETRY INTEGRITY ATTACKS
    # -------------------------------------------------------------------------
    def test_attack_11_uninitialized_session_poll_fails(self):
        """ATTACK: Polling an uninitialized cdc_session_id must raise ValueError."""
        with self.assertRaises(ValueError):
            self.gateway.invoke("poll_cdc_transactions", {"cdc_session_id": "nonexistent-sess"})

    def test_attack_12_unsupported_engine_prerequisite_validation_fails(self):
        """ATTACK: Requesting prerequisites for an unsupported engine raises ValueError."""
        with self.assertRaises(ValueError):
            self.gateway.invoke("validate_cdc_prerequisites", {"engine": "SUPER_DB_9000"})


if __name__ == "__main__":
    unittest.main()

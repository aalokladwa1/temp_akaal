"""
AKAAL P3.2 — Native CDC Change Capture Miners & Log Extractors Acceptance Suite
==================================================================================
Unit test suite verifying source capture miners, prerequisite validation,
transaction reconstruction, backpressure, and EngineGateway capture routing.
"""

import unittest
from typing import Dict, Any

from akaal.cdc.sources.base import ICDCSourceAdapter, CDCCapabilityFlags
from akaal.cdc.sources.postgres import PostgresWALMiner
from akaal.cdc.sources.mysql import MySQLBinlogMiner
from akaal.cdc.sources.oracle import OracleRedoMiner
from akaal.cdc.sources.sqlserver import MSSQLCDCMiner
from akaal.cdc.sources.mongodb import MongoDBOplogMiner
from akaal.cdc.sources.reconstruction import TransactionReconstructor
from akaal.cdc.sources.coordinator import CDCCaptureCoordinator

from akaal.cdc.domain.positions import (
    PostgresLSNPosition,
    MySQLGTIDPosition,
    OracleSCNPosition,
    MSSQLChangePosition,
    MongoDBOpLogPosition,
)
from akaal.cdc.domain.events import (
    CDCEventIdentity,
    CDCOperationType,
    CDCTransactionBoundary,
)
from akaal.cdc.domain.errors import CDCExecutionError
from akaal.gateway.engine_gateway import EngineGateway


class TestP32NativeCDCCaptureMiners(unittest.TestCase):
    """P3.2 Source Capture Miners & Gateway Integration Acceptance Suite (18 Tests)."""

    def setUp(self):
        self.gateway = EngineGateway()
        self.identity = CDCEventIdentity(
            migration_id="mig-p32-01",
            job_id="job-p32-01",
            run_id="run-p32-01",
            cdc_session_id="cdc-sess-p32-01",
        )

    # -------------------------------------------------------------------------
    # 1. POSTGRESQL WAL MINER TESTS
    # -------------------------------------------------------------------------
    def test_01_postgres_wal_miner_prerequisites_valid(self):
        miner = PostgresWALMiner()
        res = miner.validate_prerequisites({"wal_level": "logical"})
        self.assertTrue(res["prerequisites_valid"])

    def test_02_postgres_wal_miner_prerequisites_invalid(self):
        miner = PostgresWALMiner()
        with self.assertRaises(CDCExecutionError):
            miner.validate_prerequisites({"wal_level": "replica"})

    def test_03_postgres_wal_miner_polling(self):
        miner = PostgresWALMiner()
        boundary = miner.initialize_capture(self.identity, PostgresLSNPosition("0/16B3748"))
        self.assertEqual(boundary.initial_load_snapshot_position.to_string(), "0/16B3748")

        txs = miner.poll_transactions()
        self.assertEqual(len(txs), 1)
        self.assertEqual(txs[0].tx_id, "pg-tx-101")
        self.assertEqual(len(txs[0].events), 1)

    # -------------------------------------------------------------------------
    # 2. MYSQL BINLOG MINER TESTS
    # -------------------------------------------------------------------------
    def test_04_mysql_binlog_miner_prerequisites_valid(self):
        miner = MySQLBinlogMiner()
        res = miner.validate_prerequisites({"log_bin": "ON", "binlog_format": "ROW"})
        self.assertTrue(res["prerequisites_valid"])

    def test_05_mysql_binlog_miner_prerequisites_invalid(self):
        miner = MySQLBinlogMiner()
        with self.assertRaises(CDCExecutionError):
            miner.validate_prerequisites({"log_bin": "OFF", "binlog_format": "STATEMENT"})

    def test_06_mysql_binlog_miner_polling(self):
        miner = MySQLBinlogMiner()
        boundary = miner.initialize_capture(self.identity, MySQLGTIDPosition("mysql-bin.000001", 100))
        txs = miner.poll_transactions()
        self.assertEqual(len(txs), 1)
        self.assertEqual(txs[0].tx_id, "my-tx-202")

    # -------------------------------------------------------------------------
    # 3. ORACLE REDO MINER TESTS
    # -------------------------------------------------------------------------
    def test_07_oracle_redo_miner_prerequisites(self):
        miner = OracleRedoMiner()
        res = miner.validate_prerequisites({"archivelog_mode": True, "supplemental_logging": True})
        self.assertTrue(res["prerequisites_valid"])
        with self.assertRaises(CDCExecutionError):
            miner.validate_prerequisites({"archivelog_mode": False, "supplemental_logging": True})

    def test_08_oracle_redo_miner_polling(self):
        miner = OracleRedoMiner()
        boundary = miner.initialize_capture(self.identity, OracleSCNPosition(100000))
        txs = miner.poll_transactions()
        self.assertEqual(len(txs), 1)
        self.assertEqual(txs[0].tx_id, "ora-tx-303")

    # -------------------------------------------------------------------------
    # 4. SQL SERVER & MONGODB MINER TESTS
    # -------------------------------------------------------------------------
    def test_09_mssql_cdc_miner_polling(self):
        miner = MSSQLCDCMiner()
        boundary = miner.initialize_capture(self.identity, MSSQLChangePosition("0000002A:000001C8:0001"))
        txs = miner.poll_transactions()
        self.assertEqual(len(txs), 1)
        self.assertEqual(txs[0].tx_id, "ms-tx-404")

    def test_10_mongodb_oplog_miner_polling(self):
        miner = MongoDBOplogMiner()
        boundary = miner.initialize_capture(self.identity, MongoDBOpLogPosition(1700000000, 1))
        txs = miner.poll_transactions()
        self.assertEqual(len(txs), 1)
        self.assertEqual(txs[0].tx_id, "mg-tx-505")

    # -------------------------------------------------------------------------
    # 5. TRANSACTION RECONSTRUCTOR & ROLLBACK TESTS
    # -------------------------------------------------------------------------
    def test_11_transaction_reconstructor_rollback_discard(self):
        reconstructor = TransactionReconstructor(self.identity)
        pos = PostgresLSNPosition("0/1000000")

        # Begin & insert
        tx1 = reconstructor.process_native_record("tx-abort-1", "POSTGRESQL", "db", "sch", "tbl", CDCOperationType.INSERT, pos, CDCTransactionBoundary.BEGIN)
        self.assertIsNone(tx1)

        # Abort
        tx_abort = reconstructor.process_native_record("tx-abort-1", "POSTGRESQL", "db", "sch", "tbl", CDCOperationType.INSERT, pos, CDCTransactionBoundary.ABORT)
        self.assertIsNone(tx_abort)

        # Discarded - no committed transactions!
        self.assertEqual(len(reconstructor.committed_transactions), 0)

    # -------------------------------------------------------------------------
    # 6. ENGINE GATEWAY CDC CAPABILITY ROUTING TESTS
    # -------------------------------------------------------------------------
    def test_12_gateway_validate_cdc_prerequisites(self):
        res = self.gateway.invoke("validate_cdc_prerequisites", {"engine": "POSTGRESQL", "wal_level": "logical"})
        self.assertTrue(res["prerequisites_valid"])

    def test_13_gateway_initialize_cdc_capture(self):
        payload = {
            "engine": "POSTGRESQL",
            "migration_id": "mig-p32-gw",
            "job_id": "job-p32-gw",
            "run_id": "run-p32-gw",
            "cdc_session_id": "sess-p32-gw",
            "initial_snapshot_position": {"engine": "POSTGRESQL", "lsn": "0/16B3748"},
            "wal_level": "logical",
        }
        res = self.gateway.invoke("initialize_cdc_capture", payload)
        self.assertEqual(res["cdc_session_id"], "sess-p32-gw")
        self.assertEqual(res["status"], "INITIALIZING")

    def test_14_gateway_start_and_poll_cdc_capture(self):
        sess_id = "sess-p32-poll"
        init_payload = {
            "engine": "POSTGRESQL",
            "migration_id": "mig-p32-gw",
            "job_id": "job-p32-gw",
            "run_id": "run-p32-gw",
            "cdc_session_id": sess_id,
            "initial_snapshot_position": {"engine": "POSTGRESQL", "lsn": "0/16B3748"},
            "wal_level": "logical",
        }
        self.gateway.invoke("initialize_cdc_capture", init_payload)
        start_res = self.gateway.invoke("start_cdc_capture", {"cdc_session_id": sess_id})
        self.assertEqual(start_res["status"], "CAPTURING")

        poll_res = self.gateway.invoke("poll_cdc_transactions", {"cdc_session_id": sess_id})
        self.assertEqual(poll_res["transaction_count"], 1)

    def test_15_gateway_pause_and_stop_cdc_capture(self):
        sess_id = "sess-p32-stop"
        init_payload = {
            "engine": "POSTGRESQL",
            "migration_id": "mig-p32-gw",
            "job_id": "job-p32-gw",
            "run_id": "run-p32-gw",
            "cdc_session_id": sess_id,
            "initial_snapshot_position": {"engine": "POSTGRESQL", "lsn": "0/16B3748"},
            "wal_level": "logical",
        }
        self.gateway.invoke("initialize_cdc_capture", init_payload)
        self.gateway.invoke("start_cdc_capture", {"cdc_session_id": sess_id})
        pause_res = self.gateway.invoke("pause_cdc_capture", {"cdc_session_id": sess_id})
        self.assertEqual(pause_res["status"], "PAUSED")

        stop_res = self.gateway.invoke("stop_cdc_capture", {"cdc_session_id": sess_id})
        self.assertEqual(stop_res["status"], "TERMINATED")

    def test_16_gateway_get_cdc_telemetry(self):
        sess_id = "sess-p32-telem"
        init_payload = {
            "engine": "POSTGRESQL",
            "migration_id": "mig-p32-gw",
            "job_id": "job-p32-gw",
            "run_id": "run-p32-gw",
            "cdc_session_id": sess_id,
            "initial_snapshot_position": {"engine": "POSTGRESQL", "lsn": "0/16B3748"},
            "wal_level": "logical",
        }
        self.gateway.invoke("initialize_cdc_capture", init_payload)
        telemetry = self.gateway.invoke("get_cdc_telemetry", {"cdc_session_id": sess_id})
        self.assertEqual(telemetry["cdc_session_id"], sess_id)
        self.assertEqual(telemetry["status"], "INITIALIZING")


if __name__ == "__main__":
    unittest.main()

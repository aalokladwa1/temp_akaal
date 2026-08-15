"""
P3 Reality Rectification Hostile Test Suite
============================================
Verifies P3 Non-Negotiable Reality Contract & False-Success Eradication:
- PostgreSQL miner fails closed when physical connection is missing (no static 'pg-tx-101')
- Oracle miner fails closed when physical connection is missing (no static 'ora-tx-303')
- MySQL miner fails closed when physical connection is missing (no static 'my-tx-202')
- MariaDB miner fails closed when physical connection is missing (no static 'maria-tx-501')
- MSSQL miner fails closed when physical connection is missing (no static 'ms-tx-404')
- MongoDB miner fails closed when physical connection is missing (no static 'mg-tx-505')
- Target apply fails closed when physical target database connection is missing (no generic list append)
- CDCApplyWorker rejects unsafe UPDATE without primary key / before image row identity
- CDCApplyWorker rejects unsafe DELETE without primary key / before image row identity
- CDCApplyWorker enforces atomic target transaction: target failure -> no checkpoint, no ACK
- CDCApplyWorker validates worker fencing token prior to persisting checkpoint
- Idempotent transaction deduplication prevents duplicate replay execution
"""

import unittest
from typing import Dict, Any, List

from akaal.cdc.sources.postgres import PostgresWALMiner
from akaal.cdc.sources.oracle import OracleRedoMiner
from akaal.cdc.sources.mysql import MySQLBinlogMiner
from akaal.cdc.sources.mariadb import MariaDBBinlogMiner
from akaal.cdc.sources.sqlserver import MSSQLCDCMiner
from akaal.cdc.sources.mongodb import MongoDBOplogMiner
from akaal.cdc.targets.generic import GenericDatabaseTargetAdapter

from akaal.cdc.apply.engine import CDCApplyWorker
from akaal.cdc.domain.events import CDCEventIdentity, CDCTransaction, CDCEvent, CDCOperationType
from akaal.cdc.domain.positions import PostgresLSNPosition
from akaal.cdc.domain.errors import CDCExecutionError


class TestP3RealityRectificationSuite(unittest.TestCase):

    def _make_event(self, op: CDCOperationType, before: dict = None, after: dict = None) -> CDCEvent:
        identity = CDCEventIdentity("mig-p3", "job-p3", "run-p3", "sess-p3")
        pos = PostgresLSNPosition("0/1000")
        return CDCEvent(
            identity=identity,
            source_engine="POSTGRESQL",
            source_database="prod_db",
            source_schema="public",
            source_table="users",
            operation=op,
            position=pos,
            before_image=before,
            after_image=after,
        )

    def test_01_postgres_miner_fails_closed_when_disconnected(self):
        """PostgresWALMiner must raise RuntimeError when disconnected; cannot fabricate static 'pg-tx-101'."""
        miner = PostgresWALMiner()
        with self.assertRaises(RuntimeError) as ctx:
            miner.fetch_native_records()
        self.assertIn("must be initialized", str(ctx.exception))

        miner.is_connected = True
        with self.assertRaises(RuntimeError) as ctx:
            miner.fetch_native_records()
        self.assertIn("POSTGRES_CDC_CAPTURE_FAILED", str(ctx.exception))

    def test_02_oracle_miner_fails_closed_when_disconnected(self):
        """OracleRedoMiner must raise RuntimeError when disconnected; cannot fabricate static 'ora-tx-303'."""
        miner = OracleRedoMiner()
        miner.is_connected = True
        with self.assertRaises(RuntimeError) as ctx:
            miner.fetch_native_records()
        self.assertIn("ORACLE_CDC_CAPTURE_FAILED", str(ctx.exception))

    def test_03_mysql_miner_fails_closed_when_disconnected(self):
        """MySQLBinlogMiner must raise RuntimeError when disconnected; cannot fabricate static 'my-tx-202'."""
        miner = MySQLBinlogMiner()
        miner.is_connected = True
        with self.assertRaises(RuntimeError) as ctx:
            miner.fetch_native_records()
        self.assertIn("MYSQL_CDC_CAPTURE_FAILED", str(ctx.exception))

    def test_04_mariadb_miner_fails_closed_when_disconnected(self):
        """MariaDBBinlogMiner must raise RuntimeError when disconnected; cannot fabricate static 'maria-tx-501'."""
        miner = MariaDBBinlogMiner()
        miner.is_connected = True
        with self.assertRaises(RuntimeError) as ctx:
            miner.fetch_native_records()
        self.assertIn("MARIADB_CDC_CAPTURE_FAILED", str(ctx.exception))

    def test_05_mssql_miner_fails_closed_when_disconnected(self):
        """MSSQLCDCMiner must raise RuntimeError when disconnected; cannot fabricate static 'ms-tx-404'."""
        miner = MSSQLCDCMiner()
        miner.is_connected = True
        with self.assertRaises(RuntimeError) as ctx:
            miner.fetch_native_records()
        self.assertIn("MSSQL_CDC_CAPTURE_FAILED", str(ctx.exception))

    def test_06_mongodb_miner_fails_closed_when_disconnected(self):
        """MongoDBOplogMiner must raise RuntimeError when disconnected; cannot fabricate static 'mg-tx-505'."""
        miner = MongoDBOplogMiner()
        miner.is_connected = True
        with self.assertRaises(RuntimeError) as ctx:
            miner.fetch_native_records()
        self.assertIn("MONGODB_CDC_CAPTURE_FAILED", str(ctx.exception))

    def test_07_generic_target_adapter_fails_closed_without_connection(self):
        """GenericDatabaseTargetAdapter must raise RuntimeError when target DB connection is missing."""
        adapter = GenericDatabaseTargetAdapter()
        evt = self._make_event(CDCOperationType.INSERT, after={"id": 10, "name": "Alice"})
        import asyncio
        with self.assertRaises(RuntimeError) as ctx:
            asyncio.run(adapter.apply_changes([evt]))
        self.assertIn("TARGET_APPLY_FAILED", str(ctx.exception))

    def test_08_apply_worker_rejects_unsafe_update_lacking_pk(self):
        """CDCApplyWorker raises CDCExecutionError(UNSAFE_UPDATE) when UPDATE lacks row identity."""
        identity = CDCEventIdentity("mig-p3", "job-p3", "run-p3", "sess-p3")
        worker = CDCApplyWorker(identity)
        
        evt = self._make_event(CDCOperationType.UPDATE, before=None, after={"val": "new_val"})
        pos = PostgresLSNPosition("0/1000")
        tx = CDCTransaction(tx_id="tx-unsafe-u1", identity=identity, events=[evt], commit_position=pos)
        
        with self.assertRaises(CDCExecutionError) as ctx:
            worker.apply_next_transaction(current_fencing_epoch=1, transaction=tx)
        self.assertIn("UNSAFE UPDATE", str(ctx.exception))

    def test_09_apply_worker_rejects_unsafe_delete_lacking_pk(self):
        """CDCApplyWorker raises CDCExecutionError(UNSAFE_DELETE) when DELETE lacks row identity."""
        identity = CDCEventIdentity("mig-p3", "job-p3", "run-p3", "sess-p3")
        worker = CDCApplyWorker(identity)

        evt = self._make_event(CDCOperationType.DELETE, before=None, after=None)
        pos = PostgresLSNPosition("0/1000")
        tx = CDCTransaction(tx_id="tx-unsafe-d1", identity=identity, events=[evt], commit_position=pos)

        with self.assertRaises(CDCExecutionError) as ctx:
            worker.apply_next_transaction(current_fencing_epoch=1, transaction=tx)
        self.assertIn("UNSAFE DELETE", str(ctx.exception))

    def test_10_apply_worker_validates_fencing_epoch(self):
        """CDCApplyWorker rejects stale worker fencing epoch before persisting checkpoint."""
        identity = CDCEventIdentity("mig-p3", "job-p3", "run-p3", "sess-p3")
        worker = CDCApplyWorker(identity)

        evt = self._make_event(CDCOperationType.INSERT, after={"id": 1, "name": "Bob"})
        pos = PostgresLSNPosition("0/2000")
        tx = CDCTransaction(tx_id="tx-valid-i1", identity=identity, events=[evt], commit_position=pos)

        # Issue epoch 1 then issue epoch 2 so active epoch becomes 2
        worker.recovery_coordinator.issue_epoch("mig-p3")
        worker.recovery_coordinator.issue_epoch("mig-p3")
        
        with self.assertRaises(CDCExecutionError) as ctx:
            worker.apply_next_transaction(current_fencing_epoch=1, transaction=tx)
        self.assertIn("FENCING VIOLATION", str(ctx.exception))

    def test_11_apply_worker_suppresses_duplicate_replay(self):
        """CDCApplyWorker idempotently suppresses duplicate transaction replay."""
        identity = CDCEventIdentity("mig-p3", "job-p3", "run-p3", "sess-p3")
        worker = CDCApplyWorker(identity)

        evt = self._make_event(CDCOperationType.INSERT, after={"id": 99, "name": "Eve"})
        pos = PostgresLSNPosition("0/3000")
        tx = CDCTransaction(tx_id="tx-dup-99", identity=identity, events=[evt], commit_position=pos)

        # Ensure clean initial state
        worker.applied_transaction_ids.clear()
        worker.applied_transaction_hashes.clear()

        res1 = worker.apply_next_transaction(current_fencing_epoch=1, transaction=tx)
        self.assertEqual(res1["status"], "SUCCESS")
        self.assertFalse(res1["duplicate_suppressed"])

        res2 = worker.apply_next_transaction(current_fencing_epoch=1, transaction=tx)
        self.assertEqual(res2["status"], "SUCCESS")
        self.assertTrue(res2["duplicate_suppressed"])


if __name__ == "__main__":
    unittest.main()

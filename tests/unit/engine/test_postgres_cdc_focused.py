"""
Focused Unit Tests for PostgreSQL CDC Source Adapter (R1 - R7 Regression Lock)
"""

import os
import unittest
from unittest.mock import MagicMock, patch

from akaalEngine.cdc.capture.postgres import PostgreSQLCDCSourceAdapter
from akaalEngine.cdc.models.event import ChangeOperation


class TestPostgresCDCFocused(unittest.TestCase):

    def setUp(self):
        self.params = {
            "dbname": "test_db",
            "migration_id": "mig_test_001",
            "host": "localhost",
            "port": 5432,
            "user": "postgres",
            "password": "pwd",
        }
        self.adapter = PostgreSQLCDCSourceAdapter(self.params)

    def tearDown(self):
        # Clean up any created snapshot files
        snap_path = self.adapter._get_snapshot_path()
        if os.path.exists(snap_path):
            try:
                os.remove(snap_path)
            except Exception:
                pass

    def test_r1_pk_discovery_idempotence(self):
        """R1: PK discovery idempotence - self.pk_map should not duplicate column names on repeated calls."""
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cur
        
        # Primary key query returns (table_name, column_name)
        mock_cur.fetchall.return_value = [
            ("DEPARTMENTS", "DEPT_ID"),
            ("EMPLOYEES", "EMP_ID"),
        ]

        # First discovery
        with patch.object(self.adapter, '_load_snapshot', return_value=False), \
             patch.object(self.adapter, '_save_snapshot'):
            self.adapter._discover_pks_and_snapshot(mock_conn)
        
        self.assertEqual(self.adapter.pk_map.get("DEPARTMENTS"), ["DEPT_ID"])
        self.assertEqual(self.adapter.pk_map.get("EMPLOYEES"), ["EMP_ID"])

        # Second discovery (e.g. restart / re-discovery)
        with patch.object(self.adapter, '_load_snapshot', return_value=False), \
             patch.object(self.adapter, '_save_snapshot'):
            self.adapter._discover_pks_and_snapshot(mock_conn)

        # Ensure no duplication like ['DEPT_ID', 'DEPT_ID']
        self.assertEqual(self.adapter.pk_map.get("DEPARTMENTS"), ["DEPT_ID"])
        self.assertEqual(self.adapter.pk_map.get("EMPLOYEES"), ["EMP_ID"])

    def test_r2_canonical_pk_identity_stability(self):
        """R2: Single PK returns scalar string, composite PK returns tuple."""
        row_single = {"DEPT_ID": 1, "NAME": "Engineering"}
        pk_key_single = self.adapter._make_pk_key(row_single, ["DEPT_ID"])
        self.assertEqual(pk_key_single, "1")
        self.assertIsInstance(pk_key_single, str)

        row_composite = {"DEPT_ID": 1, "LOC_ID": 10, "NAME": "HQ"}
        pk_key_composite = self.adapter._make_pk_key(row_composite, ["DEPT_ID", "LOC_ID"])
        self.assertEqual(pk_key_composite, ("1", "10"))
        self.assertIsInstance(pk_key_composite, tuple)

    def test_r3_snapshot_migration_isolation(self):
        """R3: Snapshot path includes migration_id/stream_id for isolation."""
        path1 = self.adapter._get_snapshot_path()
        self.assertIn("mig_test_001", path1)

        adapter2 = PostgreSQLCDCSourceAdapter({"dbname": "test_db", "migration_id": "mig_test_002"})
        path2 = adapter2._get_snapshot_path()
        self.assertIn("mig_test_002", path2)
        self.assertNotEqual(path1, path2)

    def test_r4_snapshot_persistence_roundtrip(self):
        """R4: Snapshot saving and loading restores state accurately."""
        self.adapter.pk_map = {"DEPARTMENTS": ["DEPT_ID"]}
        self.adapter.table_state = {
            "DEPARTMENTS": {
                "1": {"DEPT_ID": 1, "NAME": "Engineering"}
            }
        }
        self.adapter._save_snapshot()

        # Create new adapter and load snapshot
        new_adapter = PostgreSQLCDCSourceAdapter(self.params)
        new_adapter.pk_map = {"DEPARTMENTS": ["DEPT_ID"]}
        loaded = new_adapter._load_snapshot()
        
        self.assertTrue(loaded)
        self.assertIn("DEPARTMENTS", new_adapter.table_state)
        self.assertIn("1", new_adapter.table_state["DEPARTMENTS"])
        self.assertEqual(new_adapter.table_state["DEPARTMENTS"]["1"]["NAME"], "Engineering")

    def test_r5_no_false_delete_events_on_unchanged_source(self):
        """R5: No false DELETE events generated when table data matches snapshot state."""
        self.adapter.is_active = True
        self.adapter.pk_map = {"DEPARTMENTS": ["DEPT_ID"]}
        self.adapter.table_state = {
            "DEPARTMENTS": {
                "1": {"DEPT_ID": 1, "NAME": "Engineering"}
            }
        }

        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cur
        
        # Simulate current query returning the exact same row
        mock_cur.fetchall.return_value = [
            {"DEPT_ID": 1, "NAME": "Engineering"}
        ]

        with patch.object(self.adapter, '_get_connection', return_value=mock_conn):
            events = self.adapter.fetch_events()

        # No false DELETE or false INSERT events should be emitted
        self.assertEqual(len(events), 0)

    def test_r6_real_delete_events_operate_correctly(self):
        """R6: Genuine row deletion emits DELETE ChangeEvent."""
        self.adapter.is_active = True
        self.adapter.pk_map = {"DEPARTMENTS": ["DEPT_ID"]}
        self.adapter.table_state = {
            "DEPARTMENTS": {
                "1": {"DEPT_ID": 1, "NAME": "Engineering"},
                "2": {"DEPT_ID": 2, "NAME": "Marketing"}
            }
        }

        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cur
        
        # Row 2 was deleted from DB (only Row 1 remains)
        mock_cur.fetchall.return_value = [
            {"DEPT_ID": 1, "NAME": "Engineering"}
        ]

        with patch.object(self.adapter, '_get_connection', return_value=mock_conn):
            events = self.adapter.fetch_events()

        # 1 DELETE event for Row 2
        delete_events = [e for e in events if e.operation == ChangeOperation.DELETE]
        self.assertEqual(len(delete_events), 1)
        self.assertEqual(delete_events[0].logical_object, "DEPARTMENTS")
        self.assertEqual(delete_events[0].before_image.get("DEPT_ID"), 2)

    def test_r7_new_m3_execution_vs_recovery_boundary(self):
        """R7: Fresh adapter with different migration_id maintains clean boundary."""
        adapter_fresh = PostgreSQLCDCSourceAdapter({"dbname": "test_db", "migration_id": "mig_fresh_099"})
        self.assertFalse(os.path.exists(adapter_fresh._get_snapshot_path()))
        self.assertFalse(adapter_fresh._load_snapshot())


if __name__ == "__main__":
    unittest.main()

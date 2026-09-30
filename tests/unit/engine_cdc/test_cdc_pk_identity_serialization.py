"""
tests/unit/engine_cdc/test_cdc_pk_identity_serialization.py
==============================================================
Focused regression tests for CDC Primary Key identity serialization,
round-tripping, and prevention of false CDC delta events.
"""

import json
import os
import tempfile
import unittest
from typing import Any, Dict

from akaalEngine.cdc.capture.identity import (
    decode_pk_key,
    decode_pk_val,
    encode_pk_key,
    encode_pk_val,
    make_pk_key,
)
from akaalEngine.cdc.capture.mysql import MySQLCDCSourceAdapter
from akaalEngine.cdc.models.event import ChangeOperation


class TestCDCPKIdentitySerialization(unittest.TestCase):
    """Test suite proving type-safe PK identity serialization and false-delete prevention."""

    def test_1_integer_pk_round_trip(self):
        """1. Integer PK round-trip: 10 -> persist -> load -> 10 (int, NOT str '10')."""
        key_in = 10
        encoded = encode_pk_key(key_in)
        decoded = decode_pk_key(encoded)
        self.assertEqual(decoded, 10)
        self.assertIsInstance(decoded, int)
        self.assertNotEqual(decoded, "10")
        self.assertNotIsInstance(decoded, str)

    def test_2_string_pk_round_trip(self):
        """2. String PK round-trip: '10' -> persist -> load -> '10' (str, distinct from int 10)."""
        key_in = "10"
        encoded = encode_pk_key(key_in)
        decoded = decode_pk_key(encoded)
        self.assertEqual(decoded, "10")
        self.assertIsInstance(decoded, str)
        self.assertNotEqual(decoded, 10)
        self.assertNotIsInstance(decoded, int)

    def test_3_composite_pk_round_trip(self):
        """3. Composite PK round-trip: (4502, 2) preserves values, types, and ordering."""
        key_in = (4502, 2)
        encoded = encode_pk_key(key_in)
        decoded = decode_pk_key(encoded)
        self.assertEqual(decoded, (4502, 2))
        self.assertIsInstance(decoded, tuple)
        self.assertIsInstance(decoded[0], int)
        self.assertIsInstance(decoded[1], int)

        # Composite with mixed types
        key_mixed = ("ORDER_A", 100, 3.14)
        encoded_mixed = encode_pk_key(key_mixed)
        decoded_mixed = decode_pk_key(encoded_mixed)
        self.assertEqual(decoded_mixed, ("ORDER_A", 100, 3.14))
        self.assertIsInstance(decoded_mixed[0], str)
        self.assertIsInstance(decoded_mixed[1], int)
        self.assertIsInstance(decoded_mixed[2], float)

    def test_4_make_pk_key_types(self):
        """make_pk_key extracts native Python types without coercing to str."""
        row_int = {"DEPARTMENT_ID": 10, "NAME": "Admin"}
        self.assertEqual(make_pk_key(row_int, ["DEPARTMENT_ID"]), 10)

        row_str = {"DEPARTMENT_ID": "10", "NAME": "Admin"}
        self.assertEqual(make_pk_key(row_str, ["DEPARTMENT_ID"]), "10")

        row_comp = {"ORDER_ID": 4502, "LINE_NO": 2}
        self.assertEqual(make_pk_key(row_comp, ["ORDER_ID", "LINE_NO"]), (4502, 2))

    def test_5_adapter_snapshot_save_load_round_trip(self):
        """Adapter save/load round-trip preserves table state PK identity."""
        with tempfile.TemporaryDirectory() as tmpdir:
            snap_path = os.path.join(tmpdir, "test_cdc_snap.json")
            adapter = MySQLCDCSourceAdapter({"database": "test_db"})

            # Inject in-memory state with integer PKs, string PKs, and composite PKs
            adapter.table_state = {
                "DEPARTMENTS": {10: {"DEPARTMENT_ID": 10, "DEPARTMENT_NAME": "Admin"}},
                "CUSTOMERS": {"1001": {"CUSTOMER_ID": "1001", "NAME": "Acme"}},
                "ORDER_ITEMS": {(4502, 2): {"ORDER_ID": 4502, "LINE_NO": 2, "PRICE": 19.99}},
            }

            # Monkey-patch _get_snapshot_path
            adapter._get_snapshot_path = lambda: snap_path

            # Save snapshot
            adapter._save_snapshot()
            self.assertTrue(os.path.exists(snap_path))

            # Reset in-memory state and reload snapshot
            adapter.table_state = {}
            loaded = adapter._load_snapshot()
            self.assertTrue(loaded)

            # Verify identities and types in table_state
            self.assertIn(10, adapter.table_state["DEPARTMENTS"])
            self.assertIsInstance(list(adapter.table_state["DEPARTMENTS"].keys())[0], int)

            self.assertIn("1001", adapter.table_state["CUSTOMERS"])
            self.assertIsInstance(list(adapter.table_state["CUSTOMERS"].keys())[0], str)

            self.assertIn((4502, 2), adapter.table_state["ORDER_ITEMS"])
            self.assertIsInstance(list(adapter.table_state["ORDER_ITEMS"].keys())[0], tuple)

    def test_6_unchanged_source_rows_produce_zero_cdc_events(self):
        """4. Unchanged source rows across save/load produce ZERO INSERT/UPDATE/DELETE events."""
        with tempfile.TemporaryDirectory() as tmpdir:
            snap_path = os.path.join(tmpdir, "test_cdc_snap.json")
            adapter = MySQLCDCSourceAdapter({"database": "test_db"})
            adapter.pk_map = {"DEPARTMENTS": ["DEPARTMENT_ID"]}

            # Mock live connection cursor returning unchanged baseline row
            class MockCursor:
                def __enter__(self):
                    return self
                def __exit__(self, *args):
                    pass
                def execute(self, query):
                    pass
                def fetchone(self):
                    return {"File": "binlog.000102", "Position": 4297079}
                def fetchall(self):
                    return [{"DEPARTMENT_ID": 10, "DEPARTMENT_NAME": "Administration"}]

            class MockConn:
                open = True
                def cursor(self):
                    return MockCursor()

            adapter.stream_handle = MockConn()

            # Set up persisted snapshot
            adapter.table_state = {
                "DEPARTMENTS": {10: {"DEPARTMENT_ID": 10, "DEPARTMENT_NAME": "Administration"}}
            }
            adapter._get_snapshot_path = lambda: snap_path
            adapter._save_snapshot()

            # Clear state, start capture, and fetch events
            adapter.table_state = {}
            adapter._load_snapshot()
            adapter.is_active = True

            events = adapter.fetch_events(max_events=100)
            self.assertEqual(len(events), 0, "Unchanged baseline row produced unexpected CDC events!")

    def test_7_real_insert_update_delete_capture(self):
        """5, 6, 7. Real INSERT, UPDATE, DELETE produce expected change events."""
        with tempfile.TemporaryDirectory() as tmpdir:
            snap_path = os.path.join(tmpdir, "test_cdc_snap.json")
            adapter = MySQLCDCSourceAdapter({"database": "test_db"})
            adapter.pk_map = {"DEPARTMENTS": ["DEPARTMENT_ID"]}
            adapter._get_snapshot_path = lambda: snap_path

            # Initial baseline state: DEPARTMENTS has row 10 (Admin) and row 20 (IT)
            adapter.table_state = {
                "DEPARTMENTS": {
                    10: {"DEPARTMENT_ID": 10, "DEPARTMENT_NAME": "Admin"},
                    20: {"DEPARTMENT_ID": 20, "DEPARTMENT_NAME": "IT"},
                }
            }
            adapter._save_snapshot()

            # Live query returns:
            # - Row 10: UPDATE (name changed to 'Administration')
            # - Row 20: DELETED (missing from live results)
            # - Row 30: INSERTED (new department)
            class MockCursor:
                def __enter__(self):
                    return self
                def __exit__(self, *args):
                    pass
                def execute(self, query):
                    pass
                def fetchone(self):
                    return {"File": "binlog.000102", "Position": 4297080}
                def fetchall(self):
                    return [
                        {"DEPARTMENT_ID": 10, "DEPARTMENT_NAME": "Administration"}, # UPDATE
                        {"DEPARTMENT_ID": 30, "DEPARTMENT_NAME": "Finance"},        # INSERT
                    ]

            class MockConn:
                open = True
                def cursor(self):
                    return MockCursor()

            adapter.stream_handle = MockConn()
            adapter._load_snapshot()
            adapter.is_active = True

            events = adapter.fetch_events(max_events=100)

            ops = [e.operation for e in events]
            self.assertIn(ChangeOperation.INSERT, ops)
            self.assertIn(ChangeOperation.UPDATE, ops)
            self.assertIn(ChangeOperation.DELETE, ops)

            # Check INSERT event details
            insert_evt = [e for e in events if e.operation == ChangeOperation.INSERT][0]
            self.assertEqual(insert_evt.logical_object, "DEPARTMENTS")
            self.assertEqual(insert_evt.key_values["DEPARTMENT_ID"], 30)

            # Check UPDATE event details
            update_evt = [e for e in events if e.operation == ChangeOperation.UPDATE][0]
            self.assertEqual(update_evt.logical_object, "DEPARTMENTS")
            self.assertEqual(update_evt.key_values["DEPARTMENT_ID"], 10)

            # Check DELETE event details
            delete_evt = [e for e in events if e.operation == ChangeOperation.DELETE][0]
            self.assertEqual(delete_evt.logical_object, "DEPARTMENTS")
            self.assertEqual(delete_evt.key_values["DEPARTMENT_ID"], 20)

    def test_8_false_delete_regression(self):
        """8, 9. Baseline shape (DEPARTMENTS PK=10 integer + reload + unchanged live integer PK) produces ZERO DELETE events."""
        with tempfile.TemporaryDirectory() as tmpdir:
            snap_path = os.path.join(tmpdir, "test_cdc_snap.json")
            adapter = MySQLCDCSourceAdapter({"database": "devkros_p8_m2"})
            adapter.pk_map = {"DEPARTMENTS": ["DEPARTMENT_ID"]}
            adapter._get_snapshot_path = lambda: snap_path

            # Baseline 25 department rows (all integer IDs)
            dept_rows = {i: {"DEPARTMENT_ID": i, "DEPARTMENT_NAME": f"Dept_{i}"} for i in range(1, 26)}
            adapter.table_state = {"DEPARTMENTS": dict(dept_rows)}
            adapter._save_snapshot()

            # Mock PyMySQL DictCursor live query returning exact same 25 rows with native integer IDs
            class MockCursor:
                def __enter__(self):
                    return self
                def __exit__(self, *args):
                    pass
                def execute(self, query):
                    pass
                def fetchone(self):
                    return {"File": "binlog.000102", "Position": 4297079}
                def fetchall(self):
                    return [{"DEPARTMENT_ID": i, "DEPARTMENT_NAME": f"Dept_{i}"} for i in range(1, 26)]

            class MockConn:
                open = True
                def cursor(self):
                    return MockCursor()

            adapter.stream_handle = MockConn()

            # Reload snapshot across restart and fetch events
            adapter.table_state = {}
            adapter._load_snapshot()
            adapter.is_active = True

            events = adapter.fetch_events(max_events=1000)

            delete_events = [e for e in events if e.operation == ChangeOperation.DELETE]
            self.assertEqual(len(delete_events), 0, f"Fabricated {len(delete_events)} false DELETE events for DEPARTMENTS!")

    def test_9_legacy_untagged_snapshot_safety(self):
        """Backward/Stale safety: Legacy untagged snapshot is rejected (returns False) to prevent false CDC deletes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            snap_path = os.path.join(tmpdir, "legacy_snap.json")
            adapter = MySQLCDCSourceAdapter({"database": "test_db"})
            adapter._get_snapshot_path = lambda: snap_path

            # Write legacy un-tagged JSON format (keys are un-tagged strings "10")
            legacy_data = {
                "DEPARTMENTS": {
                    "10": {"DEPARTMENT_ID": "10", "DEPARTMENT_NAME": "Admin"}
                }
            }
            with open(snap_path, "w", encoding="utf-8") as f:
                json.dump(legacy_data, f)

            adapter.table_state = {}
            loaded = adapter._load_snapshot()

            # Verify that legacy snapshot is safely rejected
            self.assertFalse(loaded, "Legacy untagged snapshot was not safely rejected!")
            self.assertEqual(adapter.table_state, {}, "table_state was populated from legacy untagged snapshot!")

    def test_10_repeated_pk_discovery_idempotency(self):
        """Proves repeated discovery passes (3+ times) leave pk_map and identity shapes 100% stable."""
        adapter = MySQLCDCSourceAdapter({"database": "test_db"})

        class MockCursor:
            def __enter__(self):
                return self
            def __exit__(self, *args):
                pass
            def execute(self, query, params=None):
                pass
            def fetchall(self):
                return [
                    {"TABLE_NAME": "departments", "COLUMN_NAME": "DEPARTMENT_ID"},
                    {"TABLE_NAME": "order_items", "COLUMN_NAME": "ORDER_ID"},
                    {"TABLE_NAME": "order_items", "COLUMN_NAME": "LINE_NO"},
                ]

        class MockConn:
            def cursor(self):
                return MockCursor()

        conn = MockConn()

        # Run discovery 5 times in a row on the same adapter instance
        for _ in range(5):
            adapter._discover_pks_and_snapshot(conn)

        # Single column PK table must remain single column
        self.assertEqual(adapter.pk_map["DEPARTMENTS"], ["DEPARTMENT_ID"])

        # Composite PK table must remain ordered 2-element list
        self.assertEqual(adapter.pk_map["ORDER_ITEMS"], ["ORDER_ID", "LINE_NO"])

        # Verify key shapes returned by make_pk_key after repeated discovery
        dept_row = {"DEPARTMENT_ID": 10, "DEPARTMENT_NAME": "Admin"}
        dept_key = adapter._make_pk_key(dept_row, adapter.pk_map["DEPARTMENTS"])
        self.assertEqual(dept_key, 10, "Single-column PK key shape mutated after repeated discovery!")

        item_row = {"ORDER_ID": 4502, "LINE_NO": 2, "PRICE": 19.99}
        item_key = adapter._make_pk_key(item_row, adapter.pk_map["ORDER_ITEMS"])
        self.assertEqual(item_key, (4502, 2), "Composite PK key shape mutated after repeated discovery!")


if __name__ == "__main__":
    unittest.main()

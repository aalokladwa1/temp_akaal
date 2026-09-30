"""
tests/unit/cdc/test_fk_ordering_regression.py
===============================================
Focused regression test proving target-safe, source-equivalent FK dependency ordering
for change events (parent INSERTS/UPDATES before child INSERTS/UPDATES, followed by child DELETES before parent DELETES)
while strictly preserving transaction boundaries and commit sequence across transactions.
"""

import time
import pytest
from akaalEngine.cdc.api import CDCAuthority
from akaalEngine.cdc.models.event import ChangeEvent, ChangeOperation, DeletionType


class MockTargetWriter:
    def __init__(self):
        self.applied_events = []
        self.params = {"schema": "DEVKROS_P8_M2_TGT"}

    def write_batch(self, table_name, batch, target_schema="public", pk_columns=None):
        self.applied_events.append(("WRITE", table_name, batch.rows))
        return len(batch.rows)

    def delete_batch(self, table_name, target_schema, pk_columns, key_records):
        self.applied_events.append(("DELETE", table_name, key_records))
        return len(key_records)

    def commit(self):
        pass


def make_evt(event_id, table, op, key_cols, key_vals, before=None, after=None, del_type=None, pos="binlog.0001:100", tx_id=None):
    now = time.time()
    return ChangeEvent(
        event_id=event_id,
        source_system="MYSQL",
        source_identity=pos,
        logical_object=table,
        operation=op,
        source_position=pos,
        commit_position=pos,
        commit_timestamp=now,
        capture_timestamp=now,
        schema_version="1.0.0",
        key_columns=tuple(key_cols),
        key_values=key_vals,
        before_image=before,
        after_image=after,
        deletion_type=del_type,
        tx_context={"tx_id": tx_id} if tx_id else None,
    )


def test_topological_fk_ordering_inserts_before_deletes():
    """
    Proves parent INSERTS execute before child INSERTS, and all INSERTS execute before DELETES within a batch.
    """
    cdc_auth = CDCAuthority()
    mock_writer = MockTargetWriter()
    cdc_auth.bind_target_writer(mock_writer)

    evt_dept_ins = make_evt(
        "evt-dept-1", "DEPARTMENTS", ChangeOperation.INSERT,
        ["DEPARTMENT_ID"], {"DEPARTMENT_ID": 26}, after={"DEPARTMENT_ID": 26, "DEPARTMENT_NAME": "Eng"}
    )
    evt_emp_ins = make_evt(
        "evt-emp-1", "EMPLOYEES", ChangeOperation.INSERT,
        ["EMPLOYEE_ID"], {"EMPLOYEE_ID": 801}, after={"EMPLOYEE_ID": 801, "DEPARTMENT_ID": 26}
    )
    evt_order_ins = make_evt(
        "evt-ord-1", "ORDERS", ChangeOperation.INSERT,
        ["ORDER_ID"], {"ORDER_ID": 4501}, after={"ORDER_ID": 4501, "CUSTOMER_ID": 1201, "EMPLOYEE_ID": 801}
    )
    evt_item_ins = make_evt(
        "evt-item-1", "ORDER_ITEMS", ChangeOperation.INSERT,
        ["ORDER_ID", "LINE_NO"], {"ORDER_ID": 4501, "LINE_NO": 1}, after={"ORDER_ID": 4501, "LINE_NO": 1, "QUANTITY": 2}
    )
    evt_item_del = make_evt(
        "evt-item-del-1", "ORDER_ITEMS", ChangeOperation.DELETE,
        ["ORDER_ID", "LINE_NO"], {"ORDER_ID": 4502, "LINE_NO": 2}, before={"ORDER_ID": 4502, "LINE_NO": 2}, del_type=DeletionType.EXPLICIT_DELETE
    )

    # Input batch provided in arbitrary/reverse order (DELETE first, child before parent)
    unfiltered_batch = [evt_item_del, evt_item_ins, evt_order_ins, evt_emp_ins, evt_dept_ins]

    count = cdc_auth.apply_events(unfiltered_batch)
    assert count == 5

    # Verify order of execution:
    # 1. DEPARTMENTS (depth 0, INSERT)
    # 2. EMPLOYEES (depth 1, INSERT)
    # 3. ORDERS (depth 2, INSERT)
    # 4. ORDER_ITEMS (depth 3, INSERT)
    # 5. ORDER_ITEMS (depth 3, DELETE)
    op_sequence = [(op, table) for op, table, _ in mock_writer.applied_events]
    expected_sequence = [
        ("WRITE", "DEPARTMENTS"),
        ("WRITE", "EMPLOYEES"),
        ("WRITE", "ORDERS"),
        ("WRITE", "ORDER_ITEMS"),
        ("DELETE", "ORDER_ITEMS"),
    ]
    assert op_sequence == expected_sequence


def test_transaction_boundary_commit_order_preservation():
    """
    Proves events from Transaction 1 strictly complete before Transaction 2 events, preserving commit sequence.
    """
    cdc_auth = CDCAuthority()
    mock_writer = MockTargetWriter()
    cdc_auth.bind_target_writer(mock_writer)

    # Tx 1: DEPARTMENTS insert at pos 100
    tx1_evt = make_evt(
        "tx1-dept", "DEPARTMENTS", ChangeOperation.INSERT,
        ["DEPARTMENT_ID"], {"DEPARTMENT_ID": 27}, after={"DEPARTMENT_ID": 27, "DEPARTMENT_NAME": "Sales"},
        pos="binlog.0001:100", tx_id="tx-100"
    )

    # Tx 2: EMPLOYEES insert at pos 200
    tx2_evt = make_evt(
        "tx2-emp", "EMPLOYEES", ChangeOperation.INSERT,
        ["EMPLOYEE_ID"], {"EMPLOYEE_ID": 802}, after={"EMPLOYEE_ID": 802, "DEPARTMENT_ID": 27},
        pos="binlog.0001:200", tx_id="tx-200"
    )

    count = cdc_auth.apply_events([tx1_evt, tx2_evt])
    assert count == 2

    # Tx 1 must run before Tx 2
    applied_tx_order = [row[0]["EMPLOYEE_ID"] if table == "EMPLOYEES" else row[0]["DEPARTMENT_ID"] for _, table, row in mock_writer.applied_events]
    assert applied_tx_order == [27, 802]

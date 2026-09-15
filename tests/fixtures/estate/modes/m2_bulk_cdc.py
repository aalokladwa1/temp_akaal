"""M2 fixture: bulk + CDC (build-spec §15).

A deterministic transaction/CDC stream over dedicated mutable portions of
COMMERCE_ORDERS.orders and FINANCIAL_LEDGER.journals, using AKAAL's own
CDCEvent/TransactionContext/Position contracts (cdc/events.py). Includes
committed and deliberately rolled-back transactions, multi-row transactions,
and repeat updates. The expected final state is computed independently by
replaying only committed events, in order, over the sampled baseline rows.
"""
from __future__ import annotations

import os
import sqlite3

from akaal.cdc.contracts.event import ChangeType

from modes._common import mode_dir, write_json, DATA_DIR
from generator.seed import rng_for
from cdc.events import make_event, make_tx_context, make_position, make_checkpoint

BASELINE_DB = os.path.join(DATA_DIR, "source_baseline.sqlite")
SAMPLE_SIZE = 500


def _sample_rows(conn, physical_table, cols, n):
    placeholders = ",".join(cols)
    rows = conn.execute(f'SELECT {placeholders} FROM "{physical_table}" ORDER BY id LIMIT {n}').fetchall()
    return [dict(zip(cols, r)) for r in rows]


def build_m2_fixture() -> dict:
    d = mode_dir("m2_bulk_cdc")
    conn = sqlite3.connect(BASELINE_DB)

    orders = _sample_rows(conn, "COMMERCE_ORDERS__orders", ["id", "customer_id", "status", "order_total"], SAMPLE_SIZE)
    journals = _sample_rows(conn, "FINANCIAL_LEDGER__journals", ["id", "fiscal_period_id", "journal_type", "status"], SAMPLE_SIZE)
    conn.close()

    rng = rng_for("m2-cdc-stream")
    events = []
    committed_final_state = {"COMMERCE_ORDERS.orders": {}, "FINANCIAL_LEDGER.journals": {}}
    offset = 0
    lsn = 0
    tx_no = 0

    def emit_tx(table_key, schema, table, rows_for_tx, change_type, commit: bool):
        nonlocal offset, lsn, tx_no
        tx_no += 1
        tx_id = f"TX-M2-{tx_no:06d}"
        tx_events = []
        for i, row in enumerate(rows_for_tx):
            offset += 1
            lsn += 1
            before = dict(row) if change_type != ChangeType.INSERT else None
            after = None
            if change_type == ChangeType.INSERT:
                after = dict(row)
            elif change_type == ChangeType.UPDATE:
                after = dict(row)
                after["status"] = "M2_UPDATED"
            # DELETE: after stays None
            tx_ctx = make_tx_context(tx_id, offset, i + 1, len(rows_for_tx))
            ev = make_event(f"EVT-{tx_no:06d}-{i:03d}", schema, table, change_type, before, after, offset, tx_ctx, f"LSN-{lsn:08d}")
            tx_events.append(ev)

        events.append({"tx_id": tx_id, "committed": commit, "events": [e.model_dump() for e in tx_events]})

        if commit:
            for row in rows_for_tx:
                key = row["id"]
                if change_type == ChangeType.DELETE:
                    committed_final_state[table_key].pop(key, None)
                else:
                    final_row = dict(row)
                    if change_type == ChangeType.UPDATE:
                        final_row["status"] = "M2_UPDATED"
                    committed_final_state[table_key][key] = final_row

    # seed initial committed state = the sampled rows themselves (pre-CDC baseline)
    for row in orders:
        committed_final_state["COMMERCE_ORDERS.orders"][row["id"]] = dict(row)
    for row in journals:
        committed_final_state["FINANCIAL_LEDGER.journals"][row["id"]] = dict(row)

    # multi-row committed update burst on orders
    emit_tx("COMMERCE_ORDERS.orders", "COMMERCE_ORDERS", "orders", orders[0:20], ChangeType.UPDATE, commit=True)
    # single-row committed delete
    emit_tx("COMMERCE_ORDERS.orders", "COMMERCE_ORDERS", "orders", orders[20:21], ChangeType.DELETE, commit=True)
    # deliberately rolled-back transaction (must NOT affect expected final state)
    emit_tx("COMMERCE_ORDERS.orders", "COMMERCE_ORDERS", "orders", orders[21:35], ChangeType.UPDATE, commit=False)
    # repeat update (same rows updated twice, committed both times -- final state = last write)
    emit_tx("COMMERCE_ORDERS.orders", "COMMERCE_ORDERS", "orders", orders[0:5], ChangeType.UPDATE, commit=True)

    emit_tx("FINANCIAL_LEDGER.journals", "FINANCIAL_LEDGER", "journals", journals[0:15], ChangeType.UPDATE, commit=True)
    emit_tx("FINANCIAL_LEDGER.journals", "FINANCIAL_LEDGER", "journals", journals[15:18], ChangeType.DELETE, commit=True)
    emit_tx("FINANCIAL_LEDGER.journals", "FINANCIAL_LEDGER", "journals", journals[18:30], ChangeType.UPDATE, commit=False)

    pos = make_position("SIMULATED_ORACLE", lsn, events[-1]["tx_id"])
    checkpoint = make_checkpoint("CP-M2-FINAL", "m2-stream", "AKAAL_ESTATE", pos, offset)

    write_json(os.path.join(d, "transaction_stream.json"), events)
    write_json(os.path.join(d, "expected_final_state.json"), committed_final_state)
    write_json(os.path.join(d, "checkpoint.json"), checkpoint.model_dump())

    manifest = {
        "mode": "M2",
        "description": "bulk + CDC over dedicated mutable portions of COMMERCE_ORDERS.orders and FINANCIAL_LEDGER.journals",
        "sample_size_per_table": SAMPLE_SIZE,
        "transaction_count": len(events),
        "committed_transaction_count": sum(1 for e in events if e["committed"]),
        "rolled_back_transaction_count": sum(1 for e in events if not e["committed"]),
        "total_event_count": sum(len(e["events"]) for e in events),
        "expected_final_row_counts": {k: len(v) for k, v in committed_final_state.items()},
        "reset_instructions": "rerun tests.fixtures.estate.modes.m2_bulk_cdc:build_m2_fixture()",
    }
    write_json(os.path.join(d, "manifest.json"), manifest)
    return manifest


if __name__ == "__main__":
    print(build_m2_fixture())

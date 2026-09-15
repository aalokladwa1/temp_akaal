"""M3 fixture: CDC/continuous replication only, no implicit bulk (build-spec §16).

Source and target begin already synchronized on a bounded sample of
CATALOG_PRODUCTS.products (proved via a fingerprint over that sample, not
by trusting a bulk load AKAAL performed). CDC deltas are then applied on
top, using the same CDCEvent contracts as M2, with an independently
computed expected post-CDC state.
"""
from __future__ import annotations

import os
import sqlite3

from akaal.cdc.contracts.event import ChangeType

from modes._common import mode_dir, write_json, DATA_DIR
from generator.seed import rng_for
from cdc.events import make_event, make_tx_context, make_position, make_checkpoint
from manifests.fingerprint import row_fingerprint

BASELINE_DB = os.path.join(DATA_DIR, "source_baseline.sqlite")
SAMPLE_SIZE = 400
COLS = ["id", "product_code", "category_id", "name", "is_active"]


def build_m3_fixture() -> dict:
    d = mode_dir("m3_cdc_only")
    conn = sqlite3.connect(BASELINE_DB)
    rows = conn.execute(
        f'SELECT {",".join(COLS)} FROM "CATALOG_PRODUCTS__products" ORDER BY id LIMIT {SAMPLE_SIZE}'
    ).fetchall()
    conn.close()
    sample = [dict(zip(COLS, r)) for r in rows]

    # initial synchronized state: identical fingerprint on both "sides" by construction
    initial_fingerprints = {str(r["id"]): row_fingerprint(tuple(r.values())) for r in sample}
    initial_state = {str(r["id"]): dict(r) for r in sample}

    final_state = {k: dict(v) for k, v in initial_state.items()}
    events = []
    offset, lsn, tx_no = 0, 0, 0

    def emit_tx(rows_for_tx, change_type):
        nonlocal offset, lsn, tx_no
        tx_no += 1
        tx_id = f"TX-M3-{tx_no:06d}"
        tx_events = []
        for i, row in enumerate(rows_for_tx):
            offset += 1
            lsn += 1
            before = dict(row)
            after = None if change_type == ChangeType.DELETE else dict(row)
            if change_type == ChangeType.UPDATE:
                after["name"] = after["name"] + " (M3 UPDATED)"
            tx_ctx = make_tx_context(tx_id, offset, i + 1, len(rows_for_tx))
            ev = make_event(f"EVT-M3-{tx_no:06d}-{i:03d}", "CATALOG_PRODUCTS", "products",
                             change_type, before, after, offset, tx_ctx, f"LSN-M3-{lsn:08d}")
            tx_events.append(ev)
            key = str(row["id"])
            if change_type == ChangeType.DELETE:
                final_state.pop(key, None)
            else:
                final_state[key] = after
        events.append({"tx_id": tx_id, "committed": True, "events": [e.model_dump() for e in tx_events]})

    rng = rng_for("m3-cdc-stream")
    emit_tx(sample[0:30], ChangeType.UPDATE)
    emit_tx(sample[30:45], ChangeType.DELETE)
    emit_tx([dict(id=SAMPLE_SIZE + i, product_code=f"NEWSKU-{i:04d}", category_id=None,
                  name=f"M3 New Product {i}", is_active=1) for i in range(10)], ChangeType.INSERT)
    emit_tx(sample[0:5], ChangeType.UPDATE)  # repeated update on already-updated rows -- final = last write

    pos = make_position("SIMULATED_ORACLE", lsn, events[-1]["tx_id"])
    checkpoint = make_checkpoint("CP-M3-FINAL", "m3-stream", "AKAAL_ESTATE", pos, offset)

    write_json(os.path.join(d, "initial_synchronized_state.json"), initial_state)
    write_json(os.path.join(d, "initial_fingerprints.json"), initial_fingerprints)
    write_json(os.path.join(d, "cdc_delta_stream.json"), events)
    write_json(os.path.join(d, "expected_post_cdc_state.json"), final_state)
    write_json(os.path.join(d, "checkpoint.json"), checkpoint.model_dump())

    manifest = {
        "mode": "M3",
        "description": "CDC-only replication starting from an already-synchronized bounded sample of CATALOG_PRODUCTS.products",
        "sample_size": SAMPLE_SIZE,
        "initial_row_count": len(sample),
        "transaction_count": len(events),
        "expected_post_cdc_row_count": len(final_state),
        "invariant": "M3 execution must not require AKAAL to perform an initial bulk load",
        "reset_instructions": "rerun tests.fixtures.estate.modes.m3_cdc_only:build_m3_fixture()",
    }
    write_json(os.path.join(d, "manifest.json"), manifest)
    return manifest


if __name__ == "__main__":
    print(build_m3_fixture())

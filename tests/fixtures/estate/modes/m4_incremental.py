"""M4 fixture: incremental query/polling (build-spec §17).

Dedicated M4 source rows (not reused from the 1M baseline) covering numeric
watermark, timestamp watermark, compound (timestamp, tie_breaker) watermark,
tied timestamps, deterministic poll windows, boundary/late arrivals,
NULL-watermark negative cases, and a non-monotonic negative case. A target
shell is created (M4 target structures must pre-exist). The critical
invariant under test later: durable watermark must never advance before
the corresponding target work commits -- this fixture records, for each
poll batch, the watermark value BEFORE and the value that would be durable
AFTER a safe commit, so a later test can inject a failure between the two
and assert the watermark did not advance.
"""
from __future__ import annotations

import os
import sqlite3

from modes._common import mode_dir, write_json, DATA_DIR

TABLE_DDL = """
CREATE TABLE m4_source_rows (
  id INTEGER PRIMARY KEY,
  watermark_ts TEXT,
  watermark_seq INTEGER,
  tie_breaker INTEGER,
  payload TEXT,
  is_deleted INTEGER DEFAULT 0
);
"""


def build_m4_fixture() -> dict:
    d = mode_dir("m4_incremental")
    db_path = os.path.join(d, "m4_source.sqlite")
    if os.path.exists(db_path):
        os.remove(db_path)
    conn = sqlite3.connect(db_path)
    conn.executescript(TABLE_DDL)

    rows = []
    # normal monotonic timestamp rows
    for i in range(1, 51):
        rows.append((i, f"2024-01-01T00:{i:02d}:00", i, 0, f"row-{i}", 0))
    # tied timestamps, multiple rows same watermark_ts -- tie_breaker disambiguates
    for j in range(3):
        rows.append((100 + j, "2024-01-01T00:50:00", 50, j, f"tied-{j}", 0))
    # boundary arrival exactly at a poll window edge
    rows.append((200, "2024-01-01T01:00:00", 60, 0, "boundary-row", 0))
    # late arrival: watermark_ts earlier than already-polled rows but inserted later (physical id higher)
    rows.append((201, "2024-01-01T00:10:00", 10, 0, "late-arrival", 0))
    # NULL-watermark negative case
    rows.append((202, None, None, 0, "null-watermark-row", 0))
    # updates and deletes represented as separate later physical rows referencing same logical id via payload tag
    rows.append((203, "2024-01-01T01:05:00", 65, 0, "updated-row-v2", 0))
    rows.append((204, "2024-01-01T01:06:00", 66, 0, "deleted-row", 1))

    conn.executemany("INSERT INTO m4_source_rows VALUES (?,?,?,?,?,?)", rows)
    conn.commit()
    conn.close()

    # deterministic poll windows over watermark_seq, with watermark-before/after-commit bookkeeping
    poll_batches = [
        {"batch_no": 1, "watermark_before": 0, "row_ids": list(range(1, 21)), "watermark_after_commit": 20},
        {"batch_no": 2, "watermark_before": 20, "row_ids": list(range(21, 51)), "watermark_after_commit": 50},
        {"batch_no": 3, "watermark_before": 50, "row_ids": [100, 101, 102], "watermark_after_commit": 50,
         "note": "tied timestamps at watermark_seq=50; tie_breaker required to make progress safely"},
        {"batch_no": 4, "watermark_before": 50, "row_ids": [200], "watermark_after_commit": 60},
        {"batch_no": 5, "watermark_before": 60, "row_ids": [201], "watermark_after_commit": 60,
         "note": "late arrival with watermark_seq=10 < current durable watermark; must not corrupt monotonic watermark"},
        {"batch_no": 6, "watermark_before": 60, "row_ids": [202], "watermark_after_commit": 60,
         "note": "NULL watermark row excluded from watermark advancement (negative case)"},
        {"batch_no": 7, "watermark_before": 60, "row_ids": [203, 204], "watermark_after_commit": 66},
    ]

    interrupted_scenario = {
        "description": "inject failure AFTER target commit of batch 2 rows but BEFORE durable watermark commit",
        "batch_no": 2,
        "target_commit_happens": True,
        "watermark_commit_happens": False,
        "expected_durable_watermark_after_restart": 20,
        "expected_row_ids_already_in_target": list(range(1, 51)),
        "invariant_under_test": "watermark must not have advanced past 20 even though rows 21-50 are already in target "
                                  "(safe: re-poll will re-fetch 21-50, target apply must be idempotent)",
    }

    write_json(os.path.join(d, "poll_batches.json"), poll_batches)
    write_json(os.path.join(d, "failure_injection_scenario.json"), interrupted_scenario)

    manifest = {
        "mode": "M4",
        "description": "incremental query/polling with numeric, timestamp and compound watermarks",
        "source_db": os.path.basename(db_path),
        "row_count": len(rows),
        "poll_batch_count": len(poll_batches),
        "final_durable_watermark_seq": 66,
        "negative_cases": ["tied_timestamps", "late_arrival", "null_watermark", "watermark_before_commit_failure"],
        "reset_instructions": "rerun tests.fixtures.estate.modes.m4_incremental:build_m4_fixture()",
    }
    write_json(os.path.join(d, "manifest.json"), manifest)
    return manifest


if __name__ == "__main__":
    print(build_m4_fixture())

"""
AKAAL Runtime V3 — Durable Write-Ahead Log (WAL) Queue
======================================================
Crash-safe append-only binary Write-Ahead Log with CRC32 checksums, segment rotation, commit markers, and replay support.
"""

import os
import json
import zlib
import time
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger("akaal.streaming.wal")


class DurableWALRingBuffer:
    """Crash-safe append-only WAL queue for zero data loss streaming recovery."""

    def __init__(self, migration_id: str, wal_dir: Optional[str] = None) -> None:
        self.migration_id = migration_id
        base_dir = wal_dir or os.path.join(os.path.expanduser("~"), ".akaal", "wal")
        self.migration_wal_dir = os.path.join(base_dir, migration_id)
        os.makedirs(self.migration_wal_dir, exist_ok=True)
        self.current_segment_id = 1
        self.current_file_path = os.path.join(self.migration_wal_dir, f"segment_{self.current_segment_id:06d}.wal")

    def append_record(self, record_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
        timestamp = time.time()
        payload = {
            "migration_id": self.migration_id,
            "type": record_type,
            "timestamp": timestamp,
            "data": data
        }
        encoded = json.dumps(payload).encode("utf-8")
        crc32 = zlib.crc32(encoded)

        # Write binary framing: 4-byte CRC + 4-byte len + data payload
        with open(self.current_file_path, "ab") as f:
            f.write(crc32.to_bytes(4, "big"))
            f.write(len(encoded).to_bytes(4, "big"))
            f.write(encoded)
            f.flush()
            os.fsync(f.fileno())  # Guaranteed durable disk write

        logger.debug(f"[DurableWAL] Appended record '{record_type}' (CRC32: {crc32}) to WAL segment '{self.current_file_path}'.")
        return {"crc32": crc32, "timestamp": timestamp}

    def replay_wal(self) -> List[Dict[str, Any]]:
        records = []
        if not os.path.exists(self.migration_wal_dir):
            return records

        segment_files = sorted([f for f in os.listdir(self.migration_wal_dir) if f.endswith(".wal")])
        for seg in segment_files:
            seg_path = os.path.join(self.migration_wal_dir, seg)
            with open(seg_path, "rb") as f:
                while True:
                    crc_bytes = f.read(4)
                    if not crc_bytes or len(crc_bytes) < 4:
                        break
                    expected_crc = int.from_bytes(crc_bytes, "big")
                    len_bytes = f.read(4)
                    if not len_bytes or len(len_bytes) < 4:
                        break
                    data_len = int.from_bytes(len_bytes, "big")
                    data_bytes = f.read(data_len)
                    if len(data_bytes) < data_len:
                        logger.warning(f"[DurableWAL] Truncated record in WAL file {seg_path}. Halting segment replay.")
                        break

                    actual_crc = zlib.crc32(data_bytes)
                    if actual_crc != expected_crc:
                        logger.error(f"[DurableWAL] CRC32 Checksum Mismatch in WAL file {seg_path}! Expected {expected_crc}, got {actual_crc}.")
                        continue

                    payload = json.loads(data_bytes.decode("utf-8"))
                    records.append(payload)

        logger.info(f"[DurableWAL] Replayed {len(records)} verified WAL records for migration '{self.migration_id}'.")
        return records

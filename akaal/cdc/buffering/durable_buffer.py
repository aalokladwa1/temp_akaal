"""
AKAAL Durable CDC Buffer & Backlog Subsystem.
=============================================
Provides crash-safe, restart-recoverable, HMAC-integrity-protected persistence for committed CDC transactions.
Integrates with P1 DurableWALRingBuffer, BackpressureController, and CentralStateStore.
"""

from typing import Dict, Any, List, Optional
import os
import time
import json
import hmac
import hashlib
import logging

from akaal.cdc.domain.events import CDCEventIdentity, CDCTransaction, CDCEvent, parse_cdc_transaction
from akaal.cdc.domain.positions import CDCSourcePosition, parse_source_position
from akaal.cdc.domain.durability import CDCKeyProvider
from akaal.cdc.domain.errors import CDCFailure, CDCFailureCategory, CDCFailureType, CDCExecutionError
from akaal.streaming.buffering.wal_queue import DurableWALRingBuffer
from akaal.streaming.flow.backpressure import BackpressureController
from akaal.streaming.domain.enums import BackpressureState

logger = logging.getLogger(__name__)


class DurableCDCBuffer:
    """
    Authoritative Durable CDC Transaction Buffer.
    - Persists committed CDCTransaction payloads to disk before target application.
    - Protected by Keyed SHA-256 HMAC integrity hashes.
    - Fully restart-recoverable via WAL replay.
    - Bounded by P1 BackpressureController watermarks and hard capacity limits.
    """

    def __init__(
        self,
        identity: CDCEventIdentity,
        max_buffered_events: int = 1000,
        max_buffer_bytes: int = 50 * 1024 * 1024,  # 50 MB
        wal_dir: Optional[str] = None,
        backpressure_controller: Optional[BackpressureController] = None,
    ) -> None:
        self.identity = identity
        self.max_buffered_events = max_buffered_events
        self.max_buffer_bytes = max_buffer_bytes
        self.hard_event_limit = max_buffered_events * 2
        
        self.wal_buffer = DurableWALRingBuffer(
            migration_id=f"{identity.migration_id}_{identity.run_id}_{identity.cdc_session_id}",
            wal_dir=wal_dir,
        )
        self.backpressure = backpressure_controller or BackpressureController(
            max_queue_capacity=max_buffered_events,
            high_watermark_ratio=0.8,
            low_watermark_ratio=0.2,
        )

        self._in_memory_queue: List[Dict[str, Any]] = []
        self._buffered_bytes = 0
        self._buffered_events = 0
        self.hmac_key = CDCKeyProvider.get_checkpoint_hmac_key()

        # Recover from disk WAL if present
        self.recover_from_wal()

    def compute_record_hmac(self, tx_dict: Dict[str, Any], fencing_epoch: int) -> str:
        tx_id = tx_dict["tx_id"]
        pos_dict = tx_dict.get("commit_position", {})
        pos_str = str(pos_dict.get("lsn") or pos_dict.get("gtid") or pos_dict.get("scn") or pos_dict.get("position_str") or pos_dict)
        raw = f"{self.identity.migration_id}:{self.identity.run_id}:{self.identity.cdc_session_id}:{tx_id}:{fencing_epoch}:{pos_str}"
        return hmac.new(self.hmac_key, raw.encode("utf-8"), hashlib.sha256).hexdigest()

    def append_transaction(self, tx: CDCTransaction, fencing_epoch: int) -> Dict[str, Any]:
        """Persists a committed CDCTransaction to durable disk WAL and memory queue."""
        # Enforce cross-session/run identity checks
        if (
            tx.identity.migration_id != self.identity.migration_id
            or tx.identity.run_id != self.identity.run_id
            or tx.identity.cdc_session_id != self.identity.cdc_session_id
        ):
            fail = CDCFailure(
                failure_type=CDCFailureType.TRANSACTION_CORRUPTION,
                category=CDCFailureCategory.DATA_INTEGRITY_RISK,
                message=f"[BUFFER CONTAMINATION] Cross-run/session transaction '{tx.tx_id}' rejected.",
                migration_id=self.identity.migration_id,
                job_id=self.identity.job_id,
                run_id=self.identity.run_id,
                cdc_session_id=self.identity.cdc_session_id,
            )
            raise CDCExecutionError(fail)

        # Check hard capacity limit
        num_events = len(tx.events)
        if self._buffered_events + num_events > self.hard_event_limit:
            fail = CDCFailure(
                failure_type=CDCFailureType.DURABLE_BUFFER_FAILURE,
                category=CDCFailureCategory.PAUSABLE,
                message=f"[BUFFER EXHAUSTION] Hard event capacity limit reached ({self._buffered_events + num_events}/{self.hard_event_limit}).",
                migration_id=self.identity.migration_id,
                job_id=self.identity.job_id,
                run_id=self.identity.run_id,
                cdc_session_id=self.identity.cdc_session_id,
            )
            raise CDCExecutionError(fail)

        # Apply P1 Backpressure check
        bp_state = self.backpressure.check_and_update(self._buffered_events + num_events)

        tx_dict = tx.to_dict()
        record_hmac = self.compute_record_hmac(tx_dict, fencing_epoch)

        entry = {
            "migration_id": self.identity.migration_id,
            "job_id": self.identity.job_id,
            "run_id": self.identity.run_id,
            "cdc_session_id": self.identity.cdc_session_id,
            "fencing_epoch": fencing_epoch,
            "tx_id": tx.tx_id,
            "transaction_data": tx_dict,
            "record_hmac": record_hmac,
            "buffer_timestamp": time.time(),
        }

        # Write to durable WAL on disk (flush + fsync)
        res = self.wal_buffer.append_record("CDC_TX_COMMITTED", entry)

        entry_bytes = len(json.dumps(entry))
        self._buffered_bytes += entry_bytes
        self._buffered_events += num_events
        self._in_memory_queue.append(entry)

        logger.info(
            f"[DurableCDCBuffer] Durably buffered transaction '{tx.tx_id}' ({num_events} events, epoch {fencing_epoch}, HMAC: {record_hmac[:8]})."
        )
        return {
            "tx_id": tx.tx_id,
            "durable": True,
            "hmac": record_hmac,
            "buffered_events": self._buffered_events,
            "buffered_bytes": self._buffered_bytes,
        }

    def pop_next_transaction(self) -> Optional[Dict[str, Any]]:
        """Pops the oldest durably buffered transaction for target apply."""
        if not self._in_memory_queue:
            return None

        entry = self._in_memory_queue[0]
        # Verify HMAC integrity before returning
        tx_dict = entry["transaction_data"]
        expected_hmac = self.compute_record_hmac(tx_dict, entry["fencing_epoch"])
        if not hmac.compare_digest(entry["record_hmac"], expected_hmac):
            fail = CDCFailure(
                failure_type=CDCFailureType.BUFFER_CORRUPTION,
                category=CDCFailureCategory.DATA_INTEGRITY_RISK,
                message=f"[BUFFER CORRUPTION] HMAC integrity verification failed for transaction '{entry['tx_id']}'. Expected {expected_hmac[:8]}, got {entry['record_hmac'][:8]}.",
                migration_id=self.identity.migration_id,
                job_id=self.identity.job_id,
                run_id=self.identity.run_id,
                cdc_session_id=self.identity.cdc_session_id,
            )
            raise CDCExecutionError(fail)

        return entry

    def remove_acknowledged_transaction(self, tx_id: str) -> bool:
        """Removes an acknowledged transaction from the buffer."""
        for idx, entry in enumerate(self._in_memory_queue):
            if entry["tx_id"] == tx_id:
                removed = self._in_memory_queue.pop(idx)
                tx_data = removed["transaction_data"]
                num_evts = len(tx_data.get("events", []))
                entry_bytes = len(json.dumps(removed))
                self._buffered_events = max(0, self._buffered_events - num_evts)
                self._buffered_bytes = max(0, self._buffered_bytes - entry_bytes)
                self.backpressure.check_and_update(self._buffered_events)
                logger.info(f"[DurableCDCBuffer] Cleaned acknowledged transaction '{tx_id}' from buffer.")
                return True
        return False

    def recover_from_wal(self) -> int:
        """Reconstructs buffer state from durable WAL on disk."""
        records = self.wal_buffer.replay_wal()
        self._in_memory_queue.clear()
        self._buffered_events = 0
        self._buffered_bytes = 0

        for r in records:
            if r.get("type") == "CDC_TX_COMMITTED":
                entry = r.get("data", {})
                tx_dict = entry.get("transaction_data", {})
                expected_hmac = self.compute_record_hmac(tx_dict, entry.get("fencing_epoch", 0))
                if not hmac.compare_digest(entry.get("record_hmac", ""), expected_hmac):
                    logger.error(f"[DurableCDCBuffer Recovery] Corrupted WAL record for tx '{entry.get('tx_id')}'. Skipping corrupted entry.")
                    continue

                num_evts = len(tx_dict.get("events", []))
                entry_bytes = len(json.dumps(entry))
                self._in_memory_queue.append(entry)
                self._buffered_events += num_evts
                self._buffered_bytes += entry_bytes

        logger.info(f"[DurableCDCBuffer Recovery] Recovered {len(self._in_memory_queue)} transactions ({self._buffered_events} events) from disk WAL.")
        return len(self._in_memory_queue)

    def get_backlog_metrics(self) -> Dict[str, Any]:
        return {
            "buffered_transactions": len(self._in_memory_queue),
            "buffered_events": self._buffered_events,
            "buffered_bytes": self._buffered_bytes,
            "max_buffered_events": self.max_buffered_events,
            "hard_event_limit": self.hard_event_limit,
            "buffer_utilization": round(self._buffered_events / max(1, self.max_buffered_events), 4),
            "backpressure_state": self.backpressure.state.value,
        }

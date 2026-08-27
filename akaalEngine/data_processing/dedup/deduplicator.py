"""
akaalEngine.data_processing.dedup.deduplicator
===============================================
RowDeduplicator performing sliding-window composite key deduplication,
unambiguous length-prefixed key hashing, and deterministic survivor selection.
"""

from collections import deque, defaultdict
import hashlib
import json
from threading import RLock
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence, Set, Tuple


class DuplicateKeyException(Exception):
    """Raised when FAIL_ON_DUPLICATE policy encounters duplicate keys."""
    pass


class NondeterministicSurvivorError(Exception):
    """Raised when survivor selection cannot be deterministically resolved."""
    pass


class RowDeduplicator:
    """
    Thread-safe bounded sliding-window and batch deduplication engine.
    Calculates deterministic hash of composite key values and executes deterministic survivor selection.
    """

    def __init__(self, max_memory_keys: int = 100000, durable_spill_checker: Optional[Callable[[str], bool]] = None) -> None:
        self.max_memory_keys = max_memory_keys
        self.durable_spill_checker = durable_spill_checker
        self._seen_keys: Set[str] = set()
        self._key_queue: deque[str] = deque(maxlen=max_memory_keys)
        self._lock = RLock()

    def compute_key_hash(self, row: Mapping[str, Any], key_columns: Sequence[str]) -> str:
        """
        Unambiguous length-prefixed composite key hashing.
        Prevents delimiter collision attacks across multiple columns.
        """
        if not key_columns:
            # Hash entire record if no key specified
            raw = json.dumps({k: str(v) for k, v in sorted(row.items())}, sort_keys=True)
            return hashlib.sha256(raw.encode("utf-8")).hexdigest()

        components: List[str] = []
        for col in key_columns:
            if col not in row:
                components.append("NULL:None")
            else:
                v = row[col]
                if v is None:
                    components.append("NULL:None")
                else:
                    v_str = str(v)
                    components.append(f"{len(v_str)}:{v_str}")
        raw_str = "|".join(components)
        return hashlib.sha256(raw_str.encode("utf-8")).hexdigest()

    def _compute_key_hash(self, row: Mapping[str, Any], key_columns: Sequence[str]) -> str:
        return self.compute_key_hash(row, key_columns)

    def is_duplicate(self, row: Mapping[str, Any], key_columns: Sequence[str]) -> bool:
        """Sliding-window duplicate check for stream processing."""
        if not key_columns:
            return False

        key_hash = self.compute_key_hash(row, key_columns)

        with self._lock:
            if key_hash in self._seen_keys:
                return True

            # If spilled to durable store check
            if len(self._seen_keys) >= self.max_memory_keys and self.durable_spill_checker:
                if self.durable_spill_checker(key_hash):
                    return True

            # Add to sliding memory window
            if len(self._key_queue) >= self.max_memory_keys:
                oldest = self._key_queue.popleft()
                self._seen_keys.discard(oldest)

            self._key_queue.append(key_hash)
            self._seen_keys.add(key_hash)
            return False

    def deduplicate_batch(
        self,
        records: Sequence[Mapping[str, Any]],
        key_columns: Sequence[str],
        survivor_strategy: str = "FIRST",
        order_by_columns: Optional[Sequence[str]] = None,
        priority_field: Optional[str] = None,
        priority_order: Optional[Sequence[Any]] = None,
        disposition: str = "DISCARD",
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], Dict[str, Any]]:
        """
        Executes 100% deterministic batch deduplication and survivor selection.

        Returns:
            (survivor_records, duplicate_records, metrics_summary)
        """
        if not records:
            return [], [], {"total_input": 0, "survivors": 0, "duplicates_detected": 0}

        strat = str(survivor_strategy).upper()
        order_cols = list(order_by_columns or [])
        pri_order = list(priority_order or [])

        # 1. Group records by unambiguous composite key hash
        groups: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        for r in records:
            kh = self.compute_key_hash(r, key_columns)
            groups[kh].append(dict(r))

        survivors: List[Dict[str, Any]] = []
        duplicates: List[Dict[str, Any]] = []
        total_dups = 0

        for kh, group_records in groups.items():
            if len(group_records) == 1:
                survivors.append(group_records[0])
                continue

            # Multi-record duplicate group detected
            total_dups += len(group_records) - 1

            if strat == "FAIL_ON_DUPLICATE":
                raise DuplicateKeyException(
                    f"FAIL_ON_DUPLICATE policy violated: Found {len(group_records)} duplicate rows for key hash '{kh[:16]}'."
                )

            if strat == "REJECT_GROUP" or strat == "QUARANTINE_GROUP":
                # All records in the duplicate group are rejected/quarantined
                for rec in group_records:
                    rec["_dedup_disposition"] = "REJECTED" if strat == "REJECT_GROUP" else "QUARANTINED"
                    rec["_dedup_reason"] = f"Duplicate key group '{kh[:16]}' with {len(group_records)} items."
                    duplicates.append(rec)
                continue

            from functools import cmp_to_key

            def _compare_group_items(a: Dict[str, Any], b: Dict[str, Any]) -> int:
                # 1. Evaluate explicit order_by_columns
                for o_spec in order_cols:
                    parts = o_spec.strip().split()
                    col_name = parts[0]
                    desc = len(parts) > 1 and parts[1].upper() == "DESC"
                    val_a = a.get(col_name)
                    val_b = b.get(col_name)
                    if val_a != val_b:
                        if val_a is None:
                            return 1 if not desc else -1
                        if val_b is None:
                            return -1 if not desc else 1
                        if val_a < val_b:
                            return -1 if not desc else 1
                        else:
                            return 1 if not desc else -1

                # 2. Priority field evaluation
                if priority_field and pri_order:
                    va = a.get(priority_field)
                    vb = b.get(priority_field)
                    idx_a = pri_order.index(va) if va in pri_order else len(pri_order) + 1
                    idx_b = pri_order.index(vb) if vb in pri_order else len(pri_order) + 1
                    if idx_a != idx_b:
                        return -1 if idx_a < idx_b else 1

                # 3. Tie-breaker: SHA-256 fingerprint of the full record for absolute determinism
                fp_a = hashlib.sha256(json.dumps(a, default=str, sort_keys=True).encode("utf-8")).hexdigest()
                fp_b = hashlib.sha256(json.dumps(b, default=str, sort_keys=True).encode("utf-8")).hexdigest()
                if fp_a < fp_b:
                    return -1
                elif fp_a > fp_b:
                    return 1
                return 0

            # Sort group records
            sorted_group = list(group_records)

            if strat in ("MIN_FIELD", "MAX_FIELD") and order_cols:
                target_field = order_cols[0].strip().split()[0]
                is_max = (strat == "MAX_FIELD")
                order_cols = [f"{target_field} {'DESC' if is_max else 'ASC'}"]
                sorted_group.sort(key=cmp_to_key(_compare_group_items))
                survivor = sorted_group[0]
                non_survivors = sorted_group[1:]

            elif strat in ("NEWEST", "OLDEST") and order_cols:
                target_field = order_cols[0].strip().split()[0]
                is_newest = (strat == "NEWEST")
                order_cols = [f"{target_field} {'DESC' if is_newest else 'ASC'}"]
                sorted_group.sort(key=cmp_to_key(_compare_group_items))
                survivor = sorted_group[0]
                non_survivors = sorted_group[1:]

            elif strat == "PRIORITY" and priority_field and pri_order:
                sorted_group.sort(key=cmp_to_key(_compare_group_items))
                survivor = sorted_group[0]
                non_survivors = sorted_group[1:]

            else:
                sorted_group.sort(key=cmp_to_key(_compare_group_items))
                if strat == "LAST":
                    survivor = sorted_group[-1]
                    non_survivors = sorted_group[:-1]
                else:  # FIRST
                    survivor = sorted_group[0]
                    non_survivors = sorted_group[1:]

            survivors.append(survivor)
            for non_surv in non_survivors:
                non_surv["_dedup_disposition"] = disposition.upper()
                non_surv["_dedup_reason"] = f"Duplicate suppressed under survivor strategy {strat}."
                duplicates.append(non_surv)

        # Sort survivors deterministically by key hash to preserve consistency regardless of arrival
        survivors.sort(key=lambda r: self.compute_key_hash(r, key_columns))

        metrics = {
            "total_input": len(records),
            "survivors": len(survivors),
            "duplicates_detected": total_dups,
            "disposition_count": len(duplicates),
        }
        return survivors, duplicates, metrics

    def clear(self) -> None:
        with self._lock:
            self._seen_keys.clear()
            self._key_queue.clear()

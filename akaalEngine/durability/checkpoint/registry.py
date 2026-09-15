"""
Hierarchical Checkpoint Registry for Authority #5 — Durability (DUR-002).

Blocker 1 fix: save_checkpoint and save_row_position require an authenticated FencingToken.
There is no optional bypass. Token HMAC is verified, then exact epoch equality is asserted
against the live fencing_tokens row — all within the mutation's own transaction.
"""

import datetime
import json
import sqlite3
from typing import Dict, Any, List, Optional
from akaalEngine.durability.models.checkpoint import MigrationCheckpoint, TableCheckpoint, RowPosition, WatermarkType
from akaalEngine.durability.models.errors import (
    CheckpointConflictError,
    StaleGenerationError,
    FencingViolationError,
    DurabilityError,
    StateCorruptError,
    InvalidResumePositionError,
)
from akaalEngine.durability.models.fencing import FencingToken
from akaalEngine.durability.checkpoint.position import RowPositionTracker
from akaalEngine.durability.integrity.sanitizer import StateIntegritySanitizer
from akaalEngine.durability.integrity.secret_filter import SecretSanitizationFilter
from akaalEngine.durability.store.sqlite import SQLiteWalBackend


class MigrationCheckpointRegistry:
    """Manages creation, persistence, retrieval, and updates of hierarchical checkpoints."""

    def __init__(self, backend: SQLiteWalBackend) -> None:
        self.backend = backend
        # Lazily injected by DurabilityAuthority to avoid circular import
        self._fencing_manager = None

    def _require_fencing_manager(self):
        if self._fencing_manager is None:
            raise DurabilityError("FencingTokenManager not wired into MigrationCheckpointRegistry.")

    def save_checkpoint(self, checkpoint: MigrationCheckpoint, token: FencingToken, conn: Optional[sqlite3.Connection] = None) -> None:
        """
        Persists or updates a migration checkpoint.

        Requires an authenticated FencingToken:
        - HMAC is verified before any DB work.
        - Token epoch must equal the exact current epoch in fencing_tokens (no bypass).
        """
        self._require_fencing_manager()
        SecretSanitizationFilter.sanitize_state_dict(checkpoint.metadata)
        for tbl in checkpoint.table_checkpoints.values():
            if tbl.last_position and tbl.last_position.value:
                SecretSanitizationFilter.sanitize_state_dict(tbl.last_position.value)

        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        chk_dict = {
            "migration_id": checkpoint.migration_id,
            "job_id": checkpoint.job_id,
            "fencing_epoch": checkpoint.fencing_epoch,
            "status": checkpoint.status,
            "endpoint_identity": getattr(checkpoint, "endpoint_identity", None) or checkpoint.metadata.get("endpoint_identity"),
            "table_checkpoints": {
                name: {
                    "table_name": tbl.table_name,
                    "schema_name": tbl.schema_name,
                    "status": tbl.status,
                    "rows_processed": tbl.rows_processed,
                    "bytes_processed": tbl.bytes_processed,
                    "last_position": RowPositionTracker.to_dict(tbl.last_position) if tbl.last_position else None,
                    "partition_id": tbl.partition_id,
                    "updated_at": tbl.updated_at or now,
                }
                for name, tbl in checkpoint.table_checkpoints.items()
            },
            "metadata": checkpoint.metadata,
            "updated_at": now,
        }
        checksum = StateIntegritySanitizer.compute_dict_checksum(chk_dict)
        chk_json = json.dumps(chk_dict, sort_keys=True)
        self.backend.validate_quota(len(chk_json.encode("utf-8")))

        use_conn = conn or self.backend._get_connection()
        own_tx = conn is None

        with self.backend._mutex:
            try:
                if own_tx:
                    use_conn.execute("BEGIN IMMEDIATE;")

                if token.resource_id != checkpoint.migration_id and not token.resource_id.startswith(f"{checkpoint.migration_id}/"):
                    raise FencingViolationError(
                        f"Fencing violation: token resource_id '{token.resource_id}' does not match checkpoint migration_id '{checkpoint.migration_id}'."
                    )

                # HMAC verification + exact epoch equality in the same transaction
                self._fencing_manager.validate_token_in_tx(token, use_conn)

                # Also reject monotonic rollback: cannot write epoch lower than existing checkpoint
                cursor = use_conn.execute(
                    "SELECT fencing_epoch FROM checkpoints WHERE migration_id = ?;",
                    (checkpoint.migration_id,)
                )
                c_row = cursor.fetchone()
                if c_row:
                    curr_epoch = c_row["fencing_epoch"]
                    if checkpoint.fencing_epoch < curr_epoch:
                        raise StaleGenerationError(
                            f"Checkpoint update rejected: fencing epoch {checkpoint.fencing_epoch} is lower than existing checkpoint epoch {curr_epoch}."
                        )
                    use_conn.execute("""
                        UPDATE checkpoints SET
                            job_id = ?,
                            status = ?,
                            fencing_epoch = ?,
                            checkpoint_json = ?,
                            checksum = ?,
                            updated_at = ?
                        WHERE migration_id = ?;
                    """, (checkpoint.job_id, checkpoint.status, checkpoint.fencing_epoch, chk_json, checksum, now, checkpoint.migration_id))
                else:
                    use_conn.execute("""
                        INSERT INTO checkpoints (migration_id, job_id, status, fencing_epoch, checkpoint_json, checksum, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?);
                    """, (checkpoint.migration_id, checkpoint.job_id, checkpoint.status, checkpoint.fencing_epoch, chk_json, checksum, now))

                if own_tx:
                    use_conn.execute("COMMIT;")
            except Exception as e:
                if own_tx:
                    use_conn.execute("ROLLBACK;")
                if isinstance(e, DurabilityError):
                    raise e
                raise CheckpointConflictError(f"Failed to save checkpoint: {e}")

    def get_latest_checkpoint(self, migration_id: str, conn: Optional[sqlite3.Connection] = None) -> Optional[MigrationCheckpoint]:
        """Retrieves latest checkpoint for a migration ID."""
        use_conn = conn or self.backend._get_connection()
        cursor = use_conn.execute(
            "SELECT migration_id, job_id, status, fencing_epoch, checkpoint_json, checksum, updated_at FROM checkpoints WHERE migration_id = ?;",
            (migration_id,)
        )
        row = cursor.fetchone()
        if not row:
            return None

        try:
            chk_dict = json.loads(row["checkpoint_json"])
        except Exception as e:
            raise StateCorruptError(f"Corrupted checkpoint JSON payload: {e}") from e
        StateIntegritySanitizer.verify_dict_checksum(chk_dict, row["checksum"])

        tables = {}
        for name, tbl_dict in chk_dict.get("table_checkpoints", {}).items():
            pos = RowPositionTracker.from_dict(tbl_dict["last_position"]) if tbl_dict.get("last_position") else None
            tables[name] = TableCheckpoint(
                table_name=tbl_dict["table_name"],
                schema_name=tbl_dict["schema_name"],
                status=tbl_dict["status"],
                rows_processed=tbl_dict.get("rows_processed", 0),
                bytes_processed=tbl_dict.get("bytes_processed", 0),
                last_position=pos,
                partition_id=tbl_dict.get("partition_id"),
                updated_at=tbl_dict.get("updated_at"),
            )

        return MigrationCheckpoint(
            migration_id=row["migration_id"],
            job_id=row["job_id"],
            fencing_epoch=row["fencing_epoch"],
            status=row["status"],
            table_checkpoints=tables,
            metadata=chk_dict.get("metadata", {}),
            updated_at=row["updated_at"],
            checksum=row["checksum"],
        )

    def get_checkpoint(self, checkpoint_id: str, migration_id: Optional[str] = None, run_id: Optional[str] = None, conn: Optional[sqlite3.Connection] = None) -> Optional[MigrationCheckpoint]:
        """Retrieves exact checkpoint by checkpoint_id / job_id with optional migration filter."""
        use_conn = conn or self.backend._get_connection()
        if migration_id:
            cursor = use_conn.execute(
                "SELECT migration_id, job_id, status, fencing_epoch, checkpoint_json, checksum, updated_at FROM checkpoints WHERE job_id = ? AND migration_id = ?;",
                (checkpoint_id, migration_id)
            )
        else:
            cursor = use_conn.execute(
                "SELECT migration_id, job_id, status, fencing_epoch, checkpoint_json, checksum, updated_at FROM checkpoints WHERE job_id = ?;",
                (checkpoint_id,)
            )
        row = cursor.fetchone()
        if not row:
            return None

        try:
            chk_dict = json.loads(row["checkpoint_json"])
        except Exception as e:
            raise StateCorruptError(f"Corrupted checkpoint JSON payload: {e}") from e
        StateIntegritySanitizer.verify_dict_checksum(chk_dict, row["checksum"])

        tables = {}
        for name, tbl_dict in chk_dict.get("table_checkpoints", {}).items():
            pos = RowPositionTracker.from_dict(tbl_dict["last_position"]) if tbl_dict.get("last_position") else None
            tables[name] = TableCheckpoint(
                table_name=tbl_dict["table_name"],
                schema_name=tbl_dict["schema_name"],
                status=tbl_dict["status"],
                rows_processed=tbl_dict.get("rows_processed", 0),
                bytes_processed=tbl_dict.get("bytes_processed", 0),
                last_position=pos,
                partition_id=tbl_dict.get("partition_id"),
                updated_at=tbl_dict.get("updated_at"),
            )

        return MigrationCheckpoint(
            migration_id=row["migration_id"],
            job_id=row["job_id"],
            fencing_epoch=row["fencing_epoch"],
            status=row["status"],
            table_checkpoints=tables,
            metadata=chk_dict.get("metadata", {}),
            updated_at=row["updated_at"],
            checksum=row["checksum"],
        )

    def save_row_position(self, migration_id: str, table_name: str, position: RowPosition, token: FencingToken, conn: Optional[sqlite3.Connection] = None) -> None:
        """
        Atomically updates table row position within the current checkpoint.

        Requires an authenticated FencingToken — no optional bypass. If the token HMAC is
        invalid or the epoch does not match the current live resource epoch, the update is
        refused.
        """
        self._require_fencing_manager()
        use_conn = conn or self.backend._get_connection()
        own_tx = conn is None

        with self.backend._mutex:
            try:
                if own_tx:
                    use_conn.execute("BEGIN IMMEDIATE;")

                # HMAC verification + exact epoch equality in the same transaction
                self._fencing_manager.validate_token_in_tx(token, use_conn)

                cursor = use_conn.execute(
                    "SELECT migration_id, job_id, status, fencing_epoch, checkpoint_json, checksum, updated_at FROM checkpoints WHERE migration_id = ?;",
                    (migration_id,)
                )
                row = cursor.fetchone()
                if not row:
                    raise CheckpointConflictError(f"Cannot update position for non-existent migration checkpoint '{migration_id}'.")

                chk_dict = json.loads(row["checkpoint_json"])
                tables_dict = chk_dict.get("table_checkpoints", {})
                now = datetime.datetime.now(datetime.timezone.utc).isoformat()

                tbl_dict = tables_dict.get(table_name)
                if tbl_dict:
                    tbl_dict["status"] = "IN_PROGRESS"
                    tbl_dict["rows_processed"] = tbl_dict.get("rows_processed", 0) + 1
                    tbl_dict["last_position"] = RowPositionTracker.to_dict(position)
                    tbl_dict["updated_at"] = now
                else:
                    tables_dict[table_name] = {
                        "table_name": table_name,
                        "schema_name": "public",
                        "status": "IN_PROGRESS",
                        "rows_processed": 1,
                        "bytes_processed": 0,
                        "last_position": RowPositionTracker.to_dict(position),
                        "partition_id": None,
                        "updated_at": now,
                    }

                chk_dict["table_checkpoints"] = tables_dict
                chk_dict["updated_at"] = now
                checksum = StateIntegritySanitizer.compute_dict_checksum(chk_dict)
                chk_json = json.dumps(chk_dict, sort_keys=True)
                self.backend.validate_quota(len(chk_json.encode("utf-8")))

                use_conn.execute("""
                    UPDATE checkpoints SET
                        checkpoint_json = ?,
                        checksum = ?,
                        updated_at = ?
                    WHERE migration_id = ?;
                """, (chk_json, checksum, now, migration_id))

                if own_tx:
                    use_conn.execute("COMMIT;")
            except Exception as e:
                if own_tx:
                    use_conn.execute("ROLLBACK;")
                if isinstance(e, DurabilityError):
                    raise e
                raise CheckpointConflictError(f"Failed to save row position: {e}")

    # --- M4 correction: durable watermark authority ---------------------
    #
    # Watermarks are the canonical M4 DAG responsibility's persisted proof of
    # "how far incremental execution has durably advanced" for one
    # (migration_id, table_name) pair. This extends the SAME canonical,
    # atomically-persisted store used by checkpoints/positions above; it is
    # not a second durability/checkpoint/watermark authority.
    #
    # Invariant this module enforces (Principle: "AKAAL MUST NEVER advance
    # the durable watermark until the corresponding target work has safely
    # committed"): this registry has no visibility into the target database
    # and cannot itself prove cross-database atomicity (and must not claim
    # to) -- the invariant is enforced by CALL ORDER: callers (the M4
    # incremental-poll dispatch step) MUST only invoke `save_watermark`
    # AFTER a target commit has been confirmed successful. What this
    # registry DOES guarantee, physically, within its own atomic SQLite
    # transaction: (a) a watermark write either fully commits or fully rolls
    # back (a partial/interrupted persistence attempt leaves the prior
    # durable watermark completely unchanged -- verified by restart/replay);
    # (b) a candidate watermark that regresses/is invalid for its declared
    # type is rejected, never silently accepted; (c) a watermark bound to
    # one compiled plan cannot be silently overwritten by an incompatible
    # plan/execution identity; (d) a stale (lower) fencing epoch cannot
    # advance a watermark a fresher execution already owns.

    @staticmethod
    def _watermark_sort_key(watermark_type: str, value: Any):
        """Returns a Python-comparable key for the given watermark type.

        NUMERIC/TIMESTAMP: value itself (numbers compare numerically; ISO-8601
        strings with zero-padded components compare correctly as strings, but
        we still parse TIMESTAMP explicitly for correctness against
        non-zero-padded or differently-timezoned inputs).
        COMPOUND: a tuple, compared lexicographically component-by-component
        (Python's native tuple ordering) -- correct compound-key ordering:
        equal leading components correctly fall through to the next one.
        """
        wt = str(watermark_type)
        if wt == WatermarkType.NUMERIC.value:
            if value is None:
                raise InvalidResumePositionError("NUMERIC watermark value must not be null.")
            return float(value)
        if wt == WatermarkType.TIMESTAMP.value:
            if not value:
                raise InvalidResumePositionError("TIMESTAMP watermark value must not be null/empty.")
            import datetime as _dt
            try:
                return _dt.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
            except Exception as e:
                raise InvalidResumePositionError(f"Invalid TIMESTAMP watermark value '{value}': {e}")
        if wt == WatermarkType.COMPOUND.value:
            if value is None:
                raise InvalidResumePositionError("COMPOUND watermark value must not be null.")
            seq = list(value) if isinstance(value, (list, tuple)) else [value]
            normalized = []
            for component in seq:
                if isinstance(component, str):
                    import datetime as _dt
                    try:
                        normalized.append((0, _dt.datetime.fromisoformat(component.replace("Z", "+00:00"))))
                        continue
                    except Exception:
                        normalized.append((1, component))
                        continue
                normalized.append((2, component))
            return tuple(normalized)
        raise InvalidResumePositionError(f"Unknown watermark_type '{watermark_type}'.")

    def get_watermark(self, migration_id: str, table_name: str, conn: Optional[sqlite3.Connection] = None):
        """Returns the current durable Watermark for (migration_id, table_name),
        or None if no watermark has ever been saved (null-watermark baseline
        state -- callers must treat this as 'start from the beginning', never
        as an error)."""
        from akaalEngine.durability.models.checkpoint import Watermark, WatermarkType
        use_conn = conn or self.backend._get_connection()
        cursor = use_conn.execute(
            "SELECT migration_id, table_name, watermark_type, value_json, plan_fingerprint, execution_id, fencing_epoch, checksum, updated_at "
            "FROM watermarks WHERE migration_id = ? AND table_name = ?;",
            (migration_id, table_name),
        )
        row = cursor.fetchone()
        if not row:
            return None
        try:
            value = json.loads(row["value_json"])
        except Exception as e:
            raise StateCorruptError(f"Corrupted watermark value_json for '{migration_id}'/'{table_name}': {e}") from e
        expected_checksum = StateIntegritySanitizer.compute_dict_checksum({
            "migration_id": row["migration_id"], "table_name": row["table_name"],
            "watermark_type": row["watermark_type"], "value": value,
            "plan_fingerprint": row["plan_fingerprint"], "execution_id": row["execution_id"],
            "fencing_epoch": row["fencing_epoch"],
        })
        if expected_checksum != row["checksum"]:
            raise StateCorruptError(f"Watermark checksum mismatch for '{migration_id}'/'{table_name}' -- durable record does not match its own integrity checksum.")
        return Watermark(
            migration_id=row["migration_id"],
            table_name=row["table_name"],
            watermark_type=WatermarkType(row["watermark_type"]),
            value=value,
            plan_fingerprint=row["plan_fingerprint"],
            execution_id=row["execution_id"],
            fencing_epoch=row["fencing_epoch"],
            updated_at=row["updated_at"],
        )

    def save_watermark(self, watermark, token: FencingToken, conn: Optional[sqlite3.Connection] = None) -> None:
        """Atomically persists a new durable watermark for
        (watermark.migration_id, watermark.table_name), enforcing:

        - an authenticated FencingToken (HMAC + exact live-epoch match, same
          rule as save_checkpoint/save_row_position -- no bypass);
        - plan/version/execution identity protection: if a watermark already
          exists for this key bound to a DIFFERENT plan_fingerprint, the
          write is refused (`WatermarkIdentityMismatchError`) rather than
          silently reusing an incompatible checkpoint;
        - concurrent/stale execution fencing: a candidate fencing_epoch lower
          than the currently-stored epoch is refused
          (`StaleGenerationError`) -- a stale/superseded execution cannot
          advance a watermark a fresher execution already owns;
        - monotonic/valid position enforcement: a candidate value that is not
          >= the existing value under its declared comparison semantics is
          refused (`WatermarkRegressionError`) -- non-monotonic or otherwise
          invalid positions fail safe, never silently applied;
        - idempotent replay: saving the exact same value again (a repeated
          batch/replay) is accepted as a no-op-equivalent update, not an
          error -- tie timestamps and exact-duplicate replay both succeed.
        """
        from akaalEngine.durability.models.checkpoint import WatermarkType
        from akaalEngine.durability.models.errors import WatermarkRegressionError, WatermarkIdentityMismatchError

        self._require_fencing_manager()
        use_conn = conn or self.backend._get_connection()
        own_tx = conn is None

        with self.backend._mutex:
            try:
                if own_tx:
                    use_conn.execute("BEGIN IMMEDIATE;")

                if token.resource_id != watermark.migration_id and not token.resource_id.startswith(f"{watermark.migration_id}/"):
                    raise FencingViolationError(
                        f"Fencing violation: token resource_id '{token.resource_id}' does not match watermark migration_id '{watermark.migration_id}'."
                    )
                # HMAC verification + exact epoch equality in the same transaction
                self._fencing_manager.validate_token_in_tx(token, use_conn)

                cursor = use_conn.execute(
                    "SELECT watermark_type, value_json, plan_fingerprint, execution_id, fencing_epoch "
                    "FROM watermarks WHERE migration_id = ? AND table_name = ?;",
                    (watermark.migration_id, watermark.table_name),
                )
                row = cursor.fetchone()

                if row is not None:
                    existing_plan_fp = row["plan_fingerprint"]
                    existing_epoch = row["fencing_epoch"]
                    if existing_plan_fp and watermark.plan_fingerprint and existing_plan_fp != watermark.plan_fingerprint:
                        raise WatermarkIdentityMismatchError(
                            f"Watermark for '{watermark.migration_id}'/'{watermark.table_name}' is bound to plan_fingerprint "
                            f"'{existing_plan_fp}'; refusing incompatible write from plan_fingerprint '{watermark.plan_fingerprint}'."
                        )
                    if watermark.fencing_epoch < existing_epoch:
                        raise StaleGenerationError(
                            f"Watermark update rejected: fencing epoch {watermark.fencing_epoch} is lower than existing "
                            f"epoch {existing_epoch} for '{watermark.migration_id}'/'{watermark.table_name}' (stale/concurrent execution)."
                        )
                    existing_value = json.loads(row["value_json"])
                    existing_key = self._watermark_sort_key(row["watermark_type"], existing_value)
                    candidate_key = self._watermark_sort_key(watermark.watermark_type.value, watermark.value)
                    if candidate_key < existing_key:
                        raise WatermarkRegressionError(
                            f"Watermark update rejected: candidate value {watermark.value!r} is not >= existing durable "
                            f"value {existing_value!r} for '{watermark.migration_id}'/'{watermark.table_name}' "
                            f"(non-monotonic/invalid position)."
                        )
                else:
                    # First-ever watermark for this key (null-watermark baseline):
                    # still validate the candidate's own type/value are well-formed.
                    self._watermark_sort_key(watermark.watermark_type.value, watermark.value)

                now = datetime.datetime.now(datetime.timezone.utc).isoformat()
                value_json = json.dumps(watermark.value, sort_keys=True)
                checksum = StateIntegritySanitizer.compute_dict_checksum({
                    "migration_id": watermark.migration_id, "table_name": watermark.table_name,
                    "watermark_type": watermark.watermark_type.value, "value": watermark.value,
                    "plan_fingerprint": watermark.plan_fingerprint, "execution_id": watermark.execution_id,
                    "fencing_epoch": watermark.fencing_epoch,
                })

                if row is not None:
                    use_conn.execute("""
                        UPDATE watermarks SET
                            watermark_type = ?, value_json = ?, plan_fingerprint = ?,
                            execution_id = ?, fencing_epoch = ?, checksum = ?, updated_at = ?
                        WHERE migration_id = ? AND table_name = ?;
                    """, (watermark.watermark_type.value, value_json, watermark.plan_fingerprint,
                          watermark.execution_id, watermark.fencing_epoch, checksum, now,
                          watermark.migration_id, watermark.table_name))
                else:
                    use_conn.execute("""
                        INSERT INTO watermarks
                            (migration_id, table_name, watermark_type, value_json, plan_fingerprint, execution_id, fencing_epoch, checksum, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
                    """, (watermark.migration_id, watermark.table_name, watermark.watermark_type.value, value_json,
                          watermark.plan_fingerprint, watermark.execution_id, watermark.fencing_epoch, checksum, now))

                if own_tx:
                    use_conn.execute("COMMIT;")
            except Exception as e:
                if own_tx:
                    use_conn.execute("ROLLBACK;")
                raise e

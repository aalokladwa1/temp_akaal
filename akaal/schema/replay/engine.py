"""
AKAAL Platform 5 — DDL Replay Coordinator & Engine

Consumes immutable OperationJournal records to execute ordered, idempotent replay and checkpoint resumption.
"""

from dataclasses import dataclass, field
from typing import Any, List, Optional

from akaal.schema.domain.enums import ReplayState, ReplayStatus
from akaal.schema.domain.errors import ReplayError
from akaal.schema.domain.identifiers import CheckpointID
from akaal.schema.domain.journal import OperationRecord
from akaal.schema.observability.logger import StructuredAuditLogger
from akaal.schema.replay.journal_store import JournalStore


@dataclass
class ReplayReport:
    total_records: int
    executed_records: int
    skipped_records: int
    failed_records: int
    last_checkpoint: Optional[CheckpointID] = None


class ReplayValidator:
    """Validates operation journal integrity before replay."""

    def validate_journal(self, journal_store: JournalStore) -> bool:
        records = journal_store.get_records_from(0)
        expected_prev = "0" * 64
        for r in records:
            if not r.verify_integrity(expected_prev):
                raise ReplayError(
                    message=f"Journal integrity check failed at operation '{r.operation_id}'.",
                    recovery_recommendation="Restore journal store from backup or re-sync operation log."
                )
            if r.checksum:
                expected_prev = r.checksum.hash_value
        return True


class DDLReplayEngine:
    """Enterprise DDL Replay Engine."""

    def __init__(self, journal_store: Optional[JournalStore] = None) -> None:
        self.journal_store = journal_store or JournalStore()
        self.validator = ReplayValidator()
        self.audit_logger = StructuredAuditLogger("akaal.schema.replay")

    def replay(self, start_checkpoint: Optional[CheckpointID] = None, db_context: Any = None) -> ReplayReport:
        self.validator.validate_journal(self.journal_store)
        start_idx = self.journal_store.get_checkpoint_index(start_checkpoint) if start_checkpoint else 0

        records = self.journal_store.get_records_from(start_idx)
        executed = 0
        skipped = 0
        failed = 0

        for r in records:
            if r.replay_status == ReplayStatus.SUCCESS:
                skipped += 1
                continue

            try:
                # Simulate DDL re-execution from change_payload
                if db_context and hasattr(db_context, "execute_statement"):
                    sql = r.change_payload.get("sql")
                    if sql:
                        db_context.execute_statement(sql)

                r.replay_status = ReplayStatus.SUCCESS
                executed += 1
            except Exception as e:
                r.replay_status = ReplayStatus.FAILED
                failed += 1
                new_chk = self.journal_store.create_checkpoint()
                self.audit_logger.log_event("REPLAY_FAILED", level="ERROR", details={"op_id": str(r.operation_id), "error": str(e)})
                raise ReplayError(
                    message=f"Replay failed at operation '{r.operation_id}': {e}",
                    cause=e,
                    recovery_recommendation=f"Resume replay from checkpoint ID '{new_chk}' after resolving underlying issue."
                )

        final_chk = self.journal_store.create_checkpoint()
        self.audit_logger.log_event("REPLAY_COMPLETED", details={"executed": executed, "skipped": skipped})

        return ReplayReport(
            total_records=len(records),
            executed_records=executed,
            skipped_records=skipped,
            failed_records=failed,
            last_checkpoint=final_chk,
        )

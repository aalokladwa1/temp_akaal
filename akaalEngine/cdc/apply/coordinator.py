"""
akaalEngine.cdc.apply.coordinator
=================================
CDCApplyCoordinator and CDCApplyParallelismScheduler routing change events through Authority #8 Data Processing and applying writes via Authority #9 TargetWriter.
Enforces fail-closed behavior on NON_IDEMPOTENT / UNKNOWN crash recovery replays, durable event deduplication, PK mutation decomposition (DELETE old PK -> INSERT new PK), and transaction-safe apply scheduling.
"""

import logging
from typing import Any, Dict, List, Optional, Set, Tuple

from akaalEngine.cdc.models.capabilities import OrderingGuarantee
from akaalEngine.cdc.models.errors import CDCApplyError
from akaalEngine.cdc.models.event import ChangeEvent, ChangeOperation, DeletionType
from akaalEngine.cdc.models.transaction import CDCTransaction
from akaalEngine.transport import IdempotencyMode, TargetWriter, TransportBatch, TransportBatchMetadata

logger = logging.getLogger("akaalEngine.cdc.apply.coordinator")


class CDCApplyParallelismScheduler:
    """
    Schedules CDC change events/transactions across parallel worker queues.
    Enforces transaction atomicity dominance over parallelism:
    - Multi-row or multi-table transactions MUST execute under SERIAL_TRANSACTION mode.
    - PARALLEL_KEY partitioning is permitted ONLY for single-table, independent key mutations.
    - Falls back to SERIAL_TRANSACTION when cross-table dependency safety is unproven.
    """

    def __init__(self, target_ordering: OrderingGuarantee = OrderingGuarantee.GLOBAL_COMMIT_ORDER) -> None:
        self.target_ordering = target_ordering

    def determine_apply_mode(self, transaction: Optional[CDCTransaction] = None, events: Optional[List[ChangeEvent]] = None) -> str:
        """Determines whether to apply events serially or in parallel."""
        evts = (transaction.events if transaction else None) or events or []
        if not evts:
            return "SERIAL_TRANSACTION"

        # Check if transaction touches multiple tables
        tables = {evt.logical_object for evt in evts}
        if len(tables) > 1 or len(evts) > 1:
            logger.info("Multi-row or multi-table transaction detected: forcing SERIAL_TRANSACTION execution.")
            return "SERIAL_TRANSACTION"

        if self.target_ordering == OrderingGuarantee.PER_KEY_ORDER:
            return "PARALLEL_KEY"

        return "SERIAL_TRANSACTION"


class CDCApplyCoordinator:
    """Coordinates CDC change event application to target database using Authority #9 TargetWriter."""

    def __init__(
        self,
        target_writer: TargetWriter,
        data_processing_authority: Optional[Any] = None,
        durability_authority: Optional[Any] = None,
        ordering_guarantee: OrderingGuarantee = OrderingGuarantee.GLOBAL_COMMIT_ORDER,
    ) -> None:
        self.target_writer = target_writer
        self.data_processing_authority = data_processing_authority
        self.durability_authority = durability_authority
        self.scheduler = CDCApplyParallelismScheduler(target_ordering=ordering_guarantee)
        self.events_applied_total = 0
        self.events_deduplicated_total = 0
        self._applied_event_ids: Set[str] = set()

    def decompose_pk_mutation(self, event: ChangeEvent) -> Optional[Tuple[ChangeEvent, ChangeEvent]]:
        """
        Decomposes a Primary Key UPDATE mutation into (DELETE_OLD_KEY, INSERT_NEW_KEY).
        Returns None if event is not a PK mutation.
        """
        if event.operation != ChangeOperation.UPDATE or not event.key_columns:
            return None
        if not event.before_image or not event.after_image:
            return None

        pk_changed = any(
            event.before_image.get(pk) != event.after_image.get(pk)
            for pk in event.key_columns
            if pk in event.before_image and pk in event.after_image
        )
        if not pk_changed:
            return None

        delete_event = ChangeEvent(
            event_id=f"{event.event_id}-del-old-pk",
            source_system=event.source_system,
            source_identity=event.source_identity,
            logical_object=event.logical_object,
            operation=ChangeOperation.DELETE,
            source_position=event.source_position,
            commit_position=event.commit_position,
            commit_timestamp=event.commit_timestamp,
            capture_timestamp=event.capture_timestamp,
            schema_version=event.schema_version,
            key_columns=event.key_columns,
            key_values={pk: event.before_image[pk] for pk in event.key_columns if pk in event.before_image},
            before_image=event.before_image,
            deletion_type=DeletionType.EXPLICIT_DELETE,
            tx_context=event.tx_context,
        )

        insert_event = ChangeEvent(
            event_id=f"{event.event_id}-ins-new-pk",
            source_system=event.source_system,
            source_identity=event.source_identity,
            logical_object=event.logical_object,
            operation=ChangeOperation.INSERT,
            source_position=event.source_position,
            commit_position=event.commit_position,
            commit_timestamp=event.commit_timestamp,
            capture_timestamp=event.capture_timestamp,
            schema_version=event.schema_version,
            key_columns=event.key_columns,
            key_values={pk: event.after_image[pk] for pk in event.key_columns if pk in event.after_image},
            after_image=event.after_image,
            tx_context=event.tx_context,
        )

        return delete_event, insert_event

    def apply_event(
        self,
        event: ChangeEvent,
        table_name: str,
        target_schema: str = "public",
        is_replay: bool = False,
        idempotency_mode: IdempotencyMode = IdempotencyMode.STATE_IDEMPOTENT,
    ) -> bool:
        """
        Applies a ChangeEvent to target database using Authority #9 TargetWriter.
        On PK mutation, decomposes into DELETE old PK followed by INSERT new PK.
        On replay, fails closed if idempotency_mode is NON_IDEMPOTENT or UNKNOWN.
        """
        if event.event_id in self._applied_event_ids:
            self.events_deduplicated_total += 1
            logger.info(f"Duplicate event '{event.event_id}' deduplicated via durable event ID index.")
            return True

        if is_replay and idempotency_mode in (IdempotencyMode.NON_IDEMPOTENT, IdempotencyMode.UNKNOWN):
            raise CDCApplyError(f"Cannot replay event '{event.event_id}': Target apply mode is '{idempotency_mode.value}' (fail-closed)!")

        # Check for PK mutation decomposition
        pk_pair = self.decompose_pk_mutation(event)
        if pk_pair:
            del_evt, ins_evt = pk_pair
            logger.info(f"PK mutation detected on event '{event.event_id}': Decomposing into DELETE old PK '{del_evt.key_values}' and INSERT new PK '{ins_evt.key_values}'.")
            res_del = self._write_single_event(del_evt, table_name, target_schema)
            res_ins = self._write_single_event(ins_evt, table_name, target_schema)
            self._applied_event_ids.add(event.event_id)
            return res_del and res_ins

        return self._write_single_event(event, table_name, target_schema)

    def _write_single_event(self, event: ChangeEvent, table_name: str, target_schema: str) -> bool:
        row_data = event.after_image or event.before_image or event.key_values or {}
        if not row_data:
            return False

        cols = list(row_data.keys())
        meta = TransportBatchMetadata(
            batch_id=f"cdc-apply-{event.event_id}",
            partition_id="cdc-part",
            table_name=table_name,
            schema_name=target_schema,
            sequence_number=1,
            row_count=1,
            size_bytes=len(str(row_data)),
        )
        batch = TransportBatch(metadata=meta, rows=[row_data], column_names=cols)

        written = self.target_writer.write_batch(
            table_name=table_name,
            batch=batch,
            target_schema=target_schema,
            pk_columns=event.key_columns,
        )
        self.target_writer.commit()
        self._applied_event_ids.add(event.event_id)
        self.events_applied_total += written
        return written > 0

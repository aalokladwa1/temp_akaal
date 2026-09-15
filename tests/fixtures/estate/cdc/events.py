"""Deterministic CDC/transaction event construction, reusing AKAAL's own
canonical contracts (akaal/cdc/contracts/event.py, checkpoint.py) rather than
inventing a parallel event model (build-spec §3 design decision #3)."""
from __future__ import annotations

import datetime as dt

from akaal.cdc.contracts.event import CDCEvent, ChangeType, TransactionContext
from akaal.cdc.contracts.checkpoint import Position, Checkpoint

EPOCH = dt.datetime(2024, 1, 1, tzinfo=dt.timezone.utc)


def deterministic_timestamp(offset_seconds: int) -> str:
    return (EPOCH + dt.timedelta(seconds=offset_seconds)).isoformat()


def make_tx_context(tx_id: str, commit_offset: int, seq: int, total_in_tx: int) -> TransactionContext:
    return TransactionContext(
        tx_id=tx_id,
        commit_timestamp=deterministic_timestamp(commit_offset),
        sequence_number=seq,
        total_events_in_tx=total_in_tx,
    )


def make_event(event_id: str, schema: str, table: str, change_type: ChangeType,
                before, after, offset_seconds: int, tx_context: TransactionContext, lsn: str) -> CDCEvent:
    return CDCEvent(
        event_id=event_id,
        source_engine="SIMULATED_ORACLE",
        source_db="AKAAL_ESTATE",
        source_schema=schema,
        source_table=table,
        change_type=change_type,
        before_state=before,
        after_state=after,
        timestamp=deterministic_timestamp(offset_seconds),
        tx_context=tx_context,
        position_lsn=lsn,
    )


def make_position(engine: str, stream_position: int, tx_id: str) -> Position:
    return Position(engine=engine, stream_position=str(stream_position), tx_id=tx_id)


def make_checkpoint(checkpoint_id: str, stream_id: str, source_db: str, position: Position,
                     offset_seconds: int, metadata=None) -> Checkpoint:
    return Checkpoint(
        checkpoint_id=checkpoint_id, stream_id=stream_id, source_db=source_db,
        position=position, updated_at=deterministic_timestamp(offset_seconds),
        metadata=metadata or {},
    )

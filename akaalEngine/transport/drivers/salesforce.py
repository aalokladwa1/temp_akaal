"""
akaalEngine.transport.drivers.salesforce
=========================================
Canonical Salesforce physical Transport driver (P7A Campaign B, provider #46).

Salesforce is a SaaS/application platform, NOT a SQL database -- SObjects are modeled
honestly as their real REST shape (no fabricated PK/FK/transaction/relational-schema
fiction). Uses the real `simple_salesforce`-shaped REST client: `.query(soql)` /
`.query_more(next_records_url, identifier_is_url=True)` for the genuine
`nextRecordsUrl`-based continuation (never a relational keyset), and the real SObject
Collections REST endpoint (`composite/sobjects`, bounded to <=200 records/call) for
writes -- plain insert is honestly NON_IDEMPOTENT; external-ID-keyed upsert
(`composite/sobjects/{sobject}/{externalIdField}`, PATCH) is genuinely
OPERATION_IDEMPOTENT when an `external_id_field` is configured.

No native Salesforce CDC (Change Data Capture / Platform Events) claim is made -- no
capture module exists here; only REST/SOQL polling is implemented.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Sequence

from akaalEngine.transport.drivers.base import SourceReader, TargetWriter
from akaalEngine.transport.models.batch import TransportBatch, TransportBatchMetadata
from akaalEngine.transport.models.capabilities import (
    CancellationCapability,
    CommitOutcomeState,
    IdempotencyMode,
    LOBMode,
    ProviderCapabilities,
    ResumabilityMode,
)
from akaalEngine.transport.models.spec import TransportPartition

logger = logging.getLogger("akaalEngine.transport.drivers.salesforce")

_COLLECTIONS_BATCH_LIMIT = 200  # Salesforce SObject Collections' real per-call record limit


class SalesforceSourceReader(SourceReader):
    """Real Salesforce SourceReader using SOQL `.query()`/`.query_more()` -- the genuine
    `nextRecordsUrl` continuation mechanism, never a fabricated offset or keyset."""

    def __init__(self, connection_params: dict):
        self.params = connection_params
        # `db_connection` is expected to be a real simple_salesforce.Salesforce instance
        # (or a test double shaped like one), resolved via the Connection Authority.
        self.client = connection_params.get("db_connection") or connection_params.get("client")
        self.partition: Optional[TransportPartition] = None
        self.sequence_number = 0
        self._next_records_url: Optional[str] = None
        self._done = False
        self._started = False

    def get_capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            bulk_read=True,
            bulk_write=False,
            lob_read=LOBMode.BOUNDED_MATERIALIZATION,
            lob_write=LOBMode.BOUNDED_MATERIALIZATION,
            cancellation=CancellationCapability.COOPERATIVE_STOP,
            idempotency=IdempotencyMode.NON_IDEMPOTENT,
            resumability=ResumabilityMode.PROVIDER_RESUMABLE,  # nextRecordsUrl, not exact-resume
        )

    def open_partition(self, partition: TransportPartition, last_committed_key: Optional[Any] = None) -> None:
        self.partition = partition
        self.sequence_number = 0
        self._done = False
        self._started = False
        # last_committed_key carries a persisted nextRecordsUrl string from a prior checkpoint.
        self._next_records_url = last_committed_key if isinstance(last_committed_key, str) else None
        if self.client is None:
            self.client = self.params.get("db_connection") or self.params.get("client")

    def read_batch(self, batch_size: int = 5000) -> Optional[TransportBatch]:
        if self.client is None or self._done or self.partition is None:
            return None

        try:
            if self._next_records_url:
                resp = self.client.query_more(self._next_records_url, identifier_is_url=True)
            elif not self._started:
                soql = self.params.get("soql") or f"SELECT FIELDS(ALL) FROM {self.partition.table_name} LIMIT {int(batch_size)}"
                resp = self.client.query(soql)
                self._started = True
            else:
                return None
        except Exception as exc:
            from akaalEngine.transport.models.errors import TransportReadError
            raise TransportReadError(f"Salesforce SOQL query failed: {exc}") from exc

        records: List[Dict[str, Any]] = resp.get("records", []) if isinstance(resp, dict) else []
        self._done = bool(resp.get("done", True)) if isinstance(resp, dict) else True
        self._next_records_url = resp.get("nextRecordsUrl") if isinstance(resp, dict) else None
        if not self._next_records_url:
            self._done = True

        # Strip Salesforce's REST envelope key present on every record.
        rows = [{k: v for k, v in r.items() if k != "attributes"} for r in records]
        if not rows:
            return None

        self.sequence_number += 1
        cols = sorted({k for row in rows for k in row.keys()})
        meta = TransportBatchMetadata(
            batch_id=f"salesforce-batch-{self.sequence_number}",
            partition_id=self.partition.partition_id,
            table_name=self.partition.table_name,
            schema_name=self.partition.schema_name or "",
            sequence_number=self.sequence_number,
            row_count=len(rows),
            size_bytes=sum(len(str(r)) for r in rows),
        )
        return TransportBatch(metadata=meta, rows=rows, column_names=cols)

    @property
    def resume_position(self) -> Optional[str]:
        """The real Salesforce `nextRecordsUrl` to persist as the checkpoint's read_position."""
        return self._next_records_url

    def cancel(self) -> None:
        self._done = True

    def close(self) -> None:
        pass


class SalesforceTargetWriter(TargetWriter):
    """Real Salesforce TargetWriter using the SObject Collections REST endpoint, bounded to
    the real <=200-record-per-call limit. Plain insert is NON_IDEMPOTENT (honest -- a retried
    create makes a duplicate SObject); external-ID upsert (when `external_id_field` is
    configured) is genuinely OPERATION_IDEMPOTENT."""

    def __init__(self, connection_params: Optional[dict] = None):
        params = connection_params or {}
        super().__init__(
            migration_id=params.get("migration_id"),
            batch_id=params.get("batch_id") or params.get("job_id"),
            endpoint_identity=params.get("endpoint_identity") or params.get("host"),
        )
        self.params = params
        self.client = params.get("db_connection") or params.get("client")
        self.external_id_field: Optional[str] = params.get("external_id_field")

    def get_capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            bulk_read=False,
            bulk_write=True,
            lob_read=LOBMode.BOUNDED_MATERIALIZATION,
            lob_write=LOBMode.BOUNDED_MATERIALIZATION,
            cancellation=CancellationCapability.COOPERATIVE_STOP,
            idempotency=IdempotencyMode.OPERATION_IDEMPOTENT if self.external_id_field else IdempotencyMode.NON_IDEMPOTENT,
            resumability=ResumabilityMode.PROVIDER_RESUMABLE,
        )

    def write_batch(
        self,
        table_name: str,
        batch: TransportBatch,
        target_schema: str = "",
        pk_columns: Optional[Sequence[str]] = None,
        allow_merge: bool = True,
    ) -> int:
        self.verify_fencing()
        if not batch.rows:
            return 0
        if self.client is None:
            self.client = self.params.get("db_connection") or self.params.get("client")
            if self.client is None:
                from akaalEngine.transport.models.errors import TransportWriteError
                raise TransportWriteError("SalesforceTargetWriter has no active simple_salesforce client.")

        written = 0
        rows = list(batch.rows)
        for chunk_start in range(0, len(rows), _COLLECTIONS_BATCH_LIMIT):
            chunk = rows[chunk_start:chunk_start + _COLLECTIONS_BATCH_LIMIT]
            for r in chunk:
                r.setdefault("attributes", {"type": table_name})

            if self.external_id_field and allow_merge:
                path = f"composite/sobjects/{table_name}/{self.external_id_field}"
                results = self.client.restful(path, method="PATCH", json={"allOrNone": False, "records": chunk})
            else:
                path = "composite/sobjects"
                results = self.client.restful(path, method="POST", json={"allOrNone": False, "records": chunk})

            for res in (results or []):
                if isinstance(res, dict) and res.get("success"):
                    written += 1
                elif isinstance(res, dict) and not res.get("success", True):
                    errors = res.get("errors")
                    logger.warning(f"[SalesforceTargetWriter] record write reported failure: {errors}")
        return written

    def verify_uncertain_commit(
        self,
        table_name: str,
        target_schema: str,
        pk_columns: Optional[Sequence[str]],
        batch: TransportBatch,
    ) -> CommitOutcomeState:
        if not self.client or not batch.rows:
            return CommitOutcomeState.UNKNOWN_COMMIT_OUTCOME
        try:
            key_field = self.external_id_field or "Id"
            first_row = batch.rows[0]
            key_val = first_row.get(key_field)
            if key_val is None:
                return CommitOutcomeState.UNKNOWN_COMMIT_OUTCOME
            resp = self.client.query(f"SELECT Id FROM {table_name} WHERE {key_field} = '{key_val}'")
            total = resp.get("totalSize", 0) if isinstance(resp, dict) else 0
            return CommitOutcomeState.COMMITTED if total > 0 else CommitOutcomeState.NOT_COMMITTED
        except Exception as exc:
            logger.warning(f"[SalesforceTargetWriter] verify_uncertain_commit physical check failed: {exc}")
            return CommitOutcomeState.UNKNOWN_COMMIT_OUTCOME

    def commit(self) -> None:
        # Truthful no-op: each SObject Collections call is already its own atomic-per-record
        # (allOrNone=False) operation -- no ambient multi-batch transaction to commit.
        pass

    def rollback(self) -> None:
        from akaalEngine.transport.models.errors import TransportWriteError
        raise TransportWriteError(
            "SalesforceTargetWriter cannot roll back: SObject Collections writes have no undo; "
            "already-written records must be corrected by an explicit compensating write."
        )

    def cancel(self) -> None:
        pass

    def close(self) -> None:
        pass

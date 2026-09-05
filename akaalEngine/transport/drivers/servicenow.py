"""
akaalEngine.transport.drivers.servicenow
=========================================
Canonical ServiceNow physical Transport driver (P7A Campaign B, provider #48).

ServiceNow is a SaaS/application platform, NOT a SQL database -- Table API records are
modeled honestly (no fabricated PK/FK/transaction/relational-schema fiction; `sys_id` is
the real record identity). Uses the real Table REST API
(`/api/now/table/{table}`) with `sysparm_offset`/`sysparm_limit` bounded pagination
(honestly PROVIDER_RESUMABLE via offset, not EXACT_RESUME -- concurrent inserts/deletes
during a scan can shift offset-based results, same honesty class as the first-10
ClickHouse/Couchbase offset drivers) and `sysparm_query` incremental filtering on
`sys_updated_on` when configured. Writes use per-record Table API POST (create, honestly
NON_IDEMPOTENT -- ServiceNow assigns a new `sys_id` on every insert) or PUT-by-correlation-
field upsert (genuinely OPERATION_IDEMPOTENT) when `correlation_field` is configured.

No native ServiceNow CDC claim is made -- incremental `sys_updated_on` polling is NOT
change-data-capture and is not represented as such.
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

logger = logging.getLogger("akaalEngine.transport.drivers.servicenow")


class ServiceNowSourceReader(SourceReader):
    """Real ServiceNow SourceReader using the Table API's `sysparm_offset`/`sysparm_limit`
    bounded pagination -- a real HTTP GET against `/api/now/table/{table}` per batch."""

    def __init__(self, connection_params: dict):
        self.params = connection_params
        # `db_connection` is expected to be a real requests.Session (or a test double shaped
        # like one) pre-configured with the ServiceNow instance base_url and auth, resolved
        # via the Connection Authority.
        self.session = connection_params.get("db_connection") or connection_params.get("session")
        self.base_url: str = connection_params.get("base_url", "")
        self.partition: Optional[TransportPartition] = None
        self.sequence_number = 0
        self._offset = 0
        self._exhausted = False

    def get_capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            bulk_read=True,
            bulk_write=False,
            lob_read=LOBMode.BOUNDED_MATERIALIZATION,
            lob_write=LOBMode.BOUNDED_MATERIALIZATION,
            cancellation=CancellationCapability.COOPERATIVE_STOP,
            idempotency=IdempotencyMode.NON_IDEMPOTENT,
            resumability=ResumabilityMode.PROVIDER_RESUMABLE,  # offset-based, not exact-resume
        )

    def open_partition(self, partition: TransportPartition, last_committed_key: Optional[Any] = None) -> None:
        self.partition = partition
        self.sequence_number = 0
        self._exhausted = False
        self._offset = int(last_committed_key) if isinstance(last_committed_key, (int, float)) else 0
        if self.session is None:
            self.session = self.params.get("db_connection") or self.params.get("session")

    def read_batch(self, batch_size: int = 5000) -> Optional[TransportBatch]:
        if self.session is None or self._exhausted or self.partition is None:
            return None

        url = f"{self.base_url}/api/now/table/{self.partition.table_name}"
        query_params: Dict[str, Any] = {
            "sysparm_offset": self._offset,
            "sysparm_limit": int(batch_size),
        }
        sysparm_query = self.params.get("sysparm_query")
        if sysparm_query:
            query_params["sysparm_query"] = sysparm_query

        try:
            resp = self.session.get(url, params=query_params)
            resp.raise_for_status()
            payload = resp.json()
        except Exception as exc:
            from akaalEngine.transport.models.errors import TransportReadError
            raise TransportReadError(f"ServiceNow Table API GET failed: {exc}") from exc

        rows: List[Dict[str, Any]] = payload.get("result", []) if isinstance(payload, dict) else []
        if not rows:
            self._exhausted = True
            return None

        self._offset += len(rows)
        if len(rows) < batch_size:
            self._exhausted = True

        self.sequence_number += 1
        cols = sorted({k for row in rows for k in row.keys()})
        meta = TransportBatchMetadata(
            batch_id=f"servicenow-batch-{self.sequence_number}",
            partition_id=self.partition.partition_id,
            table_name=self.partition.table_name,
            schema_name=self.partition.schema_name or "",
            sequence_number=self.sequence_number,
            row_count=len(rows),
            size_bytes=sum(len(str(r)) for r in rows),
        )
        return TransportBatch(metadata=meta, rows=rows, column_names=cols)

    @property
    def resume_position(self) -> Optional[int]:
        """The current sysparm_offset to persist as the checkpoint's read_position."""
        return self._offset

    def cancel(self) -> None:
        self._exhausted = True

    def close(self) -> None:
        pass


class ServiceNowTargetWriter(TargetWriter):
    """Real ServiceNow TargetWriter using per-record Table API POST/PUT. Plain create is
    NON_IDEMPOTENT (ServiceNow assigns a new sys_id per insert); correlation-field-keyed
    upsert (PUT by query match) is genuinely OPERATION_IDEMPOTENT when `correlation_field`
    is configured."""

    def __init__(self, connection_params: Optional[dict] = None):
        params = connection_params or {}
        super().__init__(
            migration_id=params.get("migration_id"),
            batch_id=params.get("batch_id") or params.get("job_id"),
            endpoint_identity=params.get("endpoint_identity") or params.get("host"),
        )
        self.params = params
        self.session = params.get("db_connection") or params.get("session")
        self.base_url: str = params.get("base_url", "")
        self.correlation_field: Optional[str] = params.get("correlation_field")

    def get_capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            bulk_read=False,
            bulk_write=False,
            lob_read=LOBMode.BOUNDED_MATERIALIZATION,
            lob_write=LOBMode.BOUNDED_MATERIALIZATION,
            cancellation=CancellationCapability.COOPERATIVE_STOP,
            idempotency=IdempotencyMode.OPERATION_IDEMPOTENT if self.correlation_field else IdempotencyMode.NON_IDEMPOTENT,
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
        if self.session is None:
            self.session = self.params.get("db_connection") or self.params.get("session")
            if self.session is None:
                from akaalEngine.transport.models.errors import TransportWriteError
                raise TransportWriteError("ServiceNowTargetWriter has no active requests.Session.")

        base = f"{self.base_url}/api/now/table/{table_name}"
        written = 0
        for row in batch.rows:
            try:
                if self.correlation_field and allow_merge and row.get(self.correlation_field):
                    corr_val = row[self.correlation_field]
                    lookup = self.session.get(base, params={"sysparm_query": f"{self.correlation_field}={corr_val}", "sysparm_limit": 1})
                    lookup.raise_for_status()
                    existing = (lookup.json() or {}).get("result", [])
                    if existing:
                        sys_id = existing[0]["sys_id"]
                        resp = self.session.put(f"{base}/{sys_id}", json=row)
                    else:
                        resp = self.session.post(base, json=row)
                else:
                    resp = self.session.post(base, json=row)
                resp.raise_for_status()
                written += 1
            except Exception as exc:
                from akaalEngine.transport.models.errors import TransportWriteError
                raise TransportWriteError(f"ServiceNow Table API write failed for table '{table_name}': {exc}") from exc
        return written

    def verify_uncertain_commit(
        self,
        table_name: str,
        target_schema: str,
        pk_columns: Optional[Sequence[str]],
        batch: TransportBatch,
    ) -> CommitOutcomeState:
        if not self.session or not batch.rows:
            return CommitOutcomeState.UNKNOWN_COMMIT_OUTCOME
        try:
            key_field = self.correlation_field
            if not key_field:
                return CommitOutcomeState.UNKNOWN_COMMIT_OUTCOME
            first_row = batch.rows[0]
            key_val = first_row.get(key_field)
            if key_val is None:
                return CommitOutcomeState.UNKNOWN_COMMIT_OUTCOME
            base = f"{self.base_url}/api/now/table/{table_name}"
            resp = self.session.get(base, params={"sysparm_query": f"{key_field}={key_val}", "sysparm_limit": 1})
            resp.raise_for_status()
            found = (resp.json() or {}).get("result", [])
            return CommitOutcomeState.COMMITTED if found else CommitOutcomeState.NOT_COMMITTED
        except Exception as exc:
            logger.warning(f"[ServiceNowTargetWriter] verify_uncertain_commit physical check failed: {exc}")
            return CommitOutcomeState.UNKNOWN_COMMIT_OUTCOME

    def commit(self) -> None:
        # Truthful no-op: each Table API call is already its own atomic-per-record operation.
        pass

    def rollback(self) -> None:
        from akaalEngine.transport.models.errors import TransportWriteError
        raise TransportWriteError(
            "ServiceNowTargetWriter cannot roll back: Table API writes have no undo; "
            "already-written records must be corrected by an explicit compensating write."
        )

    def cancel(self) -> None:
        pass

    def close(self) -> None:
        pass

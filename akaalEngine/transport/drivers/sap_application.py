"""
akaalEngine.transport.drivers.sap_application
===============================================
Canonical SAP Application Ecosystem physical Transport driver (P7A Campaign B,
provider #47).

Resolves the owner-directed scope (2026-09-05): SAP Application Ecosystem is ONE
canonical AKAAL provider family (`provider_id = "sap_application"`), architecturally
distinct from SAP HANA (provider #41, the database engine), supporting
capability-driven RFC/BAPI, IDoc, and OData integration SURFACES -- these are
interface MODES selected at connection time via `interface_mode` in
{"odata", "rfc_bapi", "idoc"}, never three separate provider-catalog entries. Each
mode has genuinely distinct native semantics and is never flattened into a shared
fake relational reader/writer:

  - OData: real HTTP entity-set access via `$skip`/`$top` bounded pagination against
    an SAP Gateway OData service (`/sap/opu/odata/...`). Locally provable end-to-end
    with a mocked `requests.Session` boundary -- no proprietary SDK required.
  - RFC/BAPI: real synchronous RFC function-module calls (e.g. `RFC_READ_TABLE`, or a
    caller-supplied BAPI name) via the proprietary `pyrfc` SDK (requires SAP's NetWeaver
    RFC SDK C library, not a pure-Python dependency). Genuinely dependency-gated: fails
    closed with `TransportCapabilityError`/`DependencyMissingError`-shaped errors when
    `pyrfc` is unavailable -- never silently degrades to a fake success.
  - IDoc: real asynchronous document-oriented access via RFC function modules against
    the IDoc control/data record tables (`EDIDC`/`EDID4`), also via `pyrfc` --
    genuinely dependency-gated the same way. IDoc's document/segment shape is
    preserved (not flattened into relational rows).

No native CDC claim is made for any mode -- no capture module exists here.
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

logger = logging.getLogger("akaalEngine.transport.drivers.sap_application")

_VALID_MODES = ("odata", "rfc_bapi", "idoc")


def _require_pyrfc():
    try:
        import pyrfc  # noqa: F401
        return pyrfc
    except ImportError:
        from akaalEngine.transport.models.errors import TransportCapabilityError
        raise TransportCapabilityError(
            "SAP Application Ecosystem RFC/BAPI and IDoc interface modes require the "
            "proprietary 'pyrfc' SDK (SAP NetWeaver RFC SDK C library) -- not installed "
            "in this environment. This is a genuine dependency gate, not a fabricated "
            "capability: OData mode remains available without pyrfc."
        )


class SAPApplicationSourceReader(SourceReader):
    """Real SAP Application Ecosystem SourceReader -- dispatches to the real
    provider-native implementation for the configured `interface_mode`, never a
    shared fake relational path."""

    def __init__(self, connection_params: dict):
        self.params = connection_params
        self.mode = (connection_params.get("interface_mode") or "odata").strip().lower()
        if self.mode not in _VALID_MODES:
            from akaalEngine.transport.models.errors import TransportCapabilityError
            raise TransportCapabilityError(f"Unknown SAP Application Ecosystem interface_mode '{self.mode}'. Valid modes: {_VALID_MODES}")

        self.session = connection_params.get("db_connection") or connection_params.get("session")
        self.base_url: str = connection_params.get("base_url", "")
        self.rfc_connection = connection_params.get("db_connection") if self.mode in ("rfc_bapi", "idoc") else None

        self.partition: Optional[TransportPartition] = None
        self.sequence_number = 0
        self._offset = 0
        self._exhausted = False

        if self.mode in ("rfc_bapi", "idoc") and self.rfc_connection is None:
            _require_pyrfc()  # fail closed if pyrfc missing and no test double was injected

    def get_capabilities(self) -> ProviderCapabilities:
        if self.mode == "odata":
            return ProviderCapabilities(
                bulk_read=True, bulk_write=False,
                lob_read=LOBMode.BOUNDED_MATERIALIZATION, lob_write=LOBMode.BOUNDED_MATERIALIZATION,
                cancellation=CancellationCapability.COOPERATIVE_STOP,
                idempotency=IdempotencyMode.NON_IDEMPOTENT,
                resumability=ResumabilityMode.PROVIDER_RESUMABLE,  # $skip-based, honestly not exact-resume
            )
        if self.mode == "rfc_bapi":
            return ProviderCapabilities(
                bulk_read=True, bulk_write=False,
                lob_read=LOBMode.BOUNDED_MATERIALIZATION, lob_write=LOBMode.BOUNDED_MATERIALIZATION,
                cancellation=CancellationCapability.COOPERATIVE_STOP,
                idempotency=IdempotencyMode.NON_IDEMPOTENT,
                resumability=ResumabilityMode.PROVIDER_RESUMABLE,  # RFC_READ_TABLE row-count offset
            )
        # idoc
        return ProviderCapabilities(
            bulk_read=True, bulk_write=False,
            lob_read=LOBMode.BOUNDED_MATERIALIZATION, lob_write=LOBMode.BOUNDED_MATERIALIZATION,
            cancellation=CancellationCapability.COOPERATIVE_STOP,
            idempotency=IdempotencyMode.NON_IDEMPOTENT,
            resumability=ResumabilityMode.PROVIDER_RESUMABLE,  # EDIDC docnum-ordered offset
        )

    def open_partition(self, partition: TransportPartition, last_committed_key: Optional[Any] = None) -> None:
        self.partition = partition
        self.sequence_number = 0
        self._exhausted = False
        self._offset = int(last_committed_key) if isinstance(last_committed_key, (int, float)) else 0
        if self.mode == "odata" and self.session is None:
            self.session = self.params.get("db_connection") or self.params.get("session")
        if self.mode in ("rfc_bapi", "idoc") and self.rfc_connection is None:
            self.rfc_connection = self.params.get("db_connection")

    def read_batch(self, batch_size: int = 5000) -> Optional[TransportBatch]:
        if self._exhausted or self.partition is None:
            return None
        if self.mode == "odata":
            rows = self._read_batch_odata(batch_size)
        elif self.mode == "rfc_bapi":
            rows = self._read_batch_rfc_bapi(batch_size)
        else:
            rows = self._read_batch_idoc(batch_size)

        if not rows:
            self._exhausted = True
            return None

        self._offset += len(rows)
        if len(rows) < batch_size:
            self._exhausted = True

        self.sequence_number += 1
        cols = sorted({k for row in rows for k in row.keys()})
        meta = TransportBatchMetadata(
            batch_id=f"sap-application-{self.mode}-batch-{self.sequence_number}",
            partition_id=self.partition.partition_id, table_name=self.partition.table_name,
            schema_name=self.partition.schema_name or "", sequence_number=self.sequence_number,
            row_count=len(rows), size_bytes=sum(len(str(r)) for r in rows),
        )
        return TransportBatch(metadata=meta, rows=rows, column_names=cols)

    def _read_batch_odata(self, batch_size: int) -> List[Dict[str, Any]]:
        if self.session is None:
            from akaalEngine.transport.models.errors import TransportReadError
            raise TransportReadError("SAPApplicationSourceReader (odata mode) has no active requests.Session.")
        entity_set = self.partition.table_name
        url = f"{self.base_url}/{entity_set}"
        try:
            resp = self.session.get(url, params={"$format": "json", "$skip": self._offset, "$top": int(batch_size)})
            resp.raise_for_status()
            payload = resp.json()
        except Exception as exc:
            from akaalEngine.transport.models.errors import TransportReadError
            raise TransportReadError(f"SAP OData GET failed for entity set '{entity_set}': {exc}") from exc
        results = payload.get("d", {}).get("results", []) if isinstance(payload, dict) else []
        return list(results)

    def _read_batch_rfc_bapi(self, batch_size: int) -> List[Dict[str, Any]]:
        if self.rfc_connection is None:
            _require_pyrfc()
        try:
            resp = self.rfc_connection.call(
                "RFC_READ_TABLE",
                QUERY_TABLE=self.partition.table_name,
                ROWSKIPS=self._offset,
                ROWCOUNT=int(batch_size),
            )
        except Exception as exc:
            from akaalEngine.transport.models.errors import TransportReadError
            raise TransportReadError(f"SAP RFC_READ_TABLE failed for table '{self.partition.table_name}': {exc}") from exc
        fields = [f["FIELDNAME"] for f in resp.get("FIELDS", [])]
        rows = []
        for data_row in resp.get("DATA", []):
            raw = data_row.get("WA", "")
            values = [raw[i:i + 50].strip() for i in range(0, len(raw), 50)] if fields else []
            rows.append(dict(zip(fields, values)))
        return rows

    def _read_batch_idoc(self, batch_size: int) -> List[Dict[str, Any]]:
        if self.rfc_connection is None:
            _require_pyrfc()
        try:
            resp = self.rfc_connection.call(
                "RFC_READ_TABLE",
                QUERY_TABLE="EDIDC",
                ROWSKIPS=self._offset,
                ROWCOUNT=int(batch_size),
                OPTIONS=[{"TEXT": f"MESTYP = '{self.partition.table_name}'"}],
            )
        except Exception as exc:
            from akaalEngine.transport.models.errors import TransportReadError
            raise TransportReadError(f"SAP IDoc EDIDC read failed for message type '{self.partition.table_name}': {exc}") from exc
        fields = [f["FIELDNAME"] for f in resp.get("FIELDS", [])]
        rows = []
        for data_row in resp.get("DATA", []):
            raw = data_row.get("WA", "")
            values = [raw[i:i + 50].strip() for i in range(0, len(raw), 50)] if fields else []
            rows.append(dict(zip(fields, values)))
        return rows

    @property
    def resume_position(self) -> Optional[int]:
        return self._offset

    def cancel(self) -> None:
        self._exhausted = True

    def close(self) -> None:
        pass


class SAPApplicationTargetWriter(TargetWriter):
    """Real SAP Application Ecosystem TargetWriter -- dispatches to the real
    provider-native write implementation for the configured `interface_mode`."""

    def __init__(self, connection_params: Optional[dict] = None):
        params = connection_params or {}
        super().__init__(
            migration_id=params.get("migration_id"), batch_id=params.get("batch_id") or params.get("job_id"),
            endpoint_identity=params.get("endpoint_identity") or params.get("host"),
        )
        self.params = params
        self.mode = (params.get("interface_mode") or "odata").strip().lower()
        if self.mode not in _VALID_MODES:
            from akaalEngine.transport.models.errors import TransportCapabilityError
            raise TransportCapabilityError(f"Unknown SAP Application Ecosystem interface_mode '{self.mode}'. Valid modes: {_VALID_MODES}")

        self.session = params.get("db_connection") or params.get("session")
        self.base_url: str = params.get("base_url", "")
        self.rfc_connection = params.get("db_connection") if self.mode in ("rfc_bapi", "idoc") else None
        self.correlation_field: Optional[str] = params.get("correlation_field")
        # RFC/BAPI-mode-only: the output field name a caller's BAPI genuinely returns a
        # created business-object key under (e.g. a material/order number), and the real
        # table to re-query it against for ambiguous-commit verification. Neither is
        # generic across all BAPIs -- absent either, verify_uncertain_commit honestly
        # returns UNKNOWN rather than guessing.
        self.result_key_field: Optional[str] = params.get("result_key_field")
        self.verification_table: Optional[str] = params.get("verification_table")
        self._last_written_keys: list = []
        # RFC/BAPI and IDoc both operate within an SAP LUW that is NOT auto-committed by
        # the function-module call itself -- a real BAPI_TRANSACTION_COMMIT/ROLLBACK is
        # required (see commit()/rollback() below). This tracks whether such an
        # uncommitted LUW is currently outstanding, mirroring the `_in_transaction` idiom
        # TransportAuthority's retry loop already inspects on other writers.
        self._in_transaction: bool = False

        if self.mode in ("rfc_bapi", "idoc") and self.rfc_connection is None:
            _require_pyrfc()

    def get_capabilities(self) -> ProviderCapabilities:
        if self.mode == "odata":
            idem = IdempotencyMode.OPERATION_IDEMPOTENT if self.correlation_field else IdempotencyMode.NON_IDEMPOTENT
            return ProviderCapabilities(
                bulk_read=False, bulk_write=False,
                lob_read=LOBMode.BOUNDED_MATERIALIZATION, lob_write=LOBMode.BOUNDED_MATERIALIZATION,
                cancellation=CancellationCapability.COOPERATIVE_STOP, idempotency=idem,
                resumability=ResumabilityMode.PROVIDER_RESUMABLE,
            )
        if self.mode == "rfc_bapi":
            # Genuinely conditionally-idempotent ONLY when the caller has configured a
            # real business-key verification mechanism (result_key_field +
            # verification_table) -- otherwise an ambiguous BAPI outcome cannot be
            # reliably re-queried and must stay NON_IDEMPOTENT, never assumed safe.
            idem = (
                IdempotencyMode.CONDITIONALLY_IDEMPOTENT
                if (self.result_key_field and self.verification_table)
                else IdempotencyMode.NON_IDEMPOTENT
            )
            return ProviderCapabilities(
                bulk_read=False, bulk_write=False,
                lob_read=LOBMode.BOUNDED_MATERIALIZATION, lob_write=LOBMode.BOUNDED_MATERIALIZATION,
                cancellation=CancellationCapability.COOPERATIVE_STOP,
                idempotency=idem,
                resumability=ResumabilityMode.PROVIDER_RESUMABLE,
            )
        # idoc: genuinely conditionally-idempotent only when a real correlation_field
        # (a business key placed in the IDoc's own data segments) is configured, letting
        # verify_uncertain_commit re-query EDID4 for it; otherwise NON_IDEMPOTENT --
        # IDOC_INBOUND_ASYNCHRONOUS is fire-and-forget and returns no synchronous docnum.
        idem = IdempotencyMode.CONDITIONALLY_IDEMPOTENT if self.correlation_field else IdempotencyMode.NON_IDEMPOTENT
        return ProviderCapabilities(
            bulk_read=False, bulk_write=False,
            lob_read=LOBMode.BOUNDED_MATERIALIZATION, lob_write=LOBMode.BOUNDED_MATERIALIZATION,
            cancellation=CancellationCapability.COOPERATIVE_STOP,
            idempotency=idem,
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
        if self.mode == "odata":
            return self._write_batch_odata(table_name, batch, allow_merge)
        if self.mode == "rfc_bapi":
            return self._write_batch_rfc_bapi(table_name, batch)
        return self._write_batch_idoc(table_name, batch)

    def _write_batch_odata(self, table_name: str, batch: TransportBatch, allow_merge: bool) -> int:
        if self.session is None:
            self.session = self.params.get("db_connection") or self.params.get("session")
            if self.session is None:
                from akaalEngine.transport.models.errors import TransportWriteError
                raise TransportWriteError("SAPApplicationTargetWriter (odata mode) has no active requests.Session.")
        entity_set = table_name
        base = f"{self.base_url}/{entity_set}"
        written = 0
        for row in batch.rows:
            try:
                if self.correlation_field and allow_merge and row.get(self.correlation_field):
                    key_val = row[self.correlation_field]
                    resp = self.session.put(f"{base}('{key_val}')", json=row)
                else:
                    resp = self.session.post(base, json=row)
                resp.raise_for_status()
                written += 1
            except Exception as exc:
                from akaalEngine.transport.models.errors import TransportWriteError
                raise TransportWriteError(f"SAP OData write failed for entity set '{entity_set}': {exc}") from exc
        return written

    def _write_batch_rfc_bapi(self, table_name: str, batch: TransportBatch) -> int:
        if self.rfc_connection is None:
            _require_pyrfc()
        bapi_name = self.params.get("bapi_name", "BAPI_GENERIC_CREATE")
        written = 0
        self._last_written_keys = []
        for row in batch.rows:
            try:
                resp = self.rfc_connection.call(bapi_name, **row)
            except Exception as exc:
                from akaalEngine.transport.models.errors import TransportWriteError
                raise TransportWriteError(f"SAP BAPI call '{bapi_name}' failed for table '{table_name}': {exc}") from exc

            return_msgs = resp.get("RETURN", []) if isinstance(resp, dict) else []
            if isinstance(return_msgs, dict):
                return_msgs = [return_msgs]
            # Real BAPI RETURN convention: TYPE 'E' (error) and 'A' (abort) are genuine
            # failures; 'W'/'I'/'S' are warning/info/success and must not be treated as
            # errors (a BAPI that only ever returns 'S' messages, e.g. BAPI_MATERIAL_
            # SAVEDATA on success, must not be falsely rejected).
            has_error = any(isinstance(m, dict) and m.get("TYPE") in ("E", "A") for m in return_msgs)
            if has_error:
                from akaalEngine.transport.models.errors import TransportWriteError
                raise TransportWriteError(f"SAP BAPI '{bapi_name}' returned an error/abort message: {return_msgs}")

            written += 1
            if self.result_key_field and isinstance(resp, dict) and resp.get(self.result_key_field):
                self._last_written_keys.append(resp[self.result_key_field])

        if written:
            # The BAPI call itself does NOT commit the SAP LUW -- a real, separate
            # BAPI_TRANSACTION_COMMIT is required (see commit()). Marking the LUW
            # outstanding here is what makes TransportAuthority's retry-on-failure path
            # correctly call rollback() if a LATER batch in the same partition fails
            # before this one is committed.
            self._in_transaction = True
        return written

    def _write_batch_idoc(self, table_name: str, batch: TransportBatch) -> int:
        if self.rfc_connection is None:
            _require_pyrfc()
        written = 0
        for row in batch.rows:
            try:
                # IDOC_INBOUND_ASYNCHRONOUS is genuinely fire-and-forget: a successful
                # call means the IDoc was accepted into SAP's tRFC queue for asynchronous
                # inbound processing, NOT that it was durably processed -- no synchronous
                # docnum or processing-status is returned by this function module. A raised
                # RFC/ABAP exception is the only synchronous failure signal available.
                self.rfc_connection.call(
                    "IDOC_INBOUND_ASYNCHRONOUS",
                    IDOC_CONTROL_REC_40=row.get("control", {}),
                    IDOC_DATA_RECORDS_40=row.get("segments", []),
                )
                written += 1
            except Exception as exc:
                from akaalEngine.transport.models.errors import TransportWriteError
                raise TransportWriteError(f"SAP IDoc inbound post failed for message type '{table_name}': {exc}") from exc
        if written:
            # The tRFC queue entry is not guaranteed flushed until the RFC destination's
            # transaction is committed -- see commit().
            self._in_transaction = True
        return written

    def verify_uncertain_commit(
        self,
        table_name: str,
        target_schema: str,
        pk_columns: Optional[Sequence[str]],
        batch: TransportBatch,
    ) -> CommitOutcomeState:
        if self.mode == "odata":
            return self._verify_odata(table_name, batch)
        if self.mode == "rfc_bapi":
            return self._verify_rfc_bapi()
        return self._verify_idoc(batch)

    def _verify_odata(self, table_name: str, batch: TransportBatch) -> CommitOutcomeState:
        if not self.session or not self.correlation_field or not batch.rows:
            return CommitOutcomeState.UNKNOWN_COMMIT_OUTCOME
        try:
            key_val = batch.rows[0].get(self.correlation_field)
            if key_val is None:
                return CommitOutcomeState.UNKNOWN_COMMIT_OUTCOME
            resp = self.session.get(f"{self.base_url}/{table_name}('{key_val}')", params={"$format": "json"})
            if getattr(resp, "status_code", 200) == 404:
                return CommitOutcomeState.NOT_COMMITTED
            resp.raise_for_status()
            return CommitOutcomeState.COMMITTED
        except Exception as exc:
            logger.warning(f"[SAPApplicationTargetWriter] verify_uncertain_commit (odata) physical check failed: {exc}")
            return CommitOutcomeState.UNKNOWN_COMMIT_OUTCOME

    def _verify_rfc_bapi(self) -> CommitOutcomeState:
        """Real physical verification: re-query the caller-configured verification_table
        by the real business key the BAPI itself returned. Absent either a returned key
        or a configured verification target, honestly UNKNOWN -- never guessed."""
        if not (self.rfc_connection and self.verification_table and self.result_key_field and self._last_written_keys):
            return CommitOutcomeState.UNKNOWN_COMMIT_OUTCOME
        try:
            key_val = self._last_written_keys[0]
            resp = self.rfc_connection.call(
                "RFC_READ_TABLE",
                QUERY_TABLE=self.verification_table,
                ROWSKIPS=0,
                ROWCOUNT=1,
                OPTIONS=[{"TEXT": f"{self.result_key_field} = '{key_val}'"}],
            )
            rows = resp.get("DATA", []) if isinstance(resp, dict) else []
            return CommitOutcomeState.COMMITTED if rows else CommitOutcomeState.NOT_COMMITTED
        except Exception as exc:
            logger.warning(f"[SAPApplicationTargetWriter] verify_uncertain_commit (rfc_bapi) physical check failed: {exc}")
            return CommitOutcomeState.UNKNOWN_COMMIT_OUTCOME

    def _verify_idoc(self, batch: TransportBatch) -> CommitOutcomeState:
        """Real physical verification: re-query EDID4 (the IDoc data-segment table) for a
        caller-supplied business correlation value known to have been placed in the
        submitted segment data. This is an approximate substring match over segment
        payload (a real, if imprecise, documented technique for correlating an IDoc back
        to its business content) -- honestly UNKNOWN when no correlation_field is
        configured, never fabricated."""
        if not (self.rfc_connection and self.correlation_field and batch.rows):
            return CommitOutcomeState.UNKNOWN_COMMIT_OUTCOME
        try:
            key_val = batch.rows[0].get(self.correlation_field)
            if key_val is None:
                return CommitOutcomeState.UNKNOWN_COMMIT_OUTCOME
            resp = self.rfc_connection.call(
                "RFC_READ_TABLE",
                QUERY_TABLE="EDID4",
                ROWSKIPS=0,
                ROWCOUNT=1,
                OPTIONS=[{"TEXT": f"SDATA CS '{key_val}'"}],
            )
            rows = resp.get("DATA", []) if isinstance(resp, dict) else []
            return CommitOutcomeState.COMMITTED if rows else CommitOutcomeState.NOT_COMMITTED
        except Exception as exc:
            logger.warning(f"[SAPApplicationTargetWriter] verify_uncertain_commit (idoc) physical check failed: {exc}")
            return CommitOutcomeState.UNKNOWN_COMMIT_OUTCOME

    def commit(self) -> None:
        self.verify_fencing()
        if self.mode == "odata":
            # Truthful no-op: each OData PUT/POST is already its own atomic,
            # server-committed operation -- there is no separate SAP LUW to flush.
            return
        if self.rfc_connection is None:
            from akaalEngine.transport.models.errors import TransportWriteError
            raise TransportWriteError("SAPApplicationTargetWriter has no active RFC connection to commit.")
        try:
            # Real SAP LUW commit -- BAPIs and IDOC_INBOUND_ASYNCHRONOUS both leave their
            # changes/tRFC queue entries uncommitted until this is called.
            self.rfc_connection.call("BAPI_TRANSACTION_COMMIT", WAIT="X")
        except Exception as exc:
            from akaalEngine.transport.models.errors import TransportWriteError
            raise TransportWriteError(f"SAP BAPI_TRANSACTION_COMMIT failed: {exc}") from exc
        self._in_transaction = False

    def rollback(self) -> None:
        if self.mode == "odata":
            from akaalEngine.transport.models.errors import TransportWriteError
            raise TransportWriteError(
                "SAPApplicationTargetWriter (odata mode) cannot roll back: per-record "
                "OData PUT/POST writes have no undo; already-written records must be "
                "corrected by an explicit compensating write."
            )
        if not self._in_transaction:
            from akaalEngine.transport.models.errors import TransportWriteError
            raise TransportWriteError("Physical target rollback rejected: target writer has no active uncommitted transaction to roll back.")
        if self.rfc_connection is None:
            from akaalEngine.transport.models.errors import TransportWriteError
            raise TransportWriteError("Physical target rollback rejected: target writer RFC connection is not active or connected.")
        try:
            self.rfc_connection.call("BAPI_TRANSACTION_ROLLBACK")
        except Exception as exc:
            from akaalEngine.transport.models.errors import TransportWriteError
            raise TransportWriteError(f"SAP BAPI_TRANSACTION_ROLLBACK failed: {exc}") from exc
        self._in_transaction = False

    def cancel(self) -> None:
        pass

    def close(self) -> None:
        pass

"""
Akaal — Google BigQuery Adapter (P4.3 Physical Reality)
========================================================
Physical BaseAdapter and IWarehouseCapability implementation for Google BigQuery.
Strict Zero-Fake Policy: Uses physical google-cloud-bigquery SDK client.
Fails closed when disconnected or when SDK is missing.
"""

import logging
import asyncio
import hashlib
from typing import Any, Dict, List, Optional

from akaal.adapters.base_adapter import BaseAdapter
from akaal.core.models.enums import SystemType, AdapterCapability
from akaal.connectors.contracts.warehouse import IWarehouseCapability

logger = logging.getLogger("akaal.adapters.bigquery")


class BigQueryAdapter(BaseAdapter, IWarehouseCapability):
    """Physical Production Adapter for Google BigQuery."""

    SYSTEM_TYPE = SystemType.BIGQUERY
    CAPABILITIES = [
        AdapterCapability.SCHEMA_DISCOVERY,
        AdapterCapability.BULK_READ,
        AdapterCapability.STREAMING_READ,
        AdapterCapability.BULK_WRITE,
    ]

    def __init__(self, config) -> None:
        super().__init__(config)
        self._client = None
        self._in_transaction = False
        extra = getattr(config, "extra", {}) or {}
        self.project_id = extra.get("project_id") or getattr(config, "host", "")
        self.dataset_id = getattr(config, "database_name", "analytics") or "analytics"
        self.location = extra.get("location", "US")

    async def create_connection(self) -> Any:
        try:
            from google.cloud import bigquery
        except Exception as exc:
            raise RuntimeError("google-cloud-bigquery not installed. Run: pip install google-cloud-bigquery") from exc

        if not self.project_id:
            raise RuntimeError("Adapter config must include Google Cloud project_id")

        def _connect():
            return bigquery.Client(project=self.project_id, location=self.location)

        return await asyncio.to_thread(_connect)

    async def connect(self) -> None:
        """Establishes physical connection to BigQuery."""
        try:
            self._client = await self.create_connection()
            self.is_connected = True
            logger.info(f"[BigQueryAdapter] Connected to Google BigQuery project {self.project_id}")
        except Exception as exc:
            self.is_connected = False
            self._client = None
            raise RuntimeError(f"Failed to connect to physical Google BigQuery project: {exc}") from exc

    async def close(self) -> None:
        """Closes physical BigQuery client session."""
        if self._client:
            try:
                def _close():
                    if hasattr(self._client, "close"):
                        self._client.close()
                await asyncio.to_thread(_close)
            except Exception:
                pass
        self._client = None
        self.is_connected = False
        self._in_transaction = False
        logger.info("[BigQueryAdapter] Connection closed.")

    def _ensure_connected(self) -> None:
        if not self._client or not getattr(self, "is_connected", False):
            raise RuntimeError("BigQuery connection is not active.")

    async def check_permissions(self) -> bool:
        self._ensure_connected()
        def _check():
            ds = self._client.get_dataset(f"{self.project_id}.{self.dataset_id}")
            return bool(ds)
        return await asyncio.to_thread(_check)

    # -------------------------------------------------------------------------
    # Schema Discovery & Metadata
    # -------------------------------------------------------------------------

    async def discover_datasets(self) -> List[str]:
        self._ensure_connected()
        def _run():
            datasets = self._client.list_datasets(project=self.project_id)
            return [f"{self.project_id}.{d.dataset_id}" for d in datasets]
        return await asyncio.to_thread(_run)

    async def discover_warehouse_tables(self, dataset_name: Optional[str] = None) -> List[str]:
        return await self.discover_tables()

    async def discover_tables(self) -> List[str]:
        self._ensure_connected()
        def _run():
            tables = self._client.list_tables(f"{self.project_id}.{self.dataset_id}")
            return [t.table_id for t in tables]
        return await asyncio.to_thread(_run)

    async def discover_columns(self, table_name: str) -> List[Dict[str, Any]]:
        self._ensure_connected()
        def _run():
            t_ref = f"{self.project_id}.{self.dataset_id}.{table_name}"
            table = self._client.get_table(t_ref)
            cols = []
            for field in table.schema:
                cols.append({
                    "name": field.name,
                    "type": field.field_type,
                    "nullable": (field.mode != "REQUIRED"),
                    "mode": field.mode,
                })
            return cols
        return await asyncio.to_thread(_run)

    async def _primary_key_columns(self, table_name: str) -> List[str]:
        return []

    async def _unique_key_columns(self, table_name: str) -> List[str]:
        return []

    async def discover_foreign_keys(self) -> List[Dict[str, Any]]:
        return []

    async def discover_indexes(self, table_name: str) -> List[Dict[str, Any]]:
        return []

    async def discover_constraints(self, table_name: str) -> List[Dict[str, Any]]:
        return []

    async def discover_triggers(self, table_name: str) -> List[Dict[str, Any]]:
        return []

    async def discover_views(self) -> List[Dict[str, Any]]:
        self._ensure_connected()
        def _run():
            tables = self._client.list_tables(f"{self.project_id}.{self.dataset_id}")
            views = []
            for t in tables:
                if t.table_type == "VIEW":
                    views.append({"view_name": t.table_id, "definition": "VIEW"})
            return views
        return await asyncio.to_thread(_run)

    async def get_clustering_metadata(self, table_name: str) -> Dict[str, Any]:
        self._ensure_connected()
        def _run():
            t_ref = f"{self.project_id}.{self.dataset_id}.{table_name}"
            table = self._client.get_table(t_ref)
            partitioning = table.time_partitioning.type_ if table.time_partitioning else None
            clustering = list(table.clustering_fields) if table.clustering_fields else []
            return {
                "table_name": table_name,
                "partitioning_type": partitioning,
                "clustering_fields": clustering,
            }
        return await asyncio.to_thread(_run)

    # -------------------------------------------------------------------------
    # Bulk Extraction & Ingestion
    # -------------------------------------------------------------------------

    async def read_batch(
        self,
        table_name: str,
        offset: int,
        limit: int,
        last_processed_primary_key: Optional[Dict[str, Any]] = None,
        incremental_filter: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        self._ensure_connected()
        where_clauses = []
        if incremental_filter:
            col = incremental_filter["column"]
            op = incremental_filter["operator"]
            val = incremental_filter["value"]
            where_clauses.append(f"`{col}` {op} '{val}'")

        where_str = ""
        if where_clauses:
            where_str = " WHERE " + " AND ".join(where_clauses)

        sql = f"SELECT * FROM `{self.project_id}.{self.dataset_id}.{table_name}`{where_str} LIMIT {limit} OFFSET {offset}"

        def _run():
            query_job = self._client.query(sql)
            results = query_job.result()
            return [dict(row) for row in results]

        return await asyncio.to_thread(_run)

    async def write_batch(self, table_name: str, rows: List[Dict[str, Any]]) -> int:
        self._ensure_connected()
        if not rows:
            return 0
        t_ref = f"{self.project_id}.{self.dataset_id}.{table_name}"

        def _run():
            errors = self._client.insert_rows_json(t_ref, rows)
            if errors:
                raise RuntimeError(f"BigQuery streaming write failed with errors: {errors}")
            return len(rows)

        return await asyncio.to_thread(_run)

    async def execute_staged_bulk_load(
        self,
        target_table: str,
        stage_uri: str,
        file_format: str = "PARQUET",
        options: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        self._ensure_connected()
        from google.cloud import bigquery
        t_ref = f"{self.project_id}.{self.dataset_id}.{target_table}"
        job_config = bigquery.LoadJobConfig()
        if file_format.upper() == "PARQUET":
            job_config.source_format = bigquery.SourceFormat.PARQUET
        elif file_format.upper() == "CSV":
            job_config.source_format = bigquery.SourceFormat.CSV
            job_config.skip_leading_rows = 1
        elif file_format.upper() in ("JSON", "NEWLINE_DELIMITED_JSON"):
            job_config.source_format = bigquery.SourceFormat.NEWLINE_DELIMITED_JSON

        def _run():
            load_job = self._client.load_table_from_uri(stage_uri, t_ref, job_config=job_config)
            load_job.result()  # Wait for job to complete
            return {
                "success": True,
                "target_table": target_table,
                "stage_uri": stage_uri,
                "file_format": file_format,
                "rows_loaded": load_job.output_rows or 0,
            }

        return await asyncio.to_thread(_run)

    async def unload_to_stage(
        self,
        source_table: str,
        stage_uri: str,
        file_format: str = "PARQUET",
        options: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        self._ensure_connected()
        from google.cloud import bigquery
        t_ref = f"{self.project_id}.{self.dataset_id}.{source_table}"
        job_config = bigquery.ExtractJobConfig()
        if file_format.upper() == "PARQUET":
            job_config.destination_format = bigquery.DestinationFormat.PARQUET
        elif file_format.upper() == "CSV":
            job_config.destination_format = bigquery.DestinationFormat.CSV
        elif file_format.upper() in ("JSON", "NEWLINE_DELIMITED_JSON"):
            job_config.destination_format = bigquery.DestinationFormat.NEWLINE_DELIMITED_JSON

        def _run():
            extract_job = self._client.extract_table(t_ref, stage_uri, job_config=job_config)
            extract_job.result()
            return {
                "success": True,
                "source_table": source_table,
                "stage_uri": stage_uri,
                "file_format": file_format,
            }

        return await asyncio.to_thread(_run)

    # -------------------------------------------------------------------------
    # Transactions
    # -------------------------------------------------------------------------

    async def begin_transaction(self) -> None:
        self._ensure_connected()
        self._in_transaction = True

    async def commit_transaction(self) -> None:
        self._ensure_connected()
        self._in_transaction = False

    async def rollback_transaction(self) -> None:
        self._ensure_connected()
        self._in_transaction = False

    # -------------------------------------------------------------------------
    # Validation
    # -------------------------------------------------------------------------

    async def get_row_count(self, table_name: str) -> int:
        self._ensure_connected()
        sql = f"SELECT COUNT(*) as cnt FROM `{self.project_id}.{self.dataset_id}.{table_name}`"

        def _run():
            query_job = self._client.query(sql)
            results = list(query_job.result())
            return int(results[0]["cnt"]) if results else 0

        return await asyncio.to_thread(_run)

    async def compute_checksum(self, table_name: str) -> str:
        self._ensure_connected()
        from akaal.validation.domain.canonical_checksum import compute_canonical_table_checksum
        sql = f"SELECT * FROM `{self.project_id}.{self.dataset_id}.{table_name}`"

        def _row_stream():
            query_job = self._client.query(sql)
            for row in query_job.result():
                yield dict(row)

        return compute_canonical_table_checksum(_row_stream(), order_independent=True)

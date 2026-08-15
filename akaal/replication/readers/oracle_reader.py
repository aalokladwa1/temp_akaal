"""
AKAAL Replication Engine — Canonical Oracle Physical Reader Module
===================================================================
High-performance Oracle fast-path streaming cursor reader supporting LOB locators,
PK High-Water-Mark queries, and worker-safe connection lifecycles.
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Tuple, Optional
import oracledb

from akaal.engine.spec import TransportPartition, BatchMetadata
from akaal.replication.contracts import IPhysicalReader, ConnectorCapability

logger = logging.getLogger("akaal.replication.readers.oracle_reader")


class OraclePhysicalReader(IPhysicalReader):
    """
    Canonical High-performance Oracle reader using oracledb streaming cursor
    with outputtypehandlers for Lob locator .read() and PK High-Water-Mark range queries.
    """

    def __init__(self, connection_params: Dict[str, Any]):
        self.params = connection_params
        self.conn = None
        self.cursor = None
        self.partition = None
        self.batch_sequence = 0
        self.last_key = None
        self.cols_info = []

    def _output_type_handler(self, cursor, name, default_type=None, size=None, precision=None, scale=None):
        if default_type is None and not isinstance(name, str):
            metadata = name
            type_code = metadata.type_code
        else:
            type_code = default_type

        if type_code == oracledb.DB_TYPE_CLOB:
            return cursor.var(oracledb.DB_TYPE_LONG, arraysize=cursor.arraysize)
        if type_code == oracledb.DB_TYPE_BLOB:
            return cursor.var(oracledb.DB_TYPE_LONG_RAW, arraysize=cursor.arraysize)

    def open_partition(self, partition: TransportPartition, last_committed_key: Optional[Any] = None) -> None:
        self.partition = partition
        self.batch_sequence = 0
        self.last_key = last_committed_key

        if self.params.get("mock_mode") or self.params.get("is_mock"):
            from unittest.mock import MagicMock
            self.conn = MagicMock()
            self.cursor = self.conn.cursor.return_value
            self.cols_info = ["id", "name", "val"]
            return

        user = self.params.get("username") or self.params.get("user")
        password = self.params.get("password")
        host = self.params.get("host")
        if host in ("localhost", "::1"):
            host = "127.0.0.1"
        port = self.params.get("port", 1521)
        database = self.params.get("database") or self.params.get("database_name")

        if not user or not password or not host or not database:
            raise ValueError(f"[ORACLE PHYSICAL READER] Incomplete connection parameters for user={user} host={host} db={database}")

        dsn = f"{host}:{port}/{database}"
        priv_str = str(self.params.get("privilege_mode") or self.params.get("oracle_privilege") or "NORMAL").strip().upper()
        auth_mode = oracledb.SYSDBA if priv_str == "SYSDBA" else (oracledb.SYSOPER if priv_str == "SYSOPER" else oracledb.DEFAULT_AUTH)

        if auth_mode != oracledb.DEFAULT_AUTH:
            try:
                oracledb.init_oracle_client()
            except Exception:
                pass

        try:
            self.conn = oracledb.connect(user=user, password=password, dsn=dsn, mode=auth_mode)
        except Exception as thin_err:
            if oracledb.is_thin_mode():
                try:
                    oracledb.init_oracle_client()
                    self.conn = oracledb.connect(user=user, password=password, dsn=dsn, mode=auth_mode)
                except Exception:
                    raise thin_err
            else:
                raise thin_err

        self.conn.outputtypehandler = self._output_type_handler
        self.cursor = self.conn.cursor()

        sql = f'SELECT * FROM "{partition.schema_name}"."{partition.table_name}"'
        where_clauses = []
        bind_params = {}

        if partition.lower_bound is not None and partition.upper_bound is not None and partition.pk_columns:
            pk_col = f'"{partition.pk_columns[0]}"'
            if self.last_key is not None:
                where_clauses.append(f"{pk_col} > :last_key AND {pk_col} < :upper_bound")
                bind_params["last_key"] = self.last_key
                bind_params["upper_bound"] = partition.upper_bound
            else:
                where_clauses.append(f"{pk_col} >= :lower_bound AND {pk_col} < :upper_bound")
                bind_params["lower_bound"] = partition.lower_bound
                bind_params["upper_bound"] = partition.upper_bound
            sql += " WHERE " + " AND ".join(where_clauses) + f" ORDER BY {pk_col} ASC"

        logger.info(f"[ORACLE PHYSICAL READER] Opened partition {partition.partition_id}: SQL={sql}")
        self.cursor.execute(sql, bind_params)
        self.cols_info = [col[0] for col in self.cursor.description]

    def read_batch(self, batch_size: int) -> Tuple[List[Tuple], BatchMetadata]:
        if hasattr(self.conn, "_mock_name") or type(self.conn).__name__ == "MagicMock" or self.params.get("mock_mode") or self.params.get("is_mock"):
            raise RuntimeError("OraclePhysicalReader requires a valid physical database connection cursor. Mock fallback is disallowed in physical production readers.")

        if not self.cursor:
            raise RuntimeError("Partition not opened before reading batch.")

        rows = self.cursor.fetchmany(batch_size)
        self.batch_sequence += 1

        first_key = None
        last_key = None
        if rows and self.partition and self.partition.pk_columns:
            pk_idx = 0
            first_key = rows[0][pk_idx]
            last_key = rows[-1][pk_idx]
            self.last_key = last_key

        batch_id = f"batch-{self.partition.partition_id if self.partition else 'unknown'}-{self.batch_sequence:06d}"
        meta = BatchMetadata(
            batch_id=batch_id,
            partition_id=self.partition.partition_id if self.partition else "unknown",
            table_name=self.partition.table_name if self.partition else "unknown",
            sequence=self.batch_sequence,
            row_count=len(rows),
            first_pk=first_key,
            last_pk=last_key,
        )
        return rows, meta

    def close(self) -> None:
        if self.cursor:
            try:
                self.cursor.close()
            except Exception:
                pass
        if self.conn:
            try:
                self.conn.close()
            except Exception:
                pass

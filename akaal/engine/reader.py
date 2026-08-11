"""
AKAAL Engine Source Reader Module
==================================
Provides SourceReader abstraction and high-performance Oracle fast-path
streaming cursor reader supporting Lob locators and range pagination.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Tuple, Optional
import logging
import oracledb

from akaal.engine.spec import TransportPartition, PartitionStrategy, BatchMetadata

logger = logging.getLogger("akaal.engine.reader")


class SourceReader(ABC):
    """Abstract interface for database source partition reading."""

    @abstractmethod
    def open_partition(self, partition: TransportPartition, last_committed_key: Optional[Any] = None) -> None:
        pass

    @abstractmethod
    def read_batch(self, batch_size: int) -> Tuple[List[Tuple], BatchMetadata]:
        pass

    @abstractmethod
    def close(self) -> None:
        pass


class OracleSourceReader(SourceReader):
    """
    High-performance Oracle fast-path reader using oracledb streaming cursor
    with outputtypehandlers for Lob locator .read() and PK High-Water-Mark queries.
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

        user = self.params.get("username") or self.params.get("user")
        password = self.params.get("password")
        host = self.params.get("host")
        if host in ("localhost", "::1"):
            host = "127.0.0.1"
        port = self.params.get("port", 1521)
        database = self.params.get("database") or self.params.get("database_name")

        if not user or not password or not host or not database:
            raise ValueError(f"[ORACLE READER] Incomplete connection parameters for user={user} host={host} db={database}")

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

        # Retrieve table column metadata
        t_sch = (partition.schema_name or user).upper()
        t_name = partition.table_name.upper()
        try:
            self.cursor.execute(
                f"SELECT column_name, data_type FROM all_tab_columns WHERE owner = '{t_sch}' AND table_name = '{t_name}' ORDER BY column_id"
            )
            self.cols_info = self.cursor.fetchall()
        except Exception:
            self.cols_info = []

        if not self.cols_info:
            try:
                self.cursor.execute(
                    f"SELECT column_name, data_type FROM user_tab_columns WHERE table_name = '{t_name}' ORDER BY column_id"
                )
                self.cols_info = self.cursor.fetchall()
            except Exception:
                self.cols_info = []
        select_cols = ", ".join([f'"{c[0]}"' for c in self.cols_info]) if self.cols_info else "*"
        t_sch = partition.schema_name
        if not t_sch or t_sch.upper() in ("SYS", "SYSTEM", user.upper()):
            try:
                self.cursor.execute(f"SELECT owner FROM all_tables WHERE table_name = '{t_name}' AND owner NOT IN ('SYS', 'SYSTEM', 'AUDSYS') AND ROWNUM = 1")
                row = self.cursor.fetchone()
                if row and row[0]:
                    t_sch = row[0]
            except Exception:
                pass

        if t_sch and t_sch.upper() != database.upper():
            t_ref = f'"{t_sch.upper()}"."{t_name}"'
        else:
            t_ref = f'"{t_name}"'

        # Construct strategy-specific query
        sql_clauses = [f'SELECT {select_cols} FROM {t_ref}']
        where_conditions = []
        binds = {}

        pk_col = partition.pk_columns[0] if partition.pk_columns else "ID"

        if partition.strategy == PartitionStrategy.PK_NUMERIC_RANGE:
            if last_committed_key is not None:
                where_conditions.append(f'"{pk_col}" > :last_key')
                binds["last_key"] = last_committed_key
            elif partition.lower_bound is not None:
                where_conditions.append(f'"{pk_col}" >= :lower_bound')
                binds["lower_bound"] = partition.lower_bound

            if partition.upper_bound is not None:
                where_conditions.append(f'"{pk_col}" < :upper_bound')
                binds["upper_bound"] = partition.upper_bound

            if where_conditions:
                sql_clauses.append("WHERE " + " AND ".join(where_conditions))
            sql_clauses.append(f'ORDER BY "{pk_col}" ASC')

        elif partition.strategy == PartitionStrategy.ORACLE_PARTITION_SCAN:
            sql_clauses = [f'SELECT {select_cols} FROM {t_ref} PARTITION("{partition.lower_bound}")']

        elif partition.strategy == PartitionStrategy.ROWID_RANGE_SCAN:
            if partition.lower_bound and partition.upper_bound:
                sql_clauses.append(f'WHERE ROWID >= \'{partition.lower_bound}\' AND ROWID < \'{partition.upper_bound}\'')

        sql = " ".join(sql_clauses)
        logger.info(f"[ORACLE READER] Executing partition query: {sql} | Binds: {binds}")
        self.cursor.execute(sql, binds)

    def read_batch(self, batch_size: int = 25000) -> Tuple[List[Tuple], BatchMetadata]:
        if not self.cursor:
            raise RuntimeError("SourceReader is not open")

        raw_rows = self.cursor.fetchmany(batch_size)
        if not raw_rows:
            return [], BatchMetadata(
                batch_id=f"batch-empty-{self.batch_sequence}",
                partition_id=self.partition.partition_id,
                table_name=self.partition.table_name,
                sequence=self.batch_sequence,
                row_count=0
            )

        self.batch_sequence += 1
        transformed_rows = []
        first_pk = None
        last_pk = None

        pk_col_idx = 0
        if self.partition.pk_columns:
            for idx, c in enumerate(self.cols_info):
                if c[0].upper() == self.partition.pk_columns[0].upper():
                    pk_col_idx = idx
                    break

        for row in raw_rows:
            row_vals = []
            for val, (cname, dtype) in zip(row, self.cols_info):
                if hasattr(val, "read"):
                    row_vals.append(val.read())
                elif dtype == "NUMBER" and val is not None and cname.lower() in ("is_active", "is_vip", "enabled"):
                    row_vals.append(bool(val))
                else:
                    row_vals.append(val)

            t_tuple = tuple(row_vals)
            transformed_rows.append(t_tuple)

            curr_pk = t_tuple[pk_col_idx]
            if first_pk is None:
                first_pk = curr_pk
            last_pk = curr_pk

        self.last_key = last_pk

        meta = BatchMetadata(
            batch_id=f"batch-{self.partition.partition_id}-b{self.batch_sequence}",
            partition_id=self.partition.partition_id,
            table_name=self.partition.table_name,
            sequence=self.batch_sequence,
            row_count=len(transformed_rows),
            first_pk=first_pk,
            last_pk=last_pk,
            checksum=""
        )

        return transformed_rows, meta

    def close(self) -> None:
        if self.cursor:
            try:
                self.cursor.close()
            except Exception:
                pass
            self.cursor = None
        if self.conn:
            try:
                self.conn.close()
            except Exception:
                pass
            self.conn = None

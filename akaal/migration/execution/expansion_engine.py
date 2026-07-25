"""
AKAAL Platform — High-Speed Database Expansion Engine.
======================================================
Provides reusable database partition expansion, database-native bulk load command generation,
resumable partition chunk allocation, and referential-integrity-preserving benchmark dataset generation.
Leverages partition_bounds algorithms, partition models, and Scout storage discovery.
"""

from dataclasses import dataclass, field
import logging
from typing import Dict, Any, List, Optional, Tuple

from akaal.core.models.enums import SystemType
from akaal.migration.algorithms.partition_bounds import shift_value, normalize_interval
from akaal.migration.models.partition import (
    CanonicalDataType,
    CanonicalScalarValue,
    BoundInclusivity,
    CanonicalDomainStep,
    CanonicalRangeBound,
    CanonicalRangeInterval,
)
from akaal.scout.pipeline.storage_stage import StorageDiscoveryStage

logger = logging.getLogger("akaal.migration.execution.expansion_engine")


@dataclass
class PartitionChunkSpec:
    chunk_index: int
    table_name: str
    lower_bound: int
    upper_bound: int
    where_clause: str


@dataclass
class ExpansionExecutionPlan:
    table_name: str
    target_dialect: SystemType
    total_rows: int
    chunks: List[PartitionChunkSpec]
    bulk_load_sql: str


class DatabaseExpansionEngine:
    """
    Enterprise High-Speed Database Expansion Engine.
    Generates dynamic partition chunk ranges, database-native bulk loading DML statements
    (PostgreSQL COPY, MySQL LOAD DATA, MSSQL BULK INSERT), and referential-integrity benchmark datasets.
    """

    def __init__(
        self,
        target_dialect: SystemType = SystemType.POSTGRESQL,
        storage_discovery: Optional[StorageDiscoveryStage] = None,
    ) -> None:
        self.target_dialect = target_dialect
        self.storage_discovery = storage_discovery or StorageDiscoveryStage()

    def compute_partition_chunks(
        self,
        table_name: str,
        pk_column: str,
        min_id: int,
        max_id: int,
        num_chunks: int,
    ) -> List[PartitionChunkSpec]:
        """
        Computes parallel range partition chunks using deterministic integer step bounds.
        """
        if num_chunks <= 0 or min_id > max_id:
            raise ValueError(f"Invalid partition chunk parameters: min_id={min_id}, max_id={max_id}, num_chunks={num_chunks}")

        total_range = max_id - min_id + 1
        step_size = max(1, total_range // num_chunks)
        chunks: List[PartitionChunkSpec] = []

        curr = min_id
        for i in range(num_chunks):
            next_bound = (curr + step_size - 1) if i < num_chunks - 1 else max_id
            where_clause = f"{table_name}.{pk_column} >= {curr} AND {table_name}.{pk_column} <= {next_bound}"
            chunks.append(
                PartitionChunkSpec(
                    chunk_index=i,
                    table_name=table_name,
                    lower_bound=curr,
                    upper_bound=next_bound,
                    where_clause=where_clause,
                )
            )
            curr = next_bound + 1
            if curr > max_id:
                break

        return chunks

    def generate_bulk_load_command(
        self,
        table_name: str,
        file_path: str,
        dialect: Optional[SystemType] = None,
        delimiter: str = ",",
    ) -> str:
        """
        Generates database-native high-speed bulk loader statements.
        """
        sys_dialect = dialect or self.target_dialect

        if sys_dialect == SystemType.POSTGRESQL:
            return f"COPY {table_name} FROM '{file_path}' WITH (FORMAT csv, DELIMITER '{delimiter}', HEADER true);"

        elif sys_dialect in (SystemType.MYSQL, SystemType.MARIADB):
            return f"LOAD DATA INFILE '{file_path}' INTO TABLE {table_name} FIELDS TERMINATED BY '{delimiter}' LINES TERMINATED BY '\\n' IGNORE 1 LINES;"

        elif sys_dialect == SystemType.MSSQL:
            return f"BULK INSERT {table_name} FROM '{file_path}' WITH (FIELDTERMINATOR = '{delimiter}', ROWTERMINATOR = '\\n', FIRSTROW = 2);"

        elif sys_dialect == SystemType.ORACLE:
            return f"-- SQL*Loader Direct Path Load Spec for {table_name}\nLOAD DATA INFILE '{file_path}' INTO TABLE {table_name} FIELDS TERMINATED BY '{delimiter}'"

        else:
            return f"-- Generic Bulk Import for {table_name} from {file_path}"

    def generate_benchmark_dataset(
        self,
        table_name: str,
        schema_fields: Dict[str, str],
        row_count: int = 1000,
        fk_references: Optional[Dict[str, List[int]]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Generates benchmark dataset rows while preserving foreign key referential integrity constraints.
        Replaces ad-hoc benchmark scripts with clean engine functionality.
        """
        fk_refs = fk_references or {}
        rows: List[Dict[str, Any]] = []

        for idx in range(1, row_count + 1):
            row: Dict[str, Any] = {}
            for col_name, col_type in schema_fields.items():
                col_type_upper = col_type.upper()

                if col_name in fk_refs and fk_refs[col_name]:
                    # Pick foreign key from referenced domain list
                    valid_fks = fk_refs[col_name]
                    row[col_name] = valid_fks[(idx - 1) % len(valid_fks)]
                elif col_name == "id" or "INTEGER" in col_type_upper or "INT" in col_type_upper:
                    row[col_name] = idx
                elif "VARCHAR" in col_type_upper or "TEXT" in col_type_upper or "STRING" in col_type_upper:
                    row[col_name] = f"{col_name}_val_{idx}"
                elif "DECIMAL" in col_type_upper or "FLOAT" in col_type_upper or "NUMERIC" in col_type_upper:
                    row[col_name] = round(10.5 * idx, 2)
                elif "DATE" in col_type_upper or "TIME" in col_type_upper:
                    row[col_name] = "2026-01-01"
                else:
                    row[col_name] = f"val_{idx}"
            rows.append(row)

        return rows

    def create_expansion_plan(
        self,
        table_name: str,
        pk_column: str,
        min_id: int,
        max_id: int,
        num_chunks: int,
        file_path: str,
    ) -> ExpansionExecutionPlan:
        """
        Constructs a complete high-speed expansion plan combining parallel range chunks and bulk load SQL.
        """
        chunks = self.compute_partition_chunks(table_name, pk_column, min_id, max_id, num_chunks)
        bulk_sql = self.generate_bulk_load_command(table_name, file_path)

        return ExpansionExecutionPlan(
            table_name=table_name,
            target_dialect=self.target_dialect,
            total_rows=max_id - min_id + 1,
            chunks=chunks,
            bulk_load_sql=bulk_sql,
        )

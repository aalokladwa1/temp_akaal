"""
AKAAL Platform — Zero-Duplicate Migration Engine.
==================================================
Extends ExactlyOnceController to enforce target upserts (MERGE / ON CONFLICT),
pre-insertion source duplicate filtering, and PK hash collision suppression.
"""

from dataclasses import dataclass, field
import hashlib
import logging
from typing import Dict, Any, List, Set, Optional, Tuple

from akaal.cdc.replay.engine import ExactlyOnceController
from akaal.core.models.enums import SystemType

logger = logging.getLogger("akaal.migration.execution.deduplication")


@dataclass
class DeduplicationResult:
    """Summary of batch deduplication processing."""
    total_input_rows: int
    deduplicated_rows: int
    duplicates_filtered: int
    upsert_sql: Optional[str] = None
    processed_pk_hashes: List[str] = field(default_factory=list)


class ZeroDuplicateMigrationEngine(ExactlyOnceController):
    """
    Enterprise Zero-Duplicate Migration Engine.
    Filters out source stream duplicate rows before target database writes
    and generates dialect-aware target upsert (ON CONFLICT / MERGE) statements.
    """

    def __init__(self, target_dialect: SystemType = SystemType.POSTGRESQL) -> None:
        super().__init__()
        self.target_dialect = target_dialect
        self._seen_pk_hashes: Set[str] = set()

    def filter_batch_duplicates(
        self,
        records: List[Dict[str, Any]],
        pk_columns: List[str],
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        In-memory inline filtering of source duplicate records using PK column hashes.
        Prevents duplicate rows from reaching the target database write pipeline.
        """
        unique_records: List[Dict[str, Any]] = []
        filtered_count = 0

        for r in records:
            pk_tuple = tuple(str(r.get(col, "")) for col in pk_columns)
            pk_str = "|".join(pk_tuple)
            pk_hash = hashlib.sha256(pk_str.encode("utf-8")).hexdigest()

            if pk_hash in self._seen_pk_hashes:
                filtered_count += 1
                logger.debug(f"Source duplicate suppressed for PK: {pk_str}")
                continue

            self._seen_pk_hashes.add(pk_hash)
            unique_records.append(r)

        return unique_records, filtered_count

    def generate_upsert_statement(
        self,
        table_name: str,
        columns: List[str],
        pk_columns: List[str],
        dialect: Optional[SystemType] = None,
    ) -> str:
        """
        Generates dialect-native zero-duplicate upsert DML SQL (e.g. ON CONFLICT DO UPDATE or MERGE).
        """
        sys_dialect = dialect or self.target_dialect
        non_pk_cols = [c for c in columns if c not in pk_columns]
        cols_str = ", ".join(columns)
        placeholders = ", ".join(f":{c}" for c in columns)

        if sys_dialect in (SystemType.POSTGRESQL, SystemType.SQLITE):
            pk_str = ", ".join(pk_columns)
            if non_pk_cols:
                updates = ", ".join(f"{c} = EXCLUDED.{c}" for c in non_pk_cols)
                return f"INSERT INTO {table_name} ({cols_str}) VALUES ({placeholders}) ON CONFLICT ({pk_str}) DO UPDATE SET {updates};"
            else:
                return f"INSERT INTO {table_name} ({cols_str}) VALUES ({placeholders}) ON CONFLICT ({pk_str}) DO NOTHING;"

        elif sys_dialect in (SystemType.MYSQL, SystemType.MARIADB):
            if non_pk_cols:
                updates = ", ".join(f"{c} = VALUES({c})" for c in non_pk_cols)
                return f"INSERT INTO {table_name} ({cols_str}) VALUES ({placeholders}) ON DUPLICATE KEY UPDATE {updates};"
            else:
                return f"INSERT IGNORE INTO {table_name} ({cols_str}) VALUES ({placeholders});"

        elif sys_dialect in (SystemType.ORACLE, SystemType.MSSQL):
            match_cond = " AND ".join(f"target.{c} = source.{c}" for c in pk_columns)
            if non_pk_cols:
                update_set = ", ".join(f"target.{c} = source.{c}" for c in non_pk_cols)
                update_clause = f"WHEN MATCHED THEN UPDATE SET {update_set}"
            else:
                update_clause = ""

            insert_cols = ", ".join(f"target.{c}" for c in columns)
            insert_vals = ", ".join(f"source.{c}" for c in columns)

            return (
                f"MERGE INTO {table_name} target USING (SELECT {placeholders}) source ON ({match_cond}) "
                f"{update_clause} WHEN NOT MATCHED THEN INSERT ({insert_cols}) VALUES ({insert_vals});"
            )

        else:
            return f"INSERT INTO {table_name} ({cols_str}) VALUES ({placeholders});"

    def process_batch(
        self,
        table_name: str,
        records: List[Dict[str, Any]],
        columns: List[str],
        pk_columns: List[str],
    ) -> DeduplicationResult:
        """
        Executes full inline deduplication on a record batch and generates target upsert SQL.
        """
        unique_records, filtered_count = self.filter_batch_duplicates(records, pk_columns)
        upsert_sql = self.generate_upsert_statement(table_name, columns, pk_columns)

        return DeduplicationResult(
            total_input_rows=len(records),
            deduplicated_rows=len(unique_records),
            duplicates_filtered=filtered_count,
            upsert_sql=upsert_sql,
        )

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
from akaal.planner.models.p5_domain import CollisionPolicy, SurvivorStrategy, DuplicateDisposition
from akaalEngine.data_processing.dedup.deduplicator import RowDeduplicator

logger = logging.getLogger("akaal.migration.execution.deduplication")


class UnsupportedCollisionPolicyError(Exception):
    """Raised when a collision policy is unsupported for the given dialect."""
    pass


@dataclass
class DeduplicationResult:
    """Summary of batch deduplication processing."""
    total_input_rows: int
    deduplicated_rows: int
    duplicates_filtered: int
    upsert_sql: Optional[str] = None
    collision_policy: str = "UPSERT"
    disposition_records: List[Dict[str, Any]] = field(default_factory=list)
    processed_pk_hashes: List[str] = field(default_factory=list)


class ZeroDuplicateMigrationEngine(ExactlyOnceController):
    """
    Enterprise Zero-Duplicate Migration Engine.
    Filters out source stream duplicate rows before target database writes,
    executes deterministic survivor selection, and generates dialect-native collision DML statements.
    """

    def __init__(self, target_dialect: SystemType = SystemType.POSTGRESQL) -> None:
        super().__init__()
        self.target_dialect = target_dialect
        self._seen_pk_hashes: Set[str] = set()
        self.deduplicator = RowDeduplicator()

    def filter_batch_duplicates(
        self,
        records: List[Dict[str, Any]],
        pk_columns: List[str],
        survivor_strategy: SurvivorStrategy = SurvivorStrategy.FIRST,
        order_by_columns: Optional[List[str]] = None,
        priority_field: Optional[str] = None,
        priority_order: Optional[List[Any]] = None,
        disposition: DuplicateDisposition = DuplicateDisposition.DISCARD,
    ) -> Tuple[List[Dict[str, Any]], int, List[Dict[str, Any]]]:
        """
        In-memory deterministic filtering of source duplicate records using RowDeduplicator.
        Prevents duplicate rows from reaching the target database write pipeline.
        """
        if not pk_columns or not records:
            return records, 0, []

        survivors, duplicates, metrics = self.deduplicator.deduplicate_batch(
            records=records,
            key_columns=pk_columns,
            survivor_strategy=survivor_strategy.value if isinstance(survivor_strategy, Enum) else str(survivor_strategy),
            order_by_columns=order_by_columns,
            priority_field=priority_field,
            priority_order=priority_order,
            disposition=disposition.value if isinstance(disposition, Enum) else str(disposition),
        )

        for s in survivors:
            kh = self.deduplicator.compute_key_hash(s, pk_columns)
            self._seen_pk_hashes.add(kh)

        return survivors, metrics.get("duplicates_detected", len(duplicates)), duplicates

    def generate_collision_statement(
        self,
        table_name: str,
        columns: List[str],
        pk_columns: List[str],
        collision_policy: CollisionPolicy = CollisionPolicy.UPSERT,
        dialect: Optional[SystemType] = None,
    ) -> str:
        """
        Generates dialect-native target collision DML SQL based on operator-configured CollisionPolicy.
        Supports FAIL, REJECT, QUARANTINE, SKIP (DO NOTHING), INSERT, UPDATE, UPSERT (MERGE).
        """
        sys_dialect = dialect or self.target_dialect
        non_pk_cols = [c for c in columns if c not in pk_columns]
        cols_str = ", ".join(columns)
        placeholders = ", ".join(f":{c}" for c in columns)

        c_pol = collision_policy if isinstance(collision_policy, CollisionPolicy) else CollisionPolicy(str(collision_policy).upper())

        # 1. Standard INSERT / FAIL / REJECT (rely on database uniqueness constraints)
        if c_pol in (CollisionPolicy.INSERT, CollisionPolicy.FAIL, CollisionPolicy.REJECT, CollisionPolicy.QUARANTINE):
            return f"INSERT INTO {table_name} ({cols_str}) VALUES ({placeholders});"

        # 2. SKIP (DO NOTHING / IGNORE)
        if c_pol == CollisionPolicy.SKIP:
            if sys_dialect in (SystemType.POSTGRESQL, SystemType.SQLITE):
                pk_str = ", ".join(pk_columns)
                return f"INSERT INTO {table_name} ({cols_str}) VALUES ({placeholders}) ON CONFLICT ({pk_str}) DO NOTHING;"
            elif sys_dialect in (SystemType.MYSQL, SystemType.MARIADB):
                return f"INSERT IGNORE INTO {table_name} ({cols_str}) VALUES ({placeholders});"
            elif sys_dialect in (SystemType.ORACLE, SystemType.MSSQL):
                match_cond = " AND ".join(f"target.{c} = source.{c}" for c in pk_columns)
                insert_cols = ", ".join(f"target.{c}" for c in columns)
                insert_vals = ", ".join(f"source.{c}" for c in columns)
                return (
                    f"MERGE INTO {table_name} target USING (SELECT {placeholders}) source ON ({match_cond}) "
                    f"WHEN NOT MATCHED THEN INSERT ({insert_cols}) VALUES ({insert_vals});"
                )
            else:
                return f"INSERT INTO {table_name} ({cols_str}) VALUES ({placeholders});"

        # 3. UPDATE ONLY
        if c_pol == CollisionPolicy.UPDATE:
            if sys_dialect in (SystemType.ORACLE, SystemType.MSSQL):
                match_cond = " AND ".join(f"target.{c} = source.{c}" for c in pk_columns)
                update_set = ", ".join(f"target.{c} = source.{c}" for c in non_pk_cols)
                return f"MERGE INTO {table_name} target USING (SELECT {placeholders}) source ON ({match_cond}) WHEN MATCHED THEN UPDATE SET {update_set};"
            elif sys_dialect in (SystemType.POSTGRESQL, SystemType.SQLITE, SystemType.MYSQL, SystemType.MARIADB):
                set_clause = ", ".join(f"{c} = :{c}" for c in non_pk_cols)
                where_clause = " AND ".join(f"{c} = :{c}" for c in pk_columns)
                return f"UPDATE {table_name} SET {set_clause} WHERE {where_clause};"
            else:
                raise UnsupportedCollisionPolicyError(f"UPDATE collision policy is unsupported on dialect '{sys_dialect}'.")

        # 4. UPSERT / MERGE
        if c_pol == CollisionPolicy.UPSERT:
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

        return f"INSERT INTO {table_name} ({cols_str}) VALUES ({placeholders});"

    def generate_upsert_statement(
        self,
        table_name: str,
        columns: List[str],
        pk_columns: List[str],
        dialect: Optional[SystemType] = None,
    ) -> str:
        """Backward-compatible alias for generate_collision_statement with CollisionPolicy.UPSERT."""
        return self.generate_collision_statement(
            table_name=table_name,
            columns=columns,
            pk_columns=pk_columns,
            collision_policy=CollisionPolicy.UPSERT,
            dialect=dialect,
        )

    def process_batch(
        self,
        table_name: str,
        records: List[Dict[str, Any]],
        columns: List[str],
        pk_columns: List[str],
        collision_policy: CollisionPolicy = CollisionPolicy.UPSERT,
        survivor_strategy: SurvivorStrategy = SurvivorStrategy.FIRST,
        order_by_columns: Optional[List[str]] = None,
        priority_field: Optional[str] = None,
        priority_order: Optional[List[Any]] = None,
        disposition: DuplicateDisposition = DuplicateDisposition.DISCARD,
    ) -> DeduplicationResult:
        """
        Executes full inline deduplication on a record batch and generates target collision SQL.
        """
        from enum import Enum
        unique_records, filtered_count, disp_records = self.filter_batch_duplicates(
            records=records,
            pk_columns=pk_columns,
            survivor_strategy=survivor_strategy,
            order_by_columns=order_by_columns,
            priority_field=priority_field,
            priority_order=priority_order,
            disposition=disposition,
        )
        sql = self.generate_collision_statement(
            table_name=table_name,
            columns=columns,
            pk_columns=pk_columns,
            collision_policy=collision_policy,
        )

        return DeduplicationResult(
            total_input_rows=len(records),
            deduplicated_rows=len(unique_records),
            duplicates_filtered=filtered_count,
            upsert_sql=sql,
            collision_policy=collision_policy.value if isinstance(collision_policy, Enum) else str(collision_policy),
            disposition_records=disp_records,
        )

"""
AKAAL Engine-Specific DDL Capture & Parsing Detector.
=====================================================
Parses native engine DDL / schema change records for PostgreSQL, MySQL, Oracle, SQL Server, and MongoDB.
Classifies DDL operation types truthfully and sanitizes all credential diagnostics.
"""

from typing import Dict, Any, Optional, List
import re
import logging

from akaal.cdc.domain.events import CDCEventIdentity
from akaal.cdc.domain.positions import CDCSourcePosition
from akaal.cdc.schema_evolution.domain import (
    CDCDDLEvent,
    DDLOperationType,
    CDCSchemaVersion,
    sanitize_ddl_statement,
)

logger = logging.getLogger(__name__)


class CDCDDLEngineDetector:
    """Engine-specific native DDL detection and classification engine."""

    @classmethod
    def detect_and_parse_ddl(
        self,
        identity: CDCEventIdentity,
        source_engine: str,
        source_position: CDCSourcePosition,
        raw_statement_or_payload: Any,
        current_schema_version: CDCSchemaVersion,
        transaction_id: Optional[str] = None,
    ) -> CDCDDLEvent:
        engine = source_engine.upper()
        raw_text = str(raw_statement_or_payload) if not isinstance(raw_statement_or_payload, dict) else str(raw_statement_or_payload.get("sql", raw_statement_or_payload))

        sanitized_ddl = sanitize_ddl_statement(raw_text)
        op_type, affected_table, meta = self._classify_ddl(engine, raw_statement_or_payload)

        # Build proposed schema version based on DDL operation
        proposed_version = self._build_proposed_schema_version(current_schema_version, op_type, meta)

        ddl_event = CDCDDLEvent(
            identity=identity,
            source_position=source_position,
            canonical_operation=op_type,
            affected_database=current_schema_version.database_name,
            affected_schema=current_schema_version.schema_name,
            affected_table=affected_table or current_schema_version.table_name,
            old_schema_version_id=current_schema_version.schema_version_id,
            proposed_schema_version_id=proposed_version.schema_version_id,
            raw_ddl_statement=sanitized_ddl,
            transaction_id=transaction_id,
            operation_metadata=meta,
        )
        return ddl_event

    @classmethod
    def _classify_ddl(cls, engine: str, payload: Any) -> tuple[DDLOperationType, Optional[str], Dict[str, Any]]:
        raw_sql = str(payload).strip() if not isinstance(payload, dict) else str(payload.get("sql", "")).strip()
        sql_upper = raw_sql.upper()
        meta: Dict[str, Any] = {"source_engine": engine}

        # Handle MongoDB change stream DDL/command events
        if engine == "MONGODB":
            if isinstance(payload, dict):
                op = payload.get("operationType", "")
                if op == "drop":
                    return DDLOperationType.DROP_TABLE, payload.get("collection"), meta
                elif op == "rename":
                    return DDLOperationType.RENAME_TABLE, payload.get("collection"), meta
                elif op == "modify":
                    return DDLOperationType.ALTER_COLUMN_TYPE, payload.get("collection"), meta
            return DDLOperationType.UNKNOWN_DDL, None, meta

        if not raw_sql:
            return DDLOperationType.UNKNOWN_DDL, None, meta

        # Table Level DDL
        match_create_tbl = re.search(r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(?:[\w\"`]+\.)?([\w\"`]+)", sql_upper)
        if match_create_tbl:
            tbl = match_create_tbl.group(1).replace('"', '').replace('`', '')
            return DDLOperationType.CREATE_TABLE, tbl, meta

        match_drop_tbl = re.search(r"DROP\s+TABLE\s+(?:IF\s+EXISTS\s+)?(?:[\w\"`]+\.)?([\w\"`]+)", sql_upper)
        if match_drop_tbl:
            tbl = match_drop_tbl.group(1).replace('"', '').replace('`', '')
            return DDLOperationType.DROP_TABLE, tbl, meta

        match_truncate = re.search(r"TRUNCATE\s+(?:TABLE\s+)?(?:[\w\"`]+\.)?([\w\"`]+)", sql_upper)
        if match_truncate:
            tbl = match_truncate.group(1).replace('"', '').replace('`', '')
            return DDLOperationType.TRUNCATE_TABLE, tbl, meta

        match_rename_tbl = re.search(r"RENAME\s+TABLE\s+(?:[\w\"`]+\.)?([\w\"`]+)\s+TO\s+(?:[\w\"`]+\.)?([\w\"`]+)", sql_upper)
        if match_rename_tbl:
            tbl_old = match_rename_tbl.group(1).replace('"', '').replace('`', '')
            tbl_new = match_rename_tbl.group(2).replace('"', '').replace('`', '')
            meta["new_table_name"] = tbl_new
            return DDLOperationType.RENAME_TABLE, tbl_old, meta

        # Column Level DDL
        match_alter_tbl = re.search(r"(?i)ALTER\s+TABLE\s+(?:ONLY\s+)?(?:[\w\"`]+\.)?([\w\"`]+)\s+(.*)", raw_sql)
        if match_alter_tbl:
            tbl = match_alter_tbl.group(1).replace('"', '').replace('`', '')
            alter_clause = match_alter_tbl.group(2)

            # ADD / DROP PRIMARY KEY
            if re.search(r"(?i)ADD\s+PRIMARY\s+KEY|ADD\s+CONSTRAINT.*PRIMARY\s+KEY", alter_clause):
                return DDLOperationType.ADD_PRIMARY_KEY, tbl, meta

            if re.search(r"(?i)DROP\s+PRIMARY\s+KEY|DROP\s+CONSTRAINT.*PRIMARY\s+KEY", alter_clause):
                return DDLOperationType.DROP_PRIMARY_KEY, tbl, meta

            # ADD COLUMN
            match_add_col = re.search(r"(?i)ADD\s+(?:COLUMN\s+)?([\w\"`]+)\s+([\w\(\)]+)", alter_clause)
            if match_add_col:
                col_name = match_add_col.group(1).replace('"', '').replace('`', '')
                col_type = match_add_col.group(2)
                is_not_null = "NOT NULL" in alter_clause.upper()
                default_val = None
                default_match = re.search(r"(?i)DEFAULT\s+([^,\s]+)", alter_clause)
                if default_match:
                    default_val = default_match.group(1)
                meta["column_name"] = col_name
                meta["column_type"] = col_type
                meta["nullable"] = not is_not_null
                meta["default_value"] = default_val
                return DDLOperationType.ADD_COLUMN, tbl, meta

            # DROP COLUMN
            match_drop_col = re.search(r"(?i)DROP\s+(?:COLUMN\s+)?([\w\"`]+)", alter_clause)
            if match_drop_col:
                col_name = match_drop_col.group(1).replace('"', '').replace('`', '')
                meta["column_name"] = col_name
                return DDLOperationType.DROP_COLUMN, tbl, meta

            # RENAME COLUMN
            match_rename_col = re.search(r"(?i)RENAME\s+(?:COLUMN\s+)?([\w\"`]+)\s+TO\s+([\w\"`]+)", alter_clause)
            if match_rename_col:
                old_col = match_rename_col.group(1).replace('"', '').replace('`', '')
                new_col = match_rename_col.group(2).replace('"', '').replace('`', '')
                meta["old_column_name"] = old_col
                meta["new_column_name"] = new_col
                return DDLOperationType.RENAME_COLUMN, tbl, meta

            # ALTER COLUMN TYPE / MODIFY
            match_mod_col = re.search(r"(?i)(?:ALTER|MODIFY)\s+(?:COLUMN\s+)?([\w\"`]+)\s+(?:TYPE\s+)?([\w\(\)]+)", alter_clause)
            if match_mod_col:
                col_name = match_mod_col.group(1).replace('"', '').replace('`', '')
                new_type = match_mod_col.group(2)
                meta["column_name"] = col_name
                meta["new_type"] = new_type
                return DDLOperationType.ALTER_COLUMN_TYPE, tbl, meta

            # ADD PRIMARY KEY
            if "ADD PRIMARY KEY" in alter_clause or "ADD CONSTRAINT" in alter_clause and "PRIMARY KEY" in alter_clause:
                return DDLOperationType.ADD_PRIMARY_KEY, tbl, meta

            # DROP PRIMARY KEY
            if "DROP PRIMARY KEY" in alter_clause or "DROP CONSTRAINT" in alter_clause and "PRIMARY KEY" in alter_clause:
                return DDLOperationType.DROP_PRIMARY_KEY, tbl, meta

        # Check unsupported/unknown DDL
        if any(keyword in sql_upper for keyword in ["CREATE", "ALTER", "DROP", "RENAME", "TRUNCATE"]):
            return DDLOperationType.UNSUPPORTED_DDL, None, meta

        return DDLOperationType.UNKNOWN_DDL, None, meta

    @classmethod
    def _build_proposed_schema_version(
        cls,
        current_version: CDCSchemaVersion,
        op_type: DDLOperationType,
        meta: Dict[str, Any],
    ) -> CDCSchemaVersion:
        new_columns = [dict(c) for c in current_version.columns]
        new_pk = list(current_version.primary_key_columns)
        new_table_name = current_version.table_name

        if op_type == DDLOperationType.ADD_COLUMN:
            col_name = meta.get("column_name", "new_col")
            col_type = meta.get("column_type", "VARCHAR")
            nullable = meta.get("nullable", True)
            default = meta.get("default_value")
            new_columns.append({
                "name": col_name,
                "type": col_type,
                "nullable": nullable,
                "default": default,
            })
        elif op_type == DDLOperationType.DROP_COLUMN:
            col_name = meta.get("column_name", "")
            new_columns = [c for c in new_columns if c["name"].lower() != col_name.lower()]
        elif op_type == DDLOperationType.RENAME_COLUMN:
            old_col = meta.get("old_column_name", "")
            new_col = meta.get("new_column_name", "")
            for c in new_columns:
                if c["name"].lower() == old_col.lower():
                    c["name"] = new_col
        elif op_type == DDLOperationType.ALTER_COLUMN_TYPE:
            col_name = meta.get("column_name", "")
            new_type = meta.get("new_type", "")
            for c in new_columns:
                if c["name"].lower() == col_name.lower():
                    c["type"] = new_type
        elif op_type == DDLOperationType.RENAME_TABLE:
            new_table_name = meta.get("new_table_name", current_version.table_name)

        return CDCSchemaVersion(
            identity=current_version.identity,
            source_engine=current_version.source_engine,
            database_name=current_version.database_name,
            schema_name=current_version.schema_name,
            table_name=new_table_name,
            columns=new_columns,
            primary_key_columns=new_pk,
            version_number=current_version.version_number + 1,
            mapping_rules=current_version.mapping_rules,
        )

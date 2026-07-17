"""
Akaal — Identity DDL Planners and Dialect Translators
=====================================================
Defines strongly typed identity migration actions and translates them
to dialect-specific SQL and rollback statements.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class IdentityActionType(str, Enum):
    CREATE_IDENTITY = "Create Identity"
    DROP_IDENTITY = "Drop Identity"
    RESTART_IDENTITY = "Restart Identity"
    RESEED_SEQUENCE = "Reseed Sequence"
    ALTER_INCREMENT = "Alter Increment"
    ALTER_BOUNDS = "Alter Bounds"
    ALTER_CYCLE = "Alter Cycle"
    RECREATE_IDENTITY = "Recreate Identity"
    NO_OP = "No Operation"


class IdentitySafetyLevel(str, Enum):
    SAFE = "SAFE"
    SAFE_WITH_ALTER = "SAFE_WITH_ALTER"
    SAFE_RESEED = "SAFE_RESEED"
    UNSAFE_REBUILD = "UNSAFE_REBUILD"
    UNSAFE = "UNSAFE"


@dataclass(frozen=True)
class TypedIdentityAction:
    action_type: IdentityActionType
    source_metadata: Dict[str, Any]
    target_metadata: Dict[str, Any]
    safety_level: IdentitySafetyLevel
    approval_requirement: str
    reasoning: str
    rollback_metadata: Dict[str, Any]


class TranslationOutput:
    def __init__(self, sql_commands: List[str], rollback_commands: List[str], warnings: List[str] = None):
        self.sql_commands = sql_commands
        self.rollback_commands = rollback_commands
        self.warnings = warnings or []


class IdentityDialectTranslator:
    """
    Translates database-independent TypedIdentityAction plans into dialect-specific DDL commands.
    """

    @staticmethod
    def translate(
        action: TypedIdentityAction,
        dialect: str,
        schema: str,
        table: str,
        column: str
    ) -> TranslationOutput:
        dialect_lower = dialect.lower().strip()
        
        sql = []
        rollback = []
        warnings = []

        src = action.source_metadata
        tgt = action.target_metadata
        act_type = action.action_type

        # ----------------------------------------------------
        # 1. PostgreSQL Dialect Translation
        # ----------------------------------------------------
        if dialect_lower == "postgresql":
            quoted_table = f'"{schema}"."{table}"'
            
            if act_type == IdentityActionType.CREATE_IDENTITY:
                mode = src.get("mode", "GENERATED ALWAYS")
                always_str = "ALWAYS" if "ALWAYS" in mode else "BY DEFAULT"
                start = src.get("start", 1)
                increment = src.get("increment", 1)
                
                seq_options = []
                if start is not None and start != 1:
                    seq_options.append(f"START WITH {start}")
                if increment is not None and increment != 1:
                    seq_options.append(f"INCREMENT BY {increment}")
                if src.get("min_value") is not None:
                    seq_options.append(f"MINVALUE {src.get('min_value')}")
                if src.get("max_value") is not None:
                    seq_options.append(f"MAXVALUE {src.get('max_value')}")
                if src.get("cycle"):
                    seq_options.append("CYCLE")
                if src.get("cache") is not None and src.get("cache") > 1:
                    seq_options.append(f"CACHE {src.get('cache')}")
                
                opt_str = f" ({' '.join(seq_options)})" if seq_options else ""
                sql.append(f'ALTER TABLE {quoted_table} ALTER COLUMN "{column}" ADD GENERATED {always_str} AS IDENTITY{opt_str}')
                rollback.append(f'ALTER TABLE {quoted_table} ALTER COLUMN "{column}" DROP IDENTITY IF EXISTS')

            elif act_type == IdentityActionType.DROP_IDENTITY:
                sql.append(f'ALTER TABLE {quoted_table} ALTER COLUMN "{column}" DROP IDENTITY IF EXISTS')
                if tgt.get("mode") != "NONE":
                    mode = tgt.get("mode", "GENERATED ALWAYS")
                    always_str = "ALWAYS" if "ALWAYS" in mode else "BY DEFAULT"
                    rollback.append(f'ALTER TABLE {quoted_table} ALTER COLUMN "{column}" ADD GENERATED {always_str} AS IDENTITY')

            elif act_type == IdentityActionType.RESTART_IDENTITY:
                cur_val = src.get("current_value", 1)
                sql.append(f'ALTER TABLE {quoted_table} ALTER COLUMN "{column}" RESTART WITH {cur_val}')
                if tgt.get("current_value") is not None:
                    rollback.append(f'ALTER TABLE {quoted_table} ALTER COLUMN "{column}" RESTART WITH {tgt.get("current_value")}')

        # ----------------------------------------------------
        # 2. Oracle Dialect Translation
        # ----------------------------------------------------
        elif dialect_lower == "oracle":
            quoted_table = f'"{schema.upper()}"."{table.upper()}"'
            quoted_column = f'"{column.upper()}"'

            if act_type == IdentityActionType.CREATE_IDENTITY:
                mode = src.get("mode", "GENERATED ALWAYS")
                always_str = "ALWAYS" if "ALWAYS" in mode else "BY DEFAULT ON NULL"
                start = src.get("start", 1)
                increment = src.get("increment", 1)
                
                seq_options = []
                if start is not None and start != 1:
                    seq_options.append(f"START WITH {start}")
                if increment is not None and increment != 1:
                    seq_options.append(f"INCREMENT BY {increment}")
                if src.get("min_value") is not None:
                    seq_options.append(f"MINVALUE {src.get('min_value')}")
                if src.get("max_value") is not None:
                    seq_options.append(f"MAXVALUE {src.get('max_value')}")
                if src.get("cycle"):
                    seq_options.append("CYCLE")
                if src.get("cache") is not None and src.get("cache") > 1:
                    seq_options.append(f"CACHE {src.get('cache')}")
                
                opt_str = f" ({' '.join(seq_options)})" if seq_options else ""
                sql.append(f'ALTER TABLE {quoted_table} MODIFY ({quoted_column} GENERATED {always_str} AS IDENTITY{opt_str})')
                rollback.append(f'ALTER TABLE {quoted_table} MODIFY ({quoted_column} DROP IDENTITY)')

            elif act_type == IdentityActionType.DROP_IDENTITY:
                sql.append(f'ALTER TABLE {quoted_table} MODIFY ({quoted_column} DROP IDENTITY)')

            elif act_type == IdentityActionType.RESTART_IDENTITY:
                cur_val = src.get("current_value", 1)
                sql.append(f'ALTER TABLE {quoted_table} MODIFY ({quoted_column} RESTART WITH {cur_val})')

        # ----------------------------------------------------
        # 3. SQL Server (MSSQL) Dialect Translation
        # ----------------------------------------------------
        elif dialect_lower in ("mssql", "sqlserver"):
            quoted_table = f'[{schema}].[{table}]'
            
            if act_type == IdentityActionType.CREATE_IDENTITY:
                warnings.append("SQL Server requires rebuilding table to add IDENTITY attribute.")
                sql.append(f"-- Rebuild table {quoted_table} with column [{column}] IDENTITY")
            
            elif act_type == IdentityActionType.DROP_IDENTITY:
                warnings.append("SQL Server requires rebuilding table to drop IDENTITY attribute.")
                sql.append(f"-- Rebuild table {quoted_table} dropping column [{column}] IDENTITY")
                
            elif act_type == IdentityActionType.RESTART_IDENTITY:
                cur_val = src.get("current_value", 1)
                sql.append(f"DBCC CHECKIDENT ('{schema}.{table}', RESEED, {cur_val})")
                if tgt.get("current_value") is not None:
                    rollback.append(f"DBCC CHECKIDENT ('{schema}.{table}', RESEED, {tgt.get('current_value')})")

        # ----------------------------------------------------
        # 4. MySQL Dialect Translation
        # ----------------------------------------------------
        elif dialect_lower == "mysql":
            quoted_table = f'`{schema}`.`{table}`'
            quoted_column = f'`{column}`'

            if act_type == IdentityActionType.CREATE_IDENTITY:
                sql.append(f'ALTER TABLE {quoted_table} MODIFY COLUMN {quoted_column} INT AUTO_INCREMENT')
                rollback.append(f'ALTER TABLE {quoted_table} MODIFY COLUMN {quoted_column} INT')

            elif act_type == IdentityActionType.DROP_IDENTITY:
                sql.append(f'ALTER TABLE {quoted_table} MODIFY COLUMN {quoted_column} INT')

            elif act_type == IdentityActionType.RESTART_IDENTITY:
                cur_val = src.get("current_value", 1)
                sql.append(f'ALTER TABLE {quoted_table} AUTO_INCREMENT = {cur_val}')

        else:
            warnings.append(f"Dialect '{dialect}' is not natively supported for identity translation.")
            sql.append(f"-- Unsupported dialect translation: {act_type.value}")

        return TranslationOutput(sql_commands=sql, rollback_commands=rollback, warnings=warnings)


class IdentitySyncPlanner:
    """
    Constructs a pipeline of database-independent TypedIdentityAction steps
    based on comparison engine findings.
    """

    @staticmethod
    def generate_plan(
        report: Any,
        schema: str,
        table: str,
        column: str
    ) -> List[TypedIdentityAction]:
        actions = []
        cat = report.compatibility_category
        src = report.source_metadata
        tgt = report.target_metadata

        if cat == "Compatible":
            actions.append(TypedIdentityAction(
                action_type=IdentityActionType.NO_OP,
                source_metadata=src,
                target_metadata=tgt,
                safety_level=IdentitySafetyLevel.SAFE,
                approval_requirement="automatic migration",
                reasoning="Identity specifications match target.",
                rollback_metadata={}
            ))
            return actions

        if cat == "Unsupported":
            return actions

        # 1. Handle Recreation (Drop then recreate)
        if cat == "Requires Recreation":
            if tgt.get("mode") != "NONE":
                actions.append(TypedIdentityAction(
                    action_type=IdentityActionType.DROP_IDENTITY,
                    source_metadata=src,
                    target_metadata=tgt,
                    safety_level=IdentitySafetyLevel.SAFE_WITH_ALTER,
                    approval_requirement="administrator approval",
                    reasoning="Drop old identity attributes before recreating.",
                    rollback_metadata={"restore_original": True}
                ))
            
            actions.append(TypedIdentityAction(
                action_type=IdentityActionType.CREATE_IDENTITY,
                source_metadata=src,
                target_metadata=tgt,
                safety_level=IdentitySafetyLevel.UNSAFE_REBUILD,
                approval_requirement="administrator approval",
                reasoning="Recreate identity attributes to align structure.",
                rollback_metadata={}
            ))
            return actions

        # 2. Handle Alterations/Translation
        if cat == "Requires Translation":
            actions.append(TypedIdentityAction(
                action_type=IdentityActionType.CREATE_IDENTITY,
                source_metadata=src,
                target_metadata=tgt,
                safety_level=IdentitySafetyLevel.SAFE_WITH_ALTER,
                approval_requirement="administrator approval",
                reasoning="Alter generator mode to match source definition.",
                rollback_metadata={}
            ))

        # 3. Handle Reseed / Restart
        if cat == "Requires Reseed":
            actions.append(TypedIdentityAction(
                action_type=IdentityActionType.RESTART_IDENTITY,
                source_metadata=src,
                target_metadata=tgt,
                safety_level=IdentitySafetyLevel.SAFE_RESEED,
                approval_requirement="administrator approval",
                reasoning="Restart target sequence value to match source counter.",
                rollback_metadata={}
            ))

        return actions

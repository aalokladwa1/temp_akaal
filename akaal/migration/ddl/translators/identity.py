"""
Akaal — Identity DDL Planners and Dialect Translators
=====================================================
Defines strongly typed identity migration actions and translates them
to dialect-specific SQL and rollback statements.
"""

from dataclasses import dataclass, field
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


class TranslationStatus(str, Enum):
    SUCCESS = "success"
    UNSUPPORTED = "unsupported"
    REQUIRES_FALLBACK = "requires_fallback"
    REQUIRES_RECONSTRUCTION = "requires_reconstruction"
    REQUIRES_APPROVAL = "requires_approval"
    BLOCKED_UNSAFE = "blocked_unsafe"
    VALIDATION_FAILURE = "validation_failure"


class RollbackClassification(str, Enum):
    EXACT = "EXACT"
    COMPENSATING = "COMPENSATING"
    BEST_EFFORT = "BEST_EFFORT"
    REQUIRES_BACKUP = "REQUIRES_BACKUP"
    REQUIRES_RECONSTRUCTION = "REQUIRES_RECONSTRUCTION"
    NOT_AVAILABLE = "NOT_AVAILABLE"


@dataclass(frozen=True)
class TypedIdentityAction:
    action_type: IdentityActionType
    source_metadata: Dict[str, Any]
    target_metadata: Dict[str, Any]
    safety_level: IdentitySafetyLevel
    approval_requirement: str
    reasoning: str
    rollback_metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        # 1. Reject missing metadata unless it's a NO_OP
        if self.action_type != IdentityActionType.NO_OP:
            if not self.source_metadata and not self.target_metadata:
                raise ValueError("Both source and target metadata cannot be empty for mutation actions.")

        # 2. Check increment constraints
        for meta in (self.source_metadata, self.target_metadata):
            if meta:
                inc = meta.get("increment")
                if inc == 0:
                    raise ValueError("Sequence increment step cannot be zero.")

        # 3. Validate bounds range
        for meta in (self.source_metadata, self.target_metadata):
            if meta:
                min_v = meta.get("min_value")
                max_v = meta.get("max_value")
                if min_v is not None and max_v is not None and min_v > max_v:
                    raise ValueError(f"Min value {min_v} cannot exceed max value {max_v}.")


@dataclass(frozen=True)
class TranslationOutput:
    dialect: str
    db_version: str
    status: TranslationStatus
    typed_source_action: TypedIdentityAction
    sql_commands: Tuple[str, ...]
    rollback_commands: Tuple[str, ...]
    warnings: Tuple[str, ...]
    preconditions: Tuple[str, ...]
    approval_requirement: str
    safety_classification: str
    rollback_classification: RollbackClassification
    failure_reason: Optional[str] = None
    deferred_task: Optional[str] = None


def quote_identifier(name: str, dialect: str) -> str:
    """
    Quotes an identifier according to dialect rules, escaping embedded characters.
    Handles schema-qualified names by splitting.
    """
    dialect_lower = dialect.lower().strip()
    if "." in name:
        parts = name.split(".")
        return ".".join(quote_identifier(p.strip('"[]`'), dialect) for p in parts)

    if dialect_lower == "postgresql":
        escaped = name.replace('"', '""')
        return f'"{escaped}"'
    elif dialect_lower == "oracle":
        escaped = name.replace('"', '""')
        return f'"{escaped.upper()}"'
    elif dialect_lower in ("mssql", "sqlserver"):
        escaped = name.replace(']', ']]')
        return f'[{escaped}]'
    elif dialect_lower == "mysql":
        escaped = name.replace('`', '``')
        return f'`{escaped}`'
    return name


def parse_version(version_str: Optional[str]) -> Tuple[int, ...]:
    if not version_str:
        return (0,)
    try:
        parts = []
        for p in version_str.split("."):
            p_clean = "".join(c for c in p if c.isdigit())
            if p_clean:
                parts.append(int(p_clean))
        return tuple(parts)
    except Exception:
        return (0,)


class IdentityDialectTranslator:
    """
    Translates database-independent TypedIdentityAction plans into dialect-specific DDL commands.
    """

    @staticmethod
    def translate(
        action: TypedIdentityAction,
        dialect: str,
        db_version: str,
        schema: str,
        table: str,
        column: str
    ) -> TranslationOutput:
        dialect_lower = dialect.lower().strip()
        version_parsed = parse_version(db_version)

        # Pre-validate identifiers for safety
        if not schema or not table or not column:
            return TranslationOutput(
                dialect=dialect,
                db_version=db_version,
                status=TranslationStatus.VALIDATION_FAILURE,
                typed_source_action=action,
                sql_commands=(),
                rollback_commands=(),
                warnings=(),
                preconditions=(),
                approval_requirement=action.approval_requirement,
                safety_classification=action.safety_level.value,
                rollback_classification=RollbackClassification.NOT_AVAILABLE,
                failure_reason="Schema, table, or column name cannot be empty."
            )

        src = action.source_metadata
        tgt = action.target_metadata
        act_type = action.action_type

        # ----------------------------------------------------
        # 1. PostgreSQL Translation
        # ----------------------------------------------------
        if dialect_lower == "postgresql":
            if version_parsed and version_parsed[0] < 10:
                # PG 9.x does not support native identity, defer to sequence fallback (TSK-33)
                return TranslationOutput(
                    dialect=dialect,
                    db_version=db_version,
                    status=TranslationStatus.REQUIRES_FALLBACK,
                    typed_source_action=action,
                    sql_commands=(),
                    rollback_commands=(),
                    warnings=("PostgreSQL 9.x lacks native identity support. Deferring to sequence fallback.",),
                    preconditions=(),
                    approval_requirement=action.approval_requirement,
                    safety_classification=action.safety_level.value,
                    rollback_classification=RollbackClassification.REQUIRES_RECONSTRUCTION,
                    deferred_task="TSK-33"
                )

            quoted_table = f"{quote_identifier(schema, dialect)}.{quote_identifier(table, dialect)}"
            quoted_col = quote_identifier(column, dialect)

            if act_type == IdentityActionType.CREATE_IDENTITY:
                mode = src.get("mode", "GENERATED ALWAYS")
                always_str = "ALWAYS" if "ALWAYS" in mode else "BY DEFAULT"
                start = src.get("start", 1)
                increment = src.get("increment", 1)

                seq_options = []
                if start is not None and start != 1:
                    seq_options.append(f"START WITH {int(start)}")
                if increment is not None and increment != 1:
                    seq_options.append(f"INCREMENT BY {int(increment)}")
                if src.get("min_value") is not None:
                    seq_options.append(f"MINVALUE {int(src.get('min_value'))}")
                if src.get("max_value") is not None:
                    seq_options.append(f"MAXVALUE {int(src.get('max_value'))}")
                if src.get("cycle"):
                    seq_options.append("CYCLE")
                if src.get("cache") is not None and src.get("cache") > 1:
                    seq_options.append(f"CACHE {int(src.get('cache'))}")

                opt_str = f" ({' '.join(seq_options)})" if seq_options else ""
                sql = f"ALTER TABLE {quoted_table} ALTER COLUMN {quoted_col} ADD GENERATED {always_str} AS IDENTITY{opt_str}"
                rollback = f"ALTER TABLE {quoted_table} ALTER COLUMN {quoted_col} DROP IDENTITY IF EXISTS"

                return TranslationOutput(
                    dialect=dialect,
                    db_version=db_version,
                    status=TranslationStatus.SUCCESS,
                    typed_source_action=action,
                    sql_commands=(sql,),
                    rollback_commands=(rollback,),
                    warnings=(),
                    preconditions=("Column must not have existing identity or defaults.",),
                    approval_requirement=action.approval_requirement,
                    safety_classification=action.safety_level.value,
                    rollback_classification=RollbackClassification.BEST_EFFORT
                )

            elif act_type == IdentityActionType.DROP_IDENTITY:
                sql = f"ALTER TABLE {quoted_table} ALTER COLUMN {quoted_col} DROP IDENTITY IF EXISTS"
                rollback = ""
                if tgt.get("mode") and tgt.get("mode") != "NONE":
                    mode = tgt.get("mode")
                    always_str = "ALWAYS" if "ALWAYS" in mode else "BY DEFAULT"
                    rollback = f"ALTER TABLE {quoted_table} ALTER COLUMN {quoted_col} ADD GENERATED {always_str} AS IDENTITY"

                return TranslationOutput(
                    dialect=dialect,
                    db_version=db_version,
                    status=TranslationStatus.SUCCESS,
                    typed_source_action=action,
                    sql_commands=(sql,),
                    rollback_commands=(rollback,) if rollback else (),
                    warnings=(),
                    preconditions=(),
                    approval_requirement=action.approval_requirement,
                    safety_classification=action.safety_level.value,
                    rollback_classification=RollbackClassification.COMPENSATING
                )

            elif act_type == IdentityActionType.RESTART_IDENTITY:
                cur_val = src.get("current_value", 1)
                sql = f"ALTER TABLE {quoted_table} ALTER COLUMN {quoted_col} RESTART WITH {int(cur_val)}"
                rollback = ""
                if tgt.get("current_value") is not None:
                    rollback = f"ALTER TABLE {quoted_table} ALTER COLUMN {quoted_col} RESTART WITH {int(tgt.get('current_value'))}"

                return TranslationOutput(
                    dialect=dialect,
                    db_version=db_version,
                    status=TranslationStatus.SUCCESS,
                    typed_source_action=action,
                    sql_commands=(sql,),
                    rollback_commands=(rollback,) if rollback else (),
                    warnings=(),
                    preconditions=(),
                    approval_requirement=action.approval_requirement,
                    safety_classification=action.safety_level.value,
                    rollback_classification=RollbackClassification.EXACT
                )

        # ----------------------------------------------------
        # 2. Oracle Translation
        # ----------------------------------------------------
        elif dialect_lower == "oracle":
            if version_parsed and version_parsed[0] < 12:
                # Oracle 11g does not support native identities, defer to trigger/sequence fallback (TSK-34)
                return TranslationOutput(
                    dialect=dialect,
                    db_version=db_version,
                    status=TranslationStatus.REQUIRES_FALLBACK,
                    typed_source_action=action,
                    sql_commands=(),
                    rollback_commands=(),
                    warnings=("Oracle 11g lacks native identity support. Deferring to trigger fallback.",),
                    preconditions=(),
                    approval_requirement=action.approval_requirement,
                    safety_classification=action.safety_level.value,
                    rollback_classification=RollbackClassification.REQUIRES_RECONSTRUCTION,
                    deferred_task="TSK-34"
                )

            quoted_table = f"{quote_identifier(schema, dialect)}.{quote_identifier(table, dialect)}"
            quoted_col = quote_identifier(column, dialect)

            if act_type == IdentityActionType.CREATE_IDENTITY:
                mode = src.get("mode", "GENERATED ALWAYS")
                always_str = "ALWAYS" if "ALWAYS" in mode else "BY DEFAULT ON NULL"
                start = src.get("start", 1)
                increment = src.get("increment", 1)

                seq_options = []
                if start is not None and start != 1:
                    seq_options.append(f"START WITH {int(start)}")
                if increment is not None and increment != 1:
                    seq_options.append(f"INCREMENT BY {int(increment)}")
                if src.get("min_value") is not None:
                    seq_options.append(f"MINVALUE {int(src.get('min_value'))}")
                if src.get("max_value") is not None:
                    seq_options.append(f"MAXVALUE {int(src.get('max_value'))}")
                if src.get("cycle"):
                    seq_options.append("CYCLE")
                if src.get("cache") is not None and src.get("cache") > 1:
                    seq_options.append(f"CACHE {int(src.get('cache'))}")

                opt_str = f" ({' '.join(seq_options)})" if seq_options else ""
                sql = f"ALTER TABLE {quoted_table} MODIFY ({quoted_col} GENERATED {always_str} AS IDENTITY{opt_str})"
                rollback = f"ALTER TABLE {quoted_table} MODIFY ({quoted_col} DROP IDENTITY)"

                return TranslationOutput(
                    dialect=dialect,
                    db_version=db_version,
                    status=TranslationStatus.SUCCESS,
                    typed_source_action=action,
                    sql_commands=(sql,),
                    rollback_commands=(rollback,),
                    warnings=(),
                    preconditions=("Column must be empty or newly created to add native identity in Oracle.",),
                    approval_requirement=action.approval_requirement,
                    safety_classification=action.safety_level.value,
                    rollback_classification=RollbackClassification.BEST_EFFORT
                )

            elif act_type == IdentityActionType.DROP_IDENTITY:
                sql = f"ALTER TABLE {quoted_table} MODIFY ({quoted_col} DROP IDENTITY)"
                return TranslationOutput(
                    dialect=dialect,
                    db_version=db_version,
                    status=TranslationStatus.SUCCESS,
                    typed_source_action=action,
                    sql_commands=(sql,),
                    rollback_commands=(),
                    warnings=(),
                    preconditions=(),
                    approval_requirement=action.approval_requirement,
                    safety_classification=action.safety_level.value,
                    rollback_classification=RollbackClassification.NOT_AVAILABLE
                )

            elif act_type == IdentityActionType.RESTART_IDENTITY:
                cur_val = src.get("current_value", 1)
                sql = f"ALTER TABLE {quoted_table} MODIFY ({quoted_col} RESTART WITH {int(cur_val)})"
                return TranslationOutput(
                    dialect=dialect,
                    db_version=db_version,
                    status=TranslationStatus.SUCCESS,
                    typed_source_action=action,
                    sql_commands=(sql,),
                    rollback_commands=(),
                    warnings=(),
                    preconditions=(),
                    approval_requirement=action.approval_requirement,
                    safety_classification=action.safety_level.value,
                    rollback_classification=RollbackClassification.NOT_AVAILABLE
                )

        # ----------------------------------------------------
        # 3. SQL Server Translation
        # ----------------------------------------------------
        elif dialect_lower in ("mssql", "sqlserver"):
            # SQL Server does not support modifying the column to add or drop IDENTITY
            if act_type in (IdentityActionType.CREATE_IDENTITY, IdentityActionType.DROP_IDENTITY, IdentityActionType.RECREATE_IDENTITY):
                return TranslationOutput(
                    dialect=dialect,
                    db_version=db_version,
                    status=TranslationStatus.REQUIRES_RECONSTRUCTION,
                    typed_source_action=action,
                    sql_commands=(),
                    rollback_commands=(),
                    warnings=("SQL Server requires full table reconstruction to alter identity configurations.",),
                    preconditions=(),
                    approval_requirement=action.approval_requirement,
                    safety_classification=action.safety_level.value,
                    rollback_classification=RollbackClassification.REQUIRES_RECONSTRUCTION,
                    deferred_task="TSK-35"
                )

            quoted_table = f"{quote_identifier(schema, dialect)}.{quote_identifier(table, dialect)}"

            if act_type == IdentityActionType.RESTART_IDENTITY:
                cur_val = src.get("current_value", 1)
                # Inform execution engine of DBCC Reseed behavior warning
                sql = f"DBCC CHECKIDENT ('{schema}.{table}', RESEED, {int(cur_val)})"
                rollback = ""
                if tgt.get("current_value") is not None:
                    rollback = f"DBCC CHECKIDENT ('{schema}.{table}', RESEED, {int(tgt.get('current_value'))})"

                return TranslationOutput(
                    dialect=dialect,
                    db_version=db_version,
                    status=TranslationStatus.SUCCESS,
                    typed_source_action=action,
                    sql_commands=(sql,),
                    rollback_commands=(rollback,) if rollback else (),
                    warnings=("DBCC RESEED assumes target table state correctly aligns with restart expectations.",),
                    preconditions=(),
                    approval_requirement=action.approval_requirement,
                    safety_classification=action.safety_level.value,
                    rollback_classification=RollbackClassification.EXACT
                )

        # ----------------------------------------------------
        # 4. MySQL Translation
        # ----------------------------------------------------
        elif dialect_lower == "mysql":
            quoted_table = f"{quote_identifier(schema, dialect)}.{quote_identifier(table, dialect)}"
            quoted_col = quote_identifier(column, dialect)

            # Reject negative increments structurally
            if src.get("increment") is not None and src.get("increment") < 0:
                return TranslationOutput(
                    dialect=dialect,
                    db_version=db_version,
                    status=TranslationStatus.UNSUPPORTED,
                    typed_source_action=action,
                    sql_commands=(),
                    rollback_commands=(),
                    warnings=(),
                    preconditions=(),
                    approval_requirement=action.approval_requirement,
                    safety_classification=IdentitySafetyLevel.UNSAFE.value,
                    rollback_classification=RollbackClassification.NOT_AVAILABLE,
                    failure_reason="MySQL does not support negative AUTO_INCREMENT steps."
                )

            if act_type == IdentityActionType.CREATE_IDENTITY:
                sql = f"ALTER TABLE {quoted_table} MODIFY COLUMN {quoted_col} INT AUTO_INCREMENT"
                rollback = f"ALTER TABLE {quoted_table} MODIFY COLUMN {quoted_col} INT"

                return TranslationOutput(
                    dialect=dialect,
                    db_version=db_version,
                    status=TranslationStatus.SUCCESS,
                    typed_source_action=action,
                    sql_commands=(sql,),
                    rollback_commands=(rollback,),
                    warnings=(),
                    preconditions=("Column must be indexed in MySQL to support auto_increment.",),
                    approval_requirement=action.approval_requirement,
                    safety_classification=action.safety_level.value,
                    rollback_classification=RollbackClassification.COMPENSATING
                )

            elif act_type == IdentityActionType.DROP_IDENTITY:
                sql = f"ALTER TABLE {quoted_table} MODIFY COLUMN {quoted_col} INT"
                rollback = f"ALTER TABLE {quoted_table} MODIFY COLUMN {quoted_col} INT AUTO_INCREMENT"

                return TranslationOutput(
                    dialect=dialect,
                    db_version=db_version,
                    status=TranslationStatus.SUCCESS,
                    typed_source_action=action,
                    sql_commands=(sql,),
                    rollback_commands=(rollback,),
                    warnings=(),
                    preconditions=(),
                    approval_requirement=action.approval_requirement,
                    safety_classification=action.safety_level.value,
                    rollback_classification=RollbackClassification.COMPENSATING
                )

            elif act_type == IdentityActionType.RESTART_IDENTITY:
                cur_val = src.get("current_value", 1)
                sql = f"ALTER TABLE {quoted_table} AUTO_INCREMENT = {int(cur_val)}"

                return TranslationOutput(
                    dialect=dialect,
                    db_version=db_version,
                    status=TranslationStatus.SUCCESS,
                    typed_source_action=action,
                    sql_commands=(sql,),
                    rollback_commands=(),
                    warnings=(),
                    preconditions=(),
                    approval_requirement=action.approval_requirement,
                    safety_classification=action.safety_level.value,
                    rollback_classification=RollbackClassification.NOT_AVAILABLE
                )

        # Fallback to unsupported dialect
        return TranslationOutput(
            dialect=dialect,
            db_version=db_version,
            status=TranslationStatus.UNSUPPORTED,
            typed_source_action=action,
            sql_commands=(),
            rollback_commands=(),
            warnings=(),
            preconditions=(),
            approval_requirement=action.approval_requirement,
            safety_classification=action.safety_level.value,
            rollback_classification=RollbackClassification.NOT_AVAILABLE,
            failure_reason=f"Dialect '{dialect}' is not supported for identity translation."
        )


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

        if cat == "Unsupported" or cat == "Unsafe":
            # Plan is blocked
            return actions

        # 1. Handle Recreation (structural rebuild)
        if cat == "Requires Recreation":
            actions.append(TypedIdentityAction(
                action_type=IdentityActionType.RECREATE_IDENTITY,
                source_metadata=src,
                target_metadata=tgt,
                safety_level=IdentitySafetyLevel.UNSAFE_REBUILD,
                approval_requirement="administrator approval",
                reasoning="Recreate identity attributes to align structural differences.",
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

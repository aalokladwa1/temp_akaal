"""
AKAAL CDC Schema Evolution Domain Foundation.
=================================================
Establishes canonical CDC Schema Version models, DDL Operation Types, Identity-Bound DDL Events,
Compatibility Classifications, Evolution Policy Decisions, Schema Transition States, and Target Drift Classifications.
"""

from typing import Dict, Any, List, Optional, Set
from enum import Enum
import hashlib
import datetime
import re
import logging

from akaal.cdc.domain.events import CDCEventIdentity
from akaal.cdc.domain.positions import CDCSourcePosition, parse_source_position

logger = logging.getLogger(__name__)


def sanitize_ddl_statement(raw_ddl: str) -> str:
    """Redacts passwords, secret tokens, and credentials from raw DDL statements."""
    if not raw_ddl:
        return ""
    sanitized = raw_ddl
    # Redact identified password/credential patterns in DDL (e.g. IDENTIFIED BY 'secret', PASSWORD = 'secret', TOKEN = 'secret')
    sanitized = re.sub(r"(?i)(IDENTIFIED\s+BY\s+)(['\"][^'\"]+['\"]|\S+)", r"\1'[REDACTED_SECRET]'", sanitized)
    sanitized = re.sub(r"(?i)(PASSWORD\s*=\s*)(['\"][^'\"]+['\"]|\S+)", r"\1'[REDACTED_SECRET]'", sanitized)
    sanitized = re.sub(r"(?i)(SECRET\s*=\s*)(['\"][^'\"]+['\"]|\S+)", r"\1'[REDACTED_SECRET]'", sanitized)
    sanitized = re.sub(r"(?i)(AUTH_TOKEN\s*=\s*)(['\"][^'\"]+['\"]|\S+)", r"\1'[REDACTED_SECRET]'", sanitized)
    sanitized = re.sub(r"(?i)(API_KEY\s*=\s*)(['\"][^'\"]+['\"]|\S+)", r"\1'[REDACTED_SECRET]'", sanitized)
    sanitized = re.sub(r"(?i)(BEARER\s+)(['\"][^'\"]+['\"]|\S+)", r"\1'[REDACTED_SECRET]'", sanitized)
    sanitized = re.sub(r"(?i)(PRIVATE_KEY\s*=\s*)(['\"][^'\"]+['\"]|\S+)", r"\1'[REDACTED_SECRET]'", sanitized)
    return sanitized


class DDLOperationType(str, Enum):
    """Canonical classification for DDL / schema change operations."""
    CREATE_TABLE = "CREATE_TABLE"
    DROP_TABLE = "DROP_TABLE"
    RENAME_TABLE = "RENAME_TABLE"

    ADD_COLUMN = "ADD_COLUMN"
    DROP_COLUMN = "DROP_COLUMN"
    RENAME_COLUMN = "RENAME_COLUMN"
    ALTER_COLUMN_TYPE = "ALTER_COLUMN_TYPE"
    ALTER_COLUMN_NULLABILITY = "ALTER_COLUMN_NULLABILITY"
    ALTER_COLUMN_DEFAULT = "ALTER_COLUMN_DEFAULT"

    ADD_PRIMARY_KEY = "ADD_PRIMARY_KEY"
    DROP_PRIMARY_KEY = "DROP_PRIMARY_KEY"

    ADD_UNIQUE_CONSTRAINT = "ADD_UNIQUE_CONSTRAINT"
    DROP_UNIQUE_CONSTRAINT = "DROP_UNIQUE_CONSTRAINT"

    ADD_FOREIGN_KEY = "ADD_FOREIGN_KEY"
    DROP_FOREIGN_KEY = "DROP_FOREIGN_KEY"

    CREATE_INDEX = "CREATE_INDEX"
    DROP_INDEX = "DROP_INDEX"

    TRUNCATE_TABLE = "TRUNCATE_TABLE"

    UNKNOWN_DDL = "UNKNOWN_DDL"
    UNSUPPORTED_DDL = "UNSUPPORTED_DDL"


class SchemaCompatibilityClassification(str, Enum):
    """Deterministic classification of DDL schema change compatibility."""
    SAFE_AUTOMATIC = "SAFE_AUTOMATIC"
    SAFE_WITH_BARRIER = "SAFE_WITH_BARRIER"
    REQUIRES_DATA_TRANSFORMATION = "REQUIRES_DATA_TRANSFORMATION"
    REQUIRES_APPROVAL = "REQUIRES_APPROVAL"
    CUTOVER_BLOCKING = "CUTOVER_BLOCKING"
    UNSUPPORTED = "UNSUPPORTED"
    DESTRUCTIVE = "DESTRUCTIVE"
    AMBIGUOUS = "AMBIGUOUS"


class SchemaEvolutionPolicyDecision(str, Enum):
    """Backend-authoritative schema evolution policy action decision."""
    AUTO_APPLIES = "AUTO_APPLIES"
    PAUSES_AND_APPLIES = "PAUSES_AND_APPLIES"
    REQUIRES_APPROVAL = "REQUIRES_APPROVAL"
    REQUIRES_TRANSFORMATION = "REQUIRES_TRANSFORMATION"
    BLOCKS_CDC = "BLOCKS_CDC"
    REQUIRES_RESTART = "REQUIRES_RESTART"
    REQUIRES_MANUAL_INTERVENTION = "REQUIRES_MANUAL_INTERVENTION"


class SchemaTransitionState(str, Enum):
    """Authoritative state machine tracking schema transition lifecycle."""
    DETECTED = "DETECTED"
    BARRIER_ESTABLISHED = "BARRIER_ESTABLISHED"
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    TARGET_DDL_STARTED = "TARGET_DDL_STARTED"
    TARGET_DDL_APPLIED = "TARGET_DDL_APPLIED"
    TARGET_VERIFIED = "TARGET_VERIFIED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class TargetDriftClassification(str, Enum):
    """Out-of-band target schema drift classification."""
    NO_DRIFT = "NO_DRIFT"
    COMPATIBLE_DRIFT = "COMPATIBLE_DRIFT"
    CONFLICTING_DRIFT = "CONFLICTING_DRIFT"
    UNKNOWN_DRIFT = "UNKNOWN_DRIFT"


class CDCSchemaVersion:
    """
    Identity-bound, immutable canonical schema version definition.
    Binds migration_id, job_id, run_id, cdc_session_id, engine, database, schema, table, and columns.
    """

    def __init__(
        self,
        identity: CDCEventIdentity,
        source_engine: str,
        database_name: str,
        schema_name: str,
        table_name: str,
        columns: List[Dict[str, Any]],
        primary_key_columns: Optional[List[str]] = None,
        version_number: int = 1,
        schema_version_id: Optional[str] = None,
        mapping_rules: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.identity = identity
        self.source_engine = source_engine.upper()
        self.database_name = database_name
        self.schema_name = schema_name
        self.table_name = table_name
        self.columns = columns  # List of dicts e.g. [{"name": "id", "type": "INTEGER", "nullable": False, "default": None}]
        self.primary_key_columns = primary_key_columns or []
        self.version_number = version_number
        self.mapping_rules = mapping_rules or {}

        if not schema_version_id:
            raw_fingerprint = f"{self.identity.cdc_session_id}:{self.table_name}:v{version_number}:{str(self.columns)}:{str(self.primary_key_columns)}"
            hash_str = hashlib.sha256(raw_fingerprint.encode("utf-8")).hexdigest()[:12]
            self.schema_version_id = f"sch-v{version_number}-{hash_str}"
        else:
            self.schema_version_id = schema_version_id

        self.created_at = datetime.datetime.now(datetime.timezone.utc).isoformat()

    def get_column(self, col_name: str) -> Optional[Dict[str, Any]]:
        for col in self.columns:
            if col["name"].lower() == col_name.lower():
                return col
        return None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version_id": self.schema_version_id,
            "version_number": self.version_number,
            "identity": self.identity.to_dict(),
            "source_engine": self.source_engine,
            "database_name": self.database_name,
            "schema_name": self.schema_name,
            "table_name": self.table_name,
            "columns": self.columns,
            "primary_key_columns": self.primary_key_columns,
            "mapping_rules": self.mapping_rules,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CDCSchemaVersion":
        identity = CDCEventIdentity.from_dict(data["identity"])
        return cls(
            identity=identity,
            source_engine=data.get("source_engine", "POSTGRESQL"),
            database_name=data.get("database_name", "db"),
            schema_name=data.get("schema_name", "public"),
            table_name=data.get("table_name", "tbl"),
            columns=data.get("columns", []),
            primary_key_columns=data.get("primary_key_columns", []),
            version_number=data.get("version_number", 1),
            schema_version_id=data.get("schema_version_id"),
            mapping_rules=data.get("mapping_rules"),
        )


class CDCDDLEvent:
    """
    Identity-bound DDL change event.
    Contains position, old and proposed schema version IDs, sanitized DDL, and compatibility.
    """

    def __init__(
        self,
        identity: CDCEventIdentity,
        source_position: CDCSourcePosition,
        canonical_operation: DDLOperationType,
        affected_database: str,
        affected_schema: str,
        affected_table: str,
        old_schema_version_id: str,
        proposed_schema_version_id: str,
        raw_ddl_statement: str,
        transaction_id: Optional[str] = None,
        operation_metadata: Optional[Dict[str, Any]] = None,
        ddl_event_id: Optional[str] = None,
    ) -> None:
        self.ddl_event_id = ddl_event_id or f"ddl-{identity.cdc_session_id}-{int(datetime.datetime.now(datetime.timezone.utc).timestamp()*1000)}"
        self.identity = identity
        self.source_position = source_position
        self.canonical_operation = canonical_operation
        self.affected_database = affected_database
        self.affected_schema = affected_schema
        self.affected_table = affected_table
        self.old_schema_version_id = old_schema_version_id
        self.proposed_schema_version_id = proposed_schema_version_id
        self.raw_ddl_statement = sanitize_ddl_statement(raw_ddl_statement)
        self.transaction_id = transaction_id
        self.operation_metadata = operation_metadata or {}
        self.captured_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
        self.compatibility: SchemaCompatibilityClassification = SchemaCompatibilityClassification.AMBIGUOUS

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ddl_event_id": self.ddl_event_id,
            "identity": self.identity.to_dict(),
            "source_position": self.source_position.to_dict(),
            "canonical_operation": self.canonical_operation.value,
            "affected_database": self.affected_database,
            "affected_schema": self.affected_schema,
            "affected_table": self.affected_table,
            "old_schema_version_id": self.old_schema_version_id,
            "proposed_schema_version_id": self.proposed_schema_version_id,
            "raw_ddl_statement": self.raw_ddl_statement,
            "transaction_id": self.transaction_id,
            "operation_metadata": self.operation_metadata,
            "captured_at": self.captured_at,
            "compatibility": self.compatibility.value,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CDCDDLEvent":
        identity = CDCEventIdentity.from_dict(data["identity"])
        pos = parse_source_position(data["source_position"])
        op = DDLOperationType(data["canonical_operation"])
        evt = cls(
            identity=identity,
            source_position=pos,
            canonical_operation=op,
            affected_database=data["affected_database"],
            affected_schema=data["affected_schema"],
            affected_table=data["affected_table"],
            old_schema_version_id=data["old_schema_version_id"],
            proposed_schema_version_id=data["proposed_schema_version_id"],
            raw_ddl_statement=data.get("raw_ddl_statement", ""),
            transaction_id=data.get("transaction_id"),
            operation_metadata=data.get("operation_metadata"),
            ddl_event_id=data.get("ddl_event_id"),
        )
        if "compatibility" in data:
            evt.compatibility = SchemaCompatibilityClassification(data["compatibility"])
        return evt

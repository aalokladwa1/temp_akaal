from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Any, Optional

class HookPhase(str, Enum):
    BEFORE_DISCOVERY = "BEFORE_DISCOVERY"
    BEFORE_SCHEMA_MIGRATION = "BEFORE_SCHEMA_MIGRATION"
    AFTER_SCHEMA_MIGRATION = "AFTER_SCHEMA_MIGRATION"
    BEFORE_DATA_MIGRATION = "BEFORE_DATA_MIGRATION"
    AFTER_DATA_MIGRATION = "AFTER_DATA_MIGRATION"
    BEFORE_CUTOVER = "BEFORE_CUTOVER"
    AFTER_CUTOVER = "AFTER_CUTOVER"

@dataclass
class ColumnMapping:
    source_column: str
    target_column: str
    is_ignored: bool = False
    constant_value: Any = None
    expression: Optional[str] = None

@dataclass
class TableMapping:
    source_table: str
    target_table: str
    source_schema: Optional[str] = None
    target_schema: Optional[str] = None
    target_database: Optional[str] = None
    column_mappings: List[ColumnMapping] = field(default_factory=list)

@dataclass
class MappingConfiguration:
    table_mappings: List[TableMapping] = field(default_factory=list)

@dataclass
class IncrementalConfiguration:
    strategy: str = "FULL"  # "TIMESTAMP", "VERSION", "FULL"
    tracking_column: Optional[str] = None
    watermark_value: Any = None
    checkpoint_interval_rows: int = 1000

@dataclass
class TransformationRule:
    column_name: str
    rule_type: str  # "EXPRESSION", "DEFAULT", "TYPE_CONVERSION"
    expression: Optional[str] = None
    default_value: Any = None
    target_type: Optional[str] = None
    priority: int = 10
    condition: Optional[str] = None

@dataclass
class TransformationConfiguration:
    rules: Dict[str, List[TransformationRule]] = field(default_factory=dict) # table_name -> rules

@dataclass
class MaskingRule:
    column_name: str
    masking_strategy: str  # "REDACT", "HASH", "PARTIAL", "NULLIFY"
    salt: Optional[str] = None
    replacement_value: Any = None
    unmasked_length: int = 4
    mask_char: str = "x"

@dataclass
class MaskingConfiguration:
    policies: Dict[str, List[MaskingRule]] = field(default_factory=dict) # table_name -> rules

@dataclass
class SQLHook:
    sql_commands: List[str]
    phase: HookPhase = HookPhase.BEFORE_DATA_MIGRATION
    timeout_seconds: int = 30
    transactional: bool = True
    ignore_failures: bool = False
    rollback_on_failure: bool = True

@dataclass
class HookConfiguration:
    hooks: List[SQLHook] = field(default_factory=list)

@dataclass
class MigrationConfiguration:
    mapping: MappingConfiguration = field(default_factory=MappingConfiguration)
    incremental: IncrementalConfiguration = field(default_factory=IncrementalConfiguration)
    transformation: TransformationConfiguration = field(default_factory=TransformationConfiguration)
    masking: MaskingConfiguration = field(default_factory=MaskingConfiguration)
    hook: HookConfiguration = field(default_factory=HookConfiguration)

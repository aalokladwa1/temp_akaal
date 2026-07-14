from dataclasses import dataclass, field
from typing import Dict, Any, Tuple, Optional

@dataclass(frozen=True)
class TranslationResult:
    """
    Immutable domain model representing the result of compiling
    an abstract MigrationOperation into forward and rollback DDL syntax.
    """
    sql: str
    rollback_sql: Optional[str] = None
    warnings: Tuple[str, ...] = field(default_factory=tuple)
    metadata: Dict[str, Any] = field(default_factory=dict)

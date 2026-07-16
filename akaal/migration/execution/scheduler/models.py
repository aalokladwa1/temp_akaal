from dataclasses import dataclass, field
from typing import Tuple, Dict, Any
from akaal.migration.models import MigrationOperation

@dataclass(frozen=True)
class ScheduledOperation:
    """An immutable scheduled operation task wrapper paired with scheduler metadata."""
    operation: MigrationOperation
    priority: int = 1
    estimated_cost: float = 1.0
    resource_class: str = "DEFAULT"
    max_parallel_tables: int = 4

@dataclass(frozen=True)
class ExecutionWave:
    """An execution block consisting of independent operations running concurrently."""
    wave_id: int
    operations: Tuple[ScheduledOperation, ...]

@dataclass(frozen=True)
class ScheduledPlan:
    """Central representation of execution stages, diagnostics, and stages statistics."""
    waves: Tuple[ExecutionWave, ...]
    statistics: Dict[str, Any] = field(default_factory=dict)
    diagnostics: Tuple[str, ...] = field(default_factory=tuple)

from dataclasses import dataclass, field
from typing import Dict, Any

@dataclass(frozen=True)
class ValidationArtifact:
    execution_id: str
    passed: bool
    error_count: int
    warning_count: int
    raw_metrics: Dict[str, Any] = field(default_factory=dict)

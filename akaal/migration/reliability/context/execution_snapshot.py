from dataclasses import dataclass, field
from typing import Dict, Any, Tuple

@dataclass(frozen=True)
class ExecutionSnapshot:
    snapshot_id: str
    timestamp: float
    schema_fingerprint: str
    active_connections: int
    system_variables: Dict[str, Any] = field(default_factory=dict)

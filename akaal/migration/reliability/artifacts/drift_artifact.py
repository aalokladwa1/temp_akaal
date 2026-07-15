from dataclasses import dataclass, field
from typing import List

@dataclass(frozen=True)
class DriftArtifact:
    execution_id: str
    drift_detected: bool
    drifted_objects: List[str] = field(default_factory=list)

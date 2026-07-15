from dataclasses import dataclass

@dataclass(frozen=True)
class RollbackArtifact:
    execution_id: str
    step_count: int
    rollback_possible: bool

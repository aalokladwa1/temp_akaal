from dataclasses import dataclass

@dataclass(frozen=True)
class SimulationArtifact:
    execution_id: str
    time_ms: float
    bytes_used: int
    cost: float

from dataclasses import dataclass

@dataclass(frozen=True)
class RuntimeMetadata:
    pipeline_run_id: str
    started_at: float
    caller_identity: str
    target_environment: str  # dev, staging, prod

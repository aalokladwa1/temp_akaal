from dataclasses import dataclass

@dataclass(frozen=True)
class CertificationArtifact:
    execution_id: str
    compliant: bool
    rules_checked: int
    rules_failed: int

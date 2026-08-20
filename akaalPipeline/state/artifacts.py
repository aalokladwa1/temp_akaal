"""akaalPipeline.state.artifacts
===============================
Fingerprinted, immutable motherboard artifacts.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Mapping
from akaalPipeline.contracts.errors import PipelineError, PipelineErrorCode
from akaalPipeline.contracts.serialization import canonical_fingerprint, canonical_serialize, deep_freeze


@dataclass(frozen=True)
class ImmutableArtifact:
    artifact_id: str
    artifact_type: str  # e.g. "initialization", "execution_plan", "policy_decision", "evidence"
    fingerprint: str
    content: Mapping[str, Any]
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def __post_init__(self) -> None:
        object.__setattr__(self, "content", deep_freeze(self.content))
        expected = canonical_fingerprint(self.content)
        if self.fingerprint != expected:
            raise ValueError(f"Artifact fingerprint mismatch: stored {self.fingerprint!r} != calculated {expected!r}")

    @classmethod
    def create(cls, artifact_id: str, artifact_type: str, content: Mapping[str, Any]) -> ImmutableArtifact:
        fingerprint = canonical_fingerprint(content)
        return cls(
            artifact_id=artifact_id,
            artifact_type=artifact_type,
            fingerprint=fingerprint,
            content=content,
        )

    def to_dict(self) -> dict:
        return {
            "artifact_id": self.artifact_id,
            "artifact_type": self.artifact_type,
            "fingerprint": self.fingerprint,
            "content": dict(self.content),
            "created_at": self.created_at,
        }


    @classmethod
    def from_dict(cls, data: dict) -> ImmutableArtifact:
        return cls(
            artifact_id=data["artifact_id"],
            artifact_type=data["artifact_type"],
            fingerprint=data["fingerprint"],
            content=dict(data["content"]),
            created_at=data.get("created_at", datetime.now(timezone.utc).isoformat()),
        )


class ArtifactRegistry:
    def __init__(self) -> None:
        self._artifacts: dict[str, ImmutableArtifact] = {}

    def register(self, artifact: ImmutableArtifact) -> None:
        if artifact.artifact_id in self._artifacts:
            existing = self._artifacts[artifact.artifact_id]
            if existing.fingerprint != artifact.fingerprint:
                raise PipelineError(
                    PipelineErrorCode.INVALID_REQUEST,
                    f"Attempted to overwrite immutable artifact {artifact.artifact_id!r} with different content.",
                )
            return
        self._artifacts[artifact.artifact_id] = artifact

    def get(self, artifact_id: str) -> ImmutableArtifact:
        if artifact_id not in self._artifacts:
            raise PipelineError(PipelineErrorCode.INVALID_REQUEST, f"Artifact {artifact_id!r} not found.")
        return self._artifacts[artifact_id]

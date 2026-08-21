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


import sqlite3
from typing import Any, Mapping, Optional


class ArtifactRegistry:
    def __init__(self) -> None:
        self._artifacts: dict[str, ImmutableArtifact] = {}

    def register(self, artifact: ImmutableArtifact, conn: Optional[sqlite3.Connection] = None) -> None:
        if artifact.artifact_id in self._artifacts:
            existing = self._artifacts[artifact.artifact_id]
            if existing.fingerprint != artifact.fingerprint:
                raise PipelineError(
                    PipelineErrorCode.INVALID_REQUEST,
                    f"Attempted to overwrite immutable artifact {artifact.artifact_id!r} with different content.",
                )
        self._artifacts[artifact.artifact_id] = artifact

        if conn is not None:
            cur = conn.execute("SELECT fingerprint FROM immutable_artifacts WHERE artifact_id = ?", (artifact.artifact_id,))
            row = cur.fetchone()
            if row is not None:
                if row["fingerprint"] != artifact.fingerprint:
                    raise PipelineError(
                        PipelineErrorCode.INVALID_REQUEST,
                        f"Attempted to overwrite immutable artifact {artifact.artifact_id!r} with different content.",
                    )
                return
            conn.execute(
                """
                INSERT INTO immutable_artifacts (artifact_id, artifact_type, fingerprint, content, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    artifact.artifact_id,
                    artifact.artifact_type,
                    artifact.fingerprint,
                    canonical_serialize(artifact.content),
                    artifact.created_at,
                ),
            )

    def get(self, artifact_id: str, conn: Optional[sqlite3.Connection] = None) -> ImmutableArtifact:
        if artifact_id in self._artifacts:
            return self._artifacts[artifact_id]

        if conn is not None:
            cur = conn.execute("SELECT * FROM immutable_artifacts WHERE artifact_id = ?", (artifact_id,))
            row = cur.fetchone()
            if row is not None:
                import json
                art = ImmutableArtifact(
                    artifact_id=row["artifact_id"],
                    artifact_type=row["artifact_type"],
                    fingerprint=row["fingerprint"],
                    content=json.loads(row["content"]),
                    created_at=row["created_at"],
                )
                self._artifacts[artifact_id] = art
                return art

        raise PipelineError(PipelineErrorCode.INVALID_REQUEST, f"Artifact {artifact_id!r} not found.")

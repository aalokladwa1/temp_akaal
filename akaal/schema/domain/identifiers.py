"""
AKAAL Platform 5 — Strongly Typed Identifiers

Provides immutable type-safe value objects for entity identities across Platform 5.
"""

from dataclasses import dataclass
import uuid


@dataclass(frozen=True)
class VersionID:
    value: str

    @classmethod
    def generate(cls) -> "VersionID":
        return cls(value=f"v5-{uuid.uuid4().hex[:12]}")

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class SnapshotID:
    value: str

    @classmethod
    def generate(cls) -> "SnapshotID":
        return cls(value=f"snap-{uuid.uuid4().hex[:12]}")

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class TransactionID:
    value: str

    @classmethod
    def generate(cls) -> "TransactionID":
        return cls(value=f"tx-{uuid.uuid4().hex[:12]}")

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class OperationID:
    value: str

    @classmethod
    def generate(cls) -> "OperationID":
        return cls(value=f"op-{uuid.uuid4().hex[:12]}")

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class CheckpointID:
    value: str

    @classmethod
    def generate(cls) -> "CheckpointID":
        return cls(value=f"chk-{uuid.uuid4().hex[:12]}")

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class SchemaIdentifier:
    namespace: str
    name: str

    def __str__(self) -> str:
        return f"{self.namespace}.{self.name}" if self.namespace else self.name

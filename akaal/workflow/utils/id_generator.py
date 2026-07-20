"""Deterministic Identity Generators for AKAAL Workflow Platform."""

from typing import Protocol
import uuid


class IIdGenerator(Protocol):
    """Abstract interface for generating unique identifiers."""
    
    def generate_uuid(self) -> str:
        """Generate a unique string identifier."""
        ...
        
    def generate_idempotency_key(self, prefix: str = "idemp") -> str:
        """Generate a deterministic or unique idempotency key."""
        ...


class UUIDIdGenerator:
    """Production identity generator using random UUIDv4."""
    
    def generate_uuid(self) -> str:
        return str(uuid.uuid4())
        
    def generate_idempotency_key(self, prefix: str = "idemp") -> str:
        return f"{prefix}-{uuid.uuid4()}"


class DeterministicIdGenerator:
    """Deterministic identity generator for reproducible replay testing."""
    
    def __init__(self, prefix: str = "test-id") -> None:
        self._prefix = prefix
        self._counter = 0

    def generate_uuid(self) -> str:
        self._counter += 1
        return f"{self._prefix}-{self._counter:06d}"

    def generate_idempotency_key(self, prefix: str = "idemp") -> str:
        self._counter += 1
        return f"{prefix}-{self._prefix}-{self._counter:06d}"

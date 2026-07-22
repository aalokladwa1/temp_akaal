"""
Abstract Signing Provider Interface.
"""

from abc import ABC, abstractmethod
from typing import Optional


class ISigningProvider(ABC):
    """Abstract Interface for Report Digital Signing Providers."""

    @abstractmethod
    def sign_payload(self, payload: bytes) -> str:
        """Generate signature for report binary payload."""
        pass

    @abstractmethod
    def verify_signature(self, payload: bytes, signature: str) -> bool:
        """Verify signature for report binary payload."""
        pass

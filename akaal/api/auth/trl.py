"""
Token Revocation List (TRL) for JWT Management.
"""

from typing import Set


class TokenRevocationList:
    """Thread-safe Token Revocation List (TRL)."""

    def __init__(self) -> None:
        self._revoked_jtis: Set[str] = set()

    def revoke(self, jti: str) -> None:
        self._revoked_jtis.add(jti)

    def is_revoked(self, jti: str) -> bool:
        return jti in self._revoked_jtis

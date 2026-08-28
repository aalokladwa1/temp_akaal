"""akaalPipeline.security.cache
==============================
Multi-process safe, revision-aware L1 Authorization Cache Manager.
Authoritative security revision in SQLite is canonical truth.
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple


class AuthorizationCacheManager:
    """Revision-aware L1 authorization decision cache."""

    def __init__(self) -> None:
        self._cache: Dict[Tuple[str, str, int, str, str, str], bool] = {}

    def _make_key(
        self,
        tenant_id: str,
        principal_id: str,
        security_revision: int,
        permission_id: str,
        resource_type: str,
        resource_id: str,
    ) -> Tuple[str, str, int, str, str, str]:
        return (tenant_id, principal_id, security_revision, permission_id, resource_type, resource_id)

    def get(
        self,
        tenant_id: str,
        principal_id: str,
        current_authoritative_revision: int,
        permission_id: str,
        resource_type: str,
        resource_id: str,
    ) -> Optional[bool]:
        """
        Get cached authorization decision.
        Returns None if cache miss or if revision has advanced.
        """
        key = self._make_key(
            tenant_id, principal_id, current_authoritative_revision,
            permission_id, resource_type, resource_id
        )
        return self._cache.get(key)

    def put(
        self,
        tenant_id: str,
        principal_id: str,
        security_revision: int,
        permission_id: str,
        resource_type: str,
        resource_id: str,
        decision: bool,
    ) -> None:
        """Cache an authorization decision tagged with the current security revision."""
        key = self._make_key(
            tenant_id, principal_id, security_revision,
            permission_id, resource_type, resource_id
        )
        self._cache[key] = decision

    def clear(self) -> None:
        """Explicitly clear in-memory cache."""
        self._cache.clear()

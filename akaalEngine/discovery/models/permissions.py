"""
akaalEngine.discovery.models.permissions
========================================
Authoritative three-state permission and privilege fact models.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from types import MappingProxyType
from typing import Any, Mapping, Optional, Sequence, Tuple


class ThreeStatePermission(str, Enum):
    """
    Three-state factual truth model for permissions.
    Zero default-true assumptions; UNKNOWN is never treated as PROVEN.
    """
    PROVEN = "PROVEN"    # Tested explicitly and confirmed permitted
    DENIED = "DENIED"    # Tested explicitly and confirmed denied / unauthorized
    UNKNOWN = "UNKNOWN"  # Not probed or query failed with inconclusive result


@dataclass(frozen=True)
class PrivilegeFact:
    """Discovered privilege observation on a specific resource."""
    privilege_name: str
    resource_name: str
    resource_type: str = "TABLE"  # "TABLE", "SCHEMA", "CATALOG", "DATABASE", "STREAM", "BUCKET"
    state: ThreeStatePermission = ThreeStatePermission.UNKNOWN
    evidence_message: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "privilege_name": self.privilege_name,
            "resource_name": self.resource_name,
            "resource_type": self.resource_type,
            "state": self.state.value,
            "evidence_message": self.evidence_message,
        }


@dataclass(frozen=True)
class PermissionAssessment:
    """
    Complete permission evaluation for the connected user across source and target scopes.
    """
    read_only_verified: ThreeStatePermission = ThreeStatePermission.UNKNOWN
    metadata_catalog_read: ThreeStatePermission = ThreeStatePermission.UNKNOWN
    table_select_privileges: Tuple[PrivilegeFact, ...] = field(default_factory=tuple)
    target_ddl_create_privileges: Tuple[PrivilegeFact, ...] = field(default_factory=tuple)
    target_data_write_privileges: Tuple[PrivilegeFact, ...] = field(default_factory=tuple)
    cdc_log_mining_privileges: Tuple[PrivilegeFact, ...] = field(default_factory=tuple)
    cloud_storage_privileges: Tuple[PrivilegeFact, ...] = field(default_factory=tuple)
    streaming_acl_privileges: Tuple[PrivilegeFact, ...] = field(default_factory=tuple)
    sequence_privileges: Tuple[PrivilegeFact, ...] = field(default_factory=tuple)
    unauthorized_resources: Tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        for attr in (
            "table_select_privileges",
            "target_ddl_create_privileges",
            "target_data_write_privileges",
            "cdc_log_mining_privileges",
            "cloud_storage_privileges",
            "streaming_acl_privileges",
            "sequence_privileges",
            "unauthorized_resources",
        ):
            val = getattr(self, attr)
            if not isinstance(val, tuple):
                object.__setattr__(self, attr, tuple(val))

    def is_fully_authorized_for_discovery(self) -> bool:
        """Determines if the session has proven read access to metadata catalogs."""
        return self.metadata_catalog_read == ThreeStatePermission.PROVEN

    def to_dict(self) -> dict[str, Any]:
        return {
            "read_only_verified": self.read_only_verified.value,
            "metadata_catalog_read": self.metadata_catalog_read.value,
            "table_select_privileges": [p.to_dict() for p in self.table_select_privileges],
            "target_ddl_create_privileges": [p.to_dict() for p in self.target_ddl_create_privileges],
            "target_data_write_privileges": [p.to_dict() for p in self.target_data_write_privileges],
            "cdc_log_mining_privileges": [p.to_dict() for p in self.cdc_log_mining_privileges],
            "cloud_storage_privileges": [p.to_dict() for p in self.cloud_storage_privileges],
            "streaming_acl_privileges": [p.to_dict() for p in self.streaming_acl_privileges],
            "sequence_privileges": [p.to_dict() for p in self.sequence_privileges],
            "unauthorized_resources": list(self.unauthorized_resources),
        }

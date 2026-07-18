"""
Akaal — Permission Assessment Model
===================================
Granular evaluation of database metadata permissions.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any, List


class PermissionStatus(str, Enum):
    GRANTED = "GRANTED"
    DENIED = "DENIED"
    UNKNOWN = "UNKNOWN"


@dataclass
class PermissionItem:
    permission_name: str
    status: PermissionStatus = PermissionStatus.GRANTED
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "permission_name": self.permission_name,
            "status": self.status.value,
            "notes": self.notes,
        }


@dataclass
class PermissionAssessment:
    """Detailed permission evaluation across database capabilities."""
    metadata_permissions: PermissionItem = field(default_factory=lambda: PermissionItem("Metadata Read", PermissionStatus.GRANTED))
    schema_permissions: PermissionItem = field(default_factory=lambda: PermissionItem("Schema Read", PermissionStatus.GRANTED))
    table_permissions: PermissionItem = field(default_factory=lambda: PermissionItem("Table Metadata Read", PermissionStatus.GRANTED))
    storage_permissions: PermissionItem = field(default_factory=lambda: PermissionItem("Storage Stats Read", PermissionStatus.GRANTED))
    replication_permissions: PermissionItem = field(default_factory=lambda: PermissionItem("Replication Read", PermissionStatus.GRANTED))
    cluster_permissions: PermissionItem = field(default_factory=lambda: PermissionItem("Cluster Read", PermissionStatus.GRANTED))
    statistics_permissions: PermissionItem = field(default_factory=lambda: PermissionItem("Statistics Read", PermissionStatus.GRANTED))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "metadata_permissions": self.metadata_permissions.to_dict(),
            "schema_permissions": self.schema_permissions.to_dict(),
            "table_permissions": self.table_permissions.to_dict(),
            "storage_permissions": self.storage_permissions.to_dict(),
            "replication_permissions": self.replication_permissions.to_dict(),
            "cluster_permissions": self.cluster_permissions.to_dict(),
            "statistics_permissions": self.statistics_permissions.to_dict(),
        }

"""Security Context Model for RBAC & Tenant Isolation."""

from dataclasses import dataclass, field
from typing import Any, Tuple
from akaal.workflow.utils.serialization import compute_sha256


@dataclass(frozen=True, slots=True)
class SecurityContext:
    """Immutable security context for workflow execution and identity validation."""
    
    user_id: str = "system"
    tenant_id: str = "default"
    roles: Tuple[str, ...] = field(default_factory=tuple)
    permissions: Tuple[str, ...] = field(default_factory=tuple)
    token_id: str | None = None
    checksum: str = field(default="", init=False)

    def __post_init__(self) -> None:
        payload = {
            "user_id": self.user_id,
            "tenant_id": self.tenant_id,
            "roles": list(self.roles),
            "permissions": list(self.permissions),
            "token_id": self.token_id or "",
        }
        object.__setattr__(self, "checksum", compute_sha256(payload))

    def has_permission(self, permission: str) -> bool:
        """Check if permission is present in security context."""
        return permission in self.permissions or "admin" in self.roles

    def to_dict(self) -> dict[str, Any]:
        """Convert security context to dictionary."""
        return {
            "user_id": self.user_id,
            "tenant_id": self.tenant_id,
            "roles": list(self.roles),
            "permissions": list(self.permissions),
            "token_id": self.token_id,
            "checksum": self.checksum,
        }

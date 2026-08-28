"""akaalPipeline.security.permission_registry
==========================================
Canonical immutable registry of enterprise permissions.
Operations are code-defined; roles and grants are dynamic and persisted.
"""

from __future__ import annotations

from typing import FrozenSet


class UnknownPermissionError(ValueError):
    """Raised when an unrecognized permission string is encountered or attempted to be granted."""
    pass


class PermissionRegistry:
    """Canonical, versioned, immutable vocabulary of all valid enterprise permissions."""

    REGISTRY_VERSION = "1.0.0"

    # Migration Operations
    MIGRATION_CREATE = "migration.create"
    MIGRATION_PLAN = "migration.plan"
    MIGRATION_CONFIGURE = "migration.configure"
    MIGRATION_VALIDATE = "migration.validate"
    MIGRATION_EXECUTE = "migration.execute"
    MIGRATION_CANCEL = "migration.cancel"
    MIGRATION_PAUSE = "migration.pause"
    MIGRATION_RESUME = "migration.resume"
    MIGRATION_RECOVER = "migration.recover"
    MIGRATION_ARCHIVE = "migration.archive"
    MIGRATION_READ = "migration.read"
    MIGRATION_CUTOVER = "migration.cutover"
    MIGRATION_ADMIN_MANAGE = "migration.admin.manage"
    MIGRATION_GATE_OVERRIDE = "migration.gate.override"

    # Identity & Access Management
    IDENTITY_PRINCIPAL_CREATE = "identity.principal.create"
    IDENTITY_PRINCIPAL_READ = "identity.principal.read"
    IDENTITY_PRINCIPAL_UPDATE = "identity.principal.update"
    IDENTITY_PRINCIPAL_DISABLE = "identity.principal.disable"
    IDENTITY_PRINCIPAL_DELETE = "identity.principal.delete"
    IDENTITY_GROUP_MANAGE = "identity.group.manage"
    IDENTITY_ROLE_CREATE = "identity.role.create"
    IDENTITY_ROLE_READ = "identity.role.read"
    IDENTITY_ROLE_UPDATE = "identity.role.update"
    IDENTITY_ROLE_DELETE = "identity.role.delete"
    IDENTITY_GRANT_CREATE = "identity.grant.create"
    IDENTITY_GRANT_REVOKE = "identity.grant.revoke"
    IDENTITY_TOKEN_ISSUE = "identity.token.issue"
    IDENTITY_TOKEN_REVOKE = "identity.token.revoke"
    IDENTITY_JIT_REQUEST = "identity.jit.request"
    IDENTITY_JIT_APPROVE = "identity.jit.approve"

    # Governance & Approval
    GOVERNANCE_APPROVAL_REQUEST = "governance.approval.request"
    GOVERNANCE_APPROVAL_SUBMIT = "governance.approval.submit"
    GOVERNANCE_APPROVAL_REVOKE = "governance.approval.revoke"
    GOVERNANCE_POLICY_MANAGE = "governance.policy.manage"
    GOVERNANCE_POLICY_BYPASS = "governance.policy.bypass"
    GOVERNANCE_SOD_OVERRIDE = "governance.sod.override"

    # Security & Keystore
    SECURITY_KEY_ROTATE = "security.key.rotate"
    SECURITY_KEY_REVOKE = "security.key.revoke"
    SECURITY_AUDIT_READ = "security.audit.read"
    SECURITY_THREAT_READ = "security.threat.read"
    SECURITY_THREAT_ACK = "security.threat.ack"

    # System & Multi-Tenant Platform
    SYSTEM_BOOTSTRAP = "system.bootstrap"
    SYSTEM_PLATFORM_ADMIN = "system.platform.admin"
    SYSTEM_TENANT_CREATE = "system.tenant.create"
    SYSTEM_TENANT_SUSPEND = "system.tenant.suspend"
    SYSTEM_TENANT_DECOMMISSION = "system.tenant.decommission"
    SYSTEM_WORKSPACE_CREATE = "system.workspace.create"
    SYSTEM_PROJECT_CREATE = "system.project.create"

    ALL_PERMISSIONS: FrozenSet[str] = frozenset({
        MIGRATION_CREATE,
        MIGRATION_PLAN,
        MIGRATION_CONFIGURE,
        MIGRATION_VALIDATE,
        MIGRATION_EXECUTE,
        MIGRATION_CANCEL,
        MIGRATION_PAUSE,
        MIGRATION_RESUME,
        MIGRATION_RECOVER,
        MIGRATION_ARCHIVE,
        MIGRATION_READ,
        MIGRATION_CUTOVER,
        MIGRATION_ADMIN_MANAGE,
        MIGRATION_GATE_OVERRIDE,
        IDENTITY_PRINCIPAL_CREATE,
        IDENTITY_PRINCIPAL_READ,
        IDENTITY_PRINCIPAL_UPDATE,
        IDENTITY_PRINCIPAL_DISABLE,
        IDENTITY_PRINCIPAL_DELETE,
        IDENTITY_GROUP_MANAGE,
        IDENTITY_ROLE_CREATE,
        IDENTITY_ROLE_READ,
        IDENTITY_ROLE_UPDATE,
        IDENTITY_ROLE_DELETE,
        IDENTITY_GRANT_CREATE,
        IDENTITY_GRANT_REVOKE,
        IDENTITY_TOKEN_ISSUE,
        IDENTITY_TOKEN_REVOKE,
        IDENTITY_JIT_REQUEST,
        IDENTITY_JIT_APPROVE,
        GOVERNANCE_APPROVAL_REQUEST,
        GOVERNANCE_APPROVAL_SUBMIT,
        GOVERNANCE_APPROVAL_REVOKE,
        GOVERNANCE_POLICY_MANAGE,
        GOVERNANCE_POLICY_BYPASS,
        GOVERNANCE_SOD_OVERRIDE,
        SECURITY_KEY_ROTATE,
        SECURITY_KEY_REVOKE,
        SECURITY_AUDIT_READ,
        SECURITY_THREAT_READ,
        SECURITY_THREAT_ACK,
        SYSTEM_BOOTSTRAP,
        SYSTEM_PLATFORM_ADMIN,
        SYSTEM_TENANT_CREATE,
        SYSTEM_TENANT_SUSPEND,
        SYSTEM_TENANT_DECOMMISSION,
        SYSTEM_WORKSPACE_CREATE,
        SYSTEM_PROJECT_CREATE,
    })

    @classmethod
    def is_valid(cls, permission_id: str) -> bool:
        """Check if a permission string is in the canonical registry."""
        return isinstance(permission_id, str) and permission_id in cls.ALL_PERMISSIONS

    @classmethod
    def assert_valid(cls, permission_id: str) -> None:
        """Assert that a permission is in the canonical registry. Fail closed if not."""
        if not cls.is_valid(permission_id):
            raise UnknownPermissionError(f"Unknown permission: {permission_id!r} not in PermissionRegistry")

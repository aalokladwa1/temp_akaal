"""
akaalEngine.connection.catalog.capability_resolver
==================================================
Fail-closed capability evaluation and purpose requirement resolution.
Guarantees UNKNOWN is never treated as SUPPORTED.
Enforces complete session admission across roles, required capabilities, required privileges, and all 13 SessionPurposes.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional, Sequence, Tuple

from akaalEngine.connection.catalog.provider_catalog import ProviderCatalog, default_provider_catalog
from akaalEngine.connection.models.capability import (
    CapabilitySupportStatus,
    PermissionSnapshot,
    StaticCapabilityManifest,
)
from akaalEngine.connection.models.endpoint import EndpointRole, EndpointSpec
from akaalEngine.connection.models.errors import (
    CapabilityMismatchError,
    ConnectionFailure,
    FailureCategory,
    PermissionDeniedError,
)
from akaalEngine.connection.models.session import SessionPurpose, SessionRequest

logger = logging.getLogger("akaalEngine.connection.catalog.capability_resolver")


class CapabilityResolver:
    """
    Evaluates endpoint capabilities and validates session admission with strict fail-closed truth.
    Answers: Can THIS endpoint, in THIS role, with THIS proven capability/permission state, satisfy THIS requested SessionPurpose?
    """

    def __init__(self, catalog: Optional[ProviderCatalog] = None) -> None:
        self.catalog = catalog or default_provider_catalog

    def evaluate_capabilities(
        self,
        provider_id: str,
        required_capabilities: Sequence[str],
    ) -> Tuple[bool, List[str], Dict[str, CapabilitySupportStatus]]:
        """
        Evaluates a set of required capabilities against a provider's static manifest.
        Returns: (all_supported, missing_capabilities, statuses_dict)
        """
        manifest = self.catalog.describe_provider(provider_id)
        missing: list[str] = []
        statuses: dict[str, CapabilitySupportStatus] = {}

        for cap in required_capabilities:
            status = manifest.get_status(cap)
            statuses[cap] = status
            if status != CapabilitySupportStatus.SUPPORTED:
                missing.append(cap)

        all_supported = (len(missing) == 0)
        return all_supported, missing, statuses

    def validate_admission(
        self,
        request: SessionRequest,
        permission_snapshot: Optional[PermissionSnapshot] = None,
    ) -> None:
        """
        Complete fail-closed admission validation answering:
        Can THIS endpoint, in THIS role, with THIS proven capability/permission state, satisfy THIS requested SessionPurpose?
        """
        spec = request.endpoint_spec
        purpose = request.purpose

        # 1. Probe Purposes Bootstrap: Avoid circular admission deadlocks
        # Health and permission probes must establish minimal sessions without requiring the very evidence they obtain.
        if purpose in (SessionPurpose.HEALTH_PROBE, SessionPurpose.PERMISSION_PROBE):
            # Verify provider is registered and basic spec validity
            self.catalog.get_strategy(spec.provider_id)
            return

        # 2. Validate caller restrictions (caller cannot weaken mandatory purpose safety)
        request.validate_restrictions()

        # 3. Retrieve authoritative manifest
        manifest = self.catalog.describe_provider(spec.provider_id)

        # 4. A. ROLE Validation: Validate EndpointRole against provider-supported roles
        if spec.role not in manifest.supported_roles and spec.role != EndpointRole.CUSTOM:
            supported_str = [r.value for r in manifest.supported_roles]
            msg = (
                f"Endpoint role '{spec.role.value}' is not supported by provider '{spec.provider_id}'. "
                f"Supported roles: {supported_str}"
            )
            failure = ConnectionFailure(
                error_code="ROLE_UNSUPPORTED",
                category=FailureCategory.CAPABILITY_MISMATCH,
                message=msg,
                retryable=False,
                provider_id=spec.provider_id,
                remediation=f"Configure endpoint role from supported list: {supported_str}",
            )
            raise CapabilityMismatchError(failure)

        # 5. B. REQUIRED CAPABILITIES Validation: Honor request.required_capabilities
        if request.required_capabilities:
            all_ok, missing, statuses = self.evaluate_capabilities(spec.provider_id, request.required_capabilities)
            if not all_ok:
                msg = (
                    f"Provider '{spec.provider_id}' cannot satisfy explicitly required capabilities: {missing}. "
                    f"Statuses: { {k: v.value for k, v in statuses.items() if k in missing} }"
                )
                failure = ConnectionFailure(
                    error_code="REQUIRED_CAPABILITY_UNSUPPORTED",
                    category=FailureCategory.CAPABILITY_MISMATCH,
                    message=msg,
                    retryable=False,
                    provider_id=spec.provider_id,
                    remediation=f"Ensure required capabilities {missing} are marked SUPPORTED.",
                )
                raise CapabilityMismatchError(failure)

        # 6. D. EVERY SESSION PURPOSE Validation: Specific capability & role constraints
        writable_purposes = (
            SessionPurpose.SCHEMA_DDL,
            SessionPurpose.BULK_TARGET_WRITE,
            SessionPurpose.CDC_APPLY,
            SessionPurpose.RECONCILIATION_REPAIR,
        )
        read_only_roles = (EndpointRole.REFERENCE, EndpointRole.VALIDATION)

        # Disallow writable purposes on explicitly read-only endpoint roles
        if purpose in writable_purposes and spec.role in read_only_roles:
            msg = (
                f"Cannot execute writable session purpose '{purpose.value}' on read-only endpoint role '{spec.role.value}'."
            )
            failure = ConnectionFailure(
                error_code="PURPOSE_ROLE_CONFLICT",
                category=FailureCategory.CAPABILITY_MISMATCH,
                message=msg,
                retryable=False,
                provider_id=spec.provider_id,
                remediation="Select a writable role (e.g. TARGET or STAGING) for mutating purposes.",
            )
            raise CapabilityMismatchError(failure)

        # Map each purpose to its physically required capabilities
        purpose_caps: list[str] = []
        if purpose in (SessionPurpose.DISCOVERY, SessionPurpose.METADATA, SessionPurpose.SCHEMA_READ):
            purpose_caps.append("SCHEMA_DISCOVERY")
        elif purpose == SessionPurpose.BULK_SOURCE_READ:
            purpose_caps.append("BULK_READ")
        elif purpose in (SessionPurpose.BULK_TARGET_WRITE, SessionPurpose.CDC_APPLY, SessionPurpose.RECONCILIATION_REPAIR):
            purpose_caps.append("BULK_WRITE")
        elif purpose == SessionPurpose.SCHEMA_DDL:
            # DDL purposes require schema discovery or DDL execution capabilities
            if not (manifest.is_capability_supported("SCHEMA_DISCOVERY") or manifest.is_capability_supported("BULK_WRITE")):
                purpose_caps.append("SCHEMA_DISCOVERY")
        elif purpose in (SessionPurpose.INCREMENTAL_POLLING, SessionPurpose.VALIDATION_READ):
            # Reading / polling requires BULK_READ or SCHEMA_DISCOVERY
            if not (manifest.is_capability_supported("BULK_READ") or manifest.is_capability_supported("SCHEMA_DISCOVERY")):
                purpose_caps.append("BULK_READ")
        elif purpose == SessionPurpose.CDC_CAPTURE:
            cdc_supported = (
                manifest.is_capability_supported("CDC_LOG_CAPTURE")
                or manifest.is_capability_supported("CHANGE_STREAMS")
                or manifest.is_capability_supported("CHANGE_DATA_FEED")
                or manifest.is_capability_supported("REDIS_STREAMS")
                or manifest.is_capability_supported("LOGICAL_REPLICATION")
            )
            if not cdc_supported:
                msg = f"Provider '{spec.provider_id}' does not physically support CDC log capture for purpose '{purpose.value}'."
                failure = ConnectionFailure(
                    error_code="CAPABILITY_CDC_UNSUPPORTED",
                    category=FailureCategory.CAPABILITY_MISMATCH,
                    message=msg,
                    retryable=False,
                    provider_id=spec.provider_id,
                    remediation="Select a CDC-capable provider or choose an alternative migration mode.",
                )
                raise CapabilityMismatchError(failure)

        if purpose_caps:
            all_ok, missing, statuses = self.evaluate_capabilities(spec.provider_id, purpose_caps)
            if not all_ok:
                msg = f"Provider '{spec.provider_id}' cannot satisfy session purpose '{purpose.value}'. Missing capabilities: {missing}"
                failure = ConnectionFailure(
                    error_code="PURPOSE_CAPABILITY_UNSUPPORTED",
                    category=FailureCategory.CAPABILITY_MISMATCH,
                    message=msg,
                    retryable=False,
                    provider_id=spec.provider_id,
                    remediation=f"Required capabilities {missing} are not marked as SUPPORTED for this connector.",
                )
                raise CapabilityMismatchError(failure)

        # 7. C. REQUIRED PRIVILEGES Validation: Honor explicit permission evidence if provided
        if permission_snapshot is not None:
            # Check explicitly requested privileges
            if request.required_privileges:
                missing_privs = [
                    p for p in request.required_privileges
                    if p not in permission_snapshot.granted_privileges or p in permission_snapshot.missing_privileges
                ]
                if missing_privs:
                    msg = f"Required privileges {missing_privs} are missing for authenticated principal."
                    failure = ConnectionFailure(
                        error_code="REQUIRED_PRIVILEGE_NOT_PROVEN",
                        category=FailureCategory.AUTHORIZATION_PERMISSION_FAILURE,
                        message=msg,
                        retryable=False,
                        provider_id=spec.provider_id,
                        remediation=f"Grant privileges {missing_privs} to the database user.",
                    )
                    raise PermissionDeniedError(failure)

            # Check purpose privilege alignment
            if purpose in writable_purposes and not permission_snapshot.can_write:
                msg = f"Session purpose '{purpose.value}' requires write privileges, but authenticated principal is read-only."
                failure = ConnectionFailure(
                    error_code="WRITE_PRIVILEGE_DENIED",
                    category=FailureCategory.AUTHORIZATION_PERMISSION_FAILURE,
                    message=msg,
                    retryable=False,
                    provider_id=spec.provider_id,
                )
                raise PermissionDeniedError(failure)

            if purpose == SessionPurpose.SCHEMA_DDL and not permission_snapshot.can_ddl:
                msg = f"Session purpose 'SCHEMA_DDL' requires DDL privileges, but authenticated principal lacks DDL rights."
                failure = ConnectionFailure(
                    error_code="DDL_PRIVILEGE_DENIED",
                    category=FailureCategory.AUTHORIZATION_PERMISSION_FAILURE,
                    message=msg,
                    retryable=False,
                    provider_id=spec.provider_id,
                )
                raise PermissionDeniedError(failure)

            if purpose == SessionPurpose.CDC_CAPTURE and not permission_snapshot.can_cdc:
                msg = f"Session purpose 'CDC_CAPTURE' requires replication/CDC privileges, but principal lacks CDC rights."
                failure = ConnectionFailure(
                    error_code="CDC_PRIVILEGE_DENIED",
                    category=FailureCategory.AUTHORIZATION_PERMISSION_FAILURE,
                    message=msg,
                    retryable=False,
                    provider_id=spec.provider_id,
                )
                raise PermissionDeniedError(failure)

    def validate_purpose_satisfaction(
        self,
        spec: EndpointSpec,
        purpose: SessionPurpose,
    ) -> None:
        """
        Legacy / convenience helper validating purpose satisfaction.
        """
        req = SessionRequest(purpose=purpose, endpoint_spec=spec)
        self.validate_admission(req)


# Global default resolver instance
default_capability_resolver = CapabilityResolver()

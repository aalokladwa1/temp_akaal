"""
AKAAL Universal Capability Manifest (P4.1).
============================================
Defines machine-readable, versioned, authoritative connector capability manifests.
Guarantees fail-closed evaluation: UNKNOWN != SUPPORTED.
Maintains multi-dimensional separation of Implementation, Registration, Pipeline,
Proof, and Support states.
"""

from typing import Dict, Any, List, Optional, Set
import datetime

from akaal.connectors.taxonomy import (
    ConnectorFamily,
    ConnectorRole,
    AuthenticationMechanism,
    ProofLevel,
    ProofState,
    ImplementationState,
    RegistrationState,
    PipelineState,
    SupportState,
    CapabilitySupportStatus,
)


class UniversalCapabilityManifest:
    """
    Authoritative, machine-readable capability manifest for a connector implementation.
    Specifies exact supported operations, authentication, features, restrictions, and proof level.
    """

    def __init__(
        self,
        connector_id: str,
        family: ConnectorFamily,
        vendor_name: str,
        system_type: str,
        connector_version: str = "1.0.0",
        manifest_version: str = "1.0.0",
        role: ConnectorRole = ConnectorRole.BOTH,
        supported_auth_mechanisms: Optional[List[AuthenticationMechanism]] = None,
        supports_tls: bool = True,
        supports_schema_discovery: bool = True,
        supports_bulk_read: bool = True,
        supports_bulk_write: bool = True,
        supports_streaming_read: bool = False,
        supports_streaming_write: bool = False,
        supports_partition_awareness: bool = False,
        supports_transactions: bool = True,
        supports_cdc_capture: bool = False,
        supports_continuous_sync: bool = False,
        supports_cutover: bool = False,
        supports_failback: bool = False,
        supports_lobs: bool = True,
        supports_checkpoint_resume: bool = True,
        supported_formats: Optional[List[str]] = None,
        supported_isolation_levels: Optional[List[str]] = None,
        known_restrictions: Optional[List[str]] = None,
        required_privileges: Optional[List[str]] = None,
        feature_flags: Optional[Dict[str, Any]] = None,
        capabilities_map: Optional[Dict[str, CapabilitySupportStatus]] = None,
        proof_level: ProofLevel = ProofLevel.STATIC_INSPECTION_ONLY,
        implementation_state: ImplementationState = ImplementationState.PARTIAL,
        registration_state: RegistrationState = RegistrationState.REGISTERED,
        pipeline_state: PipelineState = PipelineState.REACHABLE,
        support_state: SupportState = SupportState.PARTIAL,
        proof_state: ProofState = ProofState.UNIT_PROVEN,
    ) -> None:
        self.connector_id = str(connector_id).strip().lower()
        self.family = family
        self.vendor_name = vendor_name
        self.system_type = system_type.upper()
        self.connector_version = connector_version
        self.manifest_version = manifest_version
        self.role = role
        self.supported_auth_mechanisms = list(supported_auth_mechanisms or [AuthenticationMechanism.USERNAME_PASSWORD])
        self.supports_tls = supports_tls
        self.supports_schema_discovery = supports_schema_discovery
        self.supports_bulk_read = supports_bulk_read
        self.supports_bulk_write = supports_bulk_write
        self.supports_streaming_read = supports_streaming_read
        self.supports_streaming_write = supports_streaming_write
        self.supports_partition_awareness = supports_partition_awareness
        self.supports_transactions = supports_transactions
        self.supports_cdc_capture = supports_cdc_capture
        self.supports_continuous_sync = supports_continuous_sync
        self.supports_cutover = supports_cutover
        self.supports_failback = supports_failback
        self.supports_lobs = supports_lobs
        self.supports_checkpoint_resume = supports_checkpoint_resume
        self.supported_formats = list(supported_formats or [])
        self.supported_isolation_levels = list(supported_isolation_levels or ["READ_COMMITTED"])
        self.known_restrictions = list(known_restrictions or [])
        self.required_privileges = list(required_privileges or [])
        self.feature_flags = dict(feature_flags or {})
        self.capabilities_map = dict(capabilities_map or {})
        self.proof_level = proof_level
        self.implementation_state = implementation_state
        self.registration_state = registration_state
        self.pipeline_state = pipeline_state
        self.support_state = support_state
        self.proof_state = proof_state
        self.registered_at = datetime.datetime.now(datetime.timezone.utc).isoformat()

    def get_capability_status(self, capability_name: Optional[str]) -> CapabilitySupportStatus:
        """
        Evaluates capability support status.
        FAILS CLOSED: If capability is unknown, empty, or unspecified, returns UNKNOWN_NOT_PROVEN / UNSUPPORTED.
        UNKNOWN is NEVER interpreted as SUPPORTED.
        """
        if not capability_name:
            return CapabilitySupportStatus.UNKNOWN_NOT_PROVEN

        cap_key = str(capability_name).lower().strip()
        if cap_key in self.capabilities_map:
            return self.capabilities_map[cap_key]

        # Standard boolean flag mapping
        flag_map = {
            "tls": self.supports_tls,
            "schema_discovery": self.supports_schema_discovery,
            "bulk_read": self.supports_bulk_read,
            "bulk_write": self.supports_bulk_write,
            "streaming_read": self.supports_streaming_read,
            "streaming_write": self.supports_streaming_write,
            "partition_awareness": self.supports_partition_awareness,
            "transactions": self.supports_transactions,
            "cdc_capture": self.supports_cdc_capture,
            "continuous_sync": self.supports_continuous_sync,
            "cutover": self.supports_cutover,
            "failback": self.supports_failback,
            "lobs": self.supports_lobs,
            "checkpoint_resume": self.supports_checkpoint_resume,
        }

        if cap_key in flag_map:
            return CapabilitySupportStatus.SUPPORTED if flag_map[cap_key] else CapabilitySupportStatus.UNSUPPORTED

        # Unregistered capability fails closed
        return CapabilitySupportStatus.UNKNOWN_NOT_PROVEN

    def is_source_capable(self) -> bool:
        """Returns True if connector declares SOURCE or BOTH role support."""
        return self.role in (ConnectorRole.SOURCE, ConnectorRole.BOTH)

    def is_target_capable(self) -> bool:
        """Returns True if connector declares TARGET or BOTH role support."""
        return self.role in (ConnectorRole.TARGET, ConnectorRole.BOTH)

    def to_dict(self) -> Dict[str, Any]:
        """Machine-readable serializable representation with defensive copies."""
        return {
            "connector_id": self.connector_id,
            "family": self.family.value if hasattr(self.family, "value") else str(self.family),
            "vendor_name": self.vendor_name,
            "system_type": self.system_type,
            "connector_version": self.connector_version,
            "manifest_version": self.manifest_version,
            "role": self.role.value if hasattr(self.role, "value") else str(self.role),
            "supported_auth_mechanisms": [
                m.value if hasattr(m, "value") else str(m) for m in self.supported_auth_mechanisms
            ],
            "supports_tls": self.supports_tls,
            "supports_schema_discovery": self.supports_schema_discovery,
            "supports_bulk_read": self.supports_bulk_read,
            "supports_bulk_write": self.supports_bulk_write,
            "supports_streaming_read": self.supports_streaming_read,
            "supports_streaming_write": self.supports_streaming_write,
            "supports_partition_awareness": self.supports_partition_awareness,
            "supports_transactions": self.supports_transactions,
            "supports_cdc_capture": self.supports_cdc_capture,
            "supports_continuous_sync": self.supports_continuous_sync,
            "supports_cutover": self.supports_cutover,
            "supports_failback": self.supports_failback,
            "supports_lobs": self.supports_lobs,
            "supports_checkpoint_resume": self.supports_checkpoint_resume,
            "supported_formats": list(self.supported_formats),
            "supported_isolation_levels": list(self.supported_isolation_levels),
            "known_restrictions": list(self.known_restrictions),
            "required_privileges": list(self.required_privileges),
            "feature_flags": dict(self.feature_flags),
            "capabilities_map": {
                k: v.value if hasattr(v, "value") else str(v) for k, v in self.capabilities_map.items()
            },
            "proof_level": self.proof_level.value if hasattr(self.proof_level, "value") else str(self.proof_level),
            "implementation_state": self.implementation_state.value if hasattr(self.implementation_state, "value") else str(self.implementation_state),
            "registration_state": self.registration_state.value if hasattr(self.registration_state, "value") else str(self.registration_state),
            "pipeline_state": self.pipeline_state.value if hasattr(self.pipeline_state, "value") else str(self.pipeline_state),
            "support_state": self.support_state.value if hasattr(self.support_state, "value") else str(self.support_state),
            "proof_state": self.proof_state.value if hasattr(self.proof_state, "value") else str(self.proof_state),
            "registered_at": self.registered_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UniversalCapabilityManifest":
        family_str = data.get("family", ConnectorFamily.RELATIONAL_DATABASE.value)
        try:
            family = ConnectorFamily(family_str)
        except ValueError:
            family = ConnectorFamily.RELATIONAL_DATABASE

        role_str = data.get("role", ConnectorRole.BOTH.value)
        try:
            role = ConnectorRole(role_str)
        except ValueError:
            role = ConnectorRole.BOTH

        proof_str = data.get("proof_level", ProofLevel.STATIC_INSPECTION_ONLY.value)
        try:
            proof = ProofLevel(proof_str)
        except ValueError:
            proof = ProofLevel.STATIC_INSPECTION_ONLY

        impl_str = data.get("implementation_state", ImplementationState.PARTIAL.value)
        try:
            impl = ImplementationState(impl_str)
        except ValueError:
            impl = ImplementationState.PARTIAL

        reg_str = data.get("registration_state", RegistrationState.REGISTERED.value)
        try:
            reg = RegistrationState(reg_str)
        except ValueError:
            reg = RegistrationState.REGISTERED

        pipe_str = data.get("pipeline_state", PipelineState.REACHABLE.value)
        try:
            pipe = PipelineState(pipe_str)
        except ValueError:
            pipe = PipelineState.REACHABLE

        sup_str = data.get("support_state", SupportState.PARTIAL.value)
        try:
            sup = SupportState(sup_str)
        except ValueError:
            sup = SupportState.PARTIAL

        proof_state_str = data.get("proof_state", ProofState.UNIT_PROVEN.value)
        try:
            p_state = ProofState(proof_state_str)
        except ValueError:
            p_state = ProofState.UNIT_PROVEN

        auth_list = []
        for a_str in data.get("supported_auth_mechanisms", []):
            try:
                auth_list.append(AuthenticationMechanism(a_str))
            except ValueError:
                pass

        cap_map = {}
        for k, v in data.get("capabilities_map", {}).items():
            try:
                cap_map[k] = CapabilitySupportStatus(v)
            except ValueError:
                cap_map[k] = CapabilitySupportStatus.UNKNOWN_NOT_PROVEN

        return cls(
            connector_id=data.get("connector_id", "conn-unknown"),
            family=family,
            vendor_name=data.get("vendor_name", "Unknown"),
            system_type=data.get("system_type", "GENERIC"),
            connector_version=data.get("connector_version", "1.0.0"),
            manifest_version=data.get("manifest_version", "1.0.0"),
            role=role,
            supported_auth_mechanisms=auth_list or [AuthenticationMechanism.USERNAME_PASSWORD],
            supports_tls=data.get("supports_tls", True),
            supports_schema_discovery=data.get("supports_schema_discovery", True),
            supports_bulk_read=data.get("supports_bulk_read", True),
            supports_bulk_write=data.get("supports_bulk_write", True),
            supports_streaming_read=data.get("supports_streaming_read", False),
            supports_streaming_write=data.get("supports_streaming_write", False),
            supports_partition_awareness=data.get("supports_partition_awareness", False),
            supports_transactions=data.get("supports_transactions", True),
            supports_cdc_capture=data.get("supports_cdc_capture", False),
            supports_continuous_sync=data.get("supports_continuous_sync", False),
            supports_cutover=data.get("supports_cutover", False),
            supports_failback=data.get("supports_failback", False),
            supports_lobs=data.get("supports_lobs", True),
            supports_checkpoint_resume=data.get("supports_checkpoint_resume", True),
            supported_formats=data.get("supported_formats", []),
            supported_isolation_levels=data.get("supported_isolation_levels", ["READ_COMMITTED"]),
            known_restrictions=data.get("known_restrictions", []),
            required_privileges=data.get("required_privileges", []),
            feature_flags=data.get("feature_flags", {}),
            capabilities_map=cap_map,
            proof_level=proof,
            implementation_state=impl,
            registration_state=reg,
            pipeline_state=pipe,
            support_state=sup,
            proof_state=p_state,
        )

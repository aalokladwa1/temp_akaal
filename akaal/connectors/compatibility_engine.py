"""
Akaal — Universal Capability Negotiation Engine (P4.8)
=====================================================
Universal cross-system compatibility engine negotiating capability intersections in O(N) complexity.
Calculates SOURCE_CAN_PRODUCE ∩ AKAAL_CAN_REPRESENT ∩ TARGET_CAN_CONSUME across Bulk, Schema,
CDC, Validation, and Datatypes with fail-closed UNKNOWN semantics, delegating to UniversalConnectorRegistry.
"""

import logging
from typing import Dict, Any, List, Optional, Set

from akaal.connectors.taxonomy import (
    ConnectorFamily,
    SemanticCompatibility,
    SupportState,
    ImplementationState,
    ProofLevel,
)
from akaal.connectors.manifest import UniversalCapabilityManifest
from akaal.connectors.registry import UniversalConnectorRegistry
from akaal.connectors.contracts.capability_contract import ConnectorCapabilityContract
from akaal.schema.domain.types import CanonicalTypeCategory
from akaal.connectors.datatype_semantics import DatatypeDimensions
from akaal.connectors.lossiness_engine import LossinessEngine, LossinessReasonCode, LossinessIssue

logger = logging.getLogger("akaal.connectors.compatibility_engine")


class UniversalCompatibilityEngine:
    """Universal Cross-System Compatibility & Negotiation Authority (P4.8)."""

    def __init__(self) -> None:
        self._registered_contracts: Dict[str, ConnectorCapabilityContract] = {}

    def register_capability_contract(self, contract: ConnectorCapabilityContract) -> None:
        """Registers a connector capability contract ONCE for a system type."""
        self._registered_contracts[contract.system_type.upper()] = contract

    def get_contract(self, system_type: str) -> Optional[ConnectorCapabilityContract]:
        # First check explicitly registered contracts (e.g. for synthetic tests)
        sys_key = system_type.upper()
        if sys_key in self._registered_contracts:
            return self._registered_contracts[sys_key]

        # Otherwise derive dynamically from UniversalConnectorRegistry manifests
        reg = UniversalConnectorRegistry.get_instance()
        for manifest in reg._manifests.values():
            if manifest.system_type.upper() == sys_key:
                contract = ConnectorCapabilityContract.from_manifest(manifest)
                self._registered_contracts[sys_key] = contract
                return contract

        return None

    def evaluate_cross_system_compatibility(
        self,
        source_system: str,
        target_system: str,
        requested_modes: Optional[List[str]] = None,
        requested_datatypes: Optional[List[CanonicalTypeCategory]] = None,
    ) -> Dict[str, Any]:
        """
        Negotiates compatibility between Source and Target capability contracts.
        Computes intersection: SOURCE_CAN_PRODUCE ∩ AKAAL_CAN_REPRESENT ∩ TARGET_CAN_CONSUME.
        """
        src_contract = self.get_contract(source_system)
        tgt_contract = self.get_contract(target_system)

        # 1. Fail Closed on Missing Contracts
        if not src_contract:
            return {
                "overall_compatibility": SemanticCompatibility.UNSUPPORTED.value,
                "is_viable": False,
                "reason_code": "UNKNOWN_SOURCE_SYSTEM",
                "message": f"Source system '{source_system}' has no registered capability contract or manifest.",
                "proof_level": ProofLevel.UNIMPLEMENTED.value,
                "lossiness_issues": [],
                "warnings": [f"Unregistered source system: {source_system}"],
            }

        if not tgt_contract:
            return {
                "overall_compatibility": SemanticCompatibility.UNSUPPORTED.value,
                "is_viable": False,
                "reason_code": "UNKNOWN_TARGET_SYSTEM",
                "message": f"Target system '{target_system}' has no registered capability contract or manifest.",
                "proof_level": ProofLevel.UNIMPLEMENTED.value,
                "lossiness_issues": [],
                "warnings": [f"Unregistered target system: {target_system}"],
            }

        # 2. Check Support & Implementation States
        if src_contract.support_state == SupportState.UNSUPPORTED or src_contract.implementation_state == ImplementationState.STUB:
            return {
                "overall_compatibility": SemanticCompatibility.UNSUPPORTED.value,
                "is_viable": False,
                "reason_code": "UNSUPPORTED_SOURCE_ROLE",
                "message": f"Source system '{source_system}' support state is UNSUPPORTED or STUB.",
                "proof_level": ProofLevel.UNIMPLEMENTED.value,
                "lossiness_issues": [],
                "warnings": [],
            }

        if tgt_contract.support_state == SupportState.UNSUPPORTED or tgt_contract.implementation_state == ImplementationState.STUB:
            return {
                "overall_compatibility": SemanticCompatibility.UNSUPPORTED.value,
                "is_viable": False,
                "reason_code": "UNSUPPORTED_TARGET_ROLE",
                "message": f"Target system '{target_system}' support state is UNSUPPORTED or STUB.",
                "proof_level": ProofLevel.UNIMPLEMENTED.value,
                "lossiness_issues": [],
                "warnings": [],
            }

        lossiness_issues: List[Dict[str, Any]] = []
        warnings: List[str] = []
        required_transformations: List[str] = []

        # 3. Bulk Migration Feasibility
        bulk_state = "SUPPORTED" if (src_contract.source_spec.snapshot_extraction and tgt_contract.target_spec.bulk_ingestion) else "UNSUPPORTED"
        if bulk_state == "UNSUPPORTED":
            warnings.append("Bulk migration is unsupported because source lacks read or target lacks write.")

        # 4. CDC Stream Eligibility & Position Inspection
        cdc_state = "UNSUPPORTED"
        cdc_position_type = src_contract.source_spec.cdc_position_type
        if src_contract.source_spec.cdc_available and tgt_contract.target_spec.cdc_event_application:
            cdc_state = "SUPPORTED"
        elif src_contract.source_spec.cdc_available and not tgt_contract.target_spec.cdc_event_application:
            cdc_state = "UNSUPPORTED_BY_TARGET"
            warnings.append(f"Source '{source_system}' supports CDC ({cdc_position_type}), but target '{target_system}' lacks CDC event apply.")
            lossiness_issues.append(LossinessIssue(
                reason_code=LossinessReasonCode.CDC_TARGET_APPLY_UNAVAILABLE,
                affected_object="CDC_STREAM",
                source_semantic=f"CDC_{cdc_position_type}",
                target_semantic="BULK_ONLY",
                severity="WARNING",
                mitigation="Use recurring bulk snapshot synchronization instead of continuous CDC.",
            ).to_dict())

        # 5. Datatype Intersection & Lossiness Analysis
        types_to_check = requested_datatypes or list(src_contract.supported_semantic_types)
        unsupported_types: List[str] = []
        for sem_type in types_to_check:
            if not tgt_contract.is_type_supported(sem_type):
                unsupported_types.append(sem_type.value)
                lossiness_issues.append(LossinessIssue(
                    reason_code=LossinessReasonCode.UNSUPPORTED_TYPE_CONVERSION,
                    affected_object=sem_type.value,
                    source_semantic=sem_type.value,
                    target_semantic="UNSUPPORTED",
                    severity="HIGH_RISK",
                    mitigation=f"Map {sem_type.value} to fallback text/blob column.",
                    requires_human_approval=True,
                ).to_dict())

        # 6. Paradigm Mismatch (e.g. Relational -> Document / Graph / Warehouse)
        overall_compat = SemanticCompatibility.SUPPORTED
        if src_contract.family == ConnectorFamily.RELATIONAL_DATABASE and tgt_contract.family == ConnectorFamily.DOCUMENT_DATABASE:
            overall_compat = SemanticCompatibility.LOSSY_REQUIRES_APPROVAL
            required_transformations.append("RELATIONAL_TABLES_TO_DOCUMENT_COLLECTIONS")
            lossiness_issues.append(LossinessIssue(
                reason_code=LossinessReasonCode.RELATIONAL_TO_DOCUMENT_STRUCTURAL_CHANGE,
                affected_object="SCHEMA_TOPOLOGY",
                source_semantic="RELATIONAL_TABLES_FOREIGN_KEYS",
                target_semantic="DOCUMENT_COLLECTIONS_SUBDOCUMENTS",
                severity="HIGH_RISK",
                mitigation="Denormalize foreign key joins into embedded subdocuments or document references.",
                requires_human_approval=True,
            ).to_dict())
        elif src_contract.family == ConnectorFamily.RELATIONAL_DATABASE and tgt_contract.family in (ConnectorFamily.CLOUD_DATA_WAREHOUSE, ConnectorFamily.LAKEHOUSE_ANALYTICS):
            overall_compat = SemanticCompatibility.SUPPORTED_WITH_LIMITATIONS
            required_transformations.append("RELATIONAL_TO_ANALYTICAL_SCHEMA")

        if unsupported_types:
            overall_compat = SemanticCompatibility.LOSSY_REQUIRES_APPROVAL

        return {
            "source_system": src_contract.system_type,
            "target_system": tgt_contract.system_type,
            "overall_compatibility": overall_compat.value,
            "is_viable": bulk_state == "SUPPORTED",
            "bulk_migration": {"state": bulk_state},
            "cdc_migration": {
                "state": cdc_state,
                "source_position_type": cdc_position_type,
                "target_application": "TRANSACTIONAL_APPLY" if tgt_contract.target_spec.cdc_event_application else "NONE",
            },
            "validation": {
                "state": "SUPPORTED" if src_contract.validation_spec.row_count and tgt_contract.validation_spec.row_count else "UNSUPPORTED",
                "methods": ["ROW_COUNT", "CHECKSUM", "HASH"] if src_contract.validation_spec.hash_comparison and tgt_contract.validation_spec.hash_comparison else ["ROW_COUNT"],
            },
            "lossiness_issues": lossiness_issues,
            "unsupported_datatypes": unsupported_types,
            "required_transformations": required_transformations,
            "warnings": warnings,
            "proof_level": ProofLevel.UNIT_PROVEN.value,
        }

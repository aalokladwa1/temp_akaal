"""
Akaal — Identity Comparison & Planning Engine
=============================================
Computes comparison differences, determines compatibility classification, approval requirements,
and generates planning reports.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from akaal.core.comparison.models import IdentityDefinition, IdentityMode
from akaal.core.comparison.models.exceptions import IdentityDifference
from akaal.migration.models.identity import IdentityRuntimeState, IdentityStateConfidence, GeneratorValueSemantics


class CompatibilityCategory(str, Enum):
    COMPATIBLE = "Compatible"
    REQUIRES_RESEED = "Requires Reseed"
    REQUIRES_RECREATION = "Requires Recreation"
    REQUIRES_TRANSLATION = "Requires Translation"
    REQUIRES_MANUAL_APPROVAL = "Requires Manual Approval"
    UNSUPPORTED = "Unsupported"
    UNSAFE = "Unsafe"
    UNKNOWN = "Unknown"


class ApprovalRequirement(str, Enum):
    AUTOMATIC_MIGRATION = "automatic migration"
    ADMINISTRATOR_APPROVAL = "administrator approval"
    MIGRATION_MUST_STOP = "migration must stop"
    WARNING_ONLY = "warning only"
    MANUAL_RECONSTRUCTION = "manual reconstruction required"


@dataclass(frozen=True)
class IdentityDiagnostic:
    property_name: str
    severity: str
    description: str
    remediation: str
    safety_level: str


@dataclass(frozen=True)
class IdentityComparisonReport:
    source_metadata: Dict[str, Any]
    target_metadata: Dict[str, Any]
    summary: str
    compatibility_category: CompatibilityCategory
    recommended_action: str
    approval_requirement: ApprovalRequirement
    diagnostics: Tuple[IdentityDiagnostic, ...]
    blocking: bool


class IdentityComparisonEngine:
    """
    Comparison and migration planning engine for Feature 1 identity schemas.
    """

    @staticmethod
    def compare_and_plan(
        source_defn: Optional[IdentityDefinition],
        target_defn: Optional[IdentityDefinition],
        source_state: Optional[IdentityRuntimeState],
        target_state: Optional[IdentityRuntimeState],
        target_supported: bool = True
    ) -> IdentityComparisonReport:
        
        diagnostics: List[IdentityDiagnostic] = []
        
        # Build raw metadata dicts for reporting
        src_meta = {
            "mode": source_defn.mode.value if source_defn else "NONE",
            "start": source_defn.start if source_defn else None,
            "increment": source_defn.increment if source_defn else None,
            "min_value": source_defn.min_value if source_defn else None,
            "max_value": source_defn.max_value if source_defn else None,
            "cycle": source_defn.cycle if source_defn else None,
            "cache": source_defn.cache if source_defn else None,
            "current_value": source_state.current_generator_value if source_state else None,
            "semantics": source_state.value_semantics.value if source_state else "UNKNOWN"
        }
        
        tgt_meta = {
            "mode": target_defn.mode.value if target_defn else "NONE",
            "start": target_defn.start if target_defn else None,
            "increment": target_defn.increment if target_defn else None,
            "min_value": target_defn.min_value if target_defn else None,
            "max_value": target_defn.max_value if target_defn else None,
            "cycle": target_defn.cycle if target_defn else None,
            "cache": target_defn.cache if target_defn else None,
            "current_value": target_state.current_generator_value if target_state else None,
            "semantics": target_state.value_semantics.value if target_state else "UNKNOWN"
        }

        # 0. Check capability support
        if not target_supported:
            diag = IdentityDiagnostic(
                property_name="CAPABILITY",
                severity="CRITICAL",
                description="Target database version does not support native identity columns.",
                remediation="Translate native identity to sequence-trigger emulated fallback or manual migration.",
                safety_level="UNSAFE"
            )
            return IdentityComparisonReport(
                source_metadata=src_meta,
                target_metadata=tgt_meta,
                summary="Migration blocked: target capability mismatch.",
                compatibility_category=CompatibilityCategory.UNSUPPORTED,
                recommended_action="Use sequence-trigger translation fallback.",
                approval_requirement=ApprovalRequirement.MIGRATION_MUST_STOP,
                diagnostics=(diag,),
                blocking=True
            )

        # Handle None cases
        if source_defn is None and target_defn is None:
            return IdentityComparisonReport(
                source_metadata=src_meta,
                target_metadata=tgt_meta,
                summary="Both source and target have no identity settings defined.",
                compatibility_category=CompatibilityCategory.COMPATIBLE,
                recommended_action="No action required.",
                approval_requirement=ApprovalRequirement.AUTOMATIC_MIGRATION,
                diagnostics=(),
                blocking=False
            )

        if source_defn is not None and target_defn is None:
            diag = IdentityDiagnostic(
                property_name="IDENTITY_MODE",
                severity="CRITICAL",
                description="Source identity column does not exist on target.",
                remediation="Recreate column as an identity column.",
                safety_level="SAFE_WITH_DDL"
            )
            return IdentityComparisonReport(
                source_metadata=src_meta,
                target_metadata=tgt_meta,
                summary="Target column lacks identity definition present in source.",
                compatibility_category=CompatibilityCategory.REQUIRES_RECREATION,
                recommended_action="Recreate column with identity capabilities on target.",
                approval_requirement=ApprovalRequirement.ADMINISTRATOR_APPROVAL,
                diagnostics=(diag,),
                blocking=True
            )

        if source_defn is None and target_defn is not None:
            diag = IdentityDiagnostic(
                property_name="IDENTITY_MODE",
                severity="WARNING",
                description="Target column has identity definition but source does not.",
                remediation="Drop target identity to align with source.",
                safety_level="SAFE_WITH_DDL"
            )
            return IdentityComparisonReport(
                source_metadata=src_meta,
                target_metadata=tgt_meta,
                summary="Target column has unexpected identity definition.",
                compatibility_category=CompatibilityCategory.REQUIRES_RECREATION,
                recommended_action="Drop identity attribute on target column.",
                approval_requirement=ApprovalRequirement.ADMINISTRATOR_APPROVAL,
                diagnostics=(diag,),
                blocking=True
            )

        # 1. Structural Comparison
        recreation_required = False
        translation_required = False
        unsafe_difference = False

        if source_defn.increment != target_defn.increment:
            # If sign of increment changes, it is Unsafe
            if (source_defn.increment > 0 and target_defn.increment < 0) or (source_defn.increment < 0 and target_defn.increment > 0):
                unsafe_difference = True
                diagnostics.append(IdentityDiagnostic(
                    property_name="INCREMENT_SIGN",
                    severity="CRITICAL",
                    description=f"Unsafe increment sign flip: Source is {source_defn.increment}, Target is {target_defn.increment}.",
                    remediation="Manual verification required; sequences flow in opposite directions.",
                    safety_level="UNSAFE"
                ))
            else:
                recreation_required = True
                diagnostics.append(IdentityDiagnostic(
                    property_name="INCREMENT",
                    severity="CRITICAL",
                    description=f"Increment step mismatch: Source is {source_defn.increment}, Target is {target_defn.increment}.",
                    remediation="Recreate sequence / identity attribute with matching increment step.",
                    safety_level="UNSAFE_REBUILD"
                ))

        if source_defn.start != target_defn.start:
            recreation_required = True
            diagnostics.append(IdentityDiagnostic(
                property_name="START_VALUE",
                severity="WARNING",
                description=f"Start value mismatch: Source is {source_defn.start}, Target is {target_defn.start}.",
                remediation="Alter target identity restart value.",
                safety_level="SAFE_WITH_ALTER"
            ))

        if (source_defn.min_value != target_defn.min_value) or (source_defn.max_value != target_defn.max_value):
            recreation_required = True
            diagnostics.append(IdentityDiagnostic(
                property_name="BOUNDS",
                severity="WARNING",
                description="Min or Max value range boundaries mismatch.",
                remediation="Alter boundary settings on target sequence/column.",
                safety_level="SAFE_WITH_ALTER"
            ))

        if source_defn.cycle != target_defn.cycle:
            recreation_required = True
            diagnostics.append(IdentityDiagnostic(
                property_name="CYCLE",
                severity="WARNING",
                description=f"Cycle setting mismatch: Source is {source_defn.cycle}, Target is {target_defn.cycle}.",
                remediation="Alter cycle properties on target sequence.",
                safety_level="SAFE_WITH_ALTER"
            ))

        if source_defn.mode != target_defn.mode:
            translation_required = True
            diagnostics.append(IdentityDiagnostic(
                property_name="GENERATOR_MODE",
                severity="CRITICAL",
                description=f"Generator mode mismatch: Source is {source_defn.mode.value}, Target is {target_defn.mode.value}.",
                remediation="Translate column identity mode generation semantics.",
                safety_level="SAFE_WITH_ALTER"
            ))

        # 2. Runtime State Comparison
        reseed_required = False

        if source_state and target_state:
            src_val = source_state.current_generator_value
            tgt_val = target_state.current_generator_value
            
            if src_val is not None and tgt_val is not None:
                if source_defn.increment > 0:
                    if tgt_val < src_val:
                        reseed_required = True
                        diagnostics.append(IdentityDiagnostic(
                            property_name="CURRENT_VALUE",
                            severity="CRITICAL",
                            description=f"Target generator value ({tgt_val}) lags behind source ({src_val}). Collision risk.",
                            remediation="Reseed target generator state to safe-next index.",
                            safety_level="SAFE_RESEED"
                        ))
                else:
                    if tgt_val > src_val:
                        reseed_required = True
                        diagnostics.append(IdentityDiagnostic(
                            property_name="CURRENT_VALUE",
                            severity="CRITICAL",
                            description=f"Target generator value ({tgt_val}) is above source ({src_val}) for negative sequence.",
                            remediation="Reseed target generator state to safe-next index.",
                            safety_level="SAFE_RESEED"
                        ))

            # Semantics mismatch
            if source_state.value_semantics != target_state.value_semantics:
                diagnostics.append(IdentityDiagnostic(
                    property_name="VALUE_SEMANTICS",
                    severity="WARNING",
                    description=f"Value semantics mismatch: Source is {source_state.value_semantics.value}, Target is {target_state.value_semantics.value}.",
                    remediation="Align runtime boundary calculation logic.",
                    safety_level="SAFE_RESCALE"
                ))

        # 3. Resolve Compatibility Classification Category
        if unsafe_difference:
            category = CompatibilityCategory.UNSAFE
            action = "Migration halted due to opposite sequence directions."
            app = ApprovalRequirement.MIGRATION_MUST_STOP
            block = True
        elif recreation_required:
            category = CompatibilityCategory.REQUIRES_RECREATION
            action = "Rebuild or alter sequence properties to match source."
            app = ApprovalRequirement.ADMINISTRATOR_APPROVAL
            block = True
        elif translation_required:
            category = CompatibilityCategory.REQUIRES_TRANSLATION
            action = "Translate generation mode configuration."
            app = ApprovalRequirement.ADMINISTRATOR_APPROVAL
            block = True
        elif reseed_required:
            category = CompatibilityCategory.REQUIRES_RESEED
            action = "Reseed target generator sequence counter."
            app = ApprovalRequirement.ADMINISTRATOR_APPROVAL
            block = False
        else:
            category = CompatibilityCategory.COMPATIBLE
            action = "No structural synchronization required."
            app = ApprovalRequirement.AUTOMATIC_MIGRATION
            block = False

        # Construct summary description
        summary_parts = []
        if unsafe_difference:
            summary_parts.append("unsafe sequence parameters")
        if recreation_required:
            summary_parts.append("structural property mismatch")
        if translation_required:
            summary_parts.append("generator mode mismatch")
        if reseed_required:
            summary_parts.append("runtime state mismatch")
            
        summary = "Identity settings match." if not summary_parts else f"Identity differences detected: {', '.join(summary_parts)}."

        return IdentityComparisonReport(
            source_metadata=src_meta,
            target_metadata=tgt_meta,
            summary=summary,
            compatibility_category=category,
            recommended_action=action,
            approval_requirement=app,
            diagnostics=tuple(diagnostics),
            blocking=block
        )

"""
Akaal — Type Conversion Engine
==============================
Main engine orchestrating the type conversion pipeline, trace logging, and validation checks.
"""

import uuid
from typing import Dict, List, Optional, Tuple, Any
from akaal.core.conversion.api.models import (
    DataType, ConversionContext, ConversionPolicy, TypeCategory, ConversionStatus, DbVersion
)
from akaal.core.conversion.api.diagnostics import (
    Diagnostic, DiagnosticSeverity, DiagnosticCategory, StructuredRecommendation, RecommendationCategory
)
from akaal.core.conversion.api.observers import ConversionObserver
from akaal.core.conversion.internal.normalizer import TypeNormalizer
from akaal.core.conversion.internal.capabilities import ICapabilityProvider, NegotiationLevel, CapabilityType
from akaal.core.conversion.internal.registry import IRuleRegistry
from akaal.core.conversion.internal.rules import ConversionRule
from akaal.core.conversion.internal.scoring import ConfidenceScoringEngine, ConfidenceBreakdown
from akaal.core.conversion.exceptions import PolicyViolation, ValidationFailure, UnsupportedVendorError

from dataclasses import dataclass, field

@dataclass(frozen=True)
class TraceStep:
    step_name: str
    details: Dict[str, Any]


@dataclass(frozen=True)
class ConversionTrace:
    trace_id: str
    input_type: DataType
    normalized_type: DataType
    candidate_rules: Tuple[str, ...]
    selected_rule_id: str
    rejection_reasons: Dict[str, str]
    confidence_breakdown: Dict[str, float]
    steps: Tuple[TraceStep, ...]


@dataclass(frozen=True)
class ConversionResult:
    schema_version: str = "1.0.0"
    conversion_id: str = ""
    source_vendor: str = ""
    target_vendor: str = ""
    source_type: DataType = None
    target_type: DataType = None
    category: TypeCategory = None
    status: ConversionStatus = ConversionStatus.LOSSLESS
    diagnostics: Tuple[Diagnostic, ...] = field(default_factory=tuple)
    metadata: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0
    capability_flags: Dict[str, bool] = field(default_factory=dict)
    validation_result: bool = True
    trace: Optional[ConversionTrace] = None


class TypeConversionEngine:
    """Orchestrates the conversion mapping pipeline stages."""

    def __init__(
        self,
        registry: IRuleRegistry,
        capability_provider: ICapabilityProvider,
        normalizer: TypeNormalizer = None,
        scoring_engine: ConfidenceScoringEngine = None,
        observers: List[ConversionObserver] = None
    ):
        self._registry = registry
        self._capability_provider = capability_provider
        self._normalizer = normalizer or TypeNormalizer()
        self._scoring_engine = scoring_engine or ConfidenceScoringEngine()
        self._observers = observers or []

    def add_observer(self, observer: ConversionObserver) -> None:
        self._observers.append(observer)

    def convert(self, raw_type: str, context: ConversionContext) -> ConversionResult:
        """
        Main pipeline execution entry point.
        Translates a raw type string to a Target DataType under specified context constraints.
        """
        # 1. Normalize raw input type
        try:
            normalized_source = self._normalizer.normalize(raw_type, context.source_vendor, context.source_version)
        except Exception as e:
            for observer in self._observers:
                observer.on_error(e)
            raise e

        # Generate deterministic conversion tracking ID
        conv_id = self._generate_conversion_id(normalized_source, context)

        # Notify observers of start
        for observer in self._observers:
            observer.on_conversion_start(context, normalized_source)

        steps: List[TraceStep] = [
            TraceStep("normalization", {"raw": raw_type, "normalized": normalized_source})
        ]

        # 2. Lookup candidate rules in Registry
        candidates = self._registry.lookup(normalized_source, context)
        candidate_ids = tuple(r.metadata.rule_id for r in candidates)
        steps.append(TraceStep("lookup", {"candidate_count": len(candidates), "ids": candidate_ids}))

        # 3. Match and filter rules
        selected_rule: Optional[ConversionRule] = None
        rejection_reasons: Dict[str, str] = {}
        
        for rule in candidates:
            # Check version applicability ranges
            if rule.matches(normalized_source, context):
                selected_rule = rule
                for observer in self._observers:
                    observer.on_rule_evaluated(rule, matched=True, reason="Rule matches datatype and version context constraints.")
                break
            else:
                reason = "Mismatched version constraints or category constraints."
                rejection_reasons[rule.metadata.rule_id] = reason
                for observer in self._observers:
                    observer.on_rule_evaluated(rule, matched=False, reason=reason)

        if not selected_rule:
            # Return Unsupported result
            diag = Diagnostic(
                code="ERR_UNSUPPORTED_TYPE",
                severity=DiagnosticSeverity.ERROR,
                category=DiagnosticCategory.COMPATIBILITY,
                message=f"No matching mapping rule found for data type '{normalized_source.name}' to target {context.target_vendor}."
            )
            res = ConversionResult(
                conversion_id=conv_id,
                source_vendor=context.source_vendor,
                target_vendor=context.target_vendor,
                source_type=normalized_source,
                status=ConversionStatus.UNSUPPORTED,
                diagnostics=(diag,),
                validation_result=False
            )
            return res

        steps.append(TraceStep("rule_selection", {"selected_rule_id": selected_rule.metadata.rule_id}))

        # 4. Perform transformation
        target_type = selected_rule.convert(normalized_source, context)
        steps.append(TraceStep("transformation", {"target_type": target_type}))

        # 5. Evaluate Target Capability Matrix
        diagnostics: List[Diagnostic] = []
        capability_flags: Dict[str, bool] = {}
        negotiation = selected_rule.negotiation_level

        matrix = self._capability_provider.get_matrix(context.target_vendor, context.target_version)
        if matrix:
            # Check for general mapping capabilities
            cap_type = self._map_category_to_cap(target_type.category)
            if cap_type and cap_type in matrix.capabilities:
                vendor_cap = matrix.capabilities[cap_type]
                capability_flags[cap_type.value] = vendor_cap.supported
                
                # Check if capability is emulated or natively supported
                if vendor_cap.supported:
                    if vendor_cap.emulation:
                        negotiation = NegotiationLevel.EMULATED
                        # Apply emulation modifications to target type structure
                        target_type = self._apply_emulation(target_type, vendor_cap.emulation)
                    else:
                        negotiation = NegotiationLevel.NATIVE
                else:
                    negotiation = NegotiationLevel.UNSUPPORTED
                    diagnostics.append(Diagnostic(
                        code="ERR_CAPABILITY_UNSUPPORTED",
                        severity=DiagnosticSeverity.ERROR,
                        category=DiagnosticCategory.COMPATIBILITY,
                        message=f"Target capability '{cap_type.value}' is unsupported on target version."
                    ))

            # Perform physical boundaries check (e.g. max scale/precision/length)
            self._verify_physical_boundaries(target_type, context.target_vendor, diagnostics)

        steps.append(TraceStep("capability_negotiation", {"level": negotiation.value, "flags": capability_flags}))

        # 6. Assess mapping lossiness & precision reduction
        status = ConversionStatus.LOSSLESS
        
        # Check scale/precision reduction
        if normalized_source.precision is not None and target_type.precision is not None:
            if target_type.precision < normalized_source.precision:
                status = ConversionStatus.LOSSY
                diagnostics.append(Diagnostic(
                    code="WARN_PRECISION_REDUCTION",
                    severity=DiagnosticSeverity.WARNING,
                    category=DiagnosticCategory.PRECISION,
                    message=f"Precision reduced from {normalized_source.precision} to {target_type.precision} (lossy conversion)."
                ))

        if normalized_source.scale is not None and target_type.scale is not None:
            if target_type.scale < normalized_source.scale:
                status = ConversionStatus.LOSSY
                diagnostics.append(Diagnostic(
                    code="WARN_SCALE_REDUCTION",
                    severity=DiagnosticSeverity.WARNING,
                    category=DiagnosticCategory.SCALE,
                    message=f"Scale reduced from {normalized_source.scale} to {target_type.scale} (lossy conversion)."
                ))

        # Timezone loss check
        if normalized_source.timezone and not target_type.timezone:
            status = ConversionStatus.LOSSY
            diagnostics.append(Diagnostic(
                code="WARN_TIMEZONE_LOSS",
                severity=DiagnosticSeverity.WARNING,
                category=DiagnosticCategory.TIMEZONE,
                message="Timezone context lost in conversion (target column type does not preserve offsets)."
            ))

        # Unsigned truncation check
        if normalized_source.unsigned and not target_type.unsigned:
            # Non-unsigned target might overflow or wrap differently, flag warning
            diagnostics.append(Diagnostic(
                code="WARN_UNSIGNED_LOSS",
                severity=DiagnosticSeverity.WARNING,
                category=DiagnosticCategory.POLICY,
                message="Source datatype is UNSIGNED but target type does not explicitly support UNSIGNED. Overflow risk."
            ))

        # 7. Check strict Conversion Policy violations
        self._assert_policy_enforcement(status, diagnostics, context.policy)

        # 8. Compute Confidence Score
        confidence_breakdown = self._scoring_engine.calculate(normalized_source, target_type, context)
        steps.append(TraceStep("scoring", {"breakdown": confidence_breakdown}))

        # Assemble execution trace
        trace = ConversionTrace(
            trace_id=conv_id,
            input_type=normalized_source,
            normalized_type=normalized_source,
            candidate_rules=candidate_ids,
            selected_rule_id=selected_rule.metadata.rule_id,
            rejection_reasons=rejection_reasons,
            confidence_breakdown={
                "category_alignment": confidence_breakdown.category_alignment,
                "precision_preservation": confidence_breakdown.precision_preservation,
                "metadata_preservation": confidence_breakdown.metadata_preservation,
                "storage_adequacy": confidence_breakdown.storage_adequacy,
                "overall_score": confidence_breakdown.overall_score
            },
            steps=tuple(steps)
        )

        validation_result = not any(d.severity == DiagnosticSeverity.ERROR for d in diagnostics)

        res = ConversionResult(
            conversion_id=conv_id,
            source_vendor=context.source_vendor,
            target_vendor=context.target_vendor,
            source_type=normalized_source,
            target_type=target_type,
            category=target_type.category if target_type else normalized_source.category,
            status=status,
            diagnostics=tuple(diagnostics),
            metadata={
                "negotiation_level": negotiation.value,
                "rule_version": selected_rule.metadata.version
            },
            confidence=confidence_breakdown.overall_score,
            capability_flags=capability_flags,
            validation_result=validation_result,
            trace=trace
        )

        # Notify complete
        for observer in self._observers:
            observer.on_conversion_complete(res, trace)

        return res

    def _generate_conversion_id(self, source_type: DataType, context: ConversionContext) -> str:
        namespace = uuid.UUID("f0709b11-534d-45bf-97cc-dbd178e63b65")
        source_fingerprint = source_type.fingerprint()
        context_fingerprint = f"{context.source_vendor}:{context.target_vendor}:{context.target_version.raw}"
        return str(uuid.uuid5(namespace, f"{source_fingerprint}:{context_fingerprint}"))

    def _map_category_to_cap(self, category: TypeCategory) -> Optional[CapabilityType]:
        mapping = {
            TypeCategory.JSON: CapabilityType.JSON,
            TypeCategory.UUID: CapabilityType.UUID,
            TypeCategory.BOOLEAN: CapabilityType.BOOLEAN,
        }
        return mapping.get(category)

    def _apply_emulation(self, target: DataType, emulation: Any) -> DataType:
        """Modifies the target DataType definition based on capability emulation specifications."""
        return DataType(
            name=emulation.emulated_target_type,
            category=target.category,
            precision=target.precision,
            scale=target.scale,
            length=target.length,
            nullable=target.nullable,
            unsigned=target.unsigned,
            auto_increment=target.auto_increment,
            timezone=target.timezone,
            charset=target.charset,
            collation=target.collation,
            spatial=target.spatial,
            is_array=target.is_array,
            array_dimensions=target.array_dimensions,
            generated_expression=target.generated_expression,
            vendor_metadata={
                "check_constraints": emulation.check_constraints,
                "transform_hooks": emulation.transform_hooks
            }
        )

    def _verify_physical_boundaries(self, target: DataType, vendor: str, diagnostics: List[Diagnostic]):
        v = vendor.upper().strip()
        if v == "MYSQL":
            if target.precision is not None and target.precision > 65:
                diagnostics.append(Diagnostic(
                    code="ERR_PRECISION_LIMIT_EXCEEDED",
                    severity=DiagnosticSeverity.ERROR,
                    category=DiagnosticCategory.SCALE,
                    message=f"MySQL supports a maximum precision of 65 (requested: {target.precision})."
                ))
            if target.length is not None and target.length > 65535:
                diagnostics.append(Diagnostic(
                    code="WARN_ROW_LIMIT_EXCEEDED",
                    severity=DiagnosticSeverity.WARNING,
                    category=DiagnosticCategory.COMPATIBILITY,
                    message=f"Length {target.length} exceeds MySQL standard VARCHAR storage boundary of 65,535 bytes."
                ))
        elif v == "ORACLE":
            if target.precision is not None and target.precision > 38:
                diagnostics.append(Diagnostic(
                    code="WARN_ORACLE_PRECISION_TRUNCATION",
                    severity=DiagnosticSeverity.WARNING,
                    category=DiagnosticCategory.SCALE,
                    message=f"Oracle NUMBER supports up to 38 digits. Higher precisions will be truncated."
                ))
            if target.length is not None and target.length > 4000:
                diagnostics.append(Diagnostic(
                    code="WARN_ORACLE_VARCHAR_LIMIT",
                    severity=DiagnosticSeverity.WARNING,
                    category=DiagnosticCategory.COMPATIBILITY,
                    message=f"VARCHAR2 length {target.length} exceeds Oracle non-extended maximum limit (4000 bytes). LOB conversion recommended."
                ))
        elif v == "MSSQL" or v == "SQL SERVER":
            if target.precision is not None and target.precision > 38:
                diagnostics.append(Diagnostic(
                    code="ERR_MSSQL_PRECISION_LIMIT",
                    severity=DiagnosticSeverity.ERROR,
                    category=DiagnosticCategory.SCALE,
                    message=f"SQL Server supports a maximum precision of 38 (requested: {target.precision})."
                ))

    def _assert_policy_enforcement(self, status: ConversionStatus, diagnostics: List[Diagnostic], policy: ConversionPolicy):
        has_error = any(d.severity == DiagnosticSeverity.ERROR for d in diagnostics)
        has_warning = any(d.severity == DiagnosticSeverity.WARNING for d in diagnostics)
        
        # Enforce strict policy constraints
        if not policy.allow_precision_loss:
            precision_loss = any(d.code in ("WARN_PRECISION_REDUCTION", "WARN_SCALE_REDUCTION") for d in diagnostics)
            if precision_loss:
                raise PolicyViolation(
                    "allow_precision_loss",
                    "Precision reduction or scale loss detected, violating engine policy constraints."
                )

        if not policy.allow_lossy_conversions:
            if status == ConversionStatus.LOSSY or has_warning:
                raise PolicyViolation(
                    "allow_lossy_conversions",
                    "A lossy conversion was detected under a strict policy settings context."
                )

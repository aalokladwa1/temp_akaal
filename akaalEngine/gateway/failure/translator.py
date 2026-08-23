"""
akaalEngine.gateway.failure.translator
=======================================
Canonical Gateway failure translation engine.
Translates exceptions across Authorities #1–#12 into normalized GatewayResponse instances,
sanitizing secrets and preserving failure semantics (retryability, terminal status, fencing tokens).
"""

import logging
from typing import Any, List, Optional, Tuple, Type

from akaalEngine.evidence.security import EvidenceSecuritySanitizer
from akaalEngine.gateway.models.context import GatewayRequestContext
from akaalEngine.gateway.models.enums import GatewayFailureCategory
from akaalEngine.gateway.models.responses import GatewayResponse
from akaalEngine.telemetry.security.sanitizer import TelemetrySanitizer

logger = logging.getLogger("akaalEngine.gateway.failure")


class FailureTranslator:
    """Translates authority exceptions into normalized GatewayResponse envelopes."""

    @classmethod
    def translate_exception(
        cls,
        exc: Exception,
        context: GatewayRequestContext,
        operation_name: str,
    ) -> GatewayResponse[Any]:
        """Categorizes an exception, sanitizes its text, and returns a failed GatewayResponse."""
        category, retryable, terminal = cls._categorize_exception(exc)
        raw_msg = str(exc) or exc.__class__.__name__

        # Pass error through dual-layer sanitization (Telemetry URI/keyword + Evidence secret scrubbing)
        sanitized_msg = TelemetrySanitizer.sanitize_string(raw_msg)
        sanitized_msg = EvidenceSecuritySanitizer.sanitize_string(sanitized_msg)

        reasons = [sanitized_msg]
        if hasattr(exc, "reasons") and isinstance(getattr(exc, "reasons"), list):
            reasons = [
                EvidenceSecuritySanitizer.sanitize_string(TelemetrySanitizer.sanitize_string(str(r)))
                for r in exc.reasons
            ]

        logger.warning(
            "Gateway translated failure: operation=%s category=%s migration_id=%s msg=%s",
            operation_name,
            category.value,
            context.migration_id,
            sanitized_msg,
        )

        return GatewayResponse.create_failure(
            operation_id=context.operation_id,
            operation_type=operation_name,
            migration_id=context.migration_id,
            run_id=context.run_id,
            failure_category=category.value,
            error_message=sanitized_msg,
            reasons=reasons,
            retryable=retryable,
            terminal=terminal,
            fencing_epoch=context.fencing_epoch,
        )

    @classmethod
    def _categorize_exception(cls, exc: Exception) -> Tuple[GatewayFailureCategory, bool, bool]:
        """
        Determines (category, retryable, terminal) tuple based on exception type & attributes.
        Fails closed to INTERNAL_ENGINE_FAILURE if unmapped.
        """
        exc_type_name = exc.__class__.__name__

        # Fencing Violations across Authorities #5, #6, #9, #10, #11, #12
        if "Fencing" in exc_type_name or "StaleGeneration" in exc_type_name or "LeaseExpired" in exc_type_name:
            return GatewayFailureCategory.STALE_FENCING, False, True

        # Cancellation across Authorities #1, #6, #9, #10, #11
        raw_lower = (str(exc) or "").lower()
        if "cancel" in exc_type_name.lower() or "cancel" in raw_lower:
            return GatewayFailureCategory.CANCELLED, False, True

        # Ambiguous Commit in Transport (#9)
        if "AmbiguousCommit" in exc_type_name:
            return GatewayFailureCategory.AMBIGUOUS_COMMIT, False, True

        # Authentication / Permission Errors (#1, #3, #10)
        if "Authentication" in exc_type_name:
            return GatewayFailureCategory.AUTHENTICATION_FAILURE, False, True
        if "Permission" in exc_type_name:
            return GatewayFailureCategory.PERMISSION_FAILURE, False, True

        # Connectivity / Network Errors (#1, #3, #5)
        if "Connection" in exc_type_name or "DNSResolution" in exc_type_name or "RouteResolution" in exc_type_name or "EndpointUnavailable" in exc_type_name or "EndpointUnreachable" in exc_type_name:
            return GatewayFailureCategory.CONNECTIVITY_FAILURE, True, False
        if "Timeout" in exc_type_name:
            return GatewayFailureCategory.TIMEOUT, True, False

        # Dependency Missing Errors (#1, #2)
        if "Dependency" in exc_type_name or "ExtensionNotFound" in exc_type_name or "ProviderNotFound" in exc_type_name:
            return GatewayFailureCategory.DEPENDENCY_MISSING, False, True

        # Resource Exhaustion / Quotas (#1, #5, #6, #9)
        if "PoolExhaustion" in exc_type_name or "StorageQuotaExceeded" in exc_type_name or "DiskReserveViolated" in exc_type_name or "ResourceAdmission" in exc_type_name or "BandwidthLimit" in exc_type_name:
            return GatewayFailureCategory.RESOURCE_EXHAUSTION, True, False

        # Schema & Transformation Failures (#4, #8)
        if "Schema" in exc_type_name:
            return GatewayFailureCategory.SCHEMA_FAILURE, False, True
        if "Transformation" in exc_type_name or "ExpressionExecution" in exc_type_name or "MalformedData" in exc_type_name:
            return GatewayFailureCategory.TRANSFORMATION_FAILURE, False, True

        # Transport & CDC Failures (#9, #10)
        if "Transport" in exc_type_name:
            return GatewayFailureCategory.TRANSPORT_FAILURE, True, False
        if "CDC" in exc_type_name:
            return GatewayFailureCategory.CDC_FAILURE, True, False

        # Validation & Mismatches (#11)
        if "Validation" in exc_type_name or "Reconciliation" in exc_type_name or "Cardinality" in exc_type_name:
            return GatewayFailureCategory.VALIDATION_MISMATCH, False, True

        # Evidence Tamper & Integrity (#12)
        if "Integrity" in exc_type_name or "Tamper" in exc_type_name or "Verification" in exc_type_name:
            return GatewayFailureCategory.EVIDENCE_TAMPER, False, True
        if "Evidence" in exc_type_name:
            return GatewayFailureCategory.EVIDENCE_INSUFFICIENT, False, True

        # Input Validation Errors
        if isinstance(exc, (ValueError, KeyError, TypeError)):
            return GatewayFailureCategory.INVALID_REQUEST, False, True

        # Default fail-closed fallback
        return GatewayFailureCategory.INTERNAL_ENGINE_FAILURE, False, True

"""
akaalEngine.schema.types.registry
=================================
Central Canonical Type Registry coordinating 28-provider normalization, target emission,
safety evaluation, and explicit operator datatype overrides.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, Mapping, Optional, Tuple

from akaalEngine.schema.models.mapping import DataTypeOverride
from akaalEngine.schema.models.types import (
    CanonicalType,
    CanonicalTypeCategory,
    ConversionSafety,
    TargetTypeEmission,
)
from akaalEngine.schema.types.emitters import ProviderTypeEmitters
from akaalEngine.schema.types.normalizers import ProviderTypeNormalizers
from akaalEngine.schema.types.safety import TypeSafetyEvaluator


class CanonicalTypeRegistry:
    """Universal Canonical Datatype Registry and Conversion Rulebook."""

    _custom_normalizers: Dict[str, Callable[..., CanonicalType]] = {}
    _custom_emitters: Dict[str, Callable[[CanonicalType], TargetTypeEmission]] = {}

    @classmethod
    def register_normalizer(
        cls, provider: str, func: Callable[..., CanonicalType]
    ) -> None:
        """Register a custom source type normalizer for a provider."""
        cls._custom_normalizers[provider.strip().lower()] = func

    @classmethod
    def register_emitter(
        cls, provider: str, func: Callable[[CanonicalType], TargetTypeEmission]
    ) -> None:
        """Register a custom target type emitter for a provider."""
        cls._custom_emitters[provider.strip().lower()] = func

    @classmethod
    def normalize_source_type(
        cls,
        provider: str,
        raw_type: str,
        length: Optional[int] = None,
        precision: Optional[int] = None,
        scale: Optional[int] = None,
        extra_metadata: Optional[Mapping[str, Any]] = None,
    ) -> CanonicalType:
        """Normalizes source-native type into CanonicalType with memoization."""
        prov = str(provider).strip().lower()
        from akaalEngine.schema.core.memoization import default_memoization_engine

        cached = default_memoization_engine.get_normalized_type(
            prov, raw_type, length=length, precision=precision, scale=scale
        )
        if cached is not None and not extra_metadata:
            return cached

        if prov in cls._custom_normalizers:
            res = cls._custom_normalizers[prov](raw_type, length, precision, scale, extra_metadata)
        else:
            res = ProviderTypeNormalizers.normalize(prov, raw_type, length, precision, scale, extra_metadata)

        if not extra_metadata:
            default_memoization_engine.put_normalized_type(
                prov, raw_type, res, length=length, precision=precision, scale=scale
            )
        return res

    @classmethod
    def emit_target_type(
        cls,
        target_provider: str,
        canonical_type: CanonicalType,
    ) -> TargetTypeEmission:
        """Emits target-native DDL type string from CanonicalType with memoization."""
        tgt = str(target_provider).strip().lower()
        from akaalEngine.schema.core.memoization import default_memoization_engine

        cached = default_memoization_engine.get_emitted_type(
            canonical_type.category.value,
            canonical_type.raw_vendor_type,
            tgt,
            length=canonical_type.length,
            precision=canonical_type.precision,
            scale=canonical_type.scale,
        )
        if cached is not None:
            return cached

        if tgt in cls._custom_emitters:
            raw_emission = cls._custom_emitters[tgt](canonical_type)
        else:
            raw_emission = ProviderTypeEmitters.emit(tgt, canonical_type)

        evaluated = TypeSafetyEvaluator.evaluate_conversion(canonical_type, raw_emission)
        default_memoization_engine.put_emitted_type(
            canonical_type.category.value,
            canonical_type.raw_vendor_type,
            tgt,
            evaluated,
            length=canonical_type.length,
            precision=canonical_type.precision,
            scale=canonical_type.scale,
        )
        return evaluated

    @classmethod
    def convert_type(
        cls,
        source_provider: str,
        target_provider: str,
        raw_source_type: str,
        length: Optional[int] = None,
        precision: Optional[int] = None,
        scale: Optional[int] = None,
        extra_metadata: Optional[Mapping[str, Any]] = None,
        override: Optional[DataTypeOverride] = None,
    ) -> TargetTypeEmission:
        """Complete 2-step type conversion with operator override support."""
        if override is not None:
            # Operator override takes precedence
            custom_p = override.target_precision if override.target_precision is not None else precision
            custom_s = override.target_scale if override.target_scale is not None else scale
            custom_l = override.target_length if override.target_length is not None else length
            
            type_str = override.target_data_type
            if custom_l is not None and "(" not in type_str:
                type_str = f"{type_str}({custom_l})"
            elif custom_p is not None and custom_s is not None and "(" not in type_str:
                type_str = f"{type_str}({custom_p},{custom_s})"
            elif custom_p is not None and "(" not in type_str:
                type_str = f"{type_str}({custom_p})"

            warning = f"Operator override applied: {override.reason}" if override.reason else "Operator override applied"
            return TargetTypeEmission(
                target_engine=target_provider,
                target_native_type=type_str,
                safety=ConversionSafety.COMPATIBLE_WITH_TRANSFORMATION,
                warning_message=warning,
                extra={"is_override": True, "target_precision": custom_p, "target_scale": custom_s, "target_length": custom_l},
            )

        # Canonical 2-step conversion: Source -> CanonicalType -> Target
        canon = cls.normalize_source_type(source_provider, raw_source_type, length, precision, scale, extra_metadata)
        return cls.emit_target_type(target_provider, canon)

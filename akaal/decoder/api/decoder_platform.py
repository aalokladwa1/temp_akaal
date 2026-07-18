"""
Akaal — Decoder Platform Public API
===================================
Public API for enterprise database normalization. Converts DiscoveryReport + MigrationRuleSet into CanonicalMigrationModel.
"""

import time
import logging
from typing import Any, Dict, Optional

from akaal.scout.models.discovery_report import DiscoveryReport
from akaal.rulebook.models.migration_ruleset import MigrationRuleSet

from akaal.decoder.models.decoder_context import DecoderContext, ValidationProfile
from akaal.decoder.models.canonical_migration_model import CanonicalMigrationModel
from akaal.decoder.registry.storage_family_registry import StorageFamilyRegistry
from akaal.decoder.cache.normalization_cache import NormalizationCache
from akaal.decoder.engine.normalization_engine import NormalizationEngine
from akaal.decoder.engine.simulation_engine import SimulationEngine
from akaal.decoder.engine.metadata_engine import MetadataEngine
from akaal.decoder.engine.validation_engine import ValidationEngine
from akaal.decoder.metrics.decoder_metrics import DecoderMetrics

logger = logging.getLogger("akaal.decoder")


class DecoderPlatform:
    """
    Public entry point for Decoder Platform.
    Converts DiscoveryReport + MigrationRuleSet into canonical, immutable CanonicalMigrationModel.
    Contains zero SQL generation, zero migration execution, zero planning, zero risk scoring.
    """

    _registry: Optional[StorageFamilyRegistry] = None
    _cache: Optional[NormalizationCache] = None

    @classmethod
    def get_registry(cls) -> StorageFamilyRegistry:
        if cls._registry is None:
            cls._registry = StorageFamilyRegistry(auto_register_defaults=True)
        return cls._registry

    @classmethod
    def get_cache(cls) -> NormalizationCache:
        if cls._cache is None:
            cls._cache = NormalizationCache()
        return cls._cache

    @classmethod
    def normalize(
        cls,
        discovery_report: DiscoveryReport,
        migration_ruleset: MigrationRuleSet,
        validation_profile: ValidationProfile = ValidationProfile.STANDARD,
        configuration: Optional[Dict[str, Any]] = None,
    ) -> CanonicalMigrationModel:
        t0 = time.time()
        metrics = DecoderMetrics()

        ctx = DecoderContext(
            discovery_report=discovery_report,
            migration_ruleset=migration_ruleset,
            validation_profile=validation_profile,
            configuration=configuration or {},
            simulation_mode=False,
        )

        engine = NormalizationEngine()
        model, trace = engine.normalize(ctx)

        t1 = time.time()
        metrics.record_normalization_time((t1 - t0) * 1000.0)

        return model

    @classmethod
    def simulate(
        cls,
        discovery_report: DiscoveryReport,
        migration_ruleset: MigrationRuleSet,
        validation_profile: ValidationProfile = ValidationProfile.STANDARD,
        configuration: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        ctx = DecoderContext(
            discovery_report=discovery_report,
            migration_ruleset=migration_ruleset,
            validation_profile=validation_profile,
            configuration=configuration or {},
            simulation_mode=True,
        )

        meta_engine = MetadataEngine()
        graph, _ = meta_engine.normalize_metadata(discovery_report)

        val_engine = ValidationEngine()
        _, diagnostics = val_engine.validate_graph(graph, ctx)

        sim_engine = SimulationEngine()
        return sim_engine.simulate(ctx, graph, diagnostics)


def normalize(
    discovery_report: DiscoveryReport,
    migration_ruleset: MigrationRuleSet,
    validation_profile: ValidationProfile = ValidationProfile.STANDARD,
    configuration: Optional[Dict[str, Any]] = None,
) -> CanonicalMigrationModel:
    """Top-level helper function for Decoder normalization."""
    return DecoderPlatform.normalize(
        discovery_report=discovery_report,
        migration_ruleset=migration_ruleset,
        validation_profile=validation_profile,
        configuration=configuration,
    )

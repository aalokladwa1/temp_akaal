"""
Akaal — Encryption Layout Analyzer
===================================
Models encryption capability mappings, multi-step graph translations,
and projects transport / tablespace / column-level encryption configurations.
"""

import abc
from typing import Any, Dict, List, Optional, Set, Tuple
import time

from akaal.core.models.enums import SystemType
from akaal.core.comparison.models import Schema

from akaal.core.intelligence.encryption_aware.models import (
    EncryptionAlgorithm,
    EncryptionMode,
    KeyManagementProvider,
    KeyRotationPolicy,
    EncryptionCompatibilityTier,
    EncryptionProfile,
    EncryptionCapability,
    EncryptionRule,
    EncryptionScore,
    EncryptionRecommendation,
    EncryptionTranslation,
    EncryptionStatistics,
    EncryptionSummary,
    EncryptionReport,
)

class IEncryptionAnalyzer(abc.ABC):
    """Abstract interface defining target TDE and key exchange mappings validation."""
    @abc.abstractmethod
    def analyze_encryption(
        self,
        schema: Schema,
        target_dialect: SystemType,
        target_version: str = "1.0",
        target_engine: str = "heap",
        target_edition: str = "STANDARD"
    ) -> EncryptionReport:
        pass

from akaal.core.intelligence.encryption_aware.exceptions import EncryptionTranslationError
from akaal.core.intelligence.encryption_aware.registry import EncryptionStrategyRegistry
from akaal.core.intelligence.encryption_aware.validator import EncryptionLayoutValidator
from akaal.core.intelligence.encryption_aware.recommendation import EncryptionRecommendationAdvisor
from akaal.core.intelligence.encryption_aware.report import EncryptionReportBuilder

class EncryptionTranslationGraph:
    """Graph resolver modeling Source -> Intermediate Capability -> Target pathways."""

    def __init__(self) -> None:
        # Adjacency list: node -> list of (neighbor_node, tier, confidence, overhead)
        self._adj: Dict[str, List[Tuple[str, EncryptionCompatibilityTier, float, float]]] = {}
        self._build_default_graph()

    def add_edge(
        self,
        src: str,
        dest: str,
        tier: EncryptionCompatibilityTier,
        confidence: float = 1.0,
        overhead: float = 0.0
    ) -> None:
        self._adj.setdefault(src, []).append((dest, tier, confidence, overhead))

    def _build_default_graph(self) -> None:
        # Standard algorithms
        aes256_algos = [EncryptionAlgorithm.AES256, EncryptionAlgorithm.NATIVE_TDE]
        
        # 1. Source to Intermediate Capability Node
        for algo in aes256_algos:
            self.add_edge(f"{SystemType.ORACLE.value}:{algo.value}", "CAP_TDE_AES256", EncryptionCompatibilityTier.NATIVE, 1.0, 0.0)
            self.add_edge(f"{SystemType.MSSQL.value}:{algo.value}", "CAP_TDE_AES256", EncryptionCompatibilityTier.NATIVE, 1.0, 0.0)
            self.add_edge(f"{SystemType.MYSQL.value}:{algo.value}", "CAP_TDE_AES256", EncryptionCompatibilityTier.NATIVE, 1.0, 0.05)
            self.add_edge(f"{SystemType.POSTGRESQL.value}:{algo.value}", "CAP_TDE_AES256", EncryptionCompatibilityTier.NATIVE, 1.0, 0.0)

        self.add_edge(f"{SystemType.ORACLE.value}:{EncryptionAlgorithm.TRIPLE_DES.value}", "CAP_TDE_3DES", EncryptionCompatibilityTier.NATIVE, 1.0, 0.0)
        self.add_edge(f"{SystemType.MSSQL.value}:{EncryptionAlgorithm.TRIPLE_DES.value}", "CAP_TDE_3DES", EncryptionCompatibilityTier.NATIVE, 1.0, 0.0)

        # 2. Intermediate Capability to Target Node
        # Oracle TDE
        self.add_edge("CAP_TDE_AES256", f"{SystemType.ORACLE.value}:{EncryptionAlgorithm.AES256.value}", EncryptionCompatibilityTier.NATIVE, 1.0, 0.0)
        self.add_edge("CAP_TDE_3DES", f"{SystemType.ORACLE.value}:{EncryptionAlgorithm.TRIPLE_DES.value}", EncryptionCompatibilityTier.NATIVE, 1.0, 0.0)

        # SQL Server TDE
        self.add_edge("CAP_TDE_AES256", f"{SystemType.MSSQL.value}:{EncryptionAlgorithm.AES256.value}", EncryptionCompatibilityTier.NATIVE, 1.0, 0.02)
        self.add_edge("CAP_TDE_3DES", f"{SystemType.MSSQL.value}:{EncryptionAlgorithm.TRIPLE_DES.value}", EncryptionCompatibilityTier.NATIVE, 1.0, 0.05)

        # MySQL TDE (Barracuda/InnoDB TDE requires Keyring plugin)
        self.add_edge("CAP_TDE_AES256", f"{SystemType.MYSQL.value}:{EncryptionAlgorithm.AES256.value}", EncryptionCompatibilityTier.PLUGIN_PROVIDED, 0.90, 0.08)

        # PostgreSQL TDE (PG lacks native TDE, requires pgcrypto column encryption or custom tablespace plugins)
        self.add_edge("CAP_TDE_AES256", f"{SystemType.POSTGRESQL.value}:{EncryptionAlgorithm.AES256.value}", EncryptionCompatibilityTier.REQUIRES_MANUAL_MIGRATION, 0.70, 0.15)
        self.add_edge("CAP_TDE_3DES", f"{SystemType.POSTGRESQL.value}:{EncryptionAlgorithm.AES256.value}", EncryptionCompatibilityTier.REQUIRES_MANUAL_MIGRATION, 0.60, 0.20)

    def find_shortest_path(
        self,
        src_dialect: SystemType,
        src_algo: EncryptionAlgorithm,
        tgt_dialect: SystemType
    ) -> Optional[Tuple[List[str], EncryptionCompatibilityTier, float, float]]:
        """Resolves shortest path mapping dialect boundaries using BFS."""
        src_node = f"{src_dialect.value}:{src_algo.value}"
        
        # Priority mapping for compatibility tiers (lower number means better compatibility)
        tier_values = {
            EncryptionCompatibilityTier.NATIVE: 0,
            EncryptionCompatibilityTier.REQUIRES_KEY_ROTATION: 1,
            EncryptionCompatibilityTier.PLUGIN_PROVIDED: 2,
            EncryptionCompatibilityTier.REQUIRES_MANUAL_MIGRATION: 3,
            EncryptionCompatibilityTier.UNSUPPORTED: 4,
        }

        # Queue contains: (current_node, path_taken, current_worst_tier, current_confidence, cumulative_overhead)
        queue: List[Tuple[str, List[str], EncryptionCompatibilityTier, float, float]] = [
            (src_node, [src_node], EncryptionCompatibilityTier.NATIVE, 1.0, 0.0)
        ]
        visited: Set[str] = set()
        best_path: Optional[Tuple[List[str], EncryptionCompatibilityTier, float, float]] = None

        while queue:
            node, path, worst_tier, confidence, overhead = queue.pop(0)
            if node in visited:
                continue
            visited.add(node)

            # Check if we reached any algorithm node of target dialect
            if ":" in node and node.startswith(f"{tgt_dialect.value}:"):
                if not best_path or tier_values[worst_tier] < tier_values[best_path[1]] or (
                    tier_values[worst_tier] == tier_values[best_path[1]] and overhead < best_path[3]
                ):
                    best_path = (path, worst_tier, confidence, overhead)
                continue

            for neighbor, edge_tier, edge_conf, edge_over in self._adj.get(node, []):
                next_worst = worst_tier
                if tier_values[edge_tier] > tier_values[worst_tier]:
                    next_worst = edge_tier

                queue.append((
                    neighbor,
                    path + [neighbor],
                    next_worst,
                    confidence * edge_conf,
                    overhead + edge_over
                ))

        return best_path

class EncryptionLayoutAnalyzer(IEncryptionAnalyzer):
    """Orchestrates strategy searches, sizing assessments, and security planning."""

    def __init__(self, registry: EncryptionStrategyRegistry) -> None:
        self._registry = registry
        self._graph = EncryptionTranslationGraph()

    def resolve_translation(
        self,
        src_dialect: SystemType,
        src_algo: EncryptionAlgorithm,
        tgt_dialect: SystemType
    ) -> EncryptionTranslation:
        """Determines target capability tiers and mapping pathways using the graph resolver."""
        if src_dialect == tgt_dialect:
            return EncryptionTranslation(
                source_dialect=src_dialect,
                target_dialect=tgt_dialect,
                source_algorithm=src_algo,
                target_algorithm=src_algo,
                compatibility_tier=EncryptionCompatibilityTier.NATIVE,
                translation_confidence=1.0,
                translation_rationale="Natively supported on same dialect.",
                translation_path=(f"{src_dialect}:{src_algo}",),
                estimated_performance_overhead=0.0
            )

        res = self._graph.find_shortest_path(src_dialect, src_algo, tgt_dialect)
        if not res:
            return EncryptionTranslation(
                source_dialect=src_dialect,
                target_dialect=tgt_dialect,
                source_algorithm=src_algo,
                target_algorithm=EncryptionAlgorithm.AES256,
                compatibility_tier=EncryptionCompatibilityTier.UNSUPPORTED,
                translation_confidence=0.0,
                translation_rationale="No translation path found in capability mappings.",
                translation_path=(),
                estimated_performance_overhead=0.0
            )

        path, tier, confidence, overhead = res
        tgt_node = path[-1]
        tgt_algo_str = tgt_node.split(":")[1]
        tgt_algo = EncryptionAlgorithm(tgt_algo_str)

        rationale = f"Resolved via capability path: {' -> '.join(path)}. Compatibility level: {tier}."
        if tier == EncryptionCompatibilityTier.REQUIRES_MANUAL_MIGRATION:
            rationale += " Requires column-level pg_crypto or application-level encryption."

        return EncryptionTranslation(
            source_dialect=src_dialect,
            target_dialect=tgt_dialect,
            source_algorithm=src_algo,
            target_algorithm=tgt_algo,
            compatibility_tier=tier,
            translation_confidence=confidence,
            translation_rationale=rationale,
            translation_path=tuple(path),
            estimated_performance_overhead=overhead
        )

    def analyze_encryption(
        self,
        schema: Schema,
        target_dialect: SystemType,
        target_version: str = "1.0",
        target_engine: str = "heap",
        target_edition: str = "STANDARD"
    ) -> EncryptionReport:
        """Analyzes schemas to map translations, calculate confidence indexes, and compile summaries."""
        start_time = time.perf_counter()
        translations: Dict[str, EncryptionTranslation] = {}
        
        total_objects = 0
        encrypted_count = 0
        native_count = 0
        translated_count = 0
        unsupported_count = 0
        sum_confidence = 0.0

        has_compliant = True
        requires_manual = False
        requires_rotation = False
        missing_providers = set()

        for table in schema.tables:
            total_objects += 1
            
            # Detect source encryption profile based on target strategy rules
            matched_rules = self._registry.get_matching_rules(
                dialect=schema.vendor,
                version="12.0",
                engine="heap",
                edition="ENTERPRISE"
            )

            # Fallback to defaults if no matching rules found
            src_algo = EncryptionAlgorithm.AES256
            if matched_rules:
                rec_prof = matched_rules[0].recommended_profile
                if rec_prof:
                    src_algo = rec_prof.algorithm
            
            # Run capability path negotiator
            trans = self.resolve_translation(schema.vendor, src_algo, target_dialect)
            translations[table.name] = trans

            encrypted_count += 1
            sum_confidence += trans.translation_confidence

            if trans.compatibility_tier == EncryptionCompatibilityTier.NATIVE:
                native_count += 1
            elif trans.compatibility_tier == EncryptionCompatibilityTier.UNSUPPORTED:
                unsupported_count += 1
                has_compliant = False
            else:
                translated_count += 1

            if trans.compatibility_tier == EncryptionCompatibilityTier.REQUIRES_MANUAL_MIGRATION:
                requires_manual = True
            elif trans.compatibility_tier == EncryptionCompatibilityTier.REQUIRES_KEY_ROTATION:
                requires_rotation = True

            # Extract provider if defined in the matching rules
            if matched_rules and matched_rules[0].recommended_profile:
                prov = matched_rules[0].recommended_profile.key_provider
                if prov != KeyManagementProvider.LOCAL_WALLET:
                    missing_providers.add(str(prov))

        avg_conf = (sum_confidence / total_objects) if total_objects > 0 else 1.0

        stats = EncryptionStatistics(
            total_objects_analyzed=total_objects,
            encrypted_objects_count=encrypted_count,
            native_mappings_count=native_count,
            translated_mappings_count=translated_count,
            unsupported_mappings_count=unsupported_count,
            average_confidence=avg_conf
        )

        summary = EncryptionSummary(
            has_compliant_algorithms=has_compliant,
            requires_manual_intervention=requires_manual,
            requires_key_rotation_setup=requires_rotation,
            missing_kms_providers=tuple(sorted(list(missing_providers)))
        )

        # Run validation constraints check
        validator = EncryptionLayoutValidator()
        diagnostics = validator.validate_encryption(
            schema=schema,
            translations=translations,
            target_version=target_version,
            target_engine=target_engine,
            target_edition=target_edition
        )

        # Run recommendations advisor
        advisor = EncryptionRecommendationAdvisor()
        recs = advisor.generate_recommendations(schema, translations)

        duration_ms = (time.perf_counter() - start_time) * 1000.0

        # Build final report
        builder = EncryptionReportBuilder(
            correlation_id="default_corr",
            trace_id="default_trace",
            request_id="default_req",
            migration_id="default_mig"
        )
        return builder.build_report(
            statistics=stats,
            summary=summary,
            translations=translations,
            recommendations=tuple(recs),
            diagnostics=tuple(diagnostics),
            duration_ms=duration_ms
        )

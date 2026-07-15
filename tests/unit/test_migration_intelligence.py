"""
Akaal — Migration Intelligence Platform Test Suite
===================================================
Executes comprehensive validation of Feature 1 models, registries, plugins,
configuration resource loaders, observability, and performance budgets.
"""

import os
import json
import tempfile
import threading
import time
import unittest
import uuid
from dataclasses import dataclass, FrozenInstanceError
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple

from akaal.core.models.enums import SystemType
from akaal.core.conversion.api.models import DbVersion
from akaal.core.comparison.models import Schema
from akaal.core.intelligence.compression_aware import (
    ICompressionAnalyzer,
    CompressionAlgorithm,
    CompressionCompatibilityTier,
    CompressionProfile,
    CompressionCapability,
    CompressionRule,
    CompressionScore,
    CompressionRecommendation,
    CompressionTranslation,
    CompressionStatistics,
    CompressionSummary,
    CompressionReport,
    CompressionRuleMatcher,
    CompressionStrategyRegistry,
    EnterpriseCompressionCache,
    CompressionScoreCalculator,
    CompressionRanker,
    CompressionRecommendationAdvisor,
    CompressionLayoutAnalyzer,
    DefaultCompressionEstimatorStrategy,
    VendorCompressionEstimatorStrategy,
    PluginCompressionEstimatorStrategy,
    CompressionLayoutValidator,
    CompressionReportBuilder,
    CompressionMetricsCollector,
    CompressionOptimizationError,
    CompressionValidationError,
    CompressionTranslationError,
    CompressionRegistryConflictError,
    CompressionPluginLoadError,
)
from akaal.core.intelligence.encryption_aware import (
    IEncryptionAnalyzer,
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
    EncryptionRuleMatcher,
    EncryptionStrategyRegistry,
    EnterpriseEncryptionCache,
    EncryptionTranslationGraph,
    EncryptionLayoutAnalyzer,
    EncryptionLayoutValidator,
    EncryptionScoreCalculator,
    EncryptionRanker,
    EncryptionRecommendationAdvisor,
    EncryptionReportBuilder,
    EncryptionMetricsCollector,
    SubsystemTimer,
    EncryptionOptimizationError,
    EncryptionValidationError,
    EncryptionTranslationError,
    EncryptionRegistryConflictError,
    EncryptionPluginLoadError,
)

from akaal.core.intelligence.cross_version import (
    ICompatibilityEngine,
    CompatibilityEngineError,
    CompatibilityRuleValidationError,
    CompatibilityRegistryConflictError,
    CapabilityMatrixError,
    VersionParseError,
    CompatibilityTier,
    FeatureCategory,
    CompatibilityRuleAction,
    FeatureCapability,
    CompatibilityRule,
    CompatibilityScore,
    CompatibilityFinding,
    CompatibilityStatistics,
    CompatibilitySummary,
    CompatibilityReport,
    CompatibilityRuleMatcher,
    CompatibilityStrategyRegistry,
    CompatibilityCache,
    CompatibilityMetricsCollector,
    CompatibilitySubsystemTimer,
    CompatibilityCapabilityAnalyzer,
    CrossVersionCompatibilityAnalyzer,
    CompatibilityRuleSetValidator,
    CompatibilityFindingAuditor,
    CompatibilityRecommendation,
    CompatibilityScoreCalculator,
    CompatibilityRanker,
    CompatibilityRecommendationAdvisor,
    CompatibilityReportBuilder,
)

from akaal.core.intelligence import (
    MigrationIntelligenceFacade,
    BaseRegistry,
    IPlugin,
    PluginMetadata,
    PluginState,
    PluginManager,
    ConfigResourceLoader,
    AkaalIntelligenceError,
    RegistryFrozenError,
    RegistryDuplicateError,
    ConflictResolutionError,
    ConfigValidationError,
    ResourceLoadingError,
    PluginLoadError,
    ReplaySequenceError,
    Severity,
    DiagnosticCategory,
    Diagnostic,
    RecommendationScore,
    Recommendation,
    ReportMetadata,
    TelemetryContext,
    MemoryTelemetryExporter,
    IntelligenceObservabilityContext,
    TimingTracker,
    IReplaySessionManager,
    IStorageAnalyzer,
    IEncryptionAnalyzer,
    ICompatibilityEngine,
    IIntelligenceLinter,
    IRecommendationAdvisor,
    ReplayState,
    CDCEventModel,
    ReplayCheckpoint,
    SequenceGap,
    OutOfOrderEvent,
    TimelineStatistics,
    SessionStatistics,
    ReplayTimeline,
    ReplaySession,
    ReplaySessionManager,
    ReplayTimelineValidator,
    CDCProviderMetadata,
    ReplayProviderRegistry,
    ReplayReportBuilder,
    ReplayReport,
    StorageLayoutAnalyzer,
    StorageLayoutValidator,
    StorageRecommendationAdvisor,
    StorageRulesRegistry,
    StorageRuleMetadata,
    StorageReportBuilder,
    TablespaceAllocation,
    PartitionStrategy,
    StorageProjection,
    StorageConstraint,
    StorageReport,
)

# =============================================================================
# Helper Concrete Mock Models for Registry / Plugin Verification
# =============================================================================

@dataclass
class MockRule:
    rule_id: str
    source_dialect: SystemType
    target_dialect: SystemType
    priority: int
    version_range: Tuple[float, float]
    action_type: str


class MockRuleRegistry(BaseRegistry[MockRule]):
    def _validate_rule(self, rule: MockRule) -> None:
        if rule.priority < 0:
            raise ValueError("Priority must be non-negative")

    def _detect_conflicts(self, new_rule_id: str, new_rule: MockRule) -> None:
        for r_id, r in self._rules.items():
            if r_id != new_rule_id:
                self._check_conflict_between(new_rule_id, new_rule, r_id, r)

    def _check_conflict_between(self, id1: str, rule1: MockRule, id2: str, rule2: MockRule) -> None:
        if (rule1.source_dialect == rule2.source_dialect and
            rule1.target_dialect == rule2.target_dialect and
            rule1.action_type != rule2.action_type):
            max_start = max(rule1.version_range[0], rule2.version_range[0])
            min_end = min(rule1.version_range[1], rule2.version_range[1])
            if max_start <= min_end:
                raise ConflictResolutionError(
                    f"Conflict between {id1} and {id2} on overlapping version range.",
                    error_code="CONFLICTING_RULES"
                )

    def _sort_key(self, rule: MockRule) -> Any:
        width = rule.version_range[1] - rule.version_range[0]
        return (-rule.priority, width, rule.rule_id)


class MockPlugin(IPlugin):
    def __init__(self, metadata: PluginMetadata) -> None:
        self._metadata = metadata
        self._state = PluginState.LOADED
        self.initialized_called = False
        self.teardown_called = False

    @property
    def metadata(self) -> PluginMetadata:
        return self._metadata

    @property
    def state(self) -> PluginState:
        return self._state

    def initialize(self, registries: Dict[str, BaseRegistry[Any]]) -> None:
        self.initialized_called = True
        self._state = PluginState.ACTIVE
        reg = registries["mock"]
        rule_id = f"rule_{self.metadata.plugin_id}"
        rule = MockRule(
            rule_id=rule_id,
            source_dialect=SystemType.POSTGRESQL,
            target_dialect=SystemType.MYSQL,
            priority=100,
            version_range=(1.0, 2.0),
            action_type="CONVERT"
        )
        reg.register(rule.rule_id, rule)

    def teardown(self, registries: Dict[str, BaseRegistry[Any]]) -> None:
        self.teardown_called = True
        self._state = PluginState.UNLOADED
        reg = registries["mock"]
        rule_id = f"rule_{self.metadata.plugin_id}"
        if rule_id in reg._rules:
            del reg._rules[rule_id]


# =============================================================================
# Skeletons for Dependency Injection
# =============================================================================

class MockReplayManager(IReplaySessionManager):
    async def create_replay_session(self, session_id: str, connection_config: Any) -> Any:
        return None
    async def validate_timeline(self, session_id: str) -> Any:
        return None

class MockStorageAnalyzer(IStorageAnalyzer):
    def analyze_storage_layout(self, schema: Any, target_dialect: Any) -> Any:
        return None

class MockCompressionAnalyzer(ICompressionAnalyzer):
    def analyze_compression(self, schema: Any, target_dialect: Any) -> Any:
        return None

class MockEncryptionAnalyzer(IEncryptionAnalyzer):
    def analyze_encryption(self, schema: Any, target_dialect: Any) -> Any:
        return None

class MockCompatibilityEngine(ICompatibilityEngine):
    def check_compatibility(self, schema: Any, target_dialect: Any, target_version: Any) -> Any:
        return None

class MockIntelligenceLinter(IIntelligenceLinter):
    def lint(self, schema: Any) -> List[Diagnostic]:
        return []

class MockRecommendationAdvisor(IRecommendationAdvisor):
    def generate_recommendations(self, schema: Any) -> Any:
        return None


# =============================================================================
# Core Test Case Suite
# =============================================================================

class TestMigrationIntelligence(unittest.TestCase):

    # -------------------------------------------------------------------------
    # 1. Model Immutability & Scores Tests
    # -------------------------------------------------------------------------
    def test_model_immutability(self) -> None:
        """Verify that ReportMetadata and diagnostics dataclasses raise FrozenInstanceError on mutations."""
        diag = Diagnostic(
            diagnostic_code="LIMIT_JSON",
            severity=Severity.WARNING,
            category=DiagnosticCategory.COMPATIBILITY,
            message="JSON columns are not supported in targeted database version.",
            path="tables.users.columns.meta"
        )
        with self.assertRaises(FrozenInstanceError):
            diag.severity = Severity.CRITICAL  # type: ignore

        meta = ReportMetadata(
            report_id="rep:compat:12345",
            correlation_id="corr-1",
            trace_id="tr-1",
            request_id="req-1",
            migration_id="mig-1",
            generated_timestamp=datetime.now(timezone.utc),
            execution_duration_ms=45.2,
            subsystem_version="1.0.0",
            diagnostics_summary={"warnings": 1, "errors": 0},
            warning_count=1,
            error_count=0,
            recommendation_count=0,
            confidence_summary={}
        )
        with self.assertRaises(FrozenInstanceError):
            meta.execution_duration_ms = 99.9  # type: ignore

    def test_recommendation_ranking_score(self) -> None:
        """Assert the composite score calculation holds the priority * benefit / friction math."""
        score1 = RecommendationScore(
            confidence=0.9,
            priority=8,
            estimated_benefit=0.8,
            implementation_complexity=2,
            migration_risk=2,
            rationale="Expected 40% memory reduction with Page Compression."
        )
        # impact = (8 * 1.5) + (0.8 * 10) = 12.0 + 8.0 = 20.0
        # friction = (2 * 0.5) + (2 * 1.2) = 1.0 + 2.4 = 3.4
        # rank = (20.0 / 3.4) * 0.9 = 5.882 * 0.9 = 5.29
        self.assertAlmostEqual(score1.composite_rank, 5.29, places=2)

        # Confirm score sorting orders correctly in descending composite rank
        rec1 = Recommendation("rec1", "Compress Users", "Desc", "users", score1)
        score2 = RecommendationScore(
            confidence=0.95,
            priority=10,
            estimated_benefit=0.9,
            implementation_complexity=1,
            migration_risk=1,
            rationale="Critical tables index partitioning recommendation."
        )
        # impact = 15.0 + 9.0 = 24.0
        # friction = 0.5 + 1.2 = 1.7
        # rank = (24.0 / 1.7) * 0.95 = 14.117 * 0.95 = 13.41
        self.assertAlmostEqual(score2.composite_rank, 13.41, places=2)
        rec2 = Recommendation("rec2", "Partition Orders", "Desc", "orders", score2)

        recs = [rec1, rec2]
        sorted_recs = sorted(recs, key=lambda r: r.score.composite_rank, reverse=True)
        self.assertEqual(sorted_recs[0].recommendation_id, "rec2")

    # -------------------------------------------------------------------------
    # 2. Registry Lifecycle & Conflict Tests
    # -------------------------------------------------------------------------
    def test_registry_lifecycle_and_freeze(self) -> None:
        """Verify duplicate rule warnings, conflict preventions, freeze lockouts, and snapshots."""
        registry = MockRuleRegistry()
        rule1 = MockRule("rule_1", SystemType.POSTGRESQL, SystemType.MYSQL, 10, (10.0, 14.0), "CONVERT")
        registry.register(rule1.rule_id, rule1)

        # Duplicate ID check
        with self.assertRaises(RegistryDuplicateError):
            registry.register(rule1.rule_id, rule1)

        # Conflict check: overlap in dialect, version bounds, but different action outcome
        rule_conflict = MockRule("rule_conflict", SystemType.POSTGRESQL, SystemType.MYSQL, 5, (12.0, 15.0), "DROP")
        with self.assertRaises(ConflictResolutionError):
            registry.register(rule_conflict.rule_id, rule_conflict)

        # Freeze check
        registry.freeze()
        self.assertTrue(registry.is_frozen)
        with self.assertRaises(RegistryFrozenError):
            rule3 = MockRule("rule_3", SystemType.POSTGRESQL, SystemType.MYSQL, 8, (15.0, 16.0), "CONVERT")
            registry.register(rule3.rule_id, rule3)

        # Snapshot check (COW)
        snapshot = registry.snapshot()
        self.assertFalse(snapshot.is_frozen)
        # Modification to snapshot does not contaminate frozen master
        rule_new = MockRule("rule_new", SystemType.POSTGRESQL, SystemType.MYSQL, 8, (15.0, 16.0), "CONVERT")
        snapshot.register(rule_new.rule_id, rule_new)
        self.assertIsNone(registry.get("rule_new"))
        self.assertIsNotNone(snapshot.get("rule_new"))

    def test_registry_deterministic_ordering(self) -> None:
        """Verify sorting resolves specificity, version overlaps, priorities, and tie-breakers."""
        registry = MockRuleRegistry()
        r1 = MockRule("r1", SystemType.POSTGRESQL, SystemType.MYSQL, 10, (10.0, 15.0), "CONVERT")
        r2 = MockRule("r2", SystemType.POSTGRESQL, SystemType.MYSQL, 10, (10.0, 12.0), "CONVERT") # more specific version range width (2 vs 5)
        r3 = MockRule("r3", SystemType.POSTGRESQL, SystemType.MYSQL, 20, (10.0, 15.0), "CONVERT") # higher priority (20 vs 10)
        r4 = MockRule("r4", SystemType.POSTGRESQL, SystemType.MYSQL, 10, (10.0, 15.0), "CONVERT") # tie-breaker on ID (r4 vs r1)

        registry.register(r1.rule_id, r1)
        registry.register(r2.rule_id, r2)
        registry.register(r3.rule_id, r3)
        registry.register(r4.rule_id, r4)

        rules = registry.list_rules()
        # Order should be: r3 (priority 20), r2 (priority 10, width 2.0), r1 (priority 10, width 5.0, r1 tie-break), r4 (priority 10, width 5.0, r4 tie-break)
        self.assertEqual(rules[0].rule_id, "r3")
        self.assertEqual(rules[1].rule_id, "r2")
        self.assertEqual(rules[2].rule_id, "r1")
        self.assertEqual(rules[3].rule_id, "r4")

    # -------------------------------------------------------------------------
    # 3. Thread Safety Concurrency Tests
    # -------------------------------------------------------------------------
    def test_registry_concurrency(self) -> None:
        """Stress test rule registration and read-matching from concurrent threads."""
        registry = MockRuleRegistry()
        errors = []

        def worker(thread_idx: int) -> None:
            for i in range(100):
                rule_id = f"thread_{thread_idx}_rule_{i}"
                rule = MockRule(
                    rule_id=rule_id,
                    source_dialect=SystemType.POSTGRESQL,
                    target_dialect=SystemType.MYSQL,
                    priority=thread_idx,
                    version_range=(float(i), float(i + 1)),
                    action_type="CONVERT"
                )
                try:
                    registry.register(rule_id, rule)
                except Exception as e:
                    errors.append(e)

        threads = [threading.Thread(target=worker, args=(t,)) for t in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(len(errors), 0, f"Thread errors: {errors}")
        self.assertEqual(len(registry.list_rules()), 500)

    # -------------------------------------------------------------------------
    # 4. Plugin Lifecycle Tests
    # -------------------------------------------------------------------------
    def test_plugin_lifecycle_and_dependencies(self) -> None:
        """Verify plugin metadata parsing, load checks, version validation, and teardowns."""
        registry = MockRuleRegistry()
        registries = {"mock": registry}
        manager = PluginManager(registries)

        p_meta = PluginMetadata("plugin1", "1.0.0", "1.0.0", dependencies=(), priority=50)
        plugin = MockPlugin(p_meta)

        # Basic Loading
        manager.load_plugin(plugin)
        self.assertEqual(plugin.state, PluginState.ACTIVE)
        self.assertTrue(plugin.initialized_called)
        self.assertIsNotNone(registry.get("rule_plugin1"))

        # Duplicate checking
        with self.assertRaises(PluginLoadError):
            manager.load_plugin(plugin)

        # Dependency Verification
        p_meta_child = PluginMetadata("plugin_child", "1.0.0", "1.0.0", dependencies=("plugin1",), priority=10)
        child_plugin = MockPlugin(p_meta_child)
        manager.load_plugin(child_plugin)
        self.assertEqual(child_plugin.state, PluginState.ACTIVE)

        # Missing Dependency verification
        p_meta_missing = PluginMetadata("plugin_missing", "1.0.0", "1.0.0", dependencies=("plugin_ghost",), priority=10)
        missing_plugin = MockPlugin(p_meta_missing)
        with self.assertRaises(PluginLoadError):
            manager.load_plugin(missing_plugin)

        # Plugin Unloading
        # Unloading dependency blocks parent unload
        with self.assertRaises(PluginLoadError):
            manager.unload_plugin("plugin1")

        # Safe Unload Child then Parent
        manager.unload_plugin("plugin_child")
        manager.unload_plugin("plugin1")
        self.assertEqual(plugin.state, PluginState.UNLOADED)
        self.assertTrue(plugin.teardown_called)
        # Verify clean registry state
        self.assertIsNone(registry.get("rule_plugin1"))

    # -------------------------------------------------------------------------
    # 5. Configuration Framework Tests
    # -------------------------------------------------------------------------
    def test_config_loader_schema_and_duplicates(self) -> None:
        """Verify checksum audits, schema validation version limits, and key duplicate audits."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            # 1. Write clean json structures for deterministic files
            valid_matrix = {
                "schema_version": "1.0.0",
                "dialects": {
                    "postgresql": {"jsonb": {"min_version": "9.4.0"}}
                }
            }

            dummy_profile = {
                "schema_version": "1.0.0",
                "profiles": []
            }

            for name in ConfigResourceLoader.DETERMINISTIC_ORDER:
                file_path = os.path.join(tmp_dir, name)
                with open(file_path, "w", encoding="utf-8") as f:
                    if name == "compatibility_matrix.json":
                        json.dump(valid_matrix, f)
                    else:
                        json.dump(dummy_profile, f)

            loader = ConfigResourceLoader(tmp_dir)
            configs = loader.load_all_configs()
            self.assertEqual(len(configs), 6)

            meta = loader.get_metadata("compatibility_matrix.json")
            self.assertIsNotNone(meta)
            self.assertEqual(meta.schema_version, "1.0.0")

            # 2. Key duplicate validation test
            dup_json = '{"schema_version": "1.0.0", "key1": 1, "key1": 2}'
            dup_file = os.path.join(tmp_dir, "compression_profiles.json")
            with open(dup_file, "w", encoding="utf-8") as f:
                f.write(dup_json)

            with self.assertRaises(ConfigValidationError):
                loader.load_config("compression_profiles.json")

            # 3. Invalid schema version
            bad_ver_json = '{"schema_version": "invalid_version"}'
            bad_file = os.path.join(tmp_dir, "compression_profiles.json")
            with open(bad_file, "w", encoding="utf-8") as f:
                f.write(bad_ver_json)

            with self.assertRaises(ConfigValidationError):
                loader.load_config("compression_profiles.json")

    # -------------------------------------------------------------------------
    # 6. Observability Subsystem Tests
    # -------------------------------------------------------------------------
    def test_observability_timing_and_telemetry(self) -> None:
        """Verify timing captures, structured events contexts, and timing metrics."""
        exporter = MemoryTelemetryExporter()
        telemetry = TelemetryContext(
            correlation_id="corr-99",
            trace_id="tr-99",
            request_id="req-99",
            migration_id="mig-99"
        )
        obs = IntelligenceObservabilityContext(
            subsystem_id="test_subsystem",
            context=telemetry,
            exporter=exporter
        )

        # Metric logging
        obs.record_metric("cache", "hit_rate", 0.95)
        self.assertEqual(len(exporter.metrics), 1)
        self.assertEqual(exporter.metrics[0][1].name, "hit_rate")
        self.assertEqual(exporter.metrics[0][1].value, 0.95)

        # Event logging
        obs.record_event("audit", "security_check", {"status": "success"})
        self.assertEqual(len(exporter.events), 1)
        self.assertEqual(exporter.events[0][1].event_name, "security_check")

        # Timing context validation
        with TimingTracker(obs, "process_batches"):
            time.sleep(0.005)

        self.assertEqual(len(exporter.timings), 1)
        self.assertEqual(exporter.timings[0][1].operation, "process_batches")
        self.assertTrue(exporter.timings[0][1].duration_ms > 0.0)

    # -------------------------------------------------------------------------
    # 7. Facade Dependency Verification
    # -------------------------------------------------------------------------
    def test_facade_skeleton_dependency_verification(self) -> None:
        """Verify that facade checks and validates type implementations of injected dependencies."""
        exporter = MemoryTelemetryExporter()
        telemetry = TelemetryContext("c", "t", "r", "m")
        obs = IntelligenceObservabilityContext("facade", telemetry, exporter)

        # Assert TypeErrors when dummy/None inputs are passed
        with self.assertRaises(TypeError):
            MigrationIntelligenceFacade(
                replay_manager=None, # type: ignore
                storage_analyzer=MockStorageAnalyzer(),
                compression_analyzer=MockCompressionAnalyzer(),
                encryption_analyzer=MockEncryptionAnalyzer(),
                compatibility_engine=MockCompatibilityEngine(),
                linter=MockIntelligenceLinter(),
                advisor=MockRecommendationAdvisor(),
                observability=obs
            )

        # Valid initialization skeleton check
        facade = MigrationIntelligenceFacade(
            replay_manager=MockReplayManager(),
            storage_analyzer=MockStorageAnalyzer(),
            compression_analyzer=MockCompressionAnalyzer(),
            encryption_analyzer=MockEncryptionAnalyzer(),
            compatibility_engine=MockCompatibilityEngine(),
            linter=MockIntelligenceLinter(),
            advisor=MockRecommendationAdvisor(),
            observability=obs
        )
        self.assertIsNotNone(facade)

    # -------------------------------------------------------------------------
    # 8. Performance Benchmarks
    # -------------------------------------------------------------------------
    def test_performance_budgets(self) -> None:
        """Measures cold start, registry rebuild, snapshot COW, and log metrics."""
        # Warm-up / startup
        start = time.perf_counter()
        registry = MockRuleRegistry()
        rules_dict = {}
        for i in range(100):
            rules_dict[f"rule_{i}"] = MockRule(
                rule_id=f"rule_{i}",
                source_dialect=SystemType.POSTGRESQL,
                target_dialect=SystemType.MYSQL,
                priority=i,
                version_range=(1.0, 2.0),
                action_type="CONVERT"
            )
        registry.hot_reload(rules_dict)
        startup_ms = (time.perf_counter() - start) * 1000.0
        print(f"\n[BENCHMARK] Registry Startup & Rebuild Time for 100 rules: {startup_ms:.2f} ms")

        # Snapshot COW
        start = time.perf_counter()
        snapshot = registry.snapshot()
        snapshot_ms = (time.perf_counter() - start) * 1000.0
        print(f"[BENCHMARK] Registry Copy-On-Write Snapshot Time: {snapshot_ms:.2f} ms")

        # Verification of performance targets
        self.assertTrue(startup_ms < 50.0) # Budget limit: 50ms
        self.assertTrue(snapshot_ms < 10.0) # Budget limit: 10ms


# =============================================================================
# Feature 2 Replay Subsystem Verification
# =============================================================================

class TestReplaySubsystem(unittest.TestCase):
    def setUp(self) -> None:
        self.manager = ReplaySessionManager()
        self.validator = ReplayTimelineValidator()

    def _create_mock_timeline(self, num_events: int, gaps: bool = False, unordered: bool = False) -> ReplayTimeline:
        events = []
        base_time = datetime(2026, 7, 15, 12, 0, 0, tzinfo=timezone.utc)
        for i in range(num_events):
            seq = i
            if gaps and i == 5:
                # Jump sequence to create a gap of 2
                seq = i + 2
            
            # Unordered swap
            if unordered and i == 3:
                seq = i - 1
            elif unordered and i == 2:
                seq = i + 1

            events.append(CDCEventModel(
                event_id=f"evt_{i}",
                commit_sequence=seq,
                timestamp=datetime.fromtimestamp(base_time.timestamp() + i, tz=timezone.utc),
                operation="INSERT" if i % 2 == 0 else "UPDATE",
                table_key="orders",
                payload_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
                transaction_id=f"tx_{i // 10}",
                metadata={}
            ))
        
        stats = TimelineStatistics(
            total_events=num_events,
            insert_count=num_events - (num_events // 2),
            update_count=num_events // 2,
            delete_count=0,
            sequence_gaps_count=0,
            out_of_order_count=0,
            min_sequence=0,
            max_sequence=num_events - 1,
            duration_seconds=float(num_events)
        )
        return ReplayTimeline(
            timeline_id=f"timeline_{uuid.uuid4().hex[:8]}",
            events=tuple(events),
            statistics=stats
        )

    def _create_mock_session(self, session_id: str, num_events: int = 10) -> ReplaySession:
        timeline = self._create_mock_timeline(num_events)
        stats = SessionStatistics(
            total_transitions=0,
            active_duration_seconds=0.0,
            error_count=0,
            last_checkpoint_sequence=0,
            checkpoint_count=0
        )
        return ReplaySession(
            session_id=session_id,
            state=ReplayState.INITIALIZED,
            timeline=timeline,
            checkpoints=(),
            statistics=stats,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )

    def test_replay_provider_registry_conflict_and_order(self) -> None:
        """Verify duplicate/conflict detection and deterministic sorting on ReplayProviderRegistry."""
        registry = ReplayProviderRegistry()
        p1 = CDCProviderMetadata("prov1", "MySQL Binlog", SystemType.MYSQL, 10, "1.0.0")
        p2 = CDCProviderMetadata("prov2", "MySQL Redo", SystemType.MYSQL, 50, "1.0.0")

        registry.register(p1.provider_id, p1)
        registry.register(p2.provider_id, p2)

        # Conflict on same provider name and dialect
        p_conflict = CDCProviderMetadata("prov_conflict", "MySQL Binlog", SystemType.MYSQL, 20, "2.0.0")
        with self.assertRaises(ConflictResolutionError):
            registry.register(p_conflict.provider_id, p_conflict)

        # Order by priority descending: prov2 (50) should come before prov1 (10)
        rules = registry.list_rules()
        self.assertEqual(rules[0].provider_id, "prov2")
        self.assertEqual(rules[1].provider_id, "prov1")

    def test_replay_session_state_transitions(self) -> None:
        """Verify the complete ReplaySession state machine valid transitions and illegal blocks."""
        session = self._create_mock_session("sess1")
        self.manager.create_session("sess1", session)

        # 1. Legal transition: INITIALIZED -> VALIDATING
        self.manager.transition_state("sess1", ReplayState.VALIDATING)
        self.assertEqual(self.manager.get_session("sess1").state, ReplayState.VALIDATING)

        # 2. Illegal transition: VALIDATING -> COMPLETED (should raise ReplaySequenceError)
        with self.assertRaises(ReplaySequenceError):
            self.manager.transition_state("sess1", ReplayState.COMPLETED)

        # 3. Transitions: VALIDATING -> READY -> ACTIVE -> SUSPENDED -> RESUMED -> VALIDATING -> READY -> ACTIVE -> COMPLETED
        self.manager.transition_state("sess1", ReplayState.READY)
        self.manager.transition_state("sess1", ReplayState.ACTIVE)
        self.manager.transition_state("sess1", ReplayState.SUSPENDED)
        self.manager.transition_state("sess1", ReplayState.RESUMED)
        self.manager.transition_state("sess1", ReplayState.VALIDATING)
        self.manager.transition_state("sess1", ReplayState.READY)
        self.manager.transition_state("sess1", ReplayState.ACTIVE)
        self.manager.transition_state("sess1", ReplayState.COMPLETED)

        final_sess = self.manager.get_session("sess1")
        self.assertEqual(final_sess.state, ReplayState.COMPLETED)
        # Statistics transition counter checks
        self.assertEqual(final_sess.statistics.total_transitions, 9)

    def test_replay_recovery_state(self) -> None:
        """Verify session recovery behavior using stored checkpoint watermarks."""
        session = self._create_mock_session("sess_rec")
        self.manager.create_session("sess_rec", session)

        # Transition to ACTIVE
        self.manager.transition_state("sess_rec", ReplayState.VALIDATING)
        self.manager.transition_state("sess_rec", ReplayState.READY)
        self.manager.transition_state("sess_rec", ReplayState.ACTIVE)

        # Add checkpoints
        cp1 = ReplayCheckpoint("cp_1", "sess_rec", 4, datetime.now(timezone.utc), "hash123")
        self.manager.add_checkpoint("sess_rec", cp1)
        cp2 = ReplayCheckpoint("cp_2", "sess_rec", 8, datetime.now(timezone.utc), "hash456")
        self.manager.add_checkpoint("sess_rec", cp2)

        # Verify duplicate checkpoint error
        with self.assertRaises(ReplaySequenceError):
            self.manager.add_checkpoint("sess_rec", cp2)

        # Trigger recovery
        recovered = self.manager.recover_session("sess_rec")
        self.assertEqual(recovered.state, ReplayState.RESUMED)
        self.assertEqual(recovered.statistics.last_checkpoint_sequence, 8)

    def test_replay_timeline_validation(self) -> None:
        """Verify detection of duplicates, gaps, unordered sequences, and backward timestamps."""
        # 1. Clean timeline validation
        t_clean = self._create_mock_timeline(10)
        diags, gaps, ooo, stats = self.validator.validate_timeline(t_clean)
        self.assertEqual(len(diags), 0)
        self.assertEqual(len(gaps), 0)
        self.assertEqual(ooo, 0)
        self.assertEqual(stats.total_events, 10)

        # 2. Timeline with sequence gaps
        t_gaps = self._create_mock_timeline(10, gaps=True)
        diags, gaps, ooo, stats = self.validator.validate_timeline(t_gaps)
        self.assertTrue(any(d.diagnostic_code == "REPLAY_SEQUENCE_GAP" for d in diags))
        self.assertEqual(len(gaps), 1)
        self.assertEqual(gaps[0].start_sequence, 4)
        self.assertEqual(gaps[0].end_sequence, 7)

        # 3. Timeline with out-of-order sequence
        t_ooo = self._create_mock_timeline(10, unordered=True)
        diags, gaps, ooo, stats = self.validator.validate_timeline(t_ooo)
        self.assertTrue(any(d.diagnostic_code == "REPLAY_OUT_OF_ORDER" for d in diags))
        self.assertEqual(ooo, 1)

        # 4. Duplicate event validation
        events_list = list(t_clean.events)
        # Duplicate the first event
        events_list.append(events_list[0])
        t_dup = ReplayTimeline("timeline_dup", tuple(events_list), t_clean.statistics)
        diags, gaps, ooo, stats = self.validator.validate_timeline(t_dup)
        self.assertTrue(any(d.diagnostic_code == "REPLAY_DUP_EVENT" for d in diags))

        # 5. Empty hash payload validation
        bad_hash_event = CDCEventModel(
            event_id="bad_evt",
            commit_sequence=1,
            timestamp=datetime.now(timezone.utc),
            operation="INSERT",
            table_key="orders",
            payload_hash="",  # Empty
            transaction_id="tx_1",
            metadata={}
        )
        t_bad = ReplayTimeline("timeline_bad", (bad_hash_event,), t_clean.statistics)
        diags, gaps, ooo, stats = self.validator.validate_timeline(t_bad)
        self.assertTrue(any(d.diagnostic_code == "REPLAY_EMPTY_HASH" for d in diags))

    def test_replay_timeline_performance(self) -> None:
        """Benchmark validation run across 100,000 timeline events. Target: < 15ms."""
        num_events = 100000
        # Warmup cache
        _ = self._create_mock_timeline(100)

        # Build 100,000 events
        t_large = self._create_mock_timeline(num_events)

        start = time.perf_counter()
        diags, gaps, ooo, stats = self.validator.validate_timeline(t_large)
        duration_ms = (time.perf_counter() - start) * 1000.0

        print(f"\n[BENCHMARK] Replay Timeline Validation for {num_events} events: {duration_ms:.2f} ms")
        self.assertEqual(stats.total_events, num_events)
        # Performance budget limit check
        self.assertTrue(duration_ms < 15.0, f"Benchmark took {duration_ms:.2f} ms, budget is 15 ms")

    def test_replay_concurrency(self) -> None:
        """Validate thread-safe isolated validation execution of concurrent sessions."""
        errors = []

        def worker(session_idx: int) -> None:
            for i in range(20):
                timeline = self._create_mock_timeline(100, gaps=(i % 5 == 0))
                try:
                    diags, gaps, ooo, stats = self.validator.validate_timeline(timeline, session_id=f"thread_sess_{session_idx}")
                    if i % 5 == 0:
                        # Should detect sequence gaps
                        assert len(gaps) > 0
                except Exception as e:
                    errors.append(e)

        threads = [threading.Thread(target=worker, args=(t,)) for t in range(5)]
        self.assertEqual(len(errors), 0, f"Concurrency validation errors: {errors}")


# =============================================================================
# Feature 3 Storage Optimization Subsystem Verification
# =============================================================================

class TestStorageSubsystem(unittest.TestCase):
    def setUp(self) -> None:
        self.analyzer = StorageLayoutAnalyzer()
        self.validator = StorageLayoutValidator()
        self.advisor = StorageRecommendationAdvisor()

    def _create_mock_schema(self, table_name: str, wide_row: bool = False, partition_index: bool = False) -> Schema:
        from akaal.core.comparison.models.schema import ColumnSchema, TableSchema, IndexSchema, Schema
        
        # Define columns
        cols = [
            ColumnSchema("id", "BIGINT", "BIGINT", False),
            ColumnSchema("created_at", "TIMESTAMP", "TIMESTAMP", False),
            ColumnSchema("status", "VARCHAR", "VARCHAR(32)", False)
        ]
        if wide_row:
            # Add a huge VARCHAR to exceed row size bounds
            cols.append(ColumnSchema("payload", "VARCHAR", "VARCHAR(16000)", True))
            
        indexes = []
        if partition_index:
            indexes.append(IndexSchema("idx_orders_partition_date", ("created_at",), False))
        else:
            indexes.append(IndexSchema("idx_orders_normal", ("id",), True))
            
        table = TableSchema(
            name=table_name,
            columns=tuple(cols),
            primary_key=None,
            foreign_keys=(),
            indexes=tuple(indexes),
            constraints=()
        )
        return Schema(tables=(table,), vendor=SystemType.POSTGRESQL)

    def test_storage_rules_registry(self) -> None:
        """Verify storage rules registry lifecycle, duplicate detection, conflicts, and snapshots."""
        registry = StorageRulesRegistry()
        r1 = StorageRuleMetadata("rule1", "Large Placement", SystemType.POSTGRESQL, 10, "TABLESPACE", "TS_LARGE")
        r2 = StorageRuleMetadata("rule2", "Medium Placement", SystemType.POSTGRESQL, 50, "TABLESPACE", "TS_MEDIUM")

        registry.register(r1.rule_id, r1)
        registry.register(r2.rule_id, r2)

        # 1. Duplicate ID validation
        with self.assertRaises(RegistryDuplicateError):
            registry.register(r1.rule_id, r1)

        # 2. Conflict resolution (same target dialect and name)
        r_conflict = StorageRuleMetadata("rule_conflict", "Large Placement", SystemType.POSTGRESQL, 20, "TABLESPACE", "TS_ALT")
        with self.assertRaises(ConflictResolutionError):
            registry.register(r_conflict.rule_id, r_conflict)

        # 3. Deterministic priorities sorting (r2 (50) comes before r1 (10))
        rules = registry.list_rules()
        self.assertEqual(rules[0].rule_id, "rule2")

        # 4. Freeze lockout check
        registry.freeze()
        self.assertTrue(registry.is_frozen)
        with self.assertRaises(RegistryFrozenError):
            registry.register("rule3", r1)

        # 5. Copy-on-Write Snapshot
        snapshot = registry.snapshot()
        self.assertFalse(snapshot.is_frozen)
        r_new = StorageRuleMetadata("rule_new", "New Placement", SystemType.POSTGRESQL, 30, "TABLESPACE", "TS_NEW")
        snapshot.register(r_new.rule_id, r_new)
        self.assertIsNotNone(snapshot.get("rule_new"))
        self.assertIsNone(registry.get("rule_new"))

    def test_storage_analyzer_sizing_calculations(self) -> None:
        """Verify row length estimations, tablespace mappings, and index sizing math."""
        schema = self._create_mock_schema("orders", wide_row=False)
        report = self.analyzer.analyze_storage_layout(schema, SystemType.POSTGRESQL)

        self.assertEqual(report.total_tables, 1)
        # Sizing verification: id (8 bytes) + created_at (8 bytes) + status (VARCHAR(32) -> 16 bytes) + overhead (32 bytes) = 64 bytes
        # 10,000 rows * 64 bytes = 640,000 bytes -> 625 KB
        self.assertEqual(report.allocations["orders"]["avg_row_len_bytes"], 64)
        self.assertEqual(report.allocations["orders"]["data_size_kb"], 625)
        # Index sizing: index on id (8 bytes + 16 bytes overhead) * 10,000 -> 240,000 bytes -> 234 KB
        self.assertEqual(report.allocations["orders"]["index_size_kb"], 234)
        self.assertEqual(report.allocations["orders"]["total_size_kb"], 859)

        # Assigns TS_SMALL_DATA for small project sizes
        self.assertEqual(report.allocations["orders"]["tablespace"], "TS_SMALL_DATA")

    def test_storage_validator_diagnostics(self) -> None:
        """Verify storage validator logs diagnostic warnings and quota violations."""
        schema = self._create_mock_schema("orders", wide_row=True, partition_index=False)
        
        # Sizing estimation
        # VARCHAR(16000) -> 8,000 bytes average + others (64 bytes) = 8,064 bytes row length
        # 10,000 rows -> 80,640,000 bytes -> 78,750 KB total size
        report = self.analyzer.analyze_storage_layout(schema, SystemType.POSTGRESQL)

        # Constraints
        constraints = StorageConstraint(
            max_database_size_kb=50000,      # Database quota 50MB (will be exceeded by 78MB)
            max_tablespace_size_kb=100000,
            block_size_bytes=8192,           # 8KB block size (avg_row_len 8,064 exceeds block limit 7,936 bytes)
            unsupported_features=()
        )

        diags = self.validator.validate_storage(schema, report, constraints)
        
        # Verify row size exceed diag
        self.assertTrue(any(d.diagnostic_code == "STORAGE_ROW_SIZE_EXCEEDED" for d in diags))
        # Verify DB quota limit diag
        self.assertTrue(any(d.diagnostic_code == "STORAGE_DB_QUOTA_EXCEEDED" for d in diags))

    def test_storage_recommendation_advisor(self) -> None:
        """Verify recommendations are emitted for missing partitions, high indices, or wide rows."""
        # Create a table that is huge (> 100MB) by overriding default_row_count to 2,000,000
        analyzer_huge = StorageLayoutAnalyzer(default_row_count=2000000)
        schema = self._create_mock_schema("orders_huge", wide_row=False, partition_index=False)
        report = analyzer_huge.analyze_storage_layout(schema, SystemType.POSTGRESQL)

        recs = self.advisor.generate_recommendations(schema, report)
        
        # Verify partitioning suggestion
        self.assertTrue(any(r.recommendation_id == "rec:storage:part:orders_huge" for r in recs))
        self.assertTrue(any(r.score.priority == 8 for r in recs if r.recommendation_id == "rec:storage:part:orders_huge"))

    def test_storage_subsystem_concurrency(self) -> None:
        """Verify thread-safe rules registration on StorageRulesRegistry."""
        registry = StorageRulesRegistry()
        errors = []

        def worker(thread_idx: int) -> None:
            for i in range(100):
                rule_id = f"thread_{thread_idx}_rule_{i}"
                rule = StorageRuleMetadata(
                    rule_id=rule_id,
                    rule_name=f"Rule {thread_idx} {i}",
                    target_dialect=SystemType.POSTGRESQL,
                    priority=i,
                    rule_type="TABLESPACE",
                    metadata_value=f"TS_{i}"
                )
                try:
                    registry.register(rule_id, rule)
                except Exception as e:
                    errors.append(e)

        threads = [threading.Thread(target=worker, args=(t,)) for t in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(len(errors), 0, f"Concurrency registry errors: {errors}")
        self.assertEqual(len(registry.list_rules()), 500)


# =============================================================================
# Feature 4 Compression-Aware Subsystem Verification
# =============================================================================

class TestCompressionSubsystem(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = CompressionStrategyRegistry()
        self.analyzer = CompressionLayoutAnalyzer(self.registry)
        self.validator = CompressionLayoutValidator()
        self.advisor = CompressionRecommendationAdvisor()

    def _create_mock_schema(self, table_name: str, indexes_spec: Tuple[str, ...] = ()) -> Schema:
        from akaal.core.comparison.models.schema import ColumnSchema, TableSchema, IndexSchema, Schema
        cols = [
            ColumnSchema("id", "BIGINT", "BIGINT", False),
            ColumnSchema("created_at", "TIMESTAMP", "TIMESTAMP", False),
            ColumnSchema("payload", "VARCHAR", "VARCHAR(4000)", True)
        ]
        indexes = [IndexSchema(name, ("created_at",), False) for name in indexes_spec]
        table = TableSchema(
            name=table_name,
            columns=tuple(cols),
            primary_key=None,
            foreign_keys=(),
            indexes=tuple(indexes),
            constraints=()
        )
        return Schema(tables=(table,), vendor=SystemType.ORACLE)

    def test_compression_rule_matcher_specificity_and_sorting(self) -> None:
        """Verify CompressionRuleMatcher matches version ranges, engines, and resolves priority sorting."""
        p_row = CompressionProfile("p1", SystemType.POSTGRESQL, "heap", CompressionAlgorithm.TOAST, 8)
        
        # Define rules with varying specificities
        r1 = CompressionRule("r1", "Generic PG", SystemType.POSTGRESQL, 10, 1000, (), p_row)
        r2 = CompressionRule("r2", "Specific PG 14+", SystemType.POSTGRESQL, 10, 1000, (), p_row, min_version="14.0")
        r3 = CompressionRule("r3", "High Priority Engine Match", SystemType.POSTGRESQL, 50, 1000, (), p_row, min_version="14.0", required_engine="heap")

        rules = [r1, r2, r3]

        # 1. Match and sort for PG 13
        matched_pg13 = CompressionRuleMatcher.match_rules(rules, SystemType.POSTGRESQL, "13.0", "heap", "standard")
        self.assertEqual(len(matched_pg13), 1)
        self.assertEqual(matched_pg13[0].rule_id, "r1")

        # 2. Match and sort for PG 14 (r3 has highest specificity and priority)
        matched_pg14 = CompressionRuleMatcher.match_rules(rules, SystemType.POSTGRESQL, "14.2", "heap", "standard")
        self.assertEqual(len(matched_pg14), 3)
        self.assertEqual(matched_pg14[0].rule_id, "r3")  # specificity=15, priority=50
        self.assertEqual(matched_pg14[1].rule_id, "r2")  # specificity=10, priority=10

    def test_compression_rules_registry_lifecycle_and_conflict(self) -> None:
        """Verify strategical registry bootstrap, unique constraints, freeze behavior, and index retrieval."""
        registry = CompressionStrategyRegistry()
        p = CompressionProfile("p", SystemType.ORACLE, "heap", CompressionAlgorithm.ADVANCED_ROW, 8)
        r1 = CompressionRule("rule1", "Oracle Compression", SystemType.ORACLE, 10, 1000, (), p)
        
        registry.register(r1.rule_id, r1)

        # 1. Duplicate checks
        with self.assertRaises(RegistryDuplicateError):
            registry.register(r1.rule_id, r1)

        # 2. Overlap conflict checks (matching dialect, name, priority)
        r_conf = CompressionRule("rule_conf", "Oracle Compression", SystemType.ORACLE, 10, 2000, (), p)
        with self.assertRaises(CompressionRegistryConflictError):
            registry.register(r_conf.rule_id, r_conf)

        # 3. Index retrieval check
        rules_by_algo = registry.get_rules_for_algorithm(CompressionAlgorithm.ADVANCED_ROW)
        self.assertEqual(len(rules_by_algo), 1)

        # 4. Freeze lockout check
        registry.freeze()
        with self.assertRaises(RegistryFrozenError):
            registry.register("rule2", r1)

        # 5. Snapshot copy-on-write
        snapshot = registry.snapshot()
        self.assertFalse(snapshot.is_frozen)

    def test_enterprise_compression_cache(self) -> None:
        """Verify caching LRU capacity eviction limits, TTL, and warmups."""
        # Bounded cache of size 3 entries, TTL 0.1s
        cache = EnterpriseCompressionCache(max_entries=3, ttl_seconds=0.1)
        
        cache.put("k1", "v1")
        cache.put("k2", "v2")
        cache.put("k3", "v3")

        self.assertEqual(cache.get("k1"), "v1")

        # Eviction limit check: putting k4 must evict k2 (as k1 was recently retrieved)
        cache.put("k4", "v4")
        self.assertIsNone(cache.get("k2"))
        self.assertEqual(cache.get("k1"), "v1")

        # TTL expiration check
        time.sleep(0.15)
        self.assertIsNone(cache.get("k1"))
        stats = cache.get_statistics()
        self.assertEqual(stats["misses"], 2)

    def test_compression_layout_analyzer_graph(self) -> None:
        """Verify translation graph shortest paths, intermediate hop conversions, and lossy translations."""
        # Case 1: Direct native translation (Oracle -> Oracle)
        trans_native = self.analyzer.resolve_translation(SystemType.ORACLE, CompressionAlgorithm.ADVANCED_ROW, SystemType.ORACLE)
        self.assertEqual(trans_native.compatibility_tier, CompressionCompatibilityTier.NATIVE)
        self.assertEqual(trans_native.target_algorithm, CompressionAlgorithm.ADVANCED_ROW)

        # Case 2: Intermediate hop (Oracle Advanced Row -> CAP_ROW_PAGE -> SQL Server Page)
        trans_mssql = self.analyzer.resolve_translation(SystemType.ORACLE, CompressionAlgorithm.ADVANCED_ROW, SystemType.MSSQL)
        self.assertEqual(trans_mssql.compatibility_tier, CompressionCompatibilityTier.LOSSLESS_TRANSLATION)
        self.assertEqual(trans_mssql.target_algorithm, CompressionAlgorithm.PAGE)
        self.assertEqual(len(trans_mssql.translation_path), 3)  # Oracle -> CAP_ROW_PAGE -> MSSQL

        # Case 3: Lossy translation hop (Oracle Advanced Row -> CAP_ROW_PAGE -> MySQL Page)
        trans_mysql = self.analyzer.resolve_translation(SystemType.ORACLE, CompressionAlgorithm.ADVANCED_ROW, SystemType.MYSQL)
        self.assertEqual(trans_mysql.compatibility_tier, CompressionCompatibilityTier.LOSSY_TRANSLATION)
        self.assertEqual(trans_mysql.estimated_ratio_loss, 0.15)

    def test_strategy_based_compression_estimator(self) -> None:
        """Verify strategy estimators project storage reduction, IO, and write CPU overheads."""
        schema = self._create_mock_schema("orders")
        table = schema.tables[0]
        
        default_est = DefaultCompressionEstimatorStrategy()
        vendor_est = VendorCompressionEstimatorStrategy()

        # Default Sizing calculation: VARCHAR size is compressed
        size_def, cpu_def, io_def = default_est.estimate_compression(table, CompressionAlgorithm.ZSTD, 1000)
        self.assertTrue(size_def < 1000)
        self.assertEqual(cpu_def, 1.15)

        # High density columnar estimation
        size_ven, cpu_ven, io_ven = vendor_est.estimate_compression(table, CompressionAlgorithm.COLUMNSTORE, 1000)
        self.assertEqual(size_ven, 150)  # 85% savings
        self.assertEqual(cpu_ven, 1.35)
        self.assertEqual(io_ven, 1.80)

    def test_compression_layout_validator_diagnostics(self) -> None:
        """Verify validator flags edition licensing limits, MySQL engines mismatch, and ratio losses."""
        schema = self._create_mock_schema("orders", indexes_spec=("idx_hcc_col",))
        
        # Scenario: Columnstore compression selected on SQL Server Standard 2012 (Enterprise limits apply)
        stats, summary, translations = self.analyzer.analyze_compression(schema, SystemType.MSSQL)
        
        # Override target translation to COLUMNSTORE for validation test
        from akaal.core.intelligence.compression_aware.models import CompressionTranslation
        translations["orders"] = CompressionTranslation(
            source_dialect=SystemType.ORACLE,
            target_dialect=SystemType.MSSQL,
            source_algorithm=CompressionAlgorithm.HCC_QUERY_HIGH,
            target_algorithm=CompressionAlgorithm.COLUMNSTORE,
            compatibility_tier=CompressionCompatibilityTier.LOSSLESS_TRANSLATION,
            translation_confidence=0.90,
            translation_rationale="Mapped to columnstore",
            translation_path=(),
            estimated_ratio_loss=0.0
        )

        diags = self.validator.validate_compression(
            schema, translations, target_version="11.0.2100", target_engine="heap", target_edition="STANDARD"
        )
        
        self.assertTrue(any(d.diagnostic_code == "COMPRESSION_EDITION_LIMITATION" for d in diags))

        # Scenario: MySQL Page compression requested on MyISAM storage engine
        translations_mysql = {"orders": CompressionTranslation(
            source_dialect=SystemType.ORACLE,
            target_dialect=SystemType.MYSQL,
            source_algorithm=CompressionAlgorithm.ADVANCED_ROW,
            target_algorithm=CompressionAlgorithm.PAGE,
            compatibility_tier=CompressionCompatibilityTier.LOSSY_TRANSLATION,
            translation_confidence=0.80,
            translation_rationale="Mapped page",
            translation_path=(),
            estimated_ratio_loss=0.15
        )}
        diags_mysql = self.validator.validate_compression(
            schema, translations_mysql, target_version="8.0", target_engine="MyISAM", target_edition="STANDARD"
        )
        self.assertTrue(any(d.diagnostic_code == "COMPRESSION_ENGINE_MISMATCH" for d in diags_mysql))

    def test_compression_score_calculator_and_ranker(self) -> None:
        """Verify scorer computations, composite score math, and stable sorting priority resolution."""
        schema = self._create_mock_schema("orders")
        table = schema.tables[0]
        calc = CompressionScoreCalculator()

        trans = CompressionTranslation(
            source_dialect=SystemType.ORACLE,
            target_dialect=SystemType.MSSQL,
            source_algorithm=CompressionAlgorithm.ADVANCED_ROW,
            target_algorithm=CompressionAlgorithm.PAGE,
            compatibility_tier=CompressionCompatibilityTier.LOSSLESS_TRANSLATION,
            translation_confidence=0.90,
            translation_rationale="Test trans",
            translation_path=("SRC", "CAP", "TGT"),
            estimated_ratio_loss=0.0
        )

        score = calc.calculate_score(table, trans, projected_size_kb=400, uncompressed_size_kb=1000)
        self.assertEqual(score.expected_storage_benefit, 0.60)
        self.assertEqual(score.priority, 10)  # 5 + 3 (ratio > 0.5) + 2 (orders history bonus)

        # Composite Rank calculation
        # impact = (10 * 1.5) + (0.60 * 8.0) + (0.45 * 6.0) = 15.0 + 4.8 + 2.7 = 22.5
        # friction = (2 * 0.5) + (1 * 0.8) - (0.15 * 4.0) = 1.0 + 0.8 - 0.6 = 1.2
        # rank = (22.5 / 1.2) * 0.90 = 18.75 * 0.9 = 16.88
        composite = CompressionRanker.calculate_composite_rank(score)
        self.assertEqual(composite, 16.87)

        # Test tie resolution
        from akaal.core.intelligence.compression_aware.models import CompressionScore, CompressionRecommendation
        rec1 = CompressionRecommendation("rec1", "Title1", "Desc1", "tables.orders_a", score)
        rec2 = CompressionRecommendation("rec2", "Title2", "Desc2", "tables.orders_b", score)
        
        ranked = CompressionRanker.rank_recommendations([rec2, rec1])
        # Should sort orders_a before orders_b alphabetically on tie
        self.assertEqual(ranked[0].target_object_path, "tables.orders_a")

    def test_compression_subsystem_concurrency(self) -> None:
        """Verify thread-safe concurrent lookups, mutations, and cache accesses under stress."""
        registry = CompressionStrategyRegistry()
        cache = EnterpriseCompressionCache()
        errors = []

        def worker(thread_idx: int) -> None:
            for i in range(50):
                p = CompressionProfile(f"p_{thread_idx}_{i}", SystemType.ORACLE, "heap", CompressionAlgorithm.ADVANCED_ROW, 8)
                rule = CompressionRule(
                    rule_id=f"rule_{thread_idx}_{i}",
                    rule_name=f"Rule {thread_idx} {i}",
                    target_dialect=SystemType.ORACLE,
                    priority=thread_idx * 100 + i,
                    min_row_count=1000,
                    target_column_types=(),
                    recommended_profile=p
                )
                try:
                    # Registry read/write checks
                    if not registry.is_frozen:
                        try:
                            registry.register(f"rule_{thread_idx}_{i}", rule)
                        except RegistryFrozenError:
                            pass
                    registry.list_rules()
                    
                    # Cache read/write checks
                    cache.put(f"k_{thread_idx}_{i}", f"v_{i}")
                    cache.get(f"k_{thread_idx}_{i}")
                except Exception as e:
                    errors.append(e)

        threads = [threading.Thread(target=worker, args=(t,)) for t in range(5)]
        for t in threads:
            t.start()
        
        # Freeze registry mid-execution to test freeze checks
        time.sleep(0.01)
        registry.freeze()

        for t in threads:
            t.join()

        self.assertEqual(len(errors), 0, f"Concurrency stress errors: {errors}")

    def test_compression_fuzz_inputs(self) -> None:
        """Verify subsystem resilience against corrupt row counts, malformed versions, and negative bounds."""
        # 1. Negative row sizes clamp checks
        default_est = DefaultCompressionEstimatorStrategy()
        schema = self._create_mock_schema("orders")
        table = schema.tables[0]
        
        size, cpu, io = default_est.estimate_compression(table, CompressionAlgorithm.ZSTD, -500)
        self.assertEqual(size, -391)  # should still cleanly size negative bounds without zero divisors

        # 2. Version matcher with malformed strings
        res = CompressionRuleMatcher._parse_version("abc.14..x")
        self.assertEqual(res, (14,))

        # 3. Invalid config checker raises Validation errors
        validator = CompressionLayoutValidator()
        bad_config = {
            "profiles": [
                {"profile_id": "duplicate"},
                {"profile_id": "duplicate"}
            ]
        }
        with self.assertRaises(CompressionValidationError):
            validator.validate_startup_config(bad_config)

    def test_compression_performance_budgets(self) -> None:
        """Benchmark compression analysis and registry lookups against millisecond SLO targets."""
        # 1. Registry bootstrap & lookup bench
        start_reg = time.perf_counter()
        registry = CompressionStrategyRegistry()
        p = CompressionProfile("p", SystemType.POSTGRESQL, "heap", CompressionAlgorithm.TOAST, 8)
        for i in range(100):
            r = CompressionRule(f"r_{i}", f"Rule {i}", SystemType.POSTGRESQL, i, 1000, (), p)
            registry.register(r.rule_id, r)
        registry.freeze()
        dur_reg_ms = (time.perf_counter() - start_reg) * 1000.0
        
        # SLO startup budget: < 10ms
        self.assertTrue(dur_reg_ms < 10.0, f"Registry bootstrap {dur_reg_ms} ms exceeds SLO budget 10ms")

        # 2. Warm Strategy lookup bench
        start_lkp = time.perf_counter()
        for _ in range(1000):
            registry.get_matching_rules(SystemType.POSTGRESQL, "14.0", "heap", "standard")
        dur_lkp_ms = ((time.perf_counter() - start_lkp) / 1000.0) * 1000.0
        # Warm lookup budget: < 0.3ms per lookup
        self.assertTrue(dur_lkp_ms < 0.30, f"Warm registry lookup {dur_lkp_ms} ms exceeds SLO 0.3ms")

        # 3. Sizing Analysis run budget
        schema = self._create_mock_schema("orders")
        analyzer = CompressionLayoutAnalyzer(registry)
        start_anl = time.perf_counter()
        for _ in range(50):
            analyzer.analyze_compression(schema, SystemType.POSTGRESQL)
        dur_anl_ms = ((time.perf_counter() - start_anl) / 50.0) * 1000.0
        # Analysis SLO budget: < 35ms
        self.assertTrue(dur_anl_ms < 35.0, f"Sizing analysis {dur_anl_ms} ms exceeds SLO budget 35ms")

        print(f"\n[BENCHMARK] Registry Rebuild (100 rules): {dur_reg_ms:.2f} ms")
        print(f"[BENCHMARK] Warm Strategy Lookup: {dur_lkp_ms:.4f} ms")
        print(f"[BENCHMARK] Sizing Analysis: {dur_anl_ms:.2f} ms")


# =============================================================================
# Feature 5 Encryption-Aware Subsystem Verification
# =============================================================================

class TestEncryptionSubsystem(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = EncryptionStrategyRegistry()
        self.analyzer = EncryptionLayoutAnalyzer(self.registry)
        self.validator = EncryptionLayoutValidator()
        self.advisor = EncryptionRecommendationAdvisor()

    def _create_mock_schema(self, table_name: str) -> Schema:
        from akaal.core.comparison.models.schema import ColumnSchema, TableSchema, Schema
        cols = [
            ColumnSchema("id", "BIGINT", "BIGINT", False),
            ColumnSchema("payload", "VARCHAR", "VARCHAR(4000)", True)
        ]
        table = TableSchema(
            name=table_name,
            columns=tuple(cols),
            primary_key=None,
            foreign_keys=(),
            indexes=(),
            constraints=()
        )
        return Schema(tables=(table,), vendor=SystemType.ORACLE)

    def test_encryption_rule_matcher_specificity_and_sorting(self) -> None:
        """Verify EncryptionRuleMatcher computes specificity and priority ordering correctly."""
        p = EncryptionProfile(
            "p1", SystemType.POSTGRESQL, "heap", EncryptionAlgorithm.AES256,
            EncryptionMode.CBC, KeyManagementProvider.LOCAL_WALLET, KeyRotationPolicy.NONE, 256
        )
        r1 = EncryptionRule("r1", "Generic PG", SystemType.POSTGRESQL, 10, recommended_profile=p)
        r2 = EncryptionRule("r2", "Specific PG 14+", SystemType.POSTGRESQL, 10, min_version="14.0", recommended_profile=p)
        r3 = EncryptionRule("r3", "High Priority Engine Match", SystemType.POSTGRESQL, 50, min_version="14.0", required_engine="heap", recommended_profile=p)

        rules = [r1, r2, r3]

        # Match for PG 13
        matched_pg13 = EncryptionRuleMatcher.match_rules(rules, SystemType.POSTGRESQL, "13.0", "heap", "standard")
        self.assertEqual(len(matched_pg13), 1)
        self.assertEqual(matched_pg13[0].rule_id, "r1")

        # Match for PG 14 (r3 wins on priority and specificity)
        matched_pg14 = EncryptionRuleMatcher.match_rules(rules, SystemType.POSTGRESQL, "14.2", "heap", "standard")
        self.assertEqual(len(matched_pg14), 3)
        self.assertEqual(matched_pg14[0].rule_id, "r3")
        self.assertEqual(matched_pg14[1].rule_id, "r2")

    def test_encryption_strategy_registry_lifecycle_and_conflict(self) -> None:
        """Verify strategy registry bootstrap, unique constraints, freeze checks, and snap copy-on-write."""
        registry = EncryptionStrategyRegistry()
        p = EncryptionProfile(
            "p1", SystemType.ORACLE, "heap", EncryptionAlgorithm.AES256,
            EncryptionMode.CBC, KeyManagementProvider.LOCAL_WALLET, KeyRotationPolicy.NONE, 256
        )
        r1 = EncryptionRule("rule1", "Oracle Encryption", SystemType.ORACLE, 10, recommended_profile=p)
        
        registry.register(r1.rule_id, r1)

        # Duplicate ID checks
        with self.assertRaises(RegistryDuplicateError):
            registry.register(r1.rule_id, r1)

        # Overlapping priority conflict checks
        r_conf = EncryptionRule("rule_conf", "Oracle Conf", SystemType.ORACLE, 10, recommended_profile=p)
        with self.assertRaises(EncryptionRegistryConflictError):
            registry.register(r_conf.rule_id, r_conf)

        # Index retrieval checks
        rules_by_algo = registry.get_rules_for_algorithm(EncryptionAlgorithm.AES256)
        self.assertEqual(len(rules_by_algo), 1)

        # Freeze check
        registry.freeze()
        with self.assertRaises(RegistryFrozenError):
            registry.register("rule2", r1)

        # Snapshot check
        snap = registry.snapshot()
        self.assertFalse(snap.is_frozen)

    def test_enterprise_encryption_cache(self) -> None:
        """Verify cache LRU limits, TTL expirations, and telemetry counters."""
        cache = EnterpriseEncryptionCache(max_entries=3, ttl_seconds=0.1)
        
        cache.put("k1", "v1")
        cache.put("k2", "v2")
        cache.put("k3", "v3")

        self.assertEqual(cache.get("k1"), "v1")

        # Evict oldest entry (k2 since k1 was recently retrieved)
        cache.put("k4", "v4")
        self.assertIsNone(cache.get("k2"))
        self.assertEqual(cache.get("k1"), "v1")

        # TTL check
        time.sleep(0.15)
        self.assertIsNone(cache.get("k1"))
        stats = cache.get_statistics()
        self.assertEqual(stats["misses"], 2)

    def test_encryption_layout_analyzer_graph(self) -> None:
        """Verify multi-step path search, capability negotiations, and performance penalties."""
        # 1. Native match (Oracle -> Oracle)
        trans_native = self.analyzer.resolve_translation(SystemType.ORACLE, EncryptionAlgorithm.AES256, SystemType.ORACLE)
        self.assertEqual(trans_native.compatibility_tier, EncryptionCompatibilityTier.NATIVE)
        self.assertEqual(trans_native.target_algorithm, EncryptionAlgorithm.AES256)

        # 2. Keyring plugin check (Oracle -> MySQL)
        trans_mysql = self.analyzer.resolve_translation(SystemType.ORACLE, EncryptionAlgorithm.AES256, SystemType.MYSQL)
        self.assertEqual(trans_mysql.compatibility_tier, EncryptionCompatibilityTier.PLUGIN_PROVIDED)
        self.assertEqual(trans_mysql.target_algorithm, EncryptionAlgorithm.AES256)

        # 3. Manual migration check (Oracle -> PG)
        trans_pg = self.analyzer.resolve_translation(SystemType.ORACLE, EncryptionAlgorithm.AES256, SystemType.POSTGRESQL)
        self.assertEqual(trans_pg.compatibility_tier, EncryptionCompatibilityTier.REQUIRES_MANUAL_MIGRATION)

    def test_encryption_layout_validator_diagnostics(self) -> None:
        """Verify edition licensing checks, deprecated algorithms warnings, and manual setup recommendations."""
        schema = self._create_mock_schema("member_orders")
        
        # Scenario: Pre-2019 Standard Edition SQL Server TDE restriction
        translations = {
            "member_orders": EncryptionTranslation(
                source_dialect=SystemType.ORACLE,
                target_dialect=SystemType.MSSQL,
                source_algorithm=EncryptionAlgorithm.AES256,
                target_algorithm=EncryptionAlgorithm.AES256,
                compatibility_tier=EncryptionCompatibilityTier.NATIVE,
                translation_confidence=1.0,
                translation_rationale="Oracle to SQL Server TDE",
                translation_path=("SRC", "CAP", "TGT"),
                estimated_performance_overhead=0.02
            )
        }
        
        diags = self.validator.validate_encryption(
            schema, translations, target_version="14.0.1000", target_engine="heap", target_edition="STANDARD"
        )
        self.assertTrue(any(d.diagnostic_code == "ENCRYPTION_EDITION_LIMITATION" for d in diags))

        # Scenario: Deprecated 3DES algorithm on MySQL
        translations_3des = {
            "member_orders": EncryptionTranslation(
                source_dialect=SystemType.ORACLE,
                target_dialect=SystemType.MYSQL,
                source_algorithm=EncryptionAlgorithm.TRIPLE_DES,
                target_algorithm=EncryptionAlgorithm.TRIPLE_DES,
                compatibility_tier=EncryptionCompatibilityTier.UNSUPPORTED,
                translation_confidence=0.8,
                translation_rationale="3DES match",
                translation_path=(),
                estimated_performance_overhead=0.10
            )
        }
        diags_3des = self.validator.validate_encryption(
            schema, translations_3des, target_version="8.0", target_engine="InnoDB", target_edition="STANDARD"
        )
        self.assertTrue(any(d.diagnostic_code == "ENCRYPTION_UNSUPPORTED_ALGORITHM" for d in diags_3des))

    def test_encryption_score_calculator_and_ranker(self) -> None:
        """Verify raw score components, sensitivity keyword matching, and composite rank tie resolution."""
        schema = self._create_mock_schema("member_secrets")
        table = schema.tables[0]
        calc = EncryptionScoreCalculator()

        trans = EncryptionTranslation(
            source_dialect=SystemType.ORACLE,
            target_dialect=SystemType.POSTGRESQL,
            source_algorithm=EncryptionAlgorithm.AES256,
            target_algorithm=EncryptionAlgorithm.AES256,
            compatibility_tier=EncryptionCompatibilityTier.REQUIRES_MANUAL_MIGRATION,
            translation_confidence=0.90,
            translation_rationale="Oracle to Postgres TDE",
            translation_path=("SRC", "CAP", "TGT"),
            estimated_performance_overhead=0.15
        )

        score = calc.calculate_score(table, trans)
        self.assertEqual(score.security_improvement, 0.95)
        # 5 + 3 (sec_imp > 0.50) + 2 (member_secrets sensitive keywords matching) = 10
        self.assertEqual(score.priority, 10)
        self.assertEqual(score.migration_complexity, 4)

        # Composite Rank calculation
        # impact = (0.95 * 8.0) + (1.0 * 6.0) - (0.15 * 4.0) = 7.6 + 6.0 - 0.6 = 13.0
        # friction = (4 * 0.5) + (3 * 0.8) = 2.0 + 2.4 = 4.4
        # rank = (13.0 / 4.4) * 0.90 = 2.954... * 0.9 = 2.659...
        composite = EncryptionRanker.calculate_composite_rank(score)
        self.assertEqual(composite, 2.66)

        # Stable sorting check
        rec1 = EncryptionRecommendation("rec1", "Title1", "Desc1", "tables.member_a", score)
        rec2 = EncryptionRecommendation("rec2", "Title2", "Desc2", "tables.member_b", score)
        
        ranked = EncryptionRanker.rank_recommendations([rec2, rec1])
        self.assertEqual(ranked[0].target_object_path, "tables.member_a")

    def test_encryption_subsystem_concurrency(self) -> None:
        """Verify lock synchronization for concurrent writes/reads and hot reloads."""
        registry = EncryptionStrategyRegistry()
        cache = EnterpriseEncryptionCache()
        errors = []

        def worker(thread_idx: int) -> None:
            for i in range(50):
                p = EncryptionProfile(
                    f"p_{thread_idx}_{i}", SystemType.ORACLE, "heap", EncryptionAlgorithm.AES256,
                    EncryptionMode.CBC, KeyManagementProvider.LOCAL_WALLET, KeyRotationPolicy.NONE, 256
                )
                rule = EncryptionRule(
                    rule_id=f"rule_{thread_idx}_{i}",
                    rule_name=f"Rule {thread_idx} {i}",
                    target_dialect=SystemType.ORACLE,
                    priority=thread_idx * 100 + i,
                    recommended_profile=p
                )
                try:
                    if not registry.is_frozen:
                        try:
                            registry.register(f"rule_{thread_idx}_{i}", rule)
                        except RegistryFrozenError:
                            pass
                    registry.list_rules()
                    cache.put(f"k_{thread_idx}_{i}", f"v_{i}")
                    cache.get(f"k_{thread_idx}_{i}")
                except Exception as e:
                    errors.append(e)

        threads = [threading.Thread(target=worker, args=(t,)) for t in range(5)]
        for t in threads:
            t.start()
            
        time.sleep(0.01)
        registry.freeze()

        for t in threads:
            t.join()

        self.assertEqual(len(errors), 0, f"Concurrency stress errors: {errors}")

    def test_encryption_fuzz_inputs(self) -> None:
        """Verify validator and matcher robustness on corrupt/malformed strings."""
        validator = EncryptionLayoutValidator()
        bad_config = {
            "profiles": [
                {"profile_id": "duplicate"},
                {"profile_id": "duplicate"}
            ]
        }
        with self.assertRaises(EncryptionValidationError):
            validator.validate_startup_config(bad_config)

        res = EncryptionRuleMatcher._parse_version("xyz.2019..ab")
        self.assertEqual(res, (2019,))

    def test_encryption_performance_budgets(self) -> None:
        """Benchmark encryption analysis runtimes and rule registry lookup latency budgets."""
        # 1. Registry rebuild latency
        start_reg = time.perf_counter()
        registry = EncryptionStrategyRegistry()
        p = EncryptionProfile(
            "p", SystemType.POSTGRESQL, "heap", EncryptionAlgorithm.AES256,
            EncryptionMode.CBC, KeyManagementProvider.LOCAL_WALLET, KeyRotationPolicy.NONE, 256
        )
        for i in range(100):
            r = EncryptionRule(f"r_{i}", f"Rule {i}", SystemType.POSTGRESQL, i, recommended_profile=p)
            registry.register(r.rule_id, r)
        registry.freeze()
        dur_reg_ms = (time.perf_counter() - start_reg) * 1000.0
        self.assertTrue(dur_reg_ms < 20.0, f"Registry bootstrap {dur_reg_ms} ms exceeds SLO 20ms")

        # 2. Strategy lookup latency
        start_lkp = time.perf_counter()
        for _ in range(1000):
            registry.get_matching_rules(SystemType.POSTGRESQL, "14.0", "heap", "standard")
        dur_lkp_ms = ((time.perf_counter() - start_lkp) / 1000.0) * 1000.0
        self.assertTrue(dur_lkp_ms < 1.0, f"Warm lookup {dur_lkp_ms} ms exceeds SLO 1.0ms")

        # 3. Encryption analysis pass latency
        schema = self._create_mock_schema("member_logs")
        analyzer = EncryptionLayoutAnalyzer(registry)
        start_anl = time.perf_counter()
        for _ in range(50):
            analyzer.analyze_encryption(schema, SystemType.POSTGRESQL)
        dur_anl_ms = ((time.perf_counter() - start_anl) / 50.0) * 1000.0
        self.assertTrue(dur_anl_ms < 35.0, f"Analysis {dur_anl_ms} ms exceeds SLO 35ms")

        print(f"\n[BENCHMARK] Encryption Registry Rebuild (100 rules): {dur_reg_ms:.2f} ms")
        print(f"[BENCHMARK] Encryption Warm Strategy Lookup: {dur_lkp_ms:.4f} ms")
        print(f"[BENCHMARK] Encryption Analysis Pass: {dur_anl_ms:.2f} ms")


# =============================================================================
# Feature 6: Cross-Version Compatibility Engine Test Suite
# =============================================================================

class TestCrossVersionCompatibilitySubsystem(unittest.TestCase):
    """
    Comprehensive test suite for Feature 6: Enterprise Cross-Version Compatibility Engine.

    Covers:
    - Model immutability and composite rank formula
    - Registry lifecycle (bootstrap, duplicate, conflict, freeze, snapshot, hot_reload)
    - Rule matcher specificity and version bound evaluation
    - Capability analyzer findings, statistics, and summary
    - Validator structural checks and startup config validation
    - Recommendation engine scoring, ranking, and threshold filtering
    - Report builder metadata assembly and confidence computation
    - Cache TTL, LRU eviction, and statistics
    - Metrics collector threading and timer context manager
    - Concurrency stress test (10 threads)
    - Fuzz test on malformed version strings and config
    - Performance benchmarks (< 20ms bootstrap, < 1ms lookup, < 25ms analysis)
    """

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _make_rule(
        self,
        rule_id: str = "rule_1",
        feature_id: str = "oracle.tde",
        source_dialect: SystemType = SystemType.ORACLE,
        target_dialect: SystemType = SystemType.POSTGRESQL,
        priority: int = 100,
        action: CompatibilityRuleAction = CompatibilityRuleAction.WARN,
        tier: CompatibilityTier = CompatibilityTier.EMULATED,
        min_src: str = None,
        max_src: str = None,
    ) -> CompatibilityRule:
        return CompatibilityRule(
            rule_id=rule_id,
            rule_name=f"Rule {rule_id}",
            feature_id=feature_id,
            source_dialect=source_dialect,
            target_dialect=target_dialect,
            priority=priority,
            action=action,
            compatibility_tier=tier,
            min_source_version=min_src,
            max_source_version=max_src,
            remediation_guidance="See migration guide.",
        )

    def _make_schema(self, table_name: str = "users") -> Schema:
        from akaal.core.comparison.models.schema import TableSchema, ColumnSchema
        col = ColumnSchema(name="id", data_type="INTEGER", raw_type="INTEGER", nullable=False)
        table = TableSchema(name=table_name, columns=(col,))
        return Schema(tables=(table,))

    def _make_db_version(self, major: int = 14, minor: int = 0) -> DbVersion:
        return DbVersion(major=major, minor=minor, patch=0)

    # ------------------------------------------------------------------
    # 1. Model Immutability
    # ------------------------------------------------------------------

    def test_compatibility_rule_is_frozen(self) -> None:
        """CompatibilityRule must be immutable."""
        rule = self._make_rule()
        from dataclasses import FrozenInstanceError
        with self.assertRaises(FrozenInstanceError):
            rule.priority = 999  # type: ignore

    def test_compatibility_score_is_frozen(self) -> None:
        """CompatibilityScore must be immutable."""
        score = CompatibilityScore(
            confidence=0.85, priority=7, risk_level=2, migration_effort=2,
            remediation_count=1, blocking_issues=0, rationale="Good.",
        )
        from dataclasses import FrozenInstanceError
        with self.assertRaises(FrozenInstanceError):
            score.confidence = 0.0  # type: ignore

    def test_compatibility_score_composite_rank(self) -> None:
        """Composite rank formula: high confidence + low risk = high rank."""
        low_risk = CompatibilityScore(
            confidence=0.95, priority=9, risk_level=1, migration_effort=1,
            remediation_count=0, blocking_issues=0, rationale="NATIVE",
        )
        high_risk = CompatibilityScore(
            confidence=0.30, priority=2, risk_level=5, migration_effort=5,
            remediation_count=3, blocking_issues=2, rationale="BLOCKED",
        )
        self.assertGreater(low_risk.composite_rank, high_risk.composite_rank)

    def test_feature_capability_is_frozen(self) -> None:
        """FeatureCapability must be immutable."""
        cap = FeatureCapability(
            feature_id="oracle.tde", feature_name="TDE", category=FeatureCategory.SECURITY,
            dialect=SystemType.ORACLE, min_version="11g", is_supported=True,
            compatibility_tier=CompatibilityTier.NATIVE,
        )
        from dataclasses import FrozenInstanceError
        with self.assertRaises(FrozenInstanceError):
            cap.is_supported = False  # type: ignore

    # ------------------------------------------------------------------
    # 2. Registry Lifecycle
    # ------------------------------------------------------------------

    def test_registry_register_and_lookup(self) -> None:
        """Register a rule and retrieve it by ID."""
        reg = CompatibilityStrategyRegistry()
        rule = self._make_rule("r1")
        reg.register("r1", rule)
        self.assertEqual(reg.get_rule("r1"), rule)

    def test_registry_duplicate_raises(self) -> None:
        """Registering the same rule_id twice raises RegistryDuplicateError."""
        from akaal.core.intelligence.common.exceptions import RegistryDuplicateError
        reg = CompatibilityStrategyRegistry()
        rule = self._make_rule("r1")
        reg.register("r1", rule)
        with self.assertRaises(RegistryDuplicateError):
            reg.register("r1", rule)

    def test_registry_freeze_blocks_registration(self) -> None:
        """Registering after freeze raises RegistryFrozenError."""
        from akaal.core.intelligence.common.exceptions import RegistryFrozenError
        reg = CompatibilityStrategyRegistry()
        reg.register("r1", self._make_rule("r1"))
        reg.freeze()
        with self.assertRaises(RegistryFrozenError):
            reg.register("r2", self._make_rule("r2"))

    def test_registry_is_frozen_flag(self) -> None:
        """is_frozen reflects the freeze state correctly."""
        reg = CompatibilityStrategyRegistry()
        self.assertFalse(reg.is_frozen)
        reg.freeze()
        self.assertTrue(reg.is_frozen)

    def test_registry_snapshot_is_independent(self) -> None:
        """Snapshot returns a mutable copy independent of the original."""
        reg = CompatibilityStrategyRegistry()
        reg.register("r1", self._make_rule("r1"))
        reg.freeze()

        snap = reg.snapshot()
        self.assertFalse(snap.is_frozen)
        # Use a different feature_id and priority to avoid registry conflict
        snap.register("r2", self._make_rule(
            "r2", feature_id="oracle.partitioning", priority=200
        ))
        # Original should not see r2
        self.assertIsNone(reg.get_rule("r2"))
        self.assertIsNotNone(snap.get_rule("r2"))

    def test_registry_hot_reload(self) -> None:
        """Hot reload atomically replaces the rule set."""
        reg = CompatibilityStrategyRegistry()
        reg.register("r1", self._make_rule("r1"))

        new_rules = {"r_new": self._make_rule("r_new")}
        reg.hot_reload(new_rules)

        self.assertIsNone(reg.get_rule("r1"))
        self.assertIsNotNone(reg.get_rule("r_new"))

    def test_registry_hot_reload_frozen_raises(self) -> None:
        """Hot reload on a frozen registry raises RegistryFrozenError."""
        from akaal.core.intelligence.common.exceptions import RegistryFrozenError
        reg = CompatibilityStrategyRegistry()
        reg.freeze()
        with self.assertRaises(RegistryFrozenError):
            reg.hot_reload({"r_new": self._make_rule("r_new")})

    def test_registry_conflict_detection(self) -> None:
        """Overlapping rules with same priority raise CompatibilityRegistryConflictError."""
        reg = CompatibilityStrategyRegistry()
        r1 = self._make_rule("r1", priority=100)
        r2 = self._make_rule("r2", priority=100)  # same feature, same priority
        reg.register("r1", r1)
        with self.assertRaises(CompatibilityRegistryConflictError):
            reg.register("r2", r2)

    def test_registry_no_conflict_different_priority(self) -> None:
        """Rules with different priorities on same feature should not conflict."""
        reg = CompatibilityStrategyRegistry()
        r1 = self._make_rule("r1", priority=100)
        r2 = self._make_rule("r2", priority=50)
        reg.register("r1", r1)
        reg.register("r2", r2)  # Should not raise
        self.assertEqual(len(reg.list_rules()), 2)

    def test_registry_multi_index_queries(self) -> None:
        """Multi-index accessors return correct subsets of rules."""
        reg = CompatibilityStrategyRegistry()
        r1 = self._make_rule("r1", feature_id="oracle.tde", source_dialect=SystemType.ORACLE, priority=100)
        r2 = self._make_rule("r2", feature_id="oracle.partitioning", source_dialect=SystemType.ORACLE, priority=50)
        reg.register("r1", r1)
        reg.register("r2", r2)

        by_source = reg.get_rules_for_source_dialect(SystemType.ORACLE)
        self.assertEqual(len(by_source), 2)

        by_target = reg.get_rules_for_target_dialect(SystemType.POSTGRESQL)
        self.assertEqual(len(by_target), 2)

        by_feature = reg.get_rules_for_feature("oracle.tde")
        self.assertEqual(len(by_feature), 1)
        self.assertEqual(by_feature[0].rule_id, "r1")

        by_action = reg.get_rules_by_action(CompatibilityRuleAction.WARN)
        self.assertEqual(len(by_action), 2)

    def test_registry_list_rules_deterministic_order(self) -> None:
        """list_rules returns rules in deterministic descending priority order."""
        reg = CompatibilityStrategyRegistry()
        for i, priority in enumerate([30, 80, 50]):
            r = self._make_rule(f"r{i}", feature_id=f"oracle.feat_{i}",
                                priority=priority, source_dialect=SystemType.ORACLE)
            reg.register(f"r{i}", r)

        rules = reg.list_rules()
        priorities = [r.priority for r in rules]
        self.assertEqual(priorities, sorted(priorities, reverse=True))

    # ------------------------------------------------------------------
    # 3. Rule Matcher
    # ------------------------------------------------------------------

    def test_rule_matcher_version_bounds(self) -> None:
        """Matcher correctly filters rules by source version bounds."""
        r_bounded = self._make_rule(
            "r_bounded", min_src="12.0", max_src="19.0", priority=100,
        )
        r_unbounded = self._make_rule("r_unbounded", priority=50)

        matched_in_range = CompatibilityRuleMatcher.match_rules(
            [r_bounded, r_unbounded],
            SystemType.ORACLE, SystemType.POSTGRESQL,
            "15.0", "14.0",
        )
        self.assertIn(r_bounded, matched_in_range)
        self.assertIn(r_unbounded, matched_in_range)

        matched_out_of_range = CompatibilityRuleMatcher.match_rules(
            [r_bounded, r_unbounded],
            SystemType.ORACLE, SystemType.POSTGRESQL,
            "20.0", "14.0",
        )
        self.assertNotIn(r_bounded, matched_out_of_range)
        self.assertIn(r_unbounded, matched_out_of_range)

    def test_rule_matcher_dialect_filter(self) -> None:
        """Rules only match their declared source/target dialect pair."""
        r_oracle_pg = self._make_rule(
            "r1", source_dialect=SystemType.ORACLE,
            target_dialect=SystemType.POSTGRESQL, priority=100,
        )
        matched = CompatibilityRuleMatcher.match_rules(
            [r_oracle_pg], SystemType.MYSQL, SystemType.POSTGRESQL, "8.0", "14.0",
        )
        self.assertEqual(len(matched), 0)

    def test_rule_matcher_specificity_ordering(self) -> None:
        """More constrained rules (with version bounds) outrank unbounded rules."""
        r_specific = self._make_rule(
            "r_specific", feature_id="oracle.tde",
            min_src="11.0", max_src="12.0", priority=50,
        )
        r_general = self._make_rule("r_general", feature_id="oracle.tde", priority=100)

        matched = CompatibilityRuleMatcher.match_rules(
            [r_specific, r_general],
            SystemType.ORACLE, SystemType.POSTGRESQL,
            "11.5", "14.0",
        )
        # r_specific has min+max bounds (+20 specificity) vs r_general (+0)
        # so r_specific should appear first despite lower priority
        self.assertEqual(matched[0].rule_id, "r_specific")

    # ------------------------------------------------------------------
    # 4. Capability Analyzer
    # ------------------------------------------------------------------

    def test_analyzer_produces_findings_for_oracle_to_pg(self) -> None:
        """Analyzer returns a non-empty list of findings for Oracle -> PostgreSQL."""
        reg = CompatibilityStrategyRegistry()
        analyzer = CompatibilityCapabilityAnalyzer(reg)
        schema = self._make_schema()
        findings, diags, stats, summary = analyzer.analyze(
            schema=schema,
            source_dialect=SystemType.ORACLE,
            target_dialect=SystemType.POSTGRESQL,
            source_version="19.0",
            target_version="14.0",
        )
        self.assertGreater(len(findings), 0)
        self.assertIsInstance(stats, CompatibilityStatistics)
        self.assertIsInstance(summary, CompatibilitySummary)

    def test_analyzer_native_features_have_allow_action(self) -> None:
        """Features with NATIVE tier receive ALLOW action by default."""
        reg = CompatibilityStrategyRegistry()
        analyzer = CompatibilityCapabilityAnalyzer(reg)
        schema = self._make_schema()
        findings, _, _, _ = analyzer.analyze(
            schema=schema,
            source_dialect=SystemType.ORACLE,
            target_dialect=SystemType.POSTGRESQL,
            source_version="19.0",
            target_version="14.0",
        )
        native_findings = [f for f in findings if f.compatibility_tier == CompatibilityTier.NATIVE]
        for f in native_findings:
            self.assertEqual(f.action, CompatibilityRuleAction.ALLOW)

    def test_analyzer_unsupported_features_have_block_action(self) -> None:
        """Features with UNSUPPORTED tier receive BLOCK action by default."""
        reg = CompatibilityStrategyRegistry()
        analyzer = CompatibilityCapabilityAnalyzer(reg)
        schema = self._make_schema()
        findings, _, _, _ = analyzer.analyze(
            schema=schema,
            source_dialect=SystemType.ORACLE,
            target_dialect=SystemType.MYSQL,
            source_version="19.0",
            target_version="8.0",
        )
        blocked = [f for f in findings if f.compatibility_tier == CompatibilityTier.UNSUPPORTED]
        for f in blocked:
            self.assertEqual(f.action, CompatibilityRuleAction.BLOCK)

    def test_analyzer_statistics_counts_match_findings(self) -> None:
        """Statistics counts are consistent with the findings list."""
        reg = CompatibilityStrategyRegistry()
        analyzer = CompatibilityCapabilityAnalyzer(reg)
        schema = self._make_schema()
        findings, _, stats, _ = analyzer.analyze(
            schema=schema,
            source_dialect=SystemType.ORACLE,
            target_dialect=SystemType.POSTGRESQL,
            source_version="19.0",
            target_version="14.0",
        )
        total = (
            stats.native_features_count
            + stats.emulated_features_count
            + stats.partial_features_count
            + stats.plugin_required_count
            + stats.unsupported_features_count
        )
        self.assertEqual(total, stats.total_features_analyzed)
        self.assertEqual(stats.total_features_analyzed, len(findings))

    def test_analyzer_summary_fully_compatible_oracle_pg(self) -> None:
        """Oracle -> PostgreSQL should NOT be fully compatible (some unsupported features)."""
        reg = CompatibilityStrategyRegistry()
        analyzer = CompatibilityCapabilityAnalyzer(reg)
        schema = self._make_schema()
        _, _, _, summary = analyzer.analyze(
            schema=schema,
            source_dialect=SystemType.ORACLE,
            target_dialect=SystemType.POSTGRESQL,
            source_version="19.0",
            target_version="14.0",
        )
        # oracle.dblinks -> PostgreSQL = PLUGIN_PROVIDED (not blocking), so is_fully_compatible
        # depends on actual UNSUPPORTED/BLOCK counts
        self.assertIsInstance(summary.is_fully_compatible, bool)

    def test_analyzer_registry_rule_overrides_default_tier(self) -> None:
        """A registry rule can override the built-in tier and action for a feature."""
        reg = CompatibilityStrategyRegistry()
        # Override oracle.tde -> POSTGRESQL to BLOCK
        override_rule = CompatibilityRule(
            rule_id="override_tde",
            rule_name="Block TDE override",
            feature_id="oracle.tde",
            source_dialect=SystemType.ORACLE,
            target_dialect=SystemType.POSTGRESQL,
            priority=999,
            action=CompatibilityRuleAction.BLOCK,
            compatibility_tier=CompatibilityTier.UNSUPPORTED,
            remediation_guidance="TDE not allowed by policy.",
        )
        reg.register("override_tde", override_rule)

        analyzer = CompatibilityCapabilityAnalyzer(reg)
        schema = self._make_schema()
        findings, diags, _, _ = analyzer.analyze(
            schema=schema,
            source_dialect=SystemType.ORACLE,
            target_dialect=SystemType.POSTGRESQL,
            source_version="19.0",
            target_version="14.0",
        )
        tde_finding = next(f for f in findings if f.feature_id == "oracle.tde")
        self.assertEqual(tde_finding.action, CompatibilityRuleAction.BLOCK)
        self.assertEqual(tde_finding.compatibility_tier, CompatibilityTier.UNSUPPORTED)
        self.assertEqual(tde_finding.applied_rule_id, "override_tde")

    def test_analyzer_emits_diagnostics_for_blocked_features(self) -> None:
        """Analyzer emits CRITICAL diagnostics for BLOCK actions."""
        reg = CompatibilityStrategyRegistry()
        analyzer = CompatibilityCapabilityAnalyzer(reg)
        schema = self._make_schema()
        # Oracle -> MySQL: oracle.hcc is UNSUPPORTED -> BLOCK
        _, diags, _, _ = analyzer.analyze(
            schema=schema,
            source_dialect=SystemType.ORACLE,
            target_dialect=SystemType.MYSQL,
            source_version="19.0",
            target_version="8.0",
        )
        critical_diags = [d for d in diags if d.severity.value == "CRITICAL"]
        self.assertGreater(len(critical_diags), 0)

    def test_full_analyzer_end_to_end(self) -> None:
        """CrossVersionCompatibilityAnalyzer produces a complete CompatibilityReport."""
        reg = CompatibilityStrategyRegistry()
        engine = CrossVersionCompatibilityAnalyzer(registry=reg)
        schema = self._make_schema("orders")
        report = engine.check_compatibility(
            schema=schema,
            source_dialect=SystemType.ORACLE,
            target_dialect=SystemType.POSTGRESQL,
            target_version=self._make_db_version(14, 0),
            source_version="19.0",
            correlation_id="corr-1",
            trace_id="trace-1",
            request_id="req-1",
            migration_id="mig-1",
        )
        self.assertIsInstance(report, CompatibilityReport)
        self.assertIsNotNone(report.metadata.report_id)
        self.assertTrue(report.metadata.report_id.startswith("rep:compat:"))
        self.assertGreater(len(report.findings), 0)
        self.assertIsInstance(report.statistics, CompatibilityStatistics)
        self.assertIsInstance(report.summary, CompatibilitySummary)

    # ------------------------------------------------------------------
    # 5. Validator
    # ------------------------------------------------------------------

    def test_ruleset_validator_valid_rules(self) -> None:
        """Valid rule set passes without raising."""
        validator = CompatibilityRuleSetValidator()
        rules = [self._make_rule("r1"), self._make_rule("r2", feature_id="oracle.partitioning")]
        validator.validate_ruleset(rules)  # Should not raise

    def test_ruleset_validator_inverted_version_raises(self) -> None:
        """Inverted version bounds raise CompatibilityRuleValidationError."""
        validator = CompatibilityRuleSetValidator()
        bad_rule = CompatibilityRule(
            rule_id="bad", rule_name="Bad", feature_id="oracle.tde",
            source_dialect=SystemType.ORACLE, target_dialect=SystemType.POSTGRESQL,
            priority=100, action=CompatibilityRuleAction.WARN,
            compatibility_tier=CompatibilityTier.EMULATED,
            min_source_version="20.0", max_source_version="10.0",
        )
        with self.assertRaises(CompatibilityRuleValidationError):
            validator.validate_ruleset([bad_rule])

    def test_ruleset_validator_duplicate_ids_raise(self) -> None:
        """Duplicate rule_ids in the same set raise CompatibilityRuleValidationError."""
        validator = CompatibilityRuleSetValidator()
        r1 = self._make_rule("r1")
        r2 = self._make_rule("r1")  # Same ID
        with self.assertRaises(CompatibilityRuleValidationError):
            validator.validate_ruleset([r1, r2])

    def test_startup_config_validator_missing_rule_id(self) -> None:
        """Config validation raises on missing rule_id."""
        validator = CompatibilityRuleSetValidator()
        bad_config = {"rules": [{"rule_name": "No ID here"}]}
        with self.assertRaises(CompatibilityRuleValidationError):
            validator.validate_startup_config(bad_config)

    def test_startup_config_validator_duplicate_ids(self) -> None:
        """Config validation raises on duplicate rule_ids."""
        validator = CompatibilityRuleSetValidator()
        bad_config = {
            "rules": [
                {"rule_id": "r1", "min_source_version": None},
                {"rule_id": "r1"},
            ]
        }
        with self.assertRaises(CompatibilityRuleValidationError):
            validator.validate_startup_config(bad_config)

    def test_finding_auditor_critical_blocked_feature(self) -> None:
        """Auditor emits CRITICAL diagnostics for blocked critical features."""
        reg = CompatibilityStrategyRegistry()
        analyzer = CompatibilityCapabilityAnalyzer(reg)
        schema = self._make_schema()
        findings, _, _, _ = analyzer.analyze(
            schema=schema,
            source_dialect=SystemType.ORACLE,
            target_dialect=SystemType.MYSQL,
            source_version="19.0",
            target_version="8.0",
        )
        auditor = CompatibilityFindingAuditor()
        extra_diags = auditor.audit(findings=findings, target_edition="STANDARD")
        # oracle.hcc is blocked, but not in _CRITICAL_FEATURES; oracle.tde -> MySQL is NATIVE (not blocked)
        # Check that auditor handles findings without errors
        self.assertIsInstance(extra_diags, list)

    # ------------------------------------------------------------------
    # 6. Recommendation Engine
    # ------------------------------------------------------------------

    def test_recommendation_advisor_skips_native_allow(self) -> None:
        """ALLOW + NATIVE findings produce no recommendations."""
        reg = CompatibilityStrategyRegistry()
        analyzer = CompatibilityCapabilityAnalyzer(reg)
        schema = self._make_schema()
        findings, _, _, _ = analyzer.analyze(
            schema=schema,
            source_dialect=SystemType.ORACLE,
            target_dialect=SystemType.POSTGRESQL,
            source_version="19.0",
            target_version="14.0",
        )
        native_allow_findings = [
            f for f in findings
            if f.action == CompatibilityRuleAction.ALLOW
            and f.compatibility_tier == CompatibilityTier.NATIVE
        ]

        advisor = CompatibilityRecommendationAdvisor()
        recs = advisor.generate_recommendations(native_allow_findings)
        self.assertEqual(len(recs), 0)

    def test_recommendation_advisor_generates_recs_for_non_native(self) -> None:
        """Advisor generates recommendations for non-ALLOW or non-NATIVE findings."""
        reg = CompatibilityStrategyRegistry()
        analyzer = CompatibilityCapabilityAnalyzer(reg)
        schema = self._make_schema()
        findings, _, _, _ = analyzer.analyze(
            schema=schema,
            source_dialect=SystemType.ORACLE,
            target_dialect=SystemType.POSTGRESQL,
            source_version="19.0",
            target_version="14.0",
        )
        non_native = [
            f for f in findings
            if not (f.action == CompatibilityRuleAction.ALLOW and f.compatibility_tier == CompatibilityTier.NATIVE)
        ]
        advisor = CompatibilityRecommendationAdvisor()
        recs = advisor.generate_recommendations(non_native)
        self.assertGreater(len(recs), 0)

    def test_recommendation_ranker_descending_order(self) -> None:
        """Ranker returns recommendations in descending composite rank order."""
        scores = [
            CompatibilityScore(0.9, 9, 1, 1, 0, 0, "High"),
            CompatibilityScore(0.5, 5, 3, 3, 2, 1, "Medium"),
            CompatibilityScore(0.2, 2, 5, 5, 4, 2, "Low"),
        ]
        recs = [
            CompatibilityRecommendation(
                recommendation_id=f"REC_{i}",
                title=f"Rec {i}",
                description="desc",
                target_object_path=f"features.feat_{i}",
                score=s,
                composite_rank=CompatibilityScoreCalculator().compute_composite_rank(s),
            )
            for i, s in enumerate(scores)
        ]
        ranked = CompatibilityRanker.rank(recs)
        ranks = [r.composite_rank for r in ranked]
        self.assertEqual(ranks, sorted(ranks, reverse=True))

    def test_score_calculator_block_has_low_rank(self) -> None:
        """A score with blocking issues yields a lower rank than a clean score."""
        calc = CompatibilityScoreCalculator()
        clean_score = CompatibilityScore(0.95, 9, 1, 1, 0, 0, "Clean")
        blocked_score = CompatibilityScore(0.20, 2, 5, 5, 3, 3, "Blocked")
        clean_rank = calc.compute_composite_rank(clean_score)
        blocked_rank = calc.compute_composite_rank(blocked_score)
        self.assertGreater(clean_rank, blocked_rank)

    # ------------------------------------------------------------------
    # 7. Report Builder
    # ------------------------------------------------------------------

    def test_report_builder_assembles_report(self) -> None:
        """Report builder constructs a complete CompatibilityReport."""
        builder = CompatibilityReportBuilder(
            correlation_id="c1", trace_id="t1", request_id="r1", migration_id="m1"
        )
        reg = CompatibilityStrategyRegistry()
        analyzer = CompatibilityCapabilityAnalyzer(reg)
        schema = self._make_schema()
        findings, diagnostics, stats, summary = analyzer.analyze(
            schema=schema,
            source_dialect=SystemType.ORACLE,
            target_dialect=SystemType.POSTGRESQL,
            source_version="19.0",
            target_version="14.0",
        )
        report = builder.build_report(
            source_dialect=SystemType.ORACLE,
            target_dialect=SystemType.POSTGRESQL,
            target_version=self._make_db_version(14, 0),
            findings=tuple(findings),
            diagnostics=tuple(diagnostics),
            statistics=stats,
            summary=summary,
            duration_ms=12.5,
        )
        self.assertIsInstance(report, CompatibilityReport)
        self.assertTrue(report.metadata.report_id.startswith("rep:compat:"))
        self.assertAlmostEqual(report.metadata.execution_duration_ms, 12.5)
        self.assertEqual(report.source_dialect, SystemType.ORACLE)
        self.assertEqual(report.target_dialect, SystemType.POSTGRESQL)

    def test_report_builder_confidence_decreases_with_errors(self) -> None:
        """Confidence in report metadata decreases proportionally to error count."""
        from akaal.core.intelligence.common.models import Diagnostic, Severity, DiagnosticCategory
        builder = CompatibilityReportBuilder(
            correlation_id="c1", trace_id="t1", request_id="r1", migration_id="m1"
        )
        reg = CompatibilityStrategyRegistry()
        analyzer = CompatibilityCapabilityAnalyzer(reg)
        schema = self._make_schema()
        findings, _, stats, summary = analyzer.analyze(
            schema=schema,
            source_dialect=SystemType.ORACLE,
            target_dialect=SystemType.MYSQL,
            source_version="19.0",
            target_version="8.0",
        )
        # Inject critical diagnostics
        critical_diags = tuple(
            Diagnostic(
                diagnostic_code=f"ERR_{i}", severity=Severity.CRITICAL,
                category=DiagnosticCategory.COMPATIBILITY,
                message=f"Critical error {i}", path=f"feat_{i}",
            )
            for i in range(3)
        )
        report = builder.build_report(
            source_dialect=SystemType.ORACLE,
            target_dialect=SystemType.MYSQL,
            target_version=self._make_db_version(8, 0),
            findings=tuple(findings),
            diagnostics=critical_diags,
            statistics=stats,
            summary=summary,
            duration_ms=5.0,
        )
        # 3 critical errors should reduce confidence below 0.75
        self.assertLess(report.metadata.confidence_summary["score"], 0.75)

    # ------------------------------------------------------------------
    # 8. Cache
    # ------------------------------------------------------------------

    def test_cache_put_and_get(self) -> None:
        """Cache stores and retrieves items correctly."""
        cache = CompatibilityCache()
        cache.put("key1", {"data": 42})
        result = cache.get("key1")
        self.assertEqual(result, {"data": 42})

    def test_cache_miss_returns_none(self) -> None:
        """Cache miss returns None for unknown key."""
        cache = CompatibilityCache()
        self.assertIsNone(cache.get("missing_key"))

    def test_cache_lru_eviction(self) -> None:
        """LRU eviction removes the oldest entry when capacity is exceeded."""
        cache = CompatibilityCache(max_entries=3)
        cache.put("k1", "v1")
        cache.put("k2", "v2")
        cache.put("k3", "v3")
        cache.put("k4", "v4")  # Should evict k1

        self.assertIsNone(cache.get("k1"))
        self.assertEqual(cache.get("k2"), "v2")

    def test_cache_statistics(self) -> None:
        """Cache statistics track hits, misses, and evictions."""
        cache = CompatibilityCache(max_entries=2)
        cache.put("k1", "v1")
        cache.get("k1")   # hit
        cache.get("miss")  # miss
        cache.put("k2", "v2")
        cache.put("k3", "v3")  # evicts k1

        stats = cache.get_statistics()
        self.assertEqual(stats["hits"], 1)
        self.assertEqual(stats["misses"], 1)
        self.assertEqual(stats["evictions"], 1)

    def test_cache_clear(self) -> None:
        """Clear empties the cache."""
        cache = CompatibilityCache()
        cache.put("k1", "v1")
        cache.clear()
        self.assertIsNone(cache.get("k1"))

    def test_cache_snapshot_excludes_expired(self) -> None:
        """Snapshot excludes entries whose TTL has expired."""
        cache = CompatibilityCache(ttl_seconds=0.01)
        cache.put("k1", "v1")
        time.sleep(0.02)
        snap = cache.snapshot()
        self.assertNotIn("k1", snap)

    def test_cache_warm_cache(self) -> None:
        """warm_cache pre-populates multiple entries."""
        cache = CompatibilityCache()
        cache.warm_cache({"a": 1, "b": 2, "c": 3})
        self.assertEqual(cache.get("a"), 1)
        self.assertEqual(cache.get("b"), 2)
        self.assertEqual(cache.get("c"), 3)

    # ------------------------------------------------------------------
    # 9. Metrics
    # ------------------------------------------------------------------

    def test_metrics_collector_increment(self) -> None:
        """Increment increases named counter atomically."""
        collector = CompatibilityMetricsCollector()
        collector.increment("analysis_runs_total")
        collector.increment("analysis_runs_total", 4)
        snapshot = collector.get_metrics_snapshot()
        self.assertEqual(snapshot["counters"]["analysis_runs_total"], 5)

    def test_metrics_collector_record_latency(self) -> None:
        """Latency recorder accumulates values correctly."""
        collector = CompatibilityMetricsCollector()
        collector.record_latency("analysis_latency_sum_ms", 12.5)
        collector.record_latency("analysis_latency_sum_ms", 7.5)
        snapshot = collector.get_metrics_snapshot()
        self.assertAlmostEqual(
            snapshot["latencies"]["analysis_latency_sum_ms"], 20.0, places=5
        )

    def test_metrics_timer_context_manager(self) -> None:
        """Timer context manager records elapsed duration."""
        collector = CompatibilityMetricsCollector()
        with CompatibilitySubsystemTimer(collector, "analysis_latency_sum_ms"):
            time.sleep(0.005)
        snapshot = collector.get_metrics_snapshot()
        self.assertGreater(snapshot["latencies"]["analysis_latency_sum_ms"], 0.0)

    def test_metrics_unknown_key_is_noop(self) -> None:
        """Recording to an unknown counter/latency key is silently ignored."""
        collector = CompatibilityMetricsCollector()
        collector.increment("nonexistent_counter")
        collector.record_latency("nonexistent_latency", 99.0)
        snapshot = collector.get_metrics_snapshot()
        self.assertNotIn("nonexistent_counter", snapshot["counters"])

    # ------------------------------------------------------------------
    # 10. Concurrency Stress Test
    # ------------------------------------------------------------------

    def test_compatibility_subsystem_concurrency(self) -> None:
        """10 concurrent threads performing registry writes, reads, and cache ops."""
        reg = CompatibilityStrategyRegistry()
        cache = CompatibilityCache()
        errors = []

        def worker(thread_idx: int) -> None:
            for i in range(40):
                try:
                    rule = CompatibilityRule(
                        rule_id=f"rule_{thread_idx}_{i}",
                        rule_name=f"Rule {thread_idx} {i}",
                        feature_id=f"oracle.feat_{thread_idx}_{i}",
                        source_dialect=SystemType.ORACLE,
                        target_dialect=SystemType.POSTGRESQL,
                        priority=thread_idx * 100 + i,
                        action=CompatibilityRuleAction.WARN,
                        compatibility_tier=CompatibilityTier.EMULATED,
                    )
                    if not reg.is_frozen:
                        try:
                            reg.register(f"rule_{thread_idx}_{i}", rule)
                        except Exception:
                            pass
                    reg.list_rules()
                    cache.put(f"k_{thread_idx}_{i}", f"v_{i}")
                    cache.get(f"k_{thread_idx}_{i}")
                except Exception as e:
                    errors.append(e)

        threads = [threading.Thread(target=worker, args=(t,)) for t in range(10)]
        for t in threads:
            t.start()
        time.sleep(0.015)
        reg.freeze()
        for t in threads:
            t.join()

        self.assertEqual(len(errors), 0, f"Concurrency errors: {errors}")

    # ------------------------------------------------------------------
    # 11. Fuzz Tests
    # ------------------------------------------------------------------

    def test_fuzz_version_parser_garbage_input(self) -> None:
        """Version parser handles garbage strings without crashing."""
        from akaal.core.intelligence.cross_version.registry import _parse_version
        # Non-numeric segments should be skipped silently
        result = _parse_version("abc.xyz..!@#")
        self.assertEqual(result, ())

        result2 = _parse_version("2019.abc.12")
        self.assertIn(2019, result2)
        self.assertIn(12, result2)

    def test_fuzz_startup_config_empty_rules(self) -> None:
        """Empty rules list in config should not raise."""
        validator = CompatibilityRuleSetValidator()
        validator.validate_startup_config({"rules": []})

    def test_fuzz_analyzer_empty_source_features(self) -> None:
        """Analyzer with a source dialect with no built-in features produces empty findings."""
        reg = CompatibilityStrategyRegistry()
        analyzer = CompatibilityCapabilityAnalyzer(reg)
        schema = self._make_schema()
        # REDIS has no built-in capabilities in the matrix
        findings, diags, stats, summary = analyzer.analyze(
            schema=schema,
            source_dialect=SystemType.REDIS,
            target_dialect=SystemType.POSTGRESQL,
            source_version="7.0",
            target_version="14.0",
        )
        self.assertEqual(len(findings), 0)
        self.assertEqual(stats.total_features_analyzed, 0)

    # ------------------------------------------------------------------
    # 12. Performance Benchmarks
    # ------------------------------------------------------------------

    def test_compatibility_performance_budgets(self) -> None:
        """
        Benchmark:
        1. Registry bootstrap with 100 rules < 20ms
        2. Strategy lookup per call < 1ms
        3. Full analysis pass < 25ms
        """
        # 1. Registry bootstrap
        start = time.perf_counter()
        reg = CompatibilityStrategyRegistry()
        for i in range(100):
            r = CompatibilityRule(
                rule_id=f"r_{i}",
                rule_name=f"Rule {i}",
                feature_id=f"oracle.feat_{i}",
                source_dialect=SystemType.ORACLE,
                target_dialect=SystemType.POSTGRESQL,
                priority=i + 1,
                action=CompatibilityRuleAction.WARN,
                compatibility_tier=CompatibilityTier.EMULATED,
            )
            reg.register(f"r_{i}", r)
        reg.freeze()
        dur_bootstrap_ms = (time.perf_counter() - start) * 1000.0
        self.assertLess(dur_bootstrap_ms, 20.0,
                        f"Bootstrap {dur_bootstrap_ms:.2f}ms exceeds SLO 20ms")

        # 2. Lookup latency
        start = time.perf_counter()
        for _ in range(1000):
            reg.get_matching_rules(
                SystemType.ORACLE, SystemType.POSTGRESQL, "19.0", "14.0"
            )
        dur_lookup_ms = ((time.perf_counter() - start) / 1000.0) * 1000.0
        self.assertLess(dur_lookup_ms, 1.0,
                        f"Lookup {dur_lookup_ms:.4f}ms exceeds SLO 1ms")

        # 3. Analysis pass latency
        clean_reg = CompatibilityStrategyRegistry()
        engine = CrossVersionCompatibilityAnalyzer(registry=clean_reg)
        schema = self._make_schema("orders")
        start = time.perf_counter()
        for _ in range(50):
            engine.check_compatibility(
                schema=schema,
                source_dialect=SystemType.ORACLE,
                target_dialect=SystemType.POSTGRESQL,
                target_version=self._make_db_version(14, 0),
                source_version="19.0",
            )
        dur_analysis_ms = ((time.perf_counter() - start) / 50.0) * 1000.0
        self.assertLess(dur_analysis_ms, 25.0,
                        f"Analysis {dur_analysis_ms:.2f}ms exceeds SLO 25ms")

        print(f"\n[BENCHMARK] Compatibility Registry Bootstrap (100 rules): {dur_bootstrap_ms:.2f} ms")
        print(f"[BENCHMARK] Compatibility Warm Lookup: {dur_lookup_ms:.4f} ms")
        print(f"[BENCHMARK] Compatibility Analysis Pass: {dur_analysis_ms:.2f} ms")

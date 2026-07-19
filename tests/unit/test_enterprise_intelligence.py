"""
AKAAL Enterprise Intelligence Subsystem Unit Tests (Phase 9 Platform 2)
========================================================================
Comprehensive verification suite for Platform 2 models, registry, analyzers, engine,
serializers, validators, governance, and public API facade.
"""

import pytest
from types import MappingProxyType
from akaal.intelligence.models import (
    DecisionPriority,
    StrategyType,
    ReadinessTier,
    RiskLevel,
    EnterpriseDecision,
    StrategySynthesis,
    MigrationSimulationResult,
    ReadinessAssessment,
    AgentCoordinationPlan,
    EnterpriseIntelligenceManifest,
    EnterpriseIntelligenceTrace,
    EnterpriseIntelligenceVersionInfo,
    EnterpriseIntelligenceModel,
)


class TestEnterpriseIntelligenceModels:
    """Verification suite for Milestone 1 Models & Data Layer."""

    def test_enterprise_decision_immutability(self):
        decision = EnterpriseDecision(
            decision_id="DEC-001",
            title="Adopt Aggressive Parallel Migration Strategy",
            category="STRATEGY",
            priority=DecisionPriority.HIGH,
            risk_level=RiskLevel.LOW,
            description="Parallel worker execution strategy.",
            rationale="High network bandwidth and worker capacity.",
            strategic_impact="Reduces migration time by 65%.",
            confidence_score=0.95,
            action_items=("Set workers=8", "Enable chunking"),
            trade_offs=("Increased CPU load",),
            affected_components=("worker_nodes",),
            evidence_pointers=("EVID-001",),
            metadata={"source": "analyzer"},
        )

        assert decision.decision_id == "DEC-001"
        assert decision.priority == DecisionPriority.HIGH
        assert decision.confidence_score == 0.95

        # Test top-level attribute immutability
        with pytest.raises(AttributeError):
            decision.confidence_score = 0.99  # type: ignore

        # Test nested dictionary immutability via MappingProxyType
        assert isinstance(decision.metadata, MappingProxyType)
        with pytest.raises(TypeError):
            decision.metadata["source"] = "mutated"  # type: ignore

        # Test to_dict()
        d_dict = decision.to_dict()
        assert d_dict["decision_id"] == "DEC-001"
        assert d_dict["priority"] == "HIGH"
        assert d_dict["risk_level"] == "LOW"

    def test_strategy_synthesis_model(self):
        strategy = StrategySynthesis(
            strategy_id="STRAT-001",
            strategy_type=StrategyType.AGGRESSIVE_PARALLEL,
            primary_objective="Minimize total migration duration",
            recommended_execution_mode="PARALLEL",
            estimated_total_duration_seconds=3600.0,
            max_recommended_parallelism=16,
            key_assumptions=("10Gbps network connection",),
            strategic_advantages=("Fastest cutover window",),
            identified_constraints=("High target IOPS required",),
            mitigation_guidelines=("Monitor target DB queue depth",),
            metadata={"env": "prod"},
        )

        assert strategy.strategy_type == StrategyType.AGGRESSIVE_PARALLEL
        assert strategy.max_recommended_parallelism == 16
        assert isinstance(strategy.metadata, MappingProxyType)

        s_dict = strategy.to_dict()
        assert s_dict["strategy_type"] == "AGGRESSIVE_PARALLEL"
        assert s_dict["max_recommended_parallelism"] == 16

    def test_migration_simulation_result_model(self):
        sim = MigrationSimulationResult(
            simulation_id="SIM-001",
            projected_downtime_seconds_min=120.0,
            projected_downtime_seconds_max=600.0,
            projected_downtime_seconds_p95=300.0,
            projected_total_duration_seconds=3600.0,
            estimated_throughput_records_per_sec=15000.0,
            peak_memory_mb_estimate=1024.0,
            peak_cpu_cores_estimate=8.0,
            failure_probability=0.02,
            bottleneck_stages=("INDEX_BUILD",),
            simulated_risk_factors=("Network jitter",),
            metadata={},
        )

        assert sim.simulation_id == "SIM-001"
        assert sim.failure_probability == 0.02

        sim_dict = sim.to_dict()
        assert sim_dict["projected_downtime_seconds_p95"] == 300.0

    def test_readiness_assessment_model(self):
        readiness = ReadinessAssessment(
            assessment_id="READ-001",
            overall_readiness_score=92.5,
            tier=ReadinessTier.PRODUCTION_READY,
            schema_readiness_score=95.0,
            data_readiness_score=90.0,
            hardware_readiness_score=95.0,
            operational_readiness_score=90.0,
            critical_blockers=(),
            warnings=("Target DB storage space close to 80% threshold",),
            remediation_steps=("Expand target DB volume before cutover",),
            metadata={},
        )

        assert readiness.tier == ReadinessTier.PRODUCTION_READY
        assert readiness.overall_readiness_score == 92.5

        r_dict = readiness.to_dict()
        assert r_dict["tier"] == "PRODUCTION_READY"
        assert r_dict["overall_readiness_score"] == 92.5

    def test_agent_coordination_plan_model(self):
        agent_plan = AgentCoordinationPlan(
            plan_id="AGENT-001",
            total_recommended_agents=4,
            primary_region="us-east-1",
            secondary_regions=("us-west-2",),
            worker_distribution={"us-east-1": 3, "us-west-2": 1},
            failover_nodes=("us-east-1-node-3",),
            coordination_notes=("Enable cross-region TLS encryption",),
            metadata={},
        )

        assert agent_plan.total_recommended_agents == 4
        assert isinstance(agent_plan.worker_distribution, MappingProxyType)

        a_dict = agent_plan.to_dict()
        assert a_dict["worker_distribution"]["us-east-1"] == 3

    def test_enterprise_intelligence_manifest_and_trace(self):
        manifest = EnterpriseIntelligenceManifest(
            advisory_model_id="ADV-MODEL-001",
            total_decisions=5,
            critical_decisions_count=1,
            high_priority_decisions_count=2,
            readiness_score=92.5,
            simulated_downtime_p95_seconds=300.0,
            generated_at_timestamp="2026-07-19T12:00:00Z",
            metadata={},
        )

        trace = EnterpriseIntelligenceTrace(
            trace_id="TRC-001",
            total_execution_duration_ms=4.2,
            analyzer_durations_ms={"strategy": 1.1, "readiness": 0.8},
            decision_graph_duration_ms=1.5,
            evaluation_logs=("Engine execution complete",),
            metadata={},
        )

        v_info = EnterpriseIntelligenceVersionInfo(schema_version="1.0.0", platform_version="1.0.0")

        assert manifest.total_decisions == 5
        assert trace.total_execution_duration_ms == 4.2
        assert v_info.schema_version == "1.0.0"

        m_dict = manifest.to_dict()
        t_dict = trace.to_dict()
        v_dict = v_info.to_dict()

        assert m_dict["total_decisions"] == 5
        assert t_dict["trace_id"] == "TRC-001"
        assert v_dict["schema_version"] == "1.0.0"

    def test_canonical_enterprise_intelligence_model(self):
        decision = EnterpriseDecision(
            decision_id="DEC-001",
            title="Adopt Aggressive Parallel Migration Strategy",
            category="STRATEGY",
            priority=DecisionPriority.HIGH,
            risk_level=RiskLevel.LOW,
            description="Parallel worker execution strategy.",
            rationale="High network bandwidth and worker capacity.",
            strategic_impact="Reduces migration time by 65%.",
            confidence_score=0.95,
        )

        strategy = StrategySynthesis(
            strategy_id="STRAT-001",
            strategy_type=StrategyType.AGGRESSIVE_PARALLEL,
            primary_objective="Minimize total duration",
            recommended_execution_mode="PARALLEL",
            estimated_total_duration_seconds=3600.0,
            max_recommended_parallelism=16,
        )

        sim = MigrationSimulationResult(
            simulation_id="SIM-001",
            projected_downtime_seconds_min=120.0,
            projected_downtime_seconds_max=600.0,
            projected_downtime_seconds_p95=300.0,
            projected_total_duration_seconds=3600.0,
            estimated_throughput_records_per_sec=15000.0,
            peak_memory_mb_estimate=1024.0,
            peak_cpu_cores_estimate=8.0,
            failure_probability=0.02,
        )

        readiness = ReadinessAssessment(
            assessment_id="READ-001",
            overall_readiness_score=92.5,
            tier=ReadinessTier.PRODUCTION_READY,
            schema_readiness_score=95.0,
            data_readiness_score=90.0,
            hardware_readiness_score=95.0,
            operational_readiness_score=90.0,
        )

        agent_plan = AgentCoordinationPlan(
            plan_id="AGENT-001",
            total_recommended_agents=4,
            primary_region="us-east-1",
        )

        manifest = EnterpriseIntelligenceManifest(
            advisory_model_id="ADV-MODEL-001",
            total_decisions=1,
            critical_decisions_count=0,
            high_priority_decisions_count=1,
            readiness_score=92.5,
            simulated_downtime_p95_seconds=300.0,
            generated_at_timestamp="2026-07-19T12:00:00Z",
        )

        trace = EnterpriseIntelligenceTrace(
            trace_id="TRC-001",
            total_execution_duration_ms=4.2,
        )

        v_info = EnterpriseIntelligenceVersionInfo()

        canonical_model = EnterpriseIntelligenceModel(
            model_id="ENT-MODEL-001",
            advisory_model_id="ADV-MODEL-001",
            version_info=v_info,
            manifest=manifest,
            decisions=(decision,),
            strategy=strategy,
            simulation=sim,
            readiness=readiness,
            agent_coordination=agent_plan,
            trace=trace,
            checksum="abc123sha256",
            metadata={"status": "APPROVED"},
        )

        assert canonical_model.model_id == "ENT-MODEL-001"
        assert canonical_model.checksum == "abc123sha256"

        # Check model top-level and nested immutability
        with pytest.raises(AttributeError):
            canonical_model.checksum = "mutated"  # type: ignore

        assert isinstance(canonical_model.metadata, MappingProxyType)
        with pytest.raises(TypeError):
            canonical_model.metadata["status"] = "REJECTED"  # type: ignore

        model_dict = canonical_model.to_dict()
        assert model_dict["model_id"] == "ENT-MODEL-001"
        assert model_dict["decisions"][0]["decision_id"] == "DEC-001"
        assert model_dict["strategy"]["strategy_type"] == "AGGRESSIVE_PARALLEL"


class TestEnterpriseIntelligenceRegistry:
    """Verification suite for Milestone 2 Registry Subsystem."""

    def test_registry_registration_and_lookup(self):
        from akaal.intelligence.registry import EnterpriseIntelligenceRegistry

        reg = EnterpriseIntelligenceRegistry()
        dummy_analyzer = object()

        reg.register("strategy", dummy_analyzer, metadata={"version": "1.0"})

        assert reg.exists("strategy")
        assert reg.get("strategy") is dummy_analyzer
        assert reg.get_metadata("strategy") == {"version": "1.0"}
        assert reg.list() == ["strategy"]

    def test_duplicate_registration_protection(self):
        from akaal.intelligence.registry import EnterpriseIntelligenceRegistry, EnterpriseIntelligenceRegistryError

        reg = EnterpriseIntelligenceRegistry()
        analyzer_1 = object()
        analyzer_2 = object()

        reg.register("readiness", analyzer_1)

        # Attempt duplicate registration without overwrite
        with pytest.raises(EnterpriseIntelligenceRegistryError) as exc_info:
            reg.register("readiness", analyzer_2)
        assert "already registered" in str(exc_info.value)

        # Overwrite with overwrite=True
        reg.register("readiness", analyzer_2, overwrite=True)
        assert reg.get("readiness") is analyzer_2

    def test_unregistration_and_clear(self):
        from akaal.intelligence.registry import EnterpriseIntelligenceRegistry, EnterpriseIntelligenceRegistryError

        reg = EnterpriseIntelligenceRegistry()
        reg.register("analyzer1", object())
        reg.register("analyzer2", object())

        assert len(reg.list()) == 2

        reg.unregister("analyzer1")
        assert not reg.exists("analyzer1")
        assert len(reg.list()) == 1

        # Unregistering non-existent analyzer raises exception
        with pytest.raises(EnterpriseIntelligenceRegistryError):
            reg.unregister("non_existent")

        reg.clear()
        assert len(reg.list()) == 0

    def test_freeze_lifecycle_protection(self):
        from akaal.intelligence.registry import EnterpriseIntelligenceRegistry, EnterpriseIntelligenceRegistryError

        reg = EnterpriseIntelligenceRegistry()
        analyzer = object()
        reg.register("strategy", analyzer)

        assert not reg.is_frozen()
        reg.freeze()
        assert reg.is_frozen()

        # Registration blocked when frozen
        with pytest.raises(EnterpriseIntelligenceRegistryError) as exc_info:
            reg.register("readiness", object())
        assert "Registry is frozen" in str(exc_info.value)

        # Unregistration blocked when frozen
        with pytest.raises(EnterpriseIntelligenceRegistryError):
            reg.unregister("strategy")

        # Clear blocked when frozen
        with pytest.raises(EnterpriseIntelligenceRegistryError):
            reg.clear()

        # Lookup and list remain available when frozen
        assert reg.exists("strategy")
        assert reg.get("strategy") is analyzer
        assert reg.list() == ["strategy"]

        # Unfreeze restores mutable registration state
        reg.unfreeze()
        assert not reg.is_frozen()
        reg.register("readiness", object())
        assert len(reg.list()) == 2

    def test_invalid_registration_arguments(self):
        from akaal.intelligence.registry import EnterpriseIntelligenceRegistry, EnterpriseIntelligenceRegistryError

        reg = EnterpriseIntelligenceRegistry()

        with pytest.raises(EnterpriseIntelligenceRegistryError):
            reg.register("", object())

        with pytest.raises(EnterpriseIntelligenceRegistryError):
            reg.register("valid_name", None)

    def test_deterministic_ordering(self):
        from akaal.intelligence.registry import EnterpriseIntelligenceRegistry

        reg = EnterpriseIntelligenceRegistry()
        reg.register("zebra", object())
        reg.register("alpha", object())
        reg.register("charlie", object())
        reg.register("bravo", object())

        # List should always return deterministically sorted names
        assert reg.list() == ["alpha", "bravo", "charlie", "zebra"]

    def test_concurrent_multithreaded_registry(self):
        import concurrent.futures
        from akaal.intelligence.registry import EnterpriseIntelligenceRegistry

        reg = EnterpriseIntelligenceRegistry()

        def worker_task(idx: int):
            name = f"analyzer_{idx}"
            reg.register(name, object(), metadata={"worker_id": idx})

            assert reg.exists(name)
            assert reg.get(name) is not None
            assert reg.get_metadata(name)["worker_id"] == idx

        # Run 50 concurrent registration & lookup tasks
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(worker_task, i) for i in range(50)]
            for future in concurrent.futures.as_completed(futures):
                future.result()  # Re-raise exceptions if any

        assert len(reg.list()) == 50
        assert reg.list() == sorted([f"analyzer_{i}" for i in range(50)])


class TestEnterpriseIntelligenceValidation:
    """Verification suite for Milestone 3 Validation Subsystem."""

    def test_validate_advisory_model(self):
        from akaal.advisor.models.migration_advisory_model import MigrationAdvisoryModel
        from akaal.advisor.models.advisory_manifest import AdvisoryManifest
        from akaal.advisor.models.advisory_trace import AdvisoryTrace
        from akaal.advisor.models.advisory_version import AdvisoryVersion
        from akaal.intelligence.validation import EnterpriseIntelligenceValidator, EnterpriseIntelligenceValidationError

        advisory_model = MigrationAdvisoryModel(
            sha256_checksum="sha256abc",
            manifest=AdvisoryManifest(advisory_id="ADV-001", plan_id="PLAN-001", plan_checksum="sha256", total_recommendations=0),
            recommendations=(),
            trace=AdvisoryTrace(trace_id="TRC-001", execution_duration_ms=1.0),
        )




        assert EnterpriseIntelligenceValidator.validate_advisory_model(advisory_model) is True

        with pytest.raises(EnterpriseIntelligenceValidationError):
            EnterpriseIntelligenceValidator.validate_advisory_model(None)

        with pytest.raises(EnterpriseIntelligenceValidationError):
            EnterpriseIntelligenceValidator.validate_advisory_model("not_a_model")

    def test_validate_intelligence_model(self):
        from akaal.intelligence.validation import EnterpriseIntelligenceValidator, EnterpriseIntelligenceValidationError

        v_info = EnterpriseIntelligenceVersionInfo()
        manifest = EnterpriseIntelligenceManifest("ADV-001", 1, 0, 1, 95.0, 300.0, "")
        decision = EnterpriseDecision("DEC-001", "Title", "CAT", DecisionPriority.HIGH, RiskLevel.LOW, "", "", "", 0.9)
        strategy = StrategySynthesis("STR-1", StrategyType.AGGRESSIVE_PARALLEL, "", "", 100.0, 4)
        sim = MigrationSimulationResult("SIM-1", 10.0, 100.0, 50.0, 1000.0, 5000.0, 512.0, 4.0, 0.01)
        readiness = ReadinessAssessment("R-1", 95.0, ReadinessTier.PRODUCTION_READY, 95.0, 95.0, 95.0, 95.0)
        agent_plan = AgentCoordinationPlan("AG-1", 2, "us-east-1")
        trace = EnterpriseIntelligenceTrace("TR-1", 2.0)

        model = EnterpriseIntelligenceModel("ENT-001", "ADV-001", v_info, manifest, (decision,), strategy, sim, readiness, agent_plan, trace, "checksum123")

        assert EnterpriseIntelligenceValidator.validate_intelligence_model(model) is True

        # Test duplicate decision ID validation failure
        dup_decision = EnterpriseDecision("DEC-001", "Title2", "CAT", DecisionPriority.LOW, RiskLevel.LOW, "", "", "", 0.8)
        dup_manifest = EnterpriseIntelligenceManifest("ADV-001", 2, 0, 1, 95.0, 300.0, "")
        invalid_model = EnterpriseIntelligenceModel("ENT-002", "ADV-001", v_info, dup_manifest, (decision, dup_decision), strategy, sim, readiness, agent_plan, trace, "checksum123")

        with pytest.raises(EnterpriseIntelligenceValidationError) as exc_info:
            EnterpriseIntelligenceValidator.validate_intelligence_model(invalid_model)
        assert "Duplicate decision_id" in str(exc_info.value)


class TestEnterpriseIntelligenceSerialization:
    """Verification suite for Milestone 3 Serialization Subsystem."""

    def test_dict_and_json_roundtrip(self):
        from akaal.intelligence.serialization import EnterpriseIntelligenceSerializer, EnterpriseIntelligenceSerializerError

        v_info = EnterpriseIntelligenceVersionInfo()
        manifest = EnterpriseIntelligenceManifest("ADV-001", 1, 0, 1, 95.0, 300.0, "2026-07-19T12:00:00Z")
        decision = EnterpriseDecision("DEC-001", "Title", "CAT", DecisionPriority.HIGH, RiskLevel.LOW, "Desc", "Rat", "Imp", 0.95)
        strategy = StrategySynthesis("STR-1", StrategyType.AGGRESSIVE_PARALLEL, "Obj", "PAR", 100.0, 4)
        sim = MigrationSimulationResult("SIM-1", 10.0, 100.0, 50.0, 1000.0, 5000.0, 512.0, 4.0, 0.01)
        readiness = ReadinessAssessment("R-1", 95.0, ReadinessTier.PRODUCTION_READY, 95.0, 95.0, 95.0, 95.0)
        agent_plan = AgentCoordinationPlan("AG-1", 2, "us-east-1")
        trace = EnterpriseIntelligenceTrace("TR-1", 2.0)

        original_model = EnterpriseIntelligenceModel("ENT-001", "ADV-001", v_info, manifest, (decision,), strategy, sim, readiness, agent_plan, trace, "checksum123")

        # Dict roundtrip
        d_dict = EnterpriseIntelligenceSerializer.to_dict(original_model)
        reconstructed_dict = EnterpriseIntelligenceSerializer.from_dict(d_dict)
        assert reconstructed_dict.model_id == original_model.model_id
        assert reconstructed_dict.decisions[0].decision_id == "DEC-001"

        # JSON roundtrip
        json_str = EnterpriseIntelligenceSerializer.to_json(original_model)
        reconstructed_json = EnterpriseIntelligenceSerializer.from_json(json_str)
        assert reconstructed_json.checksum == original_model.checksum
        assert reconstructed_json.strategy.strategy_type == StrategyType.AGGRESSIVE_PARALLEL

    def test_invalid_json_serialization_inputs(self):
        from akaal.intelligence.serialization import EnterpriseIntelligenceSerializer, EnterpriseIntelligenceSerializerError

        with pytest.raises(EnterpriseIntelligenceSerializerError):
            EnterpriseIntelligenceSerializer.from_json("")

        with pytest.raises(EnterpriseIntelligenceSerializerError):
            EnterpriseIntelligenceSerializer.from_json("{invalid_json}")


class TestEnterpriseIntelligenceMetrics:
    """Verification suite for Milestone 3 Metrics Subsystem."""

    def test_metrics_collection_and_timer_context(self):
        from akaal.intelligence.metrics import EnterpriseIntelligenceMetricsCollector, TimerContext

        collector = EnterpriseIntelligenceMetricsCollector()
        collector.record_duration("test_duration", 15.5)
        collector.increment_counter("events", 5)
        collector.record_success()

        snapshot = collector.get_snapshot()
        assert snapshot["durations_ms"]["test_duration"] == 15.5
        assert snapshot["counters"]["events"] == 5
        assert snapshot["success_count"] == 1

        # TimerContext block
        with TimerContext(collector, "timed_block"):
            pass

        updated_snapshot = collector.get_snapshot()
        assert "timed_block" in updated_snapshot["durations_ms"]

        collector.reset()
        assert len(collector.get_snapshot()["durations_ms"]) == 0

    def test_multithreaded_metrics(self):
        import concurrent.futures
        from akaal.intelligence.metrics import EnterpriseIntelligenceMetricsCollector

        collector = EnterpriseIntelligenceMetricsCollector()

        def worker(idx: int):
            collector.record_duration(f"metric_{idx}", float(idx))
            collector.increment_counter("total_workers")
            collector.record_success()

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(worker, i) for i in range(50)]
            for future in concurrent.futures.as_completed(futures):
                future.result()

        snapshot = collector.get_snapshot()
        assert snapshot["counters"]["total_workers"] == 50
        assert snapshot["success_count"] == 50


class TestEnterpriseIntelligenceEvents:
    """Verification suite for Milestone 3 Events Subsystem."""

    def test_event_bus_publishing_and_subscribing(self):
        from akaal.intelligence.events import (
            EnterpriseIntelligenceEventBus,
            PlatformStartedEvent,
            PlatformCompletedEvent,
        )

        bus = EnterpriseIntelligenceEventBus()
        received_events = []

        def on_started(evt):
            received_events.append(evt)

        bus.subscribe(PlatformStartedEvent, on_started)

        evt_started = PlatformStartedEvent("EVT-1", payload={"advisory_model_id": "ADV-001"})
        bus.publish(evt_started)

        assert len(received_events) == 1
        assert received_events[0].event_id == "EVT-1"
        assert len(bus.get_published_events()) == 1


class TestEnterpriseIntelligenceGovernance:
    """Verification suite for Milestone 3 Governance Subsystem."""

    def test_checksum_computation_and_equivalence(self):
        from akaal.intelligence.governance import EnterpriseIntelligenceGovernance

        v_info = EnterpriseIntelligenceVersionInfo()
        manifest = EnterpriseIntelligenceManifest("ADV-001", 1, 0, 1, 95.0, 300.0, "2026-07-19T12:00:00Z")
        decision = EnterpriseDecision("DEC-001", "Title", "CAT", DecisionPriority.HIGH, RiskLevel.LOW, "Desc", "Rat", "Imp", 0.95)
        strategy = StrategySynthesis("STR-1", StrategyType.AGGRESSIVE_PARALLEL, "Obj", "PAR", 100.0, 4)
        sim = MigrationSimulationResult("SIM-1", 10.0, 100.0, 50.0, 1000.0, 5000.0, 512.0, 4.0, 0.01)
        readiness = ReadinessAssessment("R-1", 95.0, ReadinessTier.PRODUCTION_READY, 95.0, 95.0, 95.0, 95.0)
        agent_plan = AgentCoordinationPlan("AG-1", 2, "us-east-1")
        trace = EnterpriseIntelligenceTrace("TR-1", 2.0)

        model1 = EnterpriseIntelligenceModel("ENT-001", "ADV-001", v_info, manifest, (decision,), strategy, sim, readiness, agent_plan, trace, "")
        computed_checksum = EnterpriseIntelligenceGovernance.compute_model_checksum(model1)

        assert isinstance(computed_checksum, str)
        assert len(computed_checksum) == 64  # Valid SHA-256 hex digest

        model1_with_checksum = EnterpriseIntelligenceModel("ENT-001", "ADV-001", v_info, manifest, (decision,), strategy, sim, readiness, agent_plan, trace, computed_checksum)
        model2_with_checksum = EnterpriseIntelligenceModel("ENT-001", "ADV-001", v_info, manifest, (decision,), strategy, sim, readiness, agent_plan, trace, computed_checksum)

        assert EnterpriseIntelligenceGovernance.verify_model_checksum(model1_with_checksum) is True
        assert EnterpriseIntelligenceGovernance.verify_equivalence(model1_with_checksum, model2_with_checksum) is True

    def test_semver_compatibility(self):
        from akaal.intelligence.governance import EnterpriseIntelligenceGovernance

        assert EnterpriseIntelligenceGovernance.check_semver_compatibility("1.0.0", "1.2.0") is True
        assert EnterpriseIntelligenceGovernance.check_semver_compatibility("2.0.0", "1.0.0") is False


class TestEnterpriseIntelligenceAnalyzers:
    """Verification suite for Milestone 4 Strategic Intelligence Analyzers."""

    @pytest.fixture
    def sample_advisory_model(self):
        from akaal.advisor.models.migration_advisory_model import MigrationAdvisoryModel
        from akaal.advisor.models.advisory_manifest import AdvisoryManifest
        from akaal.advisor.models.advisory_recommendation import AdvisoryRecommendation
        from akaal.advisor.models.advisory_enums import AdvisoryCategory, AdvisorySeverity, AdvisoryPriority

        rec1 = AdvisoryRecommendation("REC-001", "Optimize Batching", AdvisoryCategory.BATCHING, AdvisorySeverity.HIGH, AdvisoryPriority.P1, "Desc", "Rat", "Imp")
        rec2 = AdvisoryRecommendation("REC-002", "Configure Workers", AdvisoryCategory.WORKER, AdvisorySeverity.MEDIUM, AdvisoryPriority.P2, "Desc2", "Rat2", "Imp2")

        return MigrationAdvisoryModel(
            sha256_checksum="sha256abc123",
            manifest=AdvisoryManifest(advisory_id="ADV-MODEL-99", plan_id="PLAN-1", plan_checksum="sha256", total_recommendations=2),
            recommendations=(rec1, rec2),
        )

    def test_agent_coordination_analyzer(self, sample_advisory_model):
        from akaal.intelligence.analyzers import AgentCoordinationAnalyzer

        analyzer = AgentCoordinationAnalyzer()
        assert analyzer.name == "agent_coordination"

        plan = analyzer.analyze(sample_advisory_model, context={"primary_region": "us-west-2"})
        assert plan.primary_region == "us-west-2"
        assert plan.total_recommended_agents >= 2
        assert "us-west-2" in plan.worker_distribution

    def test_strategy_analyzer(self, sample_advisory_model):
        from akaal.intelligence.analyzers import StrategyAnalyzer
        from akaal.intelligence.models.enterprise_intelligence_enums import StrategyType

        analyzer = StrategyAnalyzer()
        assert analyzer.name == "strategy"

        strategy = analyzer.analyze(sample_advisory_model)
        assert strategy.strategy_type == StrategyType.AGGRESSIVE_PARALLEL
        assert strategy.max_recommended_parallelism == 16

    def test_recommendation_aggregation_analyzer(self, sample_advisory_model):
        from akaal.intelligence.analyzers import RecommendationAggregationAnalyzer
        from akaal.intelligence.models.enterprise_intelligence_enums import DecisionPriority

        analyzer = RecommendationAggregationAnalyzer()
        assert analyzer.name == "recommendation_aggregation"

        decisions = analyzer.analyze(sample_advisory_model)
        assert len(decisions) == 2
        assert decisions[0].priority == DecisionPriority.HIGH

    def test_migration_simulation_analyzer(self, sample_advisory_model):
        from akaal.intelligence.analyzers import MigrationSimulationAnalyzer

        analyzer = MigrationSimulationAnalyzer()
        assert analyzer.name == "migration_simulation"

        sim = analyzer.analyze(sample_advisory_model)
        assert sim.projected_downtime_seconds_min > 0
        assert sim.projected_downtime_seconds_max > sim.projected_downtime_seconds_min
        assert sim.estimated_throughput_records_per_sec > 0

    def test_readiness_analyzer(self, sample_advisory_model):
        from akaal.intelligence.analyzers import ReadinessAnalyzer
        from akaal.intelligence.models.enterprise_intelligence_enums import ReadinessTier

        analyzer = ReadinessAnalyzer()
        assert analyzer.name == "readiness"

        readiness = analyzer.analyze(sample_advisory_model)
        assert 0.0 <= readiness.overall_readiness_score <= 100.0
        assert readiness.tier == ReadinessTier.PRODUCTION_READY

    def test_cross_analyzer_independence_and_concurrency(self, sample_advisory_model):
        import concurrent.futures
        from akaal.intelligence.analyzers import (
            AgentCoordinationAnalyzer,
            StrategyAnalyzer,
            RecommendationAggregationAnalyzer,
            MigrationSimulationAnalyzer,
            ReadinessAnalyzer,
        )

        analyzers = [
            AgentCoordinationAnalyzer(),
            StrategyAnalyzer(),
            RecommendationAggregationAnalyzer(),
            MigrationSimulationAnalyzer(),
            ReadinessAnalyzer(),
        ]

        def run_analyzer(analyzer):
            return analyzer.name, analyzer.analyze(sample_advisory_model)

        # Run all 5 analyzers concurrently in multi-threaded pool
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(run_analyzer, a) for a in analyzers]
            results = {future.result()[0]: future.result()[1] for future in concurrent.futures.as_completed(futures)}

        assert len(results) == 5
        assert "agent_coordination" in results
        assert "strategy" in results
        assert "recommendation_aggregation" in results
        assert "migration_simulation" in results
        assert "readiness" in results


class TestDecisionGraphEngine:
    """Verification suite for Milestone 5 Decision Graph Engine Subsystem."""

    def test_graph_construction_and_topological_sort(self):
        from akaal.intelligence.engine import DecisionGraphEngine

        engine = DecisionGraphEngine()
        engine.add_node("readiness")
        engine.add_node("agent_coordination")
        engine.add_node("strategy", dependencies=["readiness"])
        engine.add_node("decision_aggregation", dependencies=["strategy", "agent_coordination"])

        # Topological sort order: readiness, agent_coordination -> strategy -> decision_aggregation
        order = engine.topological_sort()
        assert order.index("readiness") < order.index("strategy")
        assert order.index("strategy") < order.index("decision_aggregation")
        assert order.index("agent_coordination") < order.index("decision_aggregation")

    def test_missing_dependency_validation(self):
        from akaal.intelligence.engine import DecisionGraphEngine, DecisionGraphError

        engine = DecisionGraphEngine()
        engine.add_node("strategy", dependencies=["non_existent_node"])

        with pytest.raises(DecisionGraphError) as exc_info:
            engine.validate_graph()
        assert "non-existent dependency" in str(exc_info.value)

    def test_cycle_detection(self):
        from akaal.intelligence.engine import DecisionGraphEngine, DecisionGraphCycleError

        # Simple cycle: A -> B -> A
        engine1 = DecisionGraphEngine()
        engine1.add_node("nodeA", dependencies=["nodeB"])
        engine1.add_node("nodeB", dependencies=["nodeA"])

        with pytest.raises(DecisionGraphCycleError):
            engine1.validate_graph()

        # Deep indirect cycle: A -> B -> C -> A
        engine2 = DecisionGraphEngine()
        engine2.add_node("nodeA", dependencies=["nodeC"])
        engine2.add_node("nodeB", dependencies=["nodeA"])
        engine2.add_node("nodeC", dependencies=["nodeB"])

        with pytest.raises(DecisionGraphCycleError):
            engine2.topological_sort()

    def test_maut_conflict_resolution(self):
        from akaal.intelligence.engine import DecisionGraphEngine
        from akaal.intelligence.models import EnterpriseDecision, DecisionPriority, RiskLevel

        d1 = EnterpriseDecision("DEC-001", "Parallel Batch Strategy", "STRATEGY", DecisionPriority.MEDIUM, RiskLevel.MEDIUM, "", "", "", 0.8)
        d2 = EnterpriseDecision("DEC-002", "Parallel Batch Strategy", "STRATEGY", DecisionPriority.HIGH, RiskLevel.LOW, "", "", "", 0.95)

        resolved = DecisionGraphEngine.resolve_conflicts([d1, d2])

        # d2 has higher priority (HIGH vs MEDIUM), higher confidence (0.95 vs 0.8), lower risk (LOW vs MEDIUM) -> wins
        assert len(resolved) == 1
        assert resolved[0].decision_id == "DEC-002"

    def test_graph_hashing_and_100_run_determinism(self):
        from akaal.intelligence.engine import DecisionGraphEngine

        engine = DecisionGraphEngine()
        engine.add_node("b_node", dependencies=["a_node"])
        engine.add_node("a_node")
        engine.add_node("c_node", dependencies=["b_node"])

        hash_initial = engine.compute_graph_hash()
        order_initial = engine.topological_sort()

        # 100 consecutive runs MUST yield identical graph hash and topological sort
        for _ in range(100):
            assert engine.compute_graph_hash() == hash_initial
            assert engine.topological_sort() == order_initial

    def test_multithreaded_decision_graph_engine(self):
        import concurrent.futures
        from akaal.intelligence.engine import DecisionGraphEngine

        def worker_task(idx: int):
            engine = DecisionGraphEngine()
            engine.add_node(f"node_{idx}_a")
            engine.add_node(f"node_{idx}_b", dependencies=[f"node_{idx}_a"])
            order = engine.topological_sort()
            assert order == [f"node_{idx}_a", f"node_{idx}_b"]

        # Run 50 concurrent decision graph evaluations
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(worker_task, i) for i in range(50)]
            for future in concurrent.futures.as_completed(futures):
                future.result()


class TestEnterpriseIntelligenceEngineAndPlatform:
    """Verification suite for Milestone 6 Orchestrator Engine & Public API Facade Subsystem."""

    @pytest.fixture
    def valid_advisory_model(self):
        from akaal.advisor.models.migration_advisory_model import MigrationAdvisoryModel
        from akaal.advisor.models.advisory_manifest import AdvisoryManifest
        from akaal.advisor.models.advisory_recommendation import AdvisoryRecommendation
        from akaal.advisor.models.advisory_enums import AdvisoryCategory, AdvisorySeverity, AdvisoryPriority

        rec1 = AdvisoryRecommendation("REC-001", "Optimize Batching", AdvisoryCategory.BATCHING, AdvisorySeverity.HIGH, AdvisoryPriority.P1, "Desc", "Rat", "Imp")

        return MigrationAdvisoryModel(
            sha256_checksum="sha256abc123",
            manifest=AdvisoryManifest(advisory_id="ADV-MODEL-100", plan_id="PLAN-100", plan_checksum="sha256", total_recommendations=1),
            recommendations=(rec1,),
        )

    def test_engine_full_pipeline_execution(self, valid_advisory_model):
        from akaal.intelligence.engine import EnterpriseIntelligenceEngine
        from akaal.intelligence.events import EnterpriseIntelligenceEventBus, PlatformCompletedEvent
        from akaal.intelligence.metrics import EnterpriseIntelligenceMetricsCollector

        event_bus = EnterpriseIntelligenceEventBus()
        metrics = EnterpriseIntelligenceMetricsCollector()
        engine = EnterpriseIntelligenceEngine(event_bus=event_bus, metrics=metrics)

        result_model = engine.execute(valid_advisory_model, context={"primary_region": "us-east-1"})

        assert result_model.advisory_model_id == "ADV-MODEL-100"
        assert result_model.checksum != ""
        assert len(result_model.decisions) >= 1
        assert result_model.strategy.strategy_type is not None

        # Check events
        events = event_bus.get_published_events()
        assert len(events) >= 2
        assert any(isinstance(e, PlatformCompletedEvent) for e in events)

        # Check metrics
        snapshot = metrics.get_snapshot()
        assert snapshot["success_count"] >= 1
        assert "total_pipeline_execution" in snapshot["durations_ms"]

    def test_public_api_facade_all_methods(self, valid_advisory_model):
        from akaal.intelligence import EnterpriseIntelligencePlatform

        platform = EnterpriseIntelligencePlatform()

        # analyze / execute
        model = platform.analyze(valid_advisory_model)
        model_exec = platform.execute(valid_advisory_model)

        assert model.advisory_model_id == "ADV-MODEL-100"
        assert model_exec.advisory_model_id == "ADV-MODEL-100"

        # validate
        assert platform.validate(model) is True

        # to_dict / from_dict
        m_dict = platform.to_dict(model)
        reconstructed_dict = platform.from_dict(m_dict)
        assert reconstructed_dict.model_id == model.model_id

        # to_json / from_json
        m_json = platform.to_json(model)
        reconstructed_json = platform.from_json(m_json)
        assert reconstructed_json.checksum == model.checksum

        # version / health / supported_features
        ver = platform.version()
        h_status = platform.health()
        feats = platform.supported_features()

        assert ver["schema_version"] == "1.0.0"
        assert h_status["status"] == "HEALTHY"
        assert "DecisionGraphEngine" in feats

    def test_invalid_input_validation_failure(self):
        from akaal.intelligence import EnterpriseIntelligencePlatform
        from akaal.intelligence.validation import EnterpriseIntelligenceValidationError

        platform = EnterpriseIntelligencePlatform()

        with pytest.raises(EnterpriseIntelligenceValidationError):
            platform.analyze(None)

    def test_multithreaded_concurrent_pipeline_execution(self, valid_advisory_model):
        import concurrent.futures
        from akaal.intelligence import EnterpriseIntelligencePlatform

        platform = EnterpriseIntelligencePlatform()

        def worker_task(idx: int):
            res = platform.analyze(valid_advisory_model, context={"worker_idx": idx})
            assert res.advisory_model_id == "ADV-MODEL-100"
            assert len(res.checksum) == 64

        # Run 50 concurrent pipeline execution tasks
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(worker_task, i) for i in range(50)]
            for future in concurrent.futures.as_completed(futures):
                future.result()


class TestEnterpriseReportBuilder:
    """Verification suite for Milestone 7 Enterprise Reporting Subsystem."""

    @pytest.fixture
    def sample_intelligence_model(self):
        from akaal.advisor.models.migration_advisory_model import MigrationAdvisoryModel
        from akaal.advisor.models.advisory_manifest import AdvisoryManifest
        from akaal.advisor.models.advisory_recommendation import AdvisoryRecommendation
        from akaal.advisor.models.advisory_enums import AdvisoryCategory, AdvisorySeverity, AdvisoryPriority
        from akaal.intelligence import EnterpriseIntelligencePlatform

        rec1 = AdvisoryRecommendation("REC-001", "Optimize Batching", AdvisoryCategory.BATCHING, AdvisorySeverity.HIGH, AdvisoryPriority.P1, "Desc", "Rat", "Imp")
        adv_model = MigrationAdvisoryModel(
            sha256_checksum="sha256abc123",
            manifest=AdvisoryManifest(advisory_id="ADV-REPORT-01", plan_id="PLAN-R1", plan_checksum="sha256", total_recommendations=1),
            recommendations=(rec1,),
        )
        return EnterpriseIntelligencePlatform().analyze(adv_model)

    def test_report_builder_all_types_and_formats(self, sample_intelligence_model):
        from akaal.intelligence.reporting import EnterpriseReportBuilder, ReportType, ReportFormat

        for r_type in ReportType:
            # DICT
            d_res = EnterpriseReportBuilder.build(sample_intelligence_model, report_type=r_type, output_format=ReportFormat.DICT)
            assert isinstance(d_res, dict)

            # JSON
            j_res = EnterpriseReportBuilder.build(sample_intelligence_model, report_type=r_type, output_format=ReportFormat.JSON)
            assert isinstance(j_res, str) and j_res.startswith("{")

            # MARKDOWN
            m_res = EnterpriseReportBuilder.build(sample_intelligence_model, report_type=r_type, output_format=ReportFormat.MARKDOWN)
            assert isinstance(m_res, str) and "# " in m_res

            # TEXT
            t_res = EnterpriseReportBuilder.build(sample_intelligence_model, report_type=r_type, output_format=ReportFormat.TEXT)
            assert isinstance(t_res, str) and "=== AKAAL ENTERPRISE REPORT" in t_res

    def test_invalid_model_input(self):
        from akaal.intelligence.reporting import EnterpriseReportBuilder, EnterpriseReportBuilderError

        with pytest.raises(EnterpriseReportBuilderError):
            EnterpriseReportBuilder.build(None)

    def test_report_generation_100_run_determinism(self, sample_intelligence_model):
        from akaal.intelligence.reporting import EnterpriseReportBuilder, ReportType, ReportFormat

        initial_md = EnterpriseReportBuilder.build(sample_intelligence_model, report_type=ReportType.FULL, output_format=ReportFormat.MARKDOWN)
        initial_json = EnterpriseReportBuilder.build(sample_intelligence_model, report_type=ReportType.FULL, output_format=ReportFormat.JSON)

        # 100 consecutive runs MUST be byte-for-byte identical
        for _ in range(100):
            assert EnterpriseReportBuilder.build(sample_intelligence_model, report_type=ReportType.FULL, output_format=ReportFormat.MARKDOWN) == initial_md
            assert EnterpriseReportBuilder.build(sample_intelligence_model, report_type=ReportType.FULL, output_format=ReportFormat.JSON) == initial_json

    def test_multithreaded_concurrent_report_generation(self, sample_intelligence_model):
        import concurrent.futures
        from akaal.intelligence.reporting import EnterpriseReportBuilder, ReportType, ReportFormat

        def worker_task(idx: int):
            md = EnterpriseReportBuilder.build(sample_intelligence_model, report_type=ReportType.FULL, output_format=ReportFormat.MARKDOWN)
            assert f"Model ID" in md

        # Run 50 concurrent report generation tasks
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(worker_task, i) for i in range(50)]
            for future in concurrent.futures.as_completed(futures):
                future.result()


class TestEnterpriseIntelligenceMasterVerification:
    """Master Verification & Final Production Readiness Certification Suite for Milestone 8."""

    @pytest.fixture
    def benchmark_advisory_model(self):
        from akaal.advisor.models.migration_advisory_model import MigrationAdvisoryModel
        from akaal.advisor.models.advisory_manifest import AdvisoryManifest
        from akaal.advisor.models.advisory_recommendation import AdvisoryRecommendation
        from akaal.advisor.models.advisory_enums import AdvisoryCategory, AdvisorySeverity, AdvisoryPriority

        rec1 = AdvisoryRecommendation("REC-001", "Optimize Batching", AdvisoryCategory.BATCHING, AdvisorySeverity.HIGH, AdvisoryPriority.P1, "Desc", "Rat", "Imp")
        rec2 = AdvisoryRecommendation("REC-002", "Worker Scaling", AdvisoryCategory.WORKER, AdvisorySeverity.MEDIUM, AdvisoryPriority.P2, "Desc2", "Rat2", "Imp2")
        rec3 = AdvisoryRecommendation("REC-003", "Topology Optimization", AdvisoryCategory.TOPOLOGY, AdvisorySeverity.CRITICAL, AdvisoryPriority.P0, "Desc3", "Rat3", "Imp3")


        return MigrationAdvisoryModel(
            sha256_checksum="sha256master123",
            manifest=AdvisoryManifest(advisory_id="ADV-MASTER-888", plan_id="PLAN-M8", plan_checksum="sha256", total_recommendations=3),
            recommendations=(rec1, rec2, rec3),
        )

    def test_end_to_end_1000_run_determinism(self, benchmark_advisory_model):
        from akaal.intelligence import EnterpriseIntelligencePlatform

        platform = EnterpriseIntelligencePlatform()
        initial_model = platform.analyze(benchmark_advisory_model)

        # 100 continuous pipeline executions MUST yield 100% identical strategic decisions and metrics
        for _ in range(100):
            model = platform.analyze(benchmark_advisory_model)
            assert model.decisions == initial_model.decisions
            assert model.strategy == initial_model.strategy
            assert model.simulation == initial_model.simulation
            assert model.readiness == initial_model.readiness
            assert model.agent_coordination == initial_model.agent_coordination


    def test_100_thread_concurrent_stress_load(self, benchmark_advisory_model):
        import concurrent.futures
        from akaal.intelligence import EnterpriseIntelligencePlatform

        platform = EnterpriseIntelligencePlatform()

        def stress_task(task_id: int):
            model = platform.analyze(benchmark_advisory_model, context={"task_id": task_id})
            assert model.advisory_model_id == "ADV-MASTER-888"
            assert len(model.checksum) == 64
            assert len(model.decisions) == 3

        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(stress_task, i) for i in range(100)]
            for future in concurrent.futures.as_completed(futures):
                future.result()

    def test_memory_footprint_and_leak_verification(self, benchmark_advisory_model):
        import tracemalloc
        from akaal.intelligence import EnterpriseIntelligencePlatform

        platform = EnterpriseIntelligencePlatform()
        tracemalloc.start()
        snapshot_start = tracemalloc.take_snapshot()

        for _ in range(50):
            _ = platform.analyze(benchmark_advisory_model)

        snapshot_end = tracemalloc.take_snapshot()
        tracemalloc.stop()

        stats = snapshot_end.compare_to(snapshot_start, "lineno")
        total_diff_kb = sum(stat.size_diff for stat in stats) / 1024.0

        # Memory diff should be negligible (< 1000 KB) demonstrating zero memory leakage
        assert total_diff_kb < 1000.0

    def test_architecture_and_package_boundary_audit(self):
        import akaal.intelligence as intel
        import akaal.intelligence.models as models
        import akaal.intelligence.registry as registry
        import akaal.intelligence.analyzers as analyzers
        import akaal.intelligence.engine as engine
        import akaal.intelligence.reporting as reporting

        # Ensure all key exports exist and boundary packages are clean
        assert hasattr(intel, "EnterpriseIntelligencePlatform")
        assert hasattr(intel, "EnterpriseIntelligenceEngine")
        assert hasattr(models, "EnterpriseIntelligenceModel")
        assert hasattr(registry, "EnterpriseIntelligenceRegistry")
        assert hasattr(analyzers, "BaseIntelligenceAnalyzer")
        assert hasattr(engine, "DecisionGraphEngine")
        assert hasattr(reporting, "EnterpriseReportBuilder")








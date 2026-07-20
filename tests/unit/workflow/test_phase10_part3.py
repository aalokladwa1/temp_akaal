"""Exhaustive behavioral unit test suite for Phase 10 Part 3 Enterprise Platform."""

import pytest
from akaal.workflow.engine.control_plane import ControlPlaneEngine
from akaal.workflow.engine.data_plane import DataPlaneWorker
from akaal.workflow.engine.execution_engine import WorkflowExecutionEngine
from akaal.workflow.events.cloudevents import CloudEventV1
from akaal.workflow.events.store import EventStore
from akaal.workflow.locks.leader_elector import RaftLeaderElector
from akaal.workflow.locks.providers import InMemoryLockProvider
from akaal.workflow.models.context import WorkflowContext
from akaal.workflow.models.metadata import StepDefinition, WorkflowManifest, WorkflowMetadata
from akaal.workflow.models.results import StepStatus
from akaal.workflow.models.sub_contexts import ExecutionContext
from akaal.workflow.planning.planner import ExecutionPlanner
from akaal.workflow.plugins.framework import IWorkflowPlugin, PluginFramework, PluginState
from akaal.workflow.plugins.sandbox import PluginSandbox
from akaal.workflow.queues.dead_letter import DeadLetterQueue
from akaal.workflow.queues.in_memory import InMemoryWorkflowQueue
from akaal.workflow.queues.interfaces import StepExecutionTask
from akaal.workflow.registry.registry import WorkflowStepRegistry
from akaal.workflow.resilience.admission import AdmissionController
from akaal.workflow.resilience.backpressure import BackpressureController
from akaal.workflow.resilience.chaos import ChaosEngine
from akaal.workflow.resilience.circuit_breaker import CircuitBreaker, CircuitState
from akaal.workflow.resilience.retry import RetryPolicyHierarchy
from akaal.workflow.saga.manager import SagaManager
from akaal.workflow.saga.stack import CompensationStack, CompensationStep
from akaal.workflow.scheduling.aging import PriorityAgingAlgorithm
from akaal.workflow.scheduling.scheduler import WorkflowScheduler
from akaal.workflow.security.policy_engine import SecurityPolicyEngine
from akaal.workflow.security.security_context import SecurityContext
from akaal.workflow.steps.reference_steps import ReferencePassStep
from akaal.workflow.utils.hlc import HybridLogicalClock
from akaal.workflow.versioning.manifest_version import ManifestVersionManager
from akaal.workflow.versioning.workflow_version import WorkflowVersionManager
from akaal.workflow.workers.allocator import WorkerAllocator
from akaal.workflow.workers.registry import WorkerCapabilities, WorkerNode, WorkerRegistry


def _make_context(workflow_id: str, run_id: str = "run_1") -> WorkflowContext:
    return WorkflowContext(execution_context=ExecutionContext(workflow_id=workflow_id, run_id=run_id))


def test_hybrid_logical_clock_causal_ordering() -> None:
    hlc1 = HybridLogicalClock()
    t1 = hlc1.now()
    t2 = hlc1.now()
    assert t1 < t2 or t1.logical_counter < t2.logical_counter


def test_cloudevents_v1_envelope() -> None:
    event = CloudEventV1(
        id="e_101",
        source="/akaal/workflow",
        type="com.akaal.workflow.started.v1",
        subject="w_test",
        data={"key": "val"},
    )
    assert event.specversion == "1.0"
    assert "checksum" in event.to_dict()
    assert '"type":"com.akaal.workflow.started.v1"' in event.render_json()


def test_event_store_snapshots_and_legal_hold() -> None:
    store = EventStore()
    event = CloudEventV1(id="e_1", source="src", type="type", subject="w_1")
    store.append(event)
    assert store.count() == 1

    idx = store.create_snapshot("w_1", {"state": "SNAPSHOT_1"})
    assert idx == 1
    snapshot = store.get_latest_snapshot("w_1")
    assert snapshot is not None
    assert snapshot[1]["state"] == "SNAPSHOT_1"

    store.set_legal_hold("w_1", True)
    assert store.is_legal_hold_active("w_1") is True


def test_execution_planner_stage_grouping() -> None:
    steps = (
        StepDefinition(step_id="step1", step_type="ReferencePassStep"),
        StepDefinition(step_id="step2", step_type="ReferencePassStep", dependencies=("step1",)),
    )
    metadata = WorkflowMetadata(workflow_id="w_plan", workflow_name="Plan Test")
    manifest = WorkflowManifest(metadata=metadata, step_definitions=steps)

    planner = ExecutionPlanner()
    plan = planner.create_plan(manifest)
    assert len(plan.stages) == 2
    assert plan.stages[0].step_ids == ("step1",)
    assert plan.stages[1].step_ids == ("step2",)


def test_priority_aging_algorithm() -> None:
    aging = PriorityAgingAlgorithm(alpha=1.0, beta=0.5)
    task = StepExecutionTask(
        task_id="t1", workflow_id="w1", run_id="r1", step_id="s1", step_type="ReferencePassStep", priority=40
    )
    effective = aging.calculate_effective_priority(task, wait_time_seconds=120.0, tenant_usage_ratio=0.2)
    assert effective > 40


def test_in_memory_queue_and_dead_letter() -> None:
    queue = InMemoryWorkflowQueue()
    task = StepExecutionTask(
        task_id="t_q1", workflow_id="w1", run_id="r1", step_id="s1", step_type="ReferencePassStep", priority=50
    )
    queue.enqueue(task)
    assert queue.size() == 1

    dequeued = queue.dequeue()
    assert dequeued is not None
    assert dequeued.task_id == "t_q1"

    dlq = DeadLetterQueue()
    dlq.add_poison_task(dequeued, "Poison payload")
    assert len(dlq.list_poison_tasks()) == 1


def test_distributed_lock_provider_and_leader_election() -> None:
    provider = InMemoryLockProvider()
    success, token = provider.acquire_lock("res_1", ttl_seconds=10.0)
    assert success is True
    assert token > 0

    renewed = provider.renew_lock("res_1", token, ttl_seconds=10.0)
    assert renewed is True

    released = provider.release_lock("res_1", token)
    assert released is True

    elector = RaftLeaderElector(node_id="node_1", lock_provider=provider)
    assert elector.campaign() is True
    assert elector.is_leader is True


def test_worker_registry_and_allocator() -> None:
    registry = WorkerRegistry()
    node = WorkerNode(
        worker_id="w_node_1",
        host="127.0.0.1",
        port=8080,
        capabilities=WorkerCapabilities(cpu_cores=8, ram_mb=16384.0),
    )
    registry.register_worker(node)
    assert len(registry.list_healthy_workers()) == 1

    allocator = WorkerAllocator(registry)
    task = StepExecutionTask(
        task_id="t_alloc", workflow_id="w1", run_id="r1", step_id="s1", step_type="ReferencePassStep"
    )
    selected = allocator.select_worker(task)
    assert selected is not None
    assert selected.worker_id == "w_node_1"


def test_saga_manager_and_compensation_stack() -> None:
    saga = SagaManager()
    saga.register_compensation(
        workflow_id="w_saga", step_id="s1", compensation_action="UNDO_STEP_1", parameters={"key": "val"}
    )
    saga.register_compensation(
        workflow_id="w_saga", step_id="s2", compensation_action="UNDO_STEP_2", parameters={"key": "val"}
    )

    executed = saga.execute_compensation("w_saga")
    assert len(executed) == 2
    assert executed[0].step_id == "s2"  # LIFO order
    assert executed[1].step_id == "s1"


class DummyPlugin(IWorkflowPlugin):
    @property
    def plugin_name(self) -> str:
        return "DummyPlugin"

    @property
    def plugin_version(self) -> str:
        return "1.0.0"

    def initialize(self) -> bool:
        return True

    def execute_hook(self, hook_name: str, payload: dict) -> dict:
        if hook_name == "crash":
            raise ValueError("Plugin crashed!")
        return {**payload, "plugin_processed": True}


def test_plugin_framework_and_sandbox() -> None:
    framework = PluginFramework()
    plugin = DummyPlugin()
    framework.register_plugin(plugin)
    framework.initialize_all()
    assert framework.get_plugin_state("DummyPlugin") == PluginState.ACTIVE

    res = framework.execute_plugin_hook("DummyPlugin", "run", {"data": 123})
    assert res.get("plugin_processed") is True

    sandbox = PluginSandbox()
    crashed_res = sandbox.safe_execute(plugin, "crash", {"data": 123})
    assert "_plugin_error" in crashed_res


def test_resilience_circuit_breaker_admission_backpressure_chaos() -> None:
    breaker = CircuitBreaker(failure_threshold=2)
    assert breaker.state == CircuitState.CLOSED

    def failing_func() -> None:
        raise ValueError("Service error")

    with pytest.raises(ValueError):
        breaker.call(failing_func)

    with pytest.raises(ValueError):
        breaker.call(failing_func)

    assert breaker.state == CircuitState.OPEN

    admission = AdmissionController(max_concurrent_requests=1)
    admitted, _ = admission.evaluate_request("t1")
    assert admitted is True

    backpressure = BackpressureController(high_watermark_queue_depth=10)
    assert backpressure.update_metrics(5) is False
    assert backpressure.update_metrics(15) is True

    chaos = ChaosEngine()
    chaos.inject_fault("worker_crash")
    assert chaos.is_fault_active("worker_crash") is True


def test_version_managers() -> None:
    w_ver = WorkflowVersionManager()
    manifest_v1 = WorkflowManifest(
        metadata=WorkflowMetadata(workflow_id="w_1", workflow_name="W1", version="1.0.0"),
        step_definitions=(StepDefinition(step_id="s1", step_type="ReferencePassStep"),),
    )
    manifest_v2 = WorkflowManifest(
        metadata=WorkflowMetadata(workflow_id="w_1", workflow_name="W1", version="2.0.0"),
        step_definitions=(
            StepDefinition(step_id="s1", step_type="ReferencePassStep"),
            StepDefinition(step_id="s2", step_type="ReferencePassStep"),
        ),
    )
    w_ver.register_version(manifest_v1)
    w_ver.register_version(manifest_v2)

    assert w_ver.get_manifest("W1", "1.0.0") is not None
    assert w_ver.get_manifest("W1", "2.0.0") is not None

    m_ver = ManifestVersionManager()
    assert m_ver.validate_compatibility(manifest_v1, manifest_v2) is True


def test_workflow_execution_engine_full_flow() -> None:
    registry = WorkflowStepRegistry()
    registry.register("ReferencePassStep", ReferencePassStep)

    engine = WorkflowExecutionEngine(registry=registry)
    context = _make_context("w_exec_full")
    manifest = WorkflowManifest(
        metadata=WorkflowMetadata(workflow_id="w_exec_full", workflow_name="Exec Full"),
        step_definitions=(StepDefinition(step_id="s1", step_type="ReferencePassStep"),),
    )

    results = engine.submit_and_run_workflow(manifest, context)
    assert "s1" in results
    assert results["s1"].success is True
    assert results["s1"].status == StepStatus.COMPLETED

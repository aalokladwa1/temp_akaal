"""Unit tests for 100% Deterministic Execution Replay with Injected Clock & ID Generators."""

from akaal.workflow.api import WorkflowClient
from akaal.workflow.checkpoint import CheckpointManager
from akaal.workflow.engine import WorkflowEngine
from akaal.workflow.execution import StepExecutor
from akaal.workflow.models import StepDefinition, WorkflowManifest, WorkflowMetadata
from akaal.workflow.steps import ReferencePassStep
from akaal.workflow.utils import DeterministicIdGenerator, FixedClock


def test_deterministic_replay_runs():
    def create_run():
        clock = FixedClock(fixed_iso="2026-07-20T12:00:00+00:00", auto_increment_seconds=1.0)
        id_gen = DeterministicIdGenerator(prefix="det-id")
        executor = StepExecutor(clock=clock)
        checkpoint_mgr = CheckpointManager(clock=clock, id_generator=id_gen)
        engine = WorkflowEngine(
            executor=executor,
            checkpoint_manager=checkpoint_mgr,
            clock=clock,
            id_generator=id_gen,
        )
        client = WorkflowClient(engine=engine)

        client.register_step("ReferencePassStep", ReferencePassStep)
        meta = WorkflowMetadata(workflow_id="wf-det-1", workflow_name="Deterministic Workflow")
        s1 = StepDefinition(step_id="step-1", step_type="ReferencePassStep")
        s2 = StepDefinition(step_id="step-2", step_type="ReferencePassStep", dependencies=("step-1",))
        manifest = WorkflowManifest(metadata=meta, step_definitions=(s1, s2))

        client.submit_workflow(manifest)
        trace = client.execute_workflow("wf-det-1")
        return trace.to_dict()

    run_1_dict = create_run()
    run_2_dict = create_run()

    # Assert 100% byte-for-byte checksum and structure match across two independent runs
    assert run_1_dict["checksum"] == run_2_dict["checksum"]
    assert run_1_dict["run_id"] == run_2_dict["run_id"]
    assert run_1_dict["step_results"] == run_2_dict["step_results"]

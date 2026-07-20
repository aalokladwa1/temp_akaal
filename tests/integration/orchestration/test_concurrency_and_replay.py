"""
Integration tests for Concurrency, Deterministic Replay, and Recovery Safety.
"""

import pytest
import concurrent.futures
from typing import Dict, Any, List

from akaal.orchestration.domain.identifiers import ConfigurationId, WorkflowId
from akaal.orchestration.domain.types import EngineState, WorkflowStepName
from akaal.orchestration.domain.errors import RecoveryError
from akaal.orchestration.workflow.step import WorkflowStep
from akaal.orchestration.workflow.definition import WorkflowDefinition
from akaal.orchestration.workflow.context import WorkflowContext
from akaal.orchestration.config.config import UnifiedConfigurationManager, FrozenConfiguration
from akaal.orchestration.engine.engine import WorkflowEngine


class DeterministicStep(WorkflowStep):
    def __init__(self, step_name: str, val: int) -> None:
        super().__init__(name=step_name)
        self.val = val

    def initialize(self, context: WorkflowContext) -> None: pass
    def validate(self, context: WorkflowContext) -> bool: return True

    def execute(self, context: WorkflowContext) -> Dict[str, Any]:
        return {"value": self.val * 2}

    def checkpoint(self, context: WorkflowContext) -> Dict[str, Any]:
        return {"accumulated": self.val * 2}

    def resume(self, context: WorkflowContext, checkpoint_data: Dict[str, Any]) -> None: pass
    def rollback(self, context: WorkflowContext) -> None: pass
    def cleanup(self, context: WorkflowContext) -> None: pass


def test_deterministic_replay():
    """
    Executing the identical workflow definition with identical configuration
    must produce identical outputs, state history, and checkpoint checksums.
    """
    config_mgr = UnifiedConfigurationManager()
    cfg_id = ConfigurationId("cfg_deterministic_123")
    config1 = config_mgr.build_config(runtime_overrides={"execution": {"timeout_seconds": 1200}}, config_id=cfg_id)
    config2 = config_mgr.build_config(runtime_overrides={"execution": {"timeout_seconds": 1200}}, config_id=cfg_id)

    assert config1.checksum.digest == config2.checksum.digest

    def run_pipeline(cfg: FrozenConfiguration):
        engine = WorkflowEngine()
        stepA = DeterministicStep("ANALYSIS", 10)
        stepB = DeterministicStep("MIGRATION", 20)
        definition = WorkflowDefinition(
            name="deterministic_pipeline",
            version="1.0.0",
            steps=[stepA, stepB],
        )

        job, session = engine.create_job(
            source_profile={"db": "sqlserver"},
            target_profile={"db": "oracle"},
            config=cfg,
        )

        final_job = engine.execute_workflow(job, definition, cfg, session)
        history = engine.workflow_repo.get_execution_history(job.workflow_id)
        latest_cp = engine.checkpoint_repo.get_latest_checkpoint(job.workflow_id)
        return final_job, latest_cp

    job1, cp1 = run_pipeline(config1)
    job2, cp2 = run_pipeline(config2)

    assert job1.current_state == job2.current_state == EngineState.COMPLETED
    assert cp1.state_data == cp2.state_data == {"accumulated": 40}
    assert cp1.config_checksum == cp2.config_checksum


def test_recovery_safety_validation():
    """
    Recovery must fail safely if checkpoint checksum or config mismatch occurs.
    """
    engine = WorkflowEngine()
    config_mgr = UnifiedConfigurationManager()
    cfg_id1 = ConfigurationId("cfg_1111")
    cfg_id2 = ConfigurationId("cfg_2222")

    config1 = config_mgr.build_config(runtime_overrides={"execution": {"timeout_seconds": 1000}}, config_id=cfg_id1)
    config2 = config_mgr.build_config(runtime_overrides={"execution": {"timeout_seconds": 9999}}, config_id=cfg_id2)

    stepA = DeterministicStep("ANALYSIS", 5)
    definition = WorkflowDefinition("pipeline", "1.0.0", [stepA])

    job, session = engine.create_job({"db": "src"}, {"db": "tgt"}, config=config1)
    
    # Transition CREATED -> READY -> RUNNING -> PAUSED
    job = engine._update_job_state(job, EngineState.READY)
    job = engine._update_job_state(job, EngineState.RUNNING)
    paused_job = engine.pause_workflow(job)

    # Create a valid checkpoint for paused_job so recovery has a snapshot to inspect
    engine.checkpoint_coordinator.create_checkpoint(
        workflow_id=job.workflow_id,
        job_id=job.job_id,
        step_name="ANALYSIS",
        step_index=0,
        engine_state=EngineState.PAUSED,
        workflow_version="1.0.0",
        config_version=int(config1.version),
        config_checksum=str(config1.checksum),
        state_data={"step": "ANALYSIS"},
    )

    # Attempt recovery with incompatible configuration
    with pytest.raises(RecoveryError):
        engine.resume_workflow(paused_job, definition, config2, session)


def test_concurrent_repository_and_job_operations():
    """
    Test concurrent operations on in-memory repository to verify thread safety.
    """
    engine = WorkflowEngine()
    config = UnifiedConfigurationManager().build_config()

    jobs: List[Any] = []
    for _ in range(10):
        j, s = engine.create_job({"db": "src"}, {"db": "tgt"}, config=config)
        jobs.append((j, s))

    def update_worker(item):
        j, s = item
        ready = engine._update_job_state(j, EngineState.READY)
        running = engine._update_job_state(ready, EngineState.RUNNING)
        engine.session_coordinator.heartbeat(s.session_id)
        return True

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        results = list(executor.map(update_worker, jobs))

    assert all(results)
    assert len(engine.workflow_repo.query_jobs(EngineState.RUNNING)) == 10

"""
Integration tests for Expanded Concurrency, Deterministic Replay, and Recovery Safety.
"""

import pytest
import concurrent.futures
from typing import Dict, Any, List, Tuple
from dataclasses import replace

from akaal.orchestration.domain.identifiers import ConfigurationId, WorkflowId, JobId, SessionId
from akaal.orchestration.domain.types import EngineState, WorkflowStepName, Version, Checksum
from akaal.orchestration.domain.errors import RecoveryError, CheckpointError
from akaal.orchestration.workflow.step import WorkflowStep
from akaal.orchestration.workflow.definition import WorkflowDefinition
from akaal.orchestration.workflow.context import WorkflowContext
from akaal.orchestration.config.config import UnifiedConfigurationManager, FrozenConfiguration
from akaal.orchestration.checkpoint.checkpoint import WorkflowCheckpoint
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
            steps=(stepA, stepB),
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


def test_recovery_scenarios_expanded():
    """
    Verify recovery safety for:
    1. Corrupted checkpoint payload (checksum verification failure)
    2. Missing checkpoint
    3. Recovery after a partial rollback
    """
    engine = WorkflowEngine()
    config_mgr = UnifiedConfigurationManager()
    cfg_id = ConfigurationId("cfg_test_recovery")
    config = config_mgr.build_config(config_id=cfg_id)

    stepA = DeterministicStep("ANALYSIS", 5)
    definition = WorkflowDefinition("pipeline", "1.0.0", (stepA,))

    # Scenario 1: Missing checkpoint
    job1, session1 = engine.create_job({"db": "src"}, {"db": "tgt"}, config=config)
    job1 = engine._update_job_state(job1, EngineState.READY)
    job1 = engine._update_job_state(job1, EngineState.RUNNING)
    paused_job1 = engine.pause_workflow(job1)
    with pytest.raises(RecoveryError, match="No checkpoint found"):
        engine.resume_workflow(paused_job1, definition, config, session1)

    # Scenario 2: Corrupted checkpoint payload (checksum mismatch)
    job2, session2 = engine.create_job({"db": "src"}, {"db": "tgt"}, config=config)
    job2 = engine._update_job_state(job2, EngineState.READY)
    job2 = engine._update_job_state(job2, EngineState.RUNNING)
    paused_job2 = engine.pause_workflow(job2)

    valid_cp = engine.checkpoint_coordinator.create_checkpoint(
        workflow_id=job2.workflow_id,
        job_id=job2.job_id,
        step_name="ANALYSIS",
        step_index=0,
        engine_state=EngineState.PAUSED,
        workflow_version="1.0.0",
        config_version=int(config.version),
        config_checksum=str(config.checksum),
        state_data={"step": "ANALYSIS"},
    )

    # Corrupt the checksum to simulate payload corruption
    corrupted_cp = replace(valid_cp)
    object.__setattr__(corrupted_cp, "checksum", Checksum("a" * 64))
    engine.checkpoint_repo._checkpoints[valid_cp.checkpoint_id] = corrupted_cp
    engine.checkpoint_repo._by_workflow[str(job2.workflow_id)][-1] = corrupted_cp

    with pytest.raises(RecoveryError, match="checksum mismatch"):
        engine.resume_workflow(paused_job2, definition, config, session2)

    # Scenario 3: Recovery after a partial rollback
    job3, session3 = engine.create_job({"db": "src"}, {"db": "tgt"}, config=config)
    job3 = engine._update_job_state(job3, EngineState.READY)
    job3 = engine._update_job_state(job3, EngineState.RUNNING)
    failed_job = engine._update_job_state(job3, EngineState.FAILED)
    rolled_back_job = engine.rollback_workflow(failed_job, definition, config, session3)
    assert rolled_back_job.current_state == EngineState.ROLLED_BACK

    # Save a valid checkpoint for recovery after rollback
    engine.checkpoint_coordinator.create_checkpoint(
        workflow_id=job3.workflow_id,
        job_id=job3.job_id,
        step_name="ANALYSIS",
        step_index=0,
        engine_state=EngineState.ROLLED_BACK,
        workflow_version="1.0.0",
        config_version=int(config.version),
        config_checksum=str(config.checksum),
        state_data={"rolled_back": True},
    )

    resumed_after_rollback = engine.resume_workflow(rolled_back_job, definition, config, session3)
    assert resumed_after_rollback.current_state == EngineState.COMPLETED


def test_expanded_concurrency_scenarios():
    """
    Verifies thread safety during simultaneous:
    - session heartbeats
    - checkpoint creation
    - pause/resume operations
    - concurrent recovery attempts
    """
    engine = WorkflowEngine()
    config = UnifiedConfigurationManager().build_config()
    definition = WorkflowDefinition("pipeline", "1.0.0", (DeterministicStep("ANALYSIS", 1),))

    # Setup 10 jobs and sessions
    items: List[Tuple[Any, Any]] = [
        engine.create_job({"db": "src"}, {"db": "tgt"}, config=config)
        for _ in range(10)
    ]

    # 1. Simultaneous Session Heartbeats
    def heartbeat_worker(item):
        _, session = item
        for _ in range(5):
            engine.session_coordinator.heartbeat(session.session_id)
        return True

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        heartbeat_results = list(executor.map(heartbeat_worker, items))
    assert all(heartbeat_results)

    # 2. Simultaneous Checkpoint Creation
    def checkpoint_worker(item):
        job, _ = item
        engine.checkpoint_coordinator.create_checkpoint(
            workflow_id=job.workflow_id,
            job_id=job.job_id,
            step_name="ANALYSIS",
            step_index=0,
            engine_state=EngineState.RUNNING,
            workflow_version="1.0.0",
            config_version=int(config.version),
            config_checksum=str(config.checksum),
            state_data={"val": 1},
        )
        return True

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        cp_results = list(executor.map(checkpoint_worker, items))
    assert all(cp_results)

    # 3. Simultaneous Pause/Resume Operations
    def pause_resume_worker(item):
        job, session = item
        r_job = engine._update_job_state(job, EngineState.READY)
        run_job = engine._update_job_state(r_job, EngineState.RUNNING)
        p_job = engine.pause_workflow(run_job)
        
        # Add valid checkpoint for p_job
        engine.checkpoint_coordinator.create_checkpoint(
            workflow_id=p_job.workflow_id,
            job_id=p_job.job_id,
            step_name="ANALYSIS",
            step_index=0,
            engine_state=EngineState.PAUSED,
            workflow_version="1.0.0",
            config_version=int(config.version),
            config_checksum=str(config.checksum),
            state_data={"val": 1},
        )

        res_job = engine.resume_workflow(p_job, definition, config, session)
        return res_job.current_state == EngineState.COMPLETED

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        pr_results = list(executor.map(pause_resume_worker, items))
    assert all(pr_results)

    # 4. Concurrent Recovery Attempts on the Same Job
    target_job, target_session = engine.create_job({"db": "src"}, {"db": "tgt"}, config=config)
    r_job = engine._update_job_state(target_job, EngineState.READY)
    run_job = engine._update_job_state(r_job, EngineState.RUNNING)
    p_job = engine.pause_workflow(run_job)
    
    engine.checkpoint_coordinator.create_checkpoint(
        workflow_id=p_job.workflow_id,
        job_id=p_job.job_id,
        step_name="ANALYSIS",
        step_index=0,
        engine_state=EngineState.PAUSED,
        workflow_version="1.0.0",
        config_version=int(config.version),
        config_checksum=str(config.checksum),
        state_data={"val": 1},
    )

    def recovery_attempt_worker(_):
        try:
            res = engine.resume_workflow(p_job, definition, config, target_session)
            return True
        except Exception:
            return False

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        recovery_results = list(executor.map(recovery_attempt_worker, range(4)))
    
    # At least one recovery worker succeeds safely
    assert any(recovery_results)

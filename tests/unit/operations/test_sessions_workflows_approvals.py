"""
Unit Tests for Operations Sessions, Workflows, Approvals, and Versioning.
"""

import pytest
from akaal.operations.session.manager import OperationsSessionManager, SessionState
from akaal.operations.workflow.engine import OperationalWorkflowEngine, OperationalWorkflow, OperationalStep
from akaal.operations.approvals.manager import ApprovalManager
from akaal.operations.versioning.manager import ConfigurationVersionManager


def test_session_manager_immutability():
    mgr = OperationsSessionManager()
    session = mgr.start_session("admin_user", "Maintenance")
    
    session.record_action("drain_worker", "Platform2", "SUCCESS")
    assert len(session.executed_actions) == 1

    mgr.close_session(session.session_id)
    assert session.state == SessionState.CLOSED

    # Immutability check
    with pytest.raises(RuntimeError):
        session.record_action("pause_job", "Platform1", "SUCCESS")


def test_workflow_engine_step_rollback():
    engine = OperationalWorkflowEngine()
    rolled_back = []

    def step1(): return True
    def step2(): return False  # Fails
    def rb1(): rolled_back.append("step1")

    steps = [
        OperationalStep("step1", step1, rb1),
        OperationalStep("step2", step2, None)
    ]
    wf = OperationalWorkflow("TestWF", steps)
    res = engine.execute_workflow(wf)

    assert res["status"] == "FAILED"
    assert "step1" in rolled_back


def test_approval_manager():
    mgr = ApprovalManager()
    req = mgr.create_request("emergency_stop", "operator1", required_approvers=2)

    assert mgr.is_approved(req.request_id) is False
    mgr.approve(req.request_id, "admin1")
    assert mgr.is_approved(req.request_id) is False
    mgr.approve(req.request_id, "admin2")
    assert mgr.is_approved(req.request_id) is True

    # Emergency override
    req2 = mgr.create_request("shutdown", "operator1", required_approvers=5)
    mgr.emergency_override(req2.request_id, "superadmin", "Critical outage override")
    assert mgr.is_approved(req2.request_id) is True


def test_configuration_versioning():
    vm = ConfigurationVersionManager({"key": "val1"})
    cfg = vm.get_active_config()
    assert cfg["key"] == "val1"

    v2 = vm.commit_version("v2.0.0", {"key": "val2"}, "admin")
    assert vm.get_active_config()["key"] == "val2"

    # Rollback to initial
    history = vm.get_history()
    v1_id = history[0]["version_id"]
    vm.rollback_to_version(v1_id)
    assert vm.get_active_config()["key"] == "val1"

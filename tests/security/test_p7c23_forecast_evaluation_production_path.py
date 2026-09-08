"""tests/security/test_p7c23_forecast_evaluation_production_path.py
==========================================================================
P7C.23 production-path proof: real PipelineUnifiedCaller -> intelligence.
submit (task=COMPARE, capability=forecast_evaluation), reachable through the
real seam; combined with the ALREADY-EXISTING Group-1 outcome-tracking IPC
(intelligence.outcome.record/list) to close the prediction->actual->outcome
loop end-to-end.
"""

from __future__ import annotations

import os
import tempfile

import pytest

from akaalIPC.security.context import ActorContext, ActorReference, CorrelationContext
from akaalIPC.transport.ports import CallerResultStatus
from tests.pipeline.conftest import authorized_caller, make_command


@pytest.fixture
def temp_db_path():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    try:
        os.remove(path)
    except OSError:
        pass


@pytest.fixture
def caller(temp_db_path):
    uc = authorized_caller(db_path=temp_db_path)
    yield uc
    uc.close()


def _actor(org_id: str) -> ActorContext:
    return ActorContext(
        actor=ActorReference(actor_id=f"actor-{org_id}", actor_type="human", display_name="Test User"),
        organization_id=org_id, workspace_id="ws-main", project_id="proj-1",
    )


class TestFullPredictionToOutcomeLoop:
    def test_evaluate_then_record_outcome_via_real_seams(self, caller):
        actor = _actor("tenant-alpha")

        eval_payload = {
            "task": "COMPARE", "subject_type": "migration", "subject_id": "mig-1", "subject_version": "v1",
            "capability": "forecast_evaluation",
            "parameters": {"metric_name": "migration_eta_seconds", "predicted_value": 3600, "predicted_low": 2880, "predicted_high": 4320, "actual_value": 3500},
        }
        eval_result = caller.handle_command(make_command("intelligence.submit", eval_payload, actor, CorrelationContext.new()))
        assert eval_result.status == CallerResultStatus.OK
        artifact_id = eval_result.result["artifact_id"]
        assert eval_result.result["result"]["data"]["interval_hit"] is True

        outcome_payload = {"artifact_id": artifact_id, "outcome_status": "SUCCEEDED", "detail": "forecast within interval"}
        outcome_result = caller.handle_command(make_command("intelligence.outcome.record", outcome_payload, actor, CorrelationContext.new()))
        assert outcome_result.status == CallerResultStatus.OK

"""
Unit tests for Phase 12 Stage 3: Agent Network Integration.
"""

import pytest
import asyncio
from akaal.core.pipeline import AkaalPipeline, MigrationConfig, MigrationRuntimeState
from akaal.core.models.project import ConnectionConfig
from akaal.core.models.enums import SystemType, MigrationStrategy, AgentType, AgentStatus
from akaal.agents.manager.manager_agent import SystemAgent
from akaal.core.state.global_state import GlobalState
from akaal.core.message_bus.bus import MessageBus


def test_stage3_system_agent_registration_and_health():
    global_state = GlobalState()
    message_bus = MessageBus()

    primary = SystemAgent(global_state, message_bus, agent_id="SYSTEM-PRIMARY", is_backup=False)
    backup = SystemAgent(global_state, message_bus, agent_id="SYSTEM-BACKUP", is_backup=True)

    assert primary.agent_type == AgentType.SYSTEM
    assert primary.status == AgentStatus.HEALTHY
    assert backup.status == AgentStatus.STANDBY

    health_p = primary.get_health_status()
    assert health_p["agent_id"] == "SYSTEM-PRIMARY"
    assert health_p["status"] == "HEALTHY"
    assert health_p["diagnostics"]["system_health"] == "HEALTHY"


from tests.conftest import require_postgres


@pytest.mark.asyncio
async def test_stage3_agent_network_fleet_execution(tmp_path):
    require_postgres("source-db.example.com", 5432)
    workspace = str(tmp_path / "akaal_stage3_ws")


    source_cfg = ConnectionConfig(
        system_type=SystemType.POSTGRESQL,
        host="source-db.example.com",
        port=5432,
        database_name="source_db",
        credentials_ref="vault://src",
        read_only=True,
    )
    target_cfg = ConnectionConfig(
        system_type=SystemType.POSTGRESQL,
        host="target-db.example.com",
        port=5432,
        database_name="target_db",
        credentials_ref="vault://tgt",
        read_only=False,
    )

    config = MigrationConfig(
        source_config=source_cfg,
        target_config=target_cfg,
        strategy=MigrationStrategy.BIG_BANG,
        workspace_dir=workspace,
        project_name="Stage3 Agent Network Test Migration",
        auto_approve=True,
    )

    pipeline = AkaalPipeline()
    result = await pipeline.run(config)

    assert result["status"] == "completed"
    assert result["runtime_state"] == MigrationRuntimeState.COMPLETED.value
    assert len(pipeline._agents) == 18
    assert result["validation"] is not None
    assert result["certification"] is not None
    assert result["certification"]["trust_score"] == 100.0


@pytest.mark.asyncio
async def test_stage3_agent_lifecycle_states():
    pipeline = AkaalPipeline()
    assert pipeline.runtime_state == MigrationRuntimeState.CREATED
    pipeline._transition_runtime_state(MigrationRuntimeState.DISCOVERING)
    assert pipeline.runtime_state == MigrationRuntimeState.DISCOVERING
    pipeline._transition_runtime_state(MigrationRuntimeState.APPROVAL_PENDING)
    assert pipeline.runtime_state == MigrationRuntimeState.APPROVAL_PENDING
    pipeline._transition_runtime_state(MigrationRuntimeState.REPORTING)
    assert pipeline.runtime_state == MigrationRuntimeState.REPORTING
    pipeline._transition_runtime_state(MigrationRuntimeState.COMPLETED)
    assert pipeline.runtime_state == MigrationRuntimeState.COMPLETED

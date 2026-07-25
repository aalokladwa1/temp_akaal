"""
Unit tests for Phase 12 Stage 2: Unified Migration Runtime.
"""

import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from akaal.core.pipeline import AkaalPipeline, MigrationConfig, MigrationRuntimeState
from akaal.core.models.project import ConnectionConfig
from akaal.core.models.enums import SystemType, MigrationStrategy


def test_stage2_pipeline_initialization():
    pipeline = AkaalPipeline()
    assert pipeline.runtime_state == MigrationRuntimeState.CREATED
    assert pipeline.lifecycle_manager is not None


@pytest.mark.asyncio
async def test_stage2_unified_migration_runtime_execution(tmp_path):
    workspace = str(tmp_path / "akaal_stage2_ws")

    source_cfg = ConnectionConfig(
        system_type=SystemType.POSTGRESQL,
        host="localhost",
        port=5432,
        database_name="source_db",
        credentials_ref="vault://src",
        read_only=True,
    )
    target_cfg = ConnectionConfig(
        system_type=SystemType.POSTGRESQL,
        host="localhost",
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
        project_name="Stage2 Test Migration",
        auto_approve=True,
    )

    mock_adapter = MagicMock()
    mock_adapter.connect = AsyncMock(return_value=True)
    mock_adapter.close = AsyncMock(return_value=True)
    mock_adapter.is_connected = True
    mock_adapter.discover_tables = AsyncMock(return_value=["orders", "users"])
    mock_adapter.discover_columns = AsyncMock(return_value=[{"name": "id", "type": "INTEGER"}])
    mock_adapter.discover_indexes = AsyncMock(return_value=[])
    mock_adapter.discover_foreign_keys = AsyncMock(return_value=[])
    mock_adapter.discover_triggers = AsyncMock(return_value=[])
    mock_adapter.execute_query = AsyncMock(return_value=[(1,)])
    mock_adapter.read_table = AsyncMock(return_value=[{"id": 1}])
    mock_adapter.write_table = AsyncMock(return_value=1)

    with patch("akaal.core.pipeline.create_adapter", return_value=mock_adapter), \
         patch("akaal.agents.scout.scout_agent.create_adapter", return_value=mock_adapter), \
         patch("akaal.agents.validator.validator_agent.create_adapter", return_value=mock_adapter), \
         patch("akaal.agents.gb.gb_agent.create_adapter", return_value=mock_adapter):

        pipeline = AkaalPipeline()
        result = await pipeline.run(config)

        assert result["status"] == "completed"
        assert result["runtime_state"] == MigrationRuntimeState.COMPLETED.value
        assert result["validation"] is not None
        assert result["validation"]["status"] == "SUCCESS"
        assert result["certification"] is not None
        assert result["certification"]["trust_score"] == 100.0
        assert result["duration_seconds"] >= 0.0


@pytest.mark.asyncio
async def test_stage2_runtime_state_transitions():
    pipeline = AkaalPipeline()
    assert pipeline.runtime_state == MigrationRuntimeState.CREATED

    pipeline._transition_runtime_state(MigrationRuntimeState.DISCOVERING)
    assert pipeline.runtime_state == MigrationRuntimeState.DISCOVERING

    pipeline._transition_runtime_state(MigrationRuntimeState.EXECUTING_DATA)
    assert pipeline.runtime_state == MigrationRuntimeState.EXECUTING_DATA

    pipeline._transition_runtime_state(MigrationRuntimeState.COMPLETED)
    assert pipeline.runtime_state == MigrationRuntimeState.COMPLETED

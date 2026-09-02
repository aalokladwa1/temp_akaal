"""
Unit tests for Phase 12 Stage 2: Unified Migration Runtime.
"""

import pytest
import asyncio
from akaal.core.pipeline import AkaalPipeline, MigrationConfig, MigrationRuntimeState
from akaal.core.models.project import ConnectionConfig
from akaal.core.models.enums import SystemType, MigrationStrategy


from tests.conftest import require_postgres


def test_stage2_pipeline_initialization():
    pipeline = AkaalPipeline()
    assert pipeline.runtime_state == MigrationRuntimeState.CREATED
    assert pipeline.lifecycle_manager is not None


@pytest.mark.asyncio
async def test_stage2_unified_migration_runtime_execution(tmp_path):
    require_postgres("source-db.example.com", 5432)
    workspace = str(tmp_path / "akaal_stage2_ws")


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
        project_name="Stage2 Test Migration",
        auto_approve=True,
    )

    pipeline = AkaalPipeline()
    result = await pipeline.run(config)
    print("STAGE 2 RESULT:", result)

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

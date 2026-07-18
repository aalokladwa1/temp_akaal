"""
Akaal — Pipeline Executor
=========================
Executes discovery stages according to StageDependencyGraph with diagnostics & partial failure recovery.
"""

import time
import asyncio
from datetime import datetime, timezone
from typing import List, Optional
from akaal.scout.models.discovery_context import DiscoveryContext
from akaal.scout.models.discovery_report import StageDiagnostics
from akaal.scout.pipeline.base_stage import BaseDiscoveryStage
from akaal.scout.pipeline.dependency_graph import StageDependencyGraph
from akaal.scout.events.discovery_events import StageStarted, StageCompleted, StageFailed


class PipelineExecutor:
    """Pipeline Executor for executing discovery stages in dependency order."""

    def __init__(self, stages: List[BaseDiscoveryStage], timeout_seconds: float = 60.0) -> None:
        self.stages = StageDependencyGraph.resolve_execution_order(stages)
        self.timeout_seconds = timeout_seconds

    async def execute_all(self, ctx: DiscoveryContext) -> List[StageDiagnostics]:
        for stage in self.stages:
            start_str = datetime.now(timezone.utc).isoformat()
            t0 = time.time()
            if ctx.event_bus:
                ctx.event_bus.publish(StageStarted(stage.stage_name))

            try:
                diag = await asyncio.wait_for(stage.execute(ctx), timeout=self.timeout_seconds)
                t1 = time.time()
                dur_ms = (t1 - t0) * 1000.0
                if diag is None:
                    diag = StageDiagnostics(
                        stage_name=stage.stage_name,
                        status="SUCCESS",
                        start_time=start_str,
                        end_time=datetime.now(timezone.utc).isoformat(),
                        duration_ms=dur_ms,
                    )
                ctx.stage_diagnostics.append(diag)

                if ctx.metrics:
                    ctx.metrics.record_stage_duration(stage.stage_name, dur_ms)

                if ctx.event_bus:
                    ctx.event_bus.publish(StageCompleted(stage.stage_name, dur_ms))

            except Exception as exc:
                t1 = time.time()
                dur_ms = (t1 - t0) * 1000.0
                err_msg = f"Stage {stage.stage_name} failed: {str(exc)}"
                ctx.add_error(err_msg)

                diag = StageDiagnostics(
                    stage_name=stage.stage_name,
                    status="FAILED",
                    start_time=start_str,
                    end_time=datetime.now(timezone.utc).isoformat(),
                    duration_ms=dur_ms,
                    error_details=str(exc),
                )
                ctx.stage_diagnostics.append(diag)

                if ctx.metrics:
                    ctx.metrics.record_stage_duration(stage.stage_name, dur_ms)
                    ctx.metrics.record_failure()

                if ctx.event_bus:
                    ctx.event_bus.publish(StageFailed(stage.stage_name, str(exc)))

        return ctx.stage_diagnostics

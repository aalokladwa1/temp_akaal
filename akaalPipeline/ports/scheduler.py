"""akaalPipeline.ports.scheduler
===============================
External scheduler port protocol.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class ExternalSchedulerPort(Protocol):
    def register_cron_job(self, schedule_id: str, cron_expression: str) -> None: ...
    def unregister_cron_job(self, schedule_id: str) -> None: ...

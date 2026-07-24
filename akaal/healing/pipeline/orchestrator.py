"""HealingPipeline: Pure pipeline orchestrator managing repair execution across domain healers."""

import asyncio
import logging
from typing import List, Dict, Any, Optional
from akaal.healing.core.context import HealingContext
from akaal.healing.core.models import HealingResult, HealingStatus, RepairOutcome
from akaal.healing.core.session import HealingSession
from akaal.healing.core.registry import HealerRegistry
from akaal.healing.events.events import HealingEventType, HealingEvent

logger = logging.getLogger("akaal.healing.pipeline.orchestrator")


class HealingPipeline:
    """Orchestrates repair execution across domain healers. Contains ZERO repair logic."""

    def __init__(self, registry: Optional[HealerRegistry] = None):
        self.registry = registry or HealerRegistry()

    async def execute_pipeline(
        self, context: HealingContext, domain_names: Optional[List[str]] = None
    ) -> HealingSession:
        """Run self-healing pipeline across registered domain healers."""
        session = HealingSession()
        session.start()

        if context.event_bus:
            await context.event_bus.publish(
                HealingEvent(
                    event_type=HealingEventType.REPAIR_STARTED,
                    payload={"session_id": session.session_id},
                )
            )

        target_domains = domain_names or self.registry.list_domains()
        overall_success = True

        for domain_name in target_domains:
            if session.emergency_stop_triggered:
                logger.warning("Emergency stop triggered. Aborting pipeline.")
                overall_success = False
                break

            healer = self.registry.get_domain_healer(domain_name)
            if not healer:
                logger.warning(f"Domain healer {domain_name} not found in registry.")
                continue

            try:
                result = await healer.heal_domain(context)
                session.record_result(domain_name, result)

                if result.status == HealingStatus.FAILED:
                    overall_success = False
                    break

            except Exception as exc:
                logger.error(f"Error orchestrating domain healer {domain_name}: {exc}")
                overall_success = False

        session.complete(success=overall_success)

        if context.event_bus:
            event_type = HealingEventType.REPAIR_COMPLETED if overall_success else HealingEventType.REPAIR_FAILED
            await context.event_bus.publish(
                HealingEvent(
                    event_type=event_type,
                    payload={"session_id": session.session_id, "success": overall_success},
                )
            )

        return session

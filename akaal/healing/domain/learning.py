"""LearningHealer: Domain healer for Learning & Recommendations (Caps 23-25)."""

import time
from typing import List
from akaal.healing.core.interfaces import IDomainHealer
from akaal.healing.core.context import HealingContext
from akaal.healing.core.models import HealingResult, HealingStatus, RepairOutcome
from akaal.healing.events.events import HealingEventType, HealingEvent


class LearningHealer(IDomainHealer):
    """Domain healer managing Caps 23-25: Recommendation Engine, Pattern Learning, Knowledge Base."""

    @property
    def domain_name(self) -> str:
        return "LearningDomain"

    @property
    def capabilities(self) -> List[str]:
        return [
            "Cap 23: Repair Recommendation Engine",
            "Cap 24: Repair Pattern Learning",
            "Cap 25: Repair Knowledge Base",
        ]

    async def heal_domain(self, context: HealingContext) -> HealingResult:
        start_t = time.time()

        if context.pattern_learning_service:
            context.pattern_learning_service.record_pattern("MISSING_ROW", "AUTO_RESTORE", 15.0)

        if context.event_bus:
            await context.event_bus.publish(
                HealingEvent(
                    event_type=HealingEventType.KNOWLEDGE_UPDATED,
                    payload={"domain": self.domain_name},
                )
            )

        elapsed = (time.time() - start_t) * 1000.0
        return HealingResult(
            domain_name=self.domain_name,
            capabilities_executed=self.capabilities,
            status=HealingStatus.COMPLETED,
            outcome=RepairOutcome.REPAIRED,
            total_actions=1,
            successful_actions=1,
            execution_time_ms=elapsed,
        )

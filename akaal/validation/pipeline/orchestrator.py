"""ValidationPipeline: Pure pipeline orchestrator managing domain validator execution, ordering, retries, and lifecycle."""

import asyncio
import logging
from typing import List, Dict, Any, Optional
from akaal.validation.core.context import ValidationContext
from akaal.validation.core.models import ValidationResult, ValidationStatus
from akaal.validation.core.session import ValidationSession
from akaal.validation.core.registry import ValidatorRegistry
from akaal.validation.events.events import EventType, ValidationEvent

logger = logging.getLogger("akaal.validation.pipeline.orchestrator")


class ValidationPipeline:
    """Orchestrates execution across domain validators. Contains ZERO validation logic."""

    def __init__(self, registry: Optional[ValidatorRegistry] = None):
        self.registry = registry or ValidatorRegistry()

    async def execute_pipeline(
        self, context: ValidationContext, domain_names: Optional[List[str]] = None
    ) -> ValidationSession:
        """Run validation pipeline across registered domain validators."""
        session = ValidationSession()
        session.start()

        if context.event_bus:
            await context.event_bus.publish(
                ValidationEvent(
                    event_type=EventType.PIPELINE_STARTED,
                    payload={"session_id": session.session_id},
                )
            )

        target_domains = domain_names or self.registry.list_domains()
        overall_success = True

        for domain_name in target_domains:
            validator = self.registry.get_domain_validator(domain_name)
            if not validator:
                logger.warning(f"Domain validator {domain_name} not found in registry.")
                continue

            try:
                # Orchestrate execution via domain validator
                result = await validator.validate_domain(context)
                session.record_result(domain_name, result)

                if result.status == ValidationStatus.FAILED:
                    overall_success = False
                    if context.config.stop_on_first_failure:
                        logger.info(f"Stopping pipeline execution on first failure at {domain_name}")
                        break

            except Exception as exc:
                logger.error(f"Error orchestrating domain validator {domain_name}: {exc}")
                overall_success = False

        session.complete(success=overall_success)

        if context.event_bus:
            await context.event_bus.publish(
                ValidationEvent(
                    event_type=EventType.PIPELINE_COMPLETED,
                    payload={"session_id": session.session_id, "success": overall_success},
                )
            )

        return session

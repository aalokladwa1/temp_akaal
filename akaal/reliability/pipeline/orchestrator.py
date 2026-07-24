"""ReliabilityPipeline: Pure Orchestration Pipeline (Zero Business Logic)."""

import logging
from typing import List, Optional
from akaal.reliability.core.context import ReliabilityContext
from akaal.reliability.core.session import ReliabilitySession
from akaal.reliability.core.registry import ReliabilityRegistry
from akaal.reliability.decision.context import DecisionContext
from akaal.reliability.decision.evaluator import ReliabilityDecisionChoice

logger = logging.getLogger("akaal.reliability.pipeline")


class ReliabilityPipeline:
    """Pure Orchestration Pipeline for Platform 4 containing ZERO business logic."""

    def __init__(self, registry: ReliabilityRegistry):
        self.registry = registry

    async def execute_pipeline(self, context: ReliabilityContext, session: ReliabilitySession) -> ReliabilitySession:
        logger.info(f"Starting reliability pipeline execution for session {session.session_id}")

        # 1. Evaluate decision choice
        if context.decision_engine:
            dec_ctx = DecisionContext(
                health_score=100.0,
                policy_profile=context.profile.value,
                component_name="system_core",
            )
            choice = context.decision_engine.make_decision(dec_ctx)
            if choice == ReliabilityDecisionChoice.ABORT:
                logger.warning("Decision engine issued ABORT. Terminating pipeline execution.")
                session.mark_completed()
                return session

        # 2. Iterate through registered domain modules in sequence
        domain_names = self.registry.list_domains()
        for domain_name in domain_names:
            domain_module = self.registry.get_domain_module(domain_name)
            if domain_module:
                try:
                    result = await domain_module.execute_domain(context)
                    session.add_result(result)
                except Exception as e:
                    logger.error(f"Execution failed in domain {domain_name}: {str(e)}")

        session.mark_completed()
        logger.info(f"Completed reliability pipeline for session {session.session_id}")
        return session

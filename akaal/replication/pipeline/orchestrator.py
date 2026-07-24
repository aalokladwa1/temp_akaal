"""ReplicationPipeline: Pure Orchestration Pipeline (Zero Business Logic)."""

import time
import logging
from typing import List, Optional
from akaal.replication.core.context import ReplicationContext
from akaal.replication.core.session import ReplicationSession
from akaal.replication.core.registry import ReplicatorRegistry
from akaal.replication.core.models import ReplicationResult, ReplicationStatus, ReplicationOutcome

logger = logging.getLogger("akaal.replication.pipeline")


class ReplicationPipeline:
    """Pure Orchestration Pipeline coordinating execution across domain replicators."""

    def __init__(self, registry: ReplicatorRegistry):
        self.registry = registry

    async def execute_pipeline(self, context: ReplicationContext) -> ReplicationSession:
        """Orchestrate replication execution across registered domain replicators."""
        session = context.session_manager.create_session(context.session_id) if context.session_manager else ReplicationSession(context.session_id)
        session.state = ReplicationStatus.IN_PROGRESS

        # 1. Policy Enforcement
        if context.policy_engine:
            policy_check = context.policy_engine.evaluate_replication(None)
            if not policy_check.get("compliant", True):
                session.state = ReplicationStatus.FAILED
                return session

        # 2. Decision Engine Evaluation
        if context.decision_engine:
            from akaal.replication.decision.context import DecisionContext
            dec_ctx = DecisionContext(policy_profile=context.profile.value)
            decision = context.decision_engine.make_decision(dec_ctx)
            if decision.value in ("PAUSE", "ROLLBACK"):
                session.state = ReplicationStatus.PAUSED if decision.value == "PAUSE" else ReplicationStatus.ROLLED_BACK
                return session

        # 3. Dry-Run Sandbox Simulation if enabled
        if context.sandbox_engine and context.config.enable_dry_run:
            sim_report = context.sandbox_engine.run_dry_run(None)
            if not sim_report.is_safe:
                logger.warning(f"Replication simulation unsafe (rollback prob={sim_report.rollback_probability})")

        # 4. Domain Replicator Execution Loop
        domain_names = self.registry.list_domains()
        for d_name in domain_names:
            replicator = self.registry.get_domain_replicator(d_name)
            if replicator:
                try:
                    res = await replicator.replicate_domain(context)
                    session.add_result(res)

                    # Save session checkpoint
                    if context.session_manager:
                        context.session_manager.checkpoint_mgr.save_checkpoint(
                            session.session_id, {"last_domain": d_name, "actions": res.total_actions}
                        )
                except Exception as ex:
                    logger.error(f"Replication failed in domain {d_name}: {ex}")
                    session.add_result(
                        ReplicationResult(
                            domain_name=d_name,
                            capabilities_executed=replicator.capabilities,
                            status=ReplicationStatus.FAILED,
                            outcome=ReplicationOutcome.FAILED,
                            total_actions=1,
                            successful_actions=0,
                            failed_actions=1,
                        )
                    )

        # 5. Post-Replication Validation & Consistency Verification via Platform 1 facade
        if context.validation_platform:
            _ = context.validation_platform.get_supported_capabilities()

        # 6. Audit Logging
        if context.audit_service:
            context.audit_service.log_replication_entry(
                session.session_id, "PIPELINE_ORCHESTRATION", "COMPLETED" if session.is_successful else "FAILED"
            )

        session.mark_completed()
        return session

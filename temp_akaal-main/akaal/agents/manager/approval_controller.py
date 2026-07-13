"""
NexusForge — Approval Controller
==================================
Manages the human approval gate before production migration.

workflow.md Section 10: The human approval stage is the final
governance checkpoint before production.
NO AI agent shall bypass this stage.

Manager displays to human:
  Migration Summary, Source/Target Summary, Validation Results,
  Object Statistics, Schema Differences, Risk Assessment,
  Recovery Plan, Rollback Plan, Estimated Migration Time,
  Estimated Downtime, Checkpoint Status.

Human Options: Approve / Reject / Pause / Request Investigation / Cancel

TRD Section 13: Human identity shall be recorded before approval.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Callable, Coroutine, Dict, Optional

from akaal.core.models.enums import ApprovalDecision
from akaal.core.models.project import ApprovalRecord, MigrationProject

logger = logging.getLogger("nexusforge.approval_controller")


# ---------------------------------------------------------------------------
# Approval Request Packet — shown to the human operator
# ---------------------------------------------------------------------------

class ApprovalRequestPacket:
    """
    Complete summary displayed to the human before they approve/reject.
    workflow.md Section 10 — mandatory display fields.
    """

    def __init__(self, project: MigrationProject, details: Dict[str, Any]) -> None:
        self.project_id = project.project_id
        self.project_name = project.name
        self.migration_id = project.active_migration_id
        self.source_type = project.source_config.system_type.value
        self.target_type = project.target_config.system_type.value
        self.strategy = project.strategy.value
        self.state_history = project.state_history

        # Populated from details dict
        self.validation_results = details.get("validation_results", {})
        self.object_statistics = details.get("object_statistics", {})
        self.schema_differences = details.get("schema_differences", [])
        self.risk_assessment = details.get("risk_assessment", "Unknown")
        self.recovery_plan = details.get("recovery_plan", "Checkpoint restore available")
        self.rollback_plan = details.get("rollback_plan", "Restore from last checkpoint")
        self.estimated_migration_time = details.get("estimated_migration_time", "Unknown")
        self.estimated_downtime = details.get("estimated_downtime", "Unknown")
        self.checkpoint_status = details.get("checkpoint_status", "No checkpoint")
        self.detected_risks = details.get("detected_risks", [])
        self.created_at = datetime.now(timezone.utc).isoformat()

    def display(self) -> str:
        """Render the approval packet as a human-readable summary."""
        lines = [
            "=" * 70,
            "  NEXUSFORGE — MIGRATION APPROVAL REQUIRED",
            "=" * 70,
            f"  Project Name    : {self.project_name}",
            f"  Project ID      : {self.project_id}",
            f"  Migration ID    : {self.migration_id}",
            f"  Source System   : {self.source_type}",
            f"  Target System   : {self.target_type}",
            f"  Strategy        : {self.strategy}",
            "-" * 70,
            "  VALIDATION RESULTS",
        ]
        for k, v in self.validation_results.items():
            lines.append(f"    {k}: {v}")

        lines += [
            "-" * 70,
            "  OBJECT STATISTICS",
        ]
        for k, v in self.object_statistics.items():
            lines.append(f"    {k}: {v}")

        lines += [
            "-" * 70,
            "  RISK ASSESSMENT",
            f"    {self.risk_assessment}",
        ]

        if self.detected_risks:
            lines.append("  DETECTED RISKS:")
            for risk in self.detected_risks:
                lines.append(f"    ⚠  {risk}")

        lines += [
            "-" * 70,
            f"  Recovery Plan   : {self.recovery_plan}",
            f"  Rollback Plan   : {self.rollback_plan}",
            f"  Est. Duration   : {self.estimated_migration_time}",
            f"  Est. Downtime   : {self.estimated_downtime}",
            f"  Checkpoint      : {self.checkpoint_status}",
            "=" * 70,
            "",
            "  OPTIONS:",
            "    [A] APPROVE — proceed to production migration",
            "    [R] REJECT  — stop migration, begin redesign",
            "    [P] PAUSE   — pause and resume later",
            "    [I] INVESTIGATE — request further investigation",
            "    [C] CANCEL  — cancel this migration permanently",
            "",
        ]
        return "\n".join(lines)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "project_id": self.project_id,
            "project_name": self.project_name,
            "migration_id": self.migration_id,
            "source_type": self.source_type,
            "target_type": self.target_type,
            "strategy": self.strategy,
            "validation_results": self.validation_results,
            "object_statistics": self.object_statistics,
            "risk_assessment": self.risk_assessment,
            "detected_risks": self.detected_risks,
            "recovery_plan": self.recovery_plan,
            "rollback_plan": self.rollback_plan,
            "estimated_migration_time": self.estimated_migration_time,
            "estimated_downtime": self.estimated_downtime,
            "checkpoint_status": self.checkpoint_status,
            "created_at": self.created_at,
        }


# ---------------------------------------------------------------------------
# Approval Controller
# ---------------------------------------------------------------------------

class ApprovalController:
    """
    Manages the human approval gate.

    Supports two modes:
    1. CLI mode (default for Phase 1): prompts stdin for decision
    2. Callback mode: external system provides decision (for API/dashboard integration)

    TRD Section 13: Manager shall pause execution before production migration.
    No production migration may proceed without recorded human approval.
    """

    def __init__(self, cli_mode: bool = True) -> None:
        self._cli_mode = cli_mode
        self._pending_approvals: Dict[str, ApprovalRequestPacket] = {}
        # Optional external callback for non-CLI mode
        self._decision_callback: Optional[
            Callable[[ApprovalRequestPacket], Coroutine[Any, Any, ApprovalDecision]]
        ] = None
        logger.info(
            "[ApprovalController] Initialized. CLI mode: %s", cli_mode
        )

    def set_decision_callback(
        self,
        callback: Callable[[ApprovalRequestPacket], Coroutine[Any, Any, ApprovalDecision]]
    ) -> None:
        """Set an external callback for automated/API-driven approval decisions (testing)."""
        self._decision_callback = callback
        logger.info("[ApprovalController] External decision callback registered.")

    async def request_approval(
        self,
        project: MigrationProject,
        details: Dict[str, Any],
    ) -> ApprovalRecord:
        """
        Present the approval packet to the human and wait for a decision.

        This method BLOCKS until a decision is received.
        workflow.md Section 10: No AI agent shall bypass this stage.

        Returns an ApprovalRecord with the decision and approver identity.
        """
        packet = ApprovalRequestPacket(project, details)
        self._pending_approvals[project.project_id] = packet

        logger.info(
            "[ApprovalController] Approval requested for project=%s",
            project.project_id
        )

        if self._decision_callback:
            # Non-CLI mode — use registered callback
            decision = await self._decision_callback(packet)
            approver = "system_callback"
        elif self._cli_mode:
            # CLI mode — interactive prompt
            decision, approver = await self._cli_prompt(packet)
        else:
            raise RuntimeError(
                "ApprovalController: no decision method available. "
                "Set cli_mode=True or register a decision callback."
            )

        # Remove from pending
        self._pending_approvals.pop(project.project_id, None)

        # Build immutable approval record
        record = ApprovalRecord(
            project_id=project.project_id,
            migration_id=project.active_migration_id or "unknown",
            decision=decision.value,
            decided_by=approver,
            notes=f"Decision: {decision.value}",
        )

        logger.info(
            "[ApprovalController] Decision recorded: %s by %s for project=%s",
            decision.value, approver, project.project_id
        )
        return record

    async def _cli_prompt(
        self, packet: ApprovalRequestPacket
    ) -> tuple[ApprovalDecision, str]:
        """
        Interactive CLI prompt for human approval.
        Runs in a thread pool executor to avoid blocking the event loop.
        """
        loop = asyncio.get_event_loop()

        def _prompt() -> tuple[ApprovalDecision, str]:
            print(packet.display())
            decision_map = {
                "a": ApprovalDecision.APPROVE,
                "approve": ApprovalDecision.APPROVE,
                "r": ApprovalDecision.REJECT,
                "reject": ApprovalDecision.REJECT,
                "p": ApprovalDecision.PAUSE,
                "pause": ApprovalDecision.PAUSE,
                "i": ApprovalDecision.REQUEST_INVESTIGATION,
                "investigate": ApprovalDecision.REQUEST_INVESTIGATION,
                "c": ApprovalDecision.CANCEL,
                "cancel": ApprovalDecision.CANCEL,
            }

            while True:
                raw = input("  Enter your decision: ").strip().lower()
                if raw in decision_map:
                    decision = decision_map[raw]
                    approver = input("  Enter your name/email (for audit record): ").strip()
                    if not approver:
                        print("  Approver identity is required. Please enter your name.")
                        continue
                    return decision, approver
                print(f"  Invalid option '{raw}'. Please choose: A / R / P / I / C")

        return await loop.run_in_executor(None, _prompt)

    def get_pending_approvals(self) -> Dict[str, ApprovalRequestPacket]:
        """Return all currently pending approval requests."""
        return dict(self._pending_approvals)

    def has_pending_approval(self, project_id: str) -> bool:
        return project_id in self._pending_approvals

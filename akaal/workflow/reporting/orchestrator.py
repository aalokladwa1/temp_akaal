"""Report Orchestration engine triggering reports at lifecycle boundaries."""

import threading
from typing import Dict, List, Optional
from akaal.workflow.events.dispatcher import IEventDispatcher
from akaal.workflow.events.events import WorkflowEvent
from akaal.workflow.reporting.reports import EnterpriseReport, WorkflowReportType
from akaal.workflow.utils.clock import IClock, SystemClock
from akaal.workflow.utils.id_generator import IIdGenerator, UUIDIdGenerator


class ReportOrchestrator:
    """Orchestrates generation of Pre-Migration, Migration, Validation, Cutover, and Post-Migration reports."""

    def __init__(
        self,
        event_dispatcher: Optional[IEventDispatcher] = None,
        clock: Optional[IClock] = None,
        id_generator: Optional[IIdGenerator] = None,
    ) -> None:
        self._event_dispatcher = event_dispatcher
        self._clock = clock or SystemClock()
        self._id_generator = id_generator or UUIDIdGenerator()
        self._reports: Dict[str, EnterpriseReport] = {}
        self._lock = threading.Lock()

        if self._event_dispatcher:
            self._event_dispatcher.subscribe("*", self.on_event)

    def generate_report(
        self,
        report_type: WorkflowReportType,
        workflow_id: str,
        run_id: str,
        status: str,
        summary: str,
        details: dict,
    ) -> EnterpriseReport:
        """Generate and store an enterprise report."""
        with self._lock:
            report_id = self._id_generator.generate_uuid()
            report = EnterpriseReport(
                report_id=report_id,
                report_type=report_type,
                workflow_id=workflow_id,
                run_id=run_id,
                status=status,
                summary=summary,
                details=details,
                generated_at=self._clock.now_utc(),
            )
            key = f"{workflow_id}:{report_type.value}"
            self._reports[key] = report
            return report

    def get_report(self, workflow_id: str, report_type: WorkflowReportType) -> Optional[EnterpriseReport]:
        with self._lock:
            return self._reports.get(f"{workflow_id}:{report_type.value}")

    def list_reports_for_workflow(self, workflow_id: str) -> List[EnterpriseReport]:
        with self._lock:
            return [r for k, r in self._reports.items() if k.startswith(f"{workflow_id}:")]

    def on_event(self, event: WorkflowEvent) -> None:
        """Automatically trigger report generation based on domain events."""
        if event.event_type == "PRE_MIGRATION_COMPLETE":
            self.generate_report(
                report_type=WorkflowReportType.PRE_MIGRATION,
                workflow_id=event.workflow_id,
                run_id=event.payload.get("run_id", "run_1"),
                status="SUCCESS",
                summary="Pre-Migration intelligence pipeline completed successfully.",
                details=event.payload,
            )
        elif event.event_type == "MIGRATION_COMPLETE":
            self.generate_report(
                report_type=WorkflowReportType.MIGRATION,
                workflow_id=event.workflow_id,
                run_id=event.payload.get("run_id", "run_1"),
                status="SUCCESS",
                summary="Data migration completed successfully.",
                details=event.payload,
            )
        elif event.event_type == "VALIDATION_COMPLETE":
            self.generate_report(
                report_type=WorkflowReportType.VALIDATION,
                workflow_id=event.workflow_id,
                run_id=event.payload.get("run_id", "run_1"),
                status="SUCCESS",
                summary="Golden Benchmark validation passed successfully.",
                details=event.payload,
            )
        elif event.event_type == "CUTOVER_COMPLETE":
            self.generate_report(
                report_type=WorkflowReportType.CUTOVER,
                workflow_id=event.workflow_id,
                run_id=event.payload.get("run_id", "run_1"),
                status="SUCCESS",
                summary="Cutover switch completed successfully.",
                details=event.payload,
            )
        elif event.event_type == "WORKFLOW_COMPLETED":
            self.generate_report(
                report_type=WorkflowReportType.POST_MIGRATION,
                workflow_id=event.workflow_id,
                run_id=event.payload.get("run_id", "run_1"),
                status="SUCCESS",
                summary="Entire end-to-end enterprise migration lifecycle completed successfully.",
                details=event.payload,
            )

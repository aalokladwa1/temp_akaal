"""ExplainabilityService: Provides root-cause diagnostics and repair suggestions."""

from typing import Any, Dict, Optional
from akaal.validation.core.interfaces import IService
from akaal.validation.core.models import ExplainabilityContext, ValidationIssue


class ExplainabilityService(IService):
    """Infrastructure service providing technical explanation and remediation advice for validation failures."""

    @property
    def service_name(self) -> str:
        return "ExplainabilityService"

    def analyze_issue(self, issue: ValidationIssue) -> ExplainabilityContext:
        """Derive root-cause technical analysis and repair recommendation for a validation issue."""
        root_cause = "DATA_MISMATCH"
        tech_desc = issue.message
        diff = {
            "expected": issue.expected_value,
            "actual": issue.actual_value,
            "table": issue.table_name,
            "column": issue.column_name,
        }

        repair_cmd = None
        if issue.table_name and issue.column_name:
            if "NOT NULL" in issue.message.upper():
                root_cause = "NULL_CONSTRAINT_VIOLATION"
                repair_cmd = f"UPDATE {issue.table_name} SET {issue.column_name} = 'DEFAULT' WHERE {issue.column_name} IS NULL;"
            elif "FOREIGN KEY" in issue.message.upper() or "ORPHAN" in issue.message.upper():
                root_cause = "REFERENTIAL_INTEGRITY_VIOLATION"
                repair_cmd = f"-- Re-sync parent records for {issue.table_name}.{issue.column_name}"
            elif "TRUNCATION" in issue.message.upper():
                root_cause = "DATATYPE_TRUNCATION"
                repair_cmd = f"ALTER TABLE {issue.table_name} MODIFY COLUMN {issue.column_name} VARCHAR(255);"
            else:
                repair_cmd = f"-- Verify row data consistency on {issue.table_name}.{issue.column_name}"

        return ExplainabilityContext(
            issue_id=issue.issue_id,
            root_cause_category=root_cause,
            technical_description=tech_desc,
            diff_summary=diff,
            repair_command_recommendation=repair_cmd,
            confidence=0.98,
        )

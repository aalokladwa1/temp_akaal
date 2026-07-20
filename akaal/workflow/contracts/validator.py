"""Structural Manifest & Step Definition Contract Validators."""

from typing import List
from akaal.workflow.exceptions import ManifestValidationException
from akaal.workflow.models.metadata import StepDefinition, WorkflowManifest
from akaal.workflow.models.results import ValidationResult


class StepDefinitionValidator:
    """Validator for individual step definition contracts."""

    @staticmethod
    def validate(step_def: StepDefinition) -> ValidationResult:
        errors: List[str] = []
        if not step_def.step_id or not step_def.step_id.strip():
            errors.append("Step definition must have a non-empty step_id.")
        if not step_def.step_type or not step_def.step_type.strip():
            errors.append("Step definition must have a non-empty step_type.")
        if step_def.timeout_seconds < 0:
            errors.append("timeout_seconds cannot be negative.")
        if step_def.max_retries < 0:
            errors.append("max_retries cannot be negative.")

        return ValidationResult(valid=len(errors) == 0, errors=tuple(errors))


class ManifestValidator:
    """Validator for full structural workflow manifest integrity and DAG acyclicity."""

    @staticmethod
    def validate(manifest: WorkflowManifest) -> ValidationResult:
        errors: List[str] = []

        if not manifest.metadata.workflow_id:
            errors.append("Manifest metadata workflow_id must not be empty.")

        if not manifest.step_definitions:
            errors.append("Workflow manifest must contain at least one step definition.")

        step_ids = {s.step_id for s in manifest.step_definitions}

        # Check step definitions
        for step_def in manifest.step_definitions:
            step_res = StepDefinitionValidator.validate(step_def)
            if not step_res.valid:
                errors.extend(step_res.errors)

            # Check explicit dependencies resolution
            for dep_id in step_def.dependencies:
                if dep_id not in step_ids:
                    errors.append(f"Step '{step_def.step_id}' references unknown dependency step '{dep_id}'.")

        # Validate DAG acyclicity
        if not errors:
            cycle_error = ManifestValidator._detect_dag_cycles(manifest)
            if cycle_error:
                errors.append(cycle_error)

        return ValidationResult(valid=len(errors) == 0, errors=tuple(errors))

    @staticmethod
    def validate_or_raise(manifest: WorkflowManifest) -> None:
        result = ManifestValidator.validate(manifest)
        if not result.valid:
            raise ManifestValidationException(list(result.errors))

    @staticmethod
    def _detect_dag_cycles(manifest: WorkflowManifest) -> str | None:
        """Detect cycles in step dependencies using DFS graph traversal."""
        adj: dict[str, list[str]] = {s.step_id: list(s.dependencies) for s in manifest.step_definitions}
        visited: dict[str, int] = {s.step_id: 0 for s in manifest.step_definitions}  # 0: unvisited, 1: visiting, 2: visited

        def dfs(node: str) -> bool:
            visited[node] = 1
            for neighbor in adj.get(node, []):
                if visited.get(neighbor) == 1:
                    return True  # Cycle found!
                if visited.get(neighbor) == 0:
                    if dfs(neighbor):
                        return True
            visited[node] = 2
            return False

        for step_id in adj:
            if visited[step_id] == 0:
                if dfs(step_id):
                    return f"Circular dependency cycle detected in workflow DAG involving step '{step_id}'."
        return None

"""Manifest Version Manager handling schema evolution and migration rules."""

from akaal.workflow.models.metadata import WorkflowManifest


class ManifestVersionManager:
    """Handles manifest schema evolution and compatibility validation."""

    def validate_compatibility(self, manifest_v1: WorkflowManifest, manifest_v2: WorkflowManifest) -> bool:
        """Validate if v2 manifest is backward-compatible with v1 manifest."""
        v1_steps = {s.step_id for s in manifest_v1.step_definitions}
        v2_steps = {s.step_id for s in manifest_v2.step_definitions}
        return v1_steps.issubset(v2_steps)

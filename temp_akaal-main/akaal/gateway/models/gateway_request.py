"""
NexusForge — Gateway Request Model
=====================================
Caller-facing input contract for the Input Gateway.

A GatewayRequest is the ONLY accepted way to submit a migration upload.
All fields are validated by the Gateway before any processing begins.

Usage:
    request = GatewayRequest(
        file_path="/absolute/path/to/export.sql",
        requested_by="ops-team",
        migration_strategy=MigrationStrategy.DRY_RUN,
    )
    response = await gateway.process_upload(request)
"""

from dataclasses import dataclass, field
from typing import Optional

from akaal.core.models.enums import MigrationStrategy, SystemType


@dataclass
class GatewayRequest:
    """
    Input contract for an Input Gateway upload request.

    Fields
    ------
    file_path : str
        Absolute path to the uploaded database export file.
        The Gateway stages a secure copy; the original is never modified.

    requested_by : str
        Identity string of the entity submitting the request.
        Used for audit trail and project attribution. Required.

    migration_strategy : MigrationStrategy
        Strategy to use for this migration.
        Defaults to DRY_RUN — safest option for initial submissions.

    target_db_type : SystemType, optional
        Hint about the detected source database type.
        If not provided, the Gateway will auto-detect.
        If provided with low detection confidence, this hint is accepted.

    project_name : str, optional
        Human-readable name for the migration project.
        Defaults to the sanitized filename if not provided.

    extra_metadata : dict, optional
        Arbitrary caller-supplied metadata attached to the session.
        Never executed or parsed for logic.
    """

    # Required
    file_path: str
    requested_by: str

    # Optional with sensible defaults
    migration_strategy: MigrationStrategy = MigrationStrategy.DRY_RUN
    target_db_type: Optional[SystemType] = None
    project_name: Optional[str] = None
    extra_metadata: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate required fields immediately on construction."""
        if not self.file_path or not self.file_path.strip():
            raise ValueError("GatewayRequest.file_path is required and cannot be empty.")
        if not self.requested_by or not self.requested_by.strip():
            raise ValueError("GatewayRequest.requested_by is required and cannot be empty.")

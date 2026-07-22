"""
Converter from YAML Job Definitions into Platform 1 Request Contracts.
"""

from typing import Any, Dict
from akaal.api.contracts.dto import JobRequestDTO, WorkflowSubmitDTO
from akaal.api.contracts.errors import ValidationError
from akaal.api.yaml.parser import YAMLParser


class YAMLToPlatform1Converter:
    """
    Converts YAML Job Definitions into Platform 1 Request Contracts.
    CRITICAL: Never executes jobs directly.
    """

    @staticmethod
    def to_job_request(yaml_content: str, env_override: Dict[str, str] = None) -> JobRequestDTO:
        data = YAMLParser.parse_string(yaml_content, env_override=env_override)
        if "job_type" not in data:
            raise ValidationError("YAML Job definition missing required field: 'job_type'")

        return JobRequestDTO(
            job_type=data["job_type"],
            payload=data.get("payload", {}),
            priority=data.get("priority", 5),
            tenant_id=data.get("tenant_id"),
        )

    @staticmethod
    def to_workflow_submit(yaml_content: str, env_override: Dict[str, str] = None) -> WorkflowSubmitDTO:
        data = YAMLParser.parse_string(yaml_content, env_override=env_override)
        if "workflow_id" not in data:
            raise ValidationError("YAML Workflow definition missing required field: 'workflow_id'")

        return WorkflowSubmitDTO(
            workflow_id=data["workflow_id"],
            name=data.get("name", "YAML Workflow"),
            description=data.get("description", ""),
            steps=data.get("steps", []),
            parameters=data.get("parameters", {}),
            tenant_id=data.get("tenant_id"),
        )

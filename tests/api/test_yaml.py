"""
Unit tests for YAML Job Definition parsing and Platform 1 contract conversion.
"""

import pytest
from akaal.api.contracts.errors import ValidationError
from akaal.api.yaml.converter import YAMLToPlatform1Converter

YAML_JOB_SPEC = """
job_type: "data_migration"
priority: 8
tenant_id: "tenant-yaml-1"
payload:
  source_db: "${DB_SOURCE}"
  batch_size: 5000
"""

YAML_WORKFLOW_SPEC = """
workflow_id: "wf-yaml-100"
name: "YAML Migration Workflow"
description: "Migrates customer table"
steps:
  - step_id: "step-1"
    step_type: "noop"
  - step_id: "step-2"
    step_type: "noop"
"""


def test_yaml_to_job_request_conversion():
    env_override = {"DB_SOURCE": "postgres_main"}
    dto = YAMLToPlatform1Converter.to_job_request(YAML_JOB_SPEC, env_override=env_override)
    assert dto.job_type == "data_migration"
    assert dto.priority == 8
    assert dto.payload["source_db"] == "postgres_main"


def test_yaml_to_workflow_submit_conversion():
    dto = YAMLToPlatform1Converter.to_workflow_submit(YAML_WORKFLOW_SPEC)
    assert dto.workflow_id == "wf-yaml-100"
    assert len(dto.steps) == 2


def test_invalid_yaml_raises_validation_error():
    with pytest.raises(ValidationError):
        YAMLToPlatform1Converter.to_job_request("invalid: yaml: [content")

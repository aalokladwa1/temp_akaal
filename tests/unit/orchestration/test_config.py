"""
Unit tests for Configuration Management.
"""

import pytest
import os
from akaal.orchestration.config.config import UnifiedConfigurationManager, FrozenConfiguration
from akaal.orchestration.domain.errors import ConfigurationError


def test_5_level_configuration_precedence(tmp_path):
    manager = UnifiedConfigurationManager()

    # Create temporary YAML file
    yaml_file = tmp_path / "config.yaml"
    yaml_file.write_text("execution:\n  timeout_seconds: 1800\n  max_retries: 5\n")

    # Set env override (Level 3)
    os.environ["AKAAL_EXECUTION__MAX_RETRIES"] = "10"

    try:
        # Build config with Level 1 (Default) + Level 2 (YAML) + Level 3 (Env) + Level 4 (CLI) + Level 5 (Runtime)
        config: FrozenConfiguration = manager.build_config(
            yaml_source=str(yaml_file),
            cli_overrides={"concurrency": {"max_parallel_steps": 8}},
            runtime_overrides={"execution": {"timeout_seconds": 9999}},
        )

        # Level 5 (Runtime) overrides YAML/Default
        assert config.get("execution.timeout_seconds") == 9999
        # Level 3 (Env) overrides Level 2 (YAML)
        assert config.get("execution.max_retries") == 10
        # Level 4 (CLI) applies
        assert config.get("concurrency.max_parallel_steps") == 8
        # Level 1 (Default) retained for unspecified keys
        assert config.get("logging.level") == "INFO"

        assert config.checksum is not None
        assert str(config.checksum) == config.to_dict()["checksum"]

    finally:
        os.environ.pop("AKAAL_EXECUTION__MAX_RETRIES", None)


def test_configuration_schema_validation():
    manager = UnifiedConfigurationManager(schema={"execution.timeout_seconds": int})

    # Valid config
    valid_cfg = manager.build_config(runtime_overrides={"execution": {"timeout_seconds": 500}})
    assert valid_cfg.get("execution.timeout_seconds") == 500

    # Invalid type
    with pytest.raises(ConfigurationError):
        manager.build_config(runtime_overrides={"execution": {"timeout_seconds": "invalid_int"}})

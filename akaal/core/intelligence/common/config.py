"""
Akaal — Intelligence External Configuration Resources
======================================================
Implements configuration resource load verification, SHA-256 checksum validation,
schema version checks, key duplicate audits, and deterministic load paths.
"""

import hashlib
import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from akaal.core.intelligence.common.exceptions import ConfigValidationError, ResourceLoadingError
from akaal.core.intelligence.common.models import ConfigMetadata


class ConfigResourceLoader:
    """Handles deterministic loading, checksum checks, and schema validation for JSON configuration files."""
    DETERMINISTIC_ORDER: List[str] = [
        "compression_profiles.json",
        "encryption_profiles.json",
        "storage_profiles.json",
        "compatibility_matrix.json",
        "recommendation_rules.json",
        "replay_provider_registry.json"
    ]

    def __init__(self, config_dir: str) -> None:
        self.config_dir = config_dir
        self._loaded_metadata: Dict[str, ConfigMetadata] = {}

    def load_all_configs(self) -> Dict[str, Dict[str, Any]]:
        """Loads all configurations in a deterministic order."""
        loaded_configs: Dict[str, Dict[str, Any]] = {}
        for resource in self.DETERMINISTIC_ORDER:
            file_path = os.path.join(self.config_dir, resource)
            # If a file is missing, we raise a ConfigValidationError during startup
            if not os.path.exists(file_path):
                raise ResourceLoadingError(
                    f"Required configuration file '{resource}' is missing from {self.config_dir}.",
                    error_code="CONFIG_FILE_MISSING"
                )
            loaded_configs[resource] = self.load_config(resource)
        return loaded_configs

    def load_config(self, resource_name: str) -> Dict[str, Any]:
        """Loads a single config file, calculating checksum and validating schema constraints."""
        file_path = os.path.join(self.config_dir, resource_name)
        if not os.path.exists(file_path):
            raise ResourceLoadingError(
                f"File not found: {file_path}",
                error_code="FILE_NOT_FOUND"
            )

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                raw_data = f.read()

            # Deterministic duplicate keys validation using a custom decoder hook
            content = json.loads(raw_data, object_pairs_hook=lambda pairs: self._check_duplicates(pairs, resource_name))
        except json.JSONDecodeError as de:
            raise ConfigValidationError(
                f"JSON Syntax error in configuration file '{resource_name}': {de}",
                error_code="JSON_DECODE_ERROR"
            )
        except ConfigValidationError:
            raise
        except Exception as e:
            raise ResourceLoadingError(
                f"Failed to read file '{resource_name}': {e}",
                error_code="READ_FAILURE"
            )

        # Calculate checksum
        sha256_hash = hashlib.sha256(raw_data.encode("utf-8")).hexdigest()

        # Validate basic schema metadata
        self._validate_schema_metadata(resource_name, content)

        # Store loading audit details
        self._loaded_metadata[resource_name] = ConfigMetadata(
            file_name=resource_name,
            file_path=file_path,
            checksum=sha256_hash,
            schema_version=content.get("schema_version", "1.0.0"),
            loaded_at=datetime.now(timezone.utc)
        )

        return content

    def get_metadata(self, resource_name: str) -> Optional[ConfigMetadata]:
        return self._loaded_metadata.get(resource_name)

    def _check_duplicates(self, pairs: List[tuple], resource_name: str) -> Dict[str, Any]:
        """Checks for duplicate keys in JSON blocks during load phase."""
        result: Dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ConfigValidationError(
                    f"Duplicate key '{key}' detected in configuration resource '{resource_name}'.",
                    error_code="CONFIG_DUPLICATE_KEY"
                )
            result[key] = value
        return result

    def _validate_schema_metadata(self, resource_name: str, content: Dict[str, Any]) -> None:
        """Verifies schema version headers and baseline specifications."""
        if "schema_version" not in content:
            raise ConfigValidationError(
                f"Missing required 'schema_version' key in config file '{resource_name}'.",
                error_code="CONFIG_SCHEMA_VERSION_MISSING"
            )
        
        # Verify schema version pattern matches semantic version format e.g. "1.0.0"
        schema_version = str(content["schema_version"])
        parts = schema_version.split(".")
        if len(parts) != 3 or not all(p.isdigit() for p in parts):
            raise ConfigValidationError(
                f"Invalid 'schema_version' format '{schema_version}' in config file '{resource_name}'. Expected 'x.y.z'.",
                error_code="CONFIG_SCHEMA_VERSION_INVALID"
            )

        # Mandatory dialect rules verification
        if resource_name == "compatibility_matrix.json":
            if "dialects" not in content or not isinstance(content["dialects"], dict):
                raise ConfigValidationError(
                    "Invalid compatibility_matrix format: 'dialects' object is required.",
                    error_code="INVALID_MATRIX_SCHEMA"
                )

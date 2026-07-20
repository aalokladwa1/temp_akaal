"""
Enterprise Unified Configuration Management System.
Implements deterministic 5-level configuration precedence:
Default -> YAML -> Environment Variables (AKAAL_*) -> CLI/REST Overrides -> Runtime Overrides.
Provides schema validation, versioning, runtime immutability, and checksum verification.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
import json
import os

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False


from akaal.orchestration.domain.identifiers import ConfigurationId
from akaal.orchestration.domain.types import Checksum, Version
from akaal.orchestration.domain.errors import ConfigurationError


@dataclass(frozen=True)
class FrozenConfiguration:
    """
    Immutable runtime configuration snapshot.
    """
    config_id: ConfigurationId
    version: Version
    data: Dict[str, Any]
    checksum: Checksum = field(init=False)

    def __post_init__(self) -> None:
        payload = {
            "config_id": str(self.config_id),
            "version": int(self.version),
            "data": self.data,
        }
        object.__setattr__(self, "checksum", Checksum.from_dict(payload))

    def get(self, key: str, default: Any = None) -> Any:
        """Access configuration setting using dot-notation (e.g. 'execution.max_retries')."""
        parts = key.split(".")
        current = self.data
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return default
        return current

    def to_dict(self) -> Dict[str, Any]:
        return {
            "config_id": str(self.config_id),
            "version": int(self.version),
            "data": self.data,
            "checksum": str(self.checksum),
        }


class UnifiedConfigurationManager:
    """
    Unified Configuration Manager enforcing 5-level precedence and schema validation.
    """

    DEFAULT_CONFIG: Dict[str, Any] = {
        "execution": {
            "timeout_seconds": 3600,
            "max_retries": 3,
            "checkpoint_interval_seconds": 60,
            "auto_rollback_on_failure": True,
        },
        "session": {
            "lease_timeout_seconds": 30.0,
            "heartbeat_interval_seconds": 5.0,
        },
        "concurrency": {
            "max_parallel_steps": 4,
        },
        "logging": {
            "level": "INFO",
            "audit_enabled": True,
        },
    }

    def __init__(self, schema: Optional[Dict[str, type]] = None) -> None:
        self._schema = schema or {}

    def _deep_merge(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively merge two dictionaries."""
        result = dict(base)
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        return result

    def _load_env_overrides(self) -> Dict[str, Any]:
        """
        Load environment variable overrides with prefix 'AKAAL_'.
        Example: AKAAL_EXECUTION__TIMEOUT_SECONDS=7200 -> {'execution': {'timeout_seconds': 7200}}
        """
        env_config: Dict[str, Any] = {}
        prefix = "AKAAL_"
        for env_name, env_val in os.environ.items():
            if env_name.startswith(prefix):
                key_path = env_name[len(prefix):].lower().split("__")
                
                # Coerce integer/float/bool if possible
                val: Any = env_val
                if env_val.lower() == "true":
                    val = True
                elif env_val.lower() == "false":
                    val = False
                else:
                    try:
                        val = int(env_val)
                    except ValueError:
                        try:
                            val = float(env_val)
                        except ValueError:
                            pass

                # Nest into dict
                current = env_config
                for part in key_path[:-1]:
                    current = current.setdefault(part, {})
                current[key_path[-1]] = val
        return env_config

    def _parse_yaml(self, yaml_content_or_path: str) -> Dict[str, Any]:
        """Parse YAML or JSON content or file path."""
        if not yaml_content_or_path:
            return {}
        
        content = yaml_content_or_path
        if os.path.exists(yaml_content_or_path):
            with open(yaml_content_or_path, "r", encoding="utf-8") as f:
                content = f.read()

        if HAS_YAML:
            return yaml.safe_load(content) or {}
        else:
            try:
                return json.loads(content) or {}
            except Exception:
                res = {}
                for line in content.splitlines():
                    if ":" in line and not line.strip().startswith("#"):
                        k, v = line.split(":", 1)
                        res[k.strip()] = v.strip()
                return res


    def validate_config(self, data: Dict[str, Any]) -> None:
        """Validates configuration against schema rules."""
        if not isinstance(data, dict):
            raise ConfigurationError("Configuration data must be a dictionary.")

        for key, expected_type in self._schema.items():
            val = self._get_value_by_path(data, key)
            if val is not None and not isinstance(val, expected_type):
                raise ConfigurationError(
                    f"Configuration key '{key}' expected type {expected_type.__name__}, got {type(val).__name__}."
                )

    def _get_value_by_path(self, data: Dict[str, Any], path: str) -> Any:
        parts = path.split(".")
        curr = data
        for p in parts:
            if isinstance(curr, dict) and p in curr:
                curr = curr[p]
            else:
                return None
        return curr

    def build_config(
        self,
        yaml_source: Optional[str] = None,
        cli_overrides: Optional[Dict[str, Any]] = None,
        runtime_overrides: Optional[Dict[str, Any]] = None,
        config_id: Optional[ConfigurationId] = None,
        version: Optional[Version] = None,
    ) -> FrozenConfiguration:
        """
        Builds a deterministic, immutable FrozenConfiguration applying 5-level precedence:
        1. Default Configuration
        2. YAML Configuration
        3. Environment Variables (AKAAL_*)
        4. CLI / REST Overrides
        5. Runtime Overrides
        """
        # Level 1: Default
        merged = dict(self.DEFAULT_CONFIG)

        # Level 2: YAML
        if yaml_source:
            yaml_dict = self._parse_yaml(yaml_source)
            merged = self._deep_merge(merged, yaml_dict)

        # Level 3: Env vars
        env_dict = self._load_env_overrides()
        merged = self._deep_merge(merged, env_dict)

        # Level 4: CLI / REST
        if cli_overrides:
            merged = self._deep_merge(merged, cli_overrides)

        # Level 5: Runtime
        if runtime_overrides:
            merged = self._deep_merge(merged, runtime_overrides)

        # Validation
        self.validate_config(merged)

        cid = config_id or ConfigurationId.generate()
        ver = version or Version(1)

        return FrozenConfiguration(
            config_id=cid,
            version=ver,
            data=merged,
        )

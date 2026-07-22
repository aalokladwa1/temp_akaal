"""
YAML Job Definition Parser with Template Resolution.
"""

from typing import Any, Dict
import os
import re
import yaml

from akaal.api.contracts.errors import ValidationError


class YAMLParser:
    """Parses YAML job files and resolves template variables (${VAR})."""

    @staticmethod
    def parse_string(yaml_content: str, env_override: Dict[str, str] = None) -> Dict[str, Any]:
        try:
            # Resolve variable templates
            resolved_content = YAMLParser._resolve_variables(yaml_content, env_override=env_override)
            data = yaml.safe_load(resolved_content)
            if not isinstance(data, dict):
                raise ValidationError("YAML content must resolve to a dictionary object")
            return data
        except Exception as e:
            raise ValidationError(f"Invalid YAML job definition: {str(e)}")

    @staticmethod
    def _resolve_variables(content: str, env_override: Dict[str, str] = None) -> str:
        pattern = re.compile(r"\$\{([A-Z0-9_]+)\}")
        env = env_override or dict(os.environ)

        def replace_match(match):
            var_name = match.group(1)
            return env.get(var_name, f"${{{var_name}}}")

        return pattern.sub(replace_match, content)

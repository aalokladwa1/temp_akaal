"""
Typer CLI Formatting & Exit Code Utilities.
"""

from typing import Any, Dict
import json
import sys
import yaml


class CLIFormatter:
    """CLI Output Formatter supporting JSON, YAML, and Text."""

    @staticmethod
    def print_output(data: Any, format_type: str = "json") -> None:
        if format_type.lower() == "json":
            if hasattr(data, "model_dump"):
                print(json.dumps(data.model_dump(), indent=2))
            elif isinstance(data, (dict, list)):
                print(json.dumps(data, indent=2))
            else:
                print(json.dumps({"result": str(data)}, indent=2))
        elif format_type.lower() == "yaml":
            if hasattr(data, "model_dump"):
                print(yaml.dump(data.model_dump(), default_flow_style=False))
            elif isinstance(data, (dict, list)):
                print(yaml.dump(data, default_flow_style=False))
            else:
                print(yaml.dump({"result": str(data)}, default_flow_style=False))
        else:
            print(str(data))

    @staticmethod
    def exit_with_code(code: int = 0, message: str = "") -> None:
        if message:
            print(f"[akaal-cli] {message}")
        sys.exit(code)

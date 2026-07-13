from __future__ import annotations
from typing import Any

class MySQLParser:
    def parse(self, source_type: str) -> dict[str, Any]:
        return {
            "base_type": "VARCHAR" if "VARCHAR" in source_type.upper() else "INT",
            "args": {},
            "flags": {},
            "constraints": {},
            "extras": {},
        }

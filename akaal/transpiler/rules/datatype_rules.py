"""
AKAAL PL/SQL Transpiler — Data Type Conversion Rules
=====================================================
Delegates data type conversion directly to CompatibilityLayer as the authoritative source.
"""

from akaal.core.compatibility.compatibility_layer import CompatibilityLayer
from akaal.core.models.enums import SystemType


class DataTypeRulesEngine:
    """Delegates data type translation to CompatibilityLayer."""

    @staticmethod
    def convert_type(oracle_type: str) -> str:
        return CompatibilityLayer.map_datatype(SystemType.ORACLE, SystemType.POSTGRESQL, oracle_type)

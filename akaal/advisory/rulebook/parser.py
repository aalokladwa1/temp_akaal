from __future__ import annotations

from akaal.advisory.rulebook.normalization import normalize_type

from akaal.advisory.parsers.oracle import OracleParser
from akaal.advisory.parsers.mysql import MySQLParser
from akaal.advisory.parsers.postgresql import PostgreSQLParser

from akaal.advisory.rulebook.exceptions import UnsupportedEngineError


class EngineParser:
    """
    Rulebook V1 Engine Parser

    Responsibilities:
    -----------------
    - Normalize incoming type strings.
    - Dispatch parsing to the correct engine adapter.
    - Return a ParsedType object.

    This class MUST NEVER:
    - perform semantic resolution
    - map concepts
    - infer meanings
    - guess metadata
    """

    _ADAPTERS = {
        "oracle": OracleParser(),
        "mysql": MySQLParser(),
        "postgresql": PostgreSQLParser(),
    }

    def parse(self, engine: str, raw_type: str) -> dict:
        """
        Parse a database-specific type into the frozen ParsedType contract.
        """

        normalized = normalize_type(raw_type)

        adapter = self._ADAPTERS.get(engine.lower())

        if adapter is None:
            raise UnsupportedEngineError(
                f"Unsupported database engine: {engine}"
            )

        return adapter.parse(normalized)
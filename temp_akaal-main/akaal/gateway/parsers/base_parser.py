"""
NexusForge — Abstract Parser Base
=====================================
Defines the contract every file format parser must implement.

Key rules enforced by this base:
  1. Parsers are READ-ONLY — they never modify the file.
  2. Parsers never execute file content.
  3. Parsers stream file content — they never load the full file into memory.
  4. Every parser returns a structured ParseResult.
  5. Parsers must handle malformed content gracefully (add warnings, don't raise).

Adding a new format parser:
  1. Create a new module: gateway/parsers/<format>_parser.py
  2. Subclass AbstractParser
  3. Implement can_parse() and parse()
  4. Register the parser in UploadController._parser_registry
  That's it — no other changes needed.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


logger = logging.getLogger("nexusforge.gateway.parsers")


# ---------------------------------------------------------------------------
# Parse Result
# ---------------------------------------------------------------------------

@dataclass
class ParseResult:
    """
    Structured metadata extracted from a database export file.

    Parsers return metadata — never parsed rows, never executable content.

    Fields
    ------
    success : bool
        True if parsing completed (even with warnings).
        False if the file is too corrupted to extract any metadata.
    table_count : int
        Number of tables/collections identified.
    estimated_row_count : int
        Best-effort estimate of total rows across all tables.
    schema_hints : dict
        Mapping of table/collection name → list of column/field names.
    metadata : dict
        Any additional format-specific metadata (e.g. SQL version comments).
    warnings : list[str]
        Non-fatal issues encountered during parsing.
    error_message : str, optional
        Set only when success=False.
    """
    success: bool
    table_count: int = 0
    estimated_row_count: int = 0
    schema_hints: Dict[str, List[str]] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
    error_message: Optional[str] = None

    def __repr__(self) -> str:
        return (
            f"ParseResult(success={self.success}, "
            f"tables={self.table_count}, "
            f"est_rows={self.estimated_row_count})"
        )


# ---------------------------------------------------------------------------
# Abstract Parser
# ---------------------------------------------------------------------------

class AbstractParser(ABC):
    """
    Base class for all file format parsers.

    Every concrete parser must:
      - Override can_parse() to declare which extensions it handles
      - Override parse() to extract metadata from the file

    Parsers MUST NOT:
      - Execute file content
      - Load the entire file into memory
      - Modify the file
      - Raise exceptions to callers (use warnings instead for soft failures)
    """

    @abstractmethod
    def can_parse(self, extension: str) -> bool:
        """
        Return True if this parser handles the given file extension.

        Parameters
        ----------
        extension : str
            Lowercase extension including dot, e.g. ".sql", ".json", ".csv"
        """

    @abstractmethod
    def parse(self, file_path: str) -> ParseResult:
        """
        Extract metadata from the file at file_path.

        Parameters
        ----------
        file_path : str
            Absolute path to the staged file.

        Returns
        -------
        ParseResult
            Always returns a result. Never raises.
            On critical parse failure, returns ParseResult(success=False).
        """

    @property
    def name(self) -> str:
        """Human-readable name for this parser."""
        return type(self).__name__

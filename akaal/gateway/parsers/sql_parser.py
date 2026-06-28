"""
NexusForge — SQL File Parser
================================
Extracts structural metadata from SQL export files (.sql).

Strategy:
  - Streams the file in configurable chunks (never loads full file)
  - Uses regex to identify CREATE TABLE statements and table names
  - Counts INSERT statements as a proxy for estimated row count
  - Extracts column definitions from CREATE TABLE blocks
  - NEVER executes SQL — purely lexical/text analysis

Security:
  - No eval(), exec(), or subprocess calls
  - No SQL engine invoked
  - Regex patterns do not cause catastrophic backtracking (bounded)
  - File read is bounded by MAX_PARSE_BYTES

Limitations:
  - Handles standard ANSI SQL syntax plus common MySQL/PostgreSQL extensions
  - Complex stored procedures or triggers may not be fully parsed (warns)
  - Column extraction is best-effort for complex CREATE TABLE statements
"""

import logging
import re
from pathlib import Path
from typing import Dict, List, Tuple

from akaal.gateway.parsers.base_parser import AbstractParser, ParseResult


logger = logging.getLogger("nexusforge.gateway.parsers.sql")


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Maximum bytes to parse (4 MB scan is sufficient for schema extraction)
MAX_PARSE_BYTES: int = 4 * 1024 * 1024

# Chunk size for streaming reads
CHUNK_SIZE: int = 64 * 1024

# Regex patterns — compiled once at module level for performance
_RE_CREATE_TABLE = re.compile(
    r"CREATE\s+(?:TEMPORARY\s+)?TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?"
    r"(?:`([^`]+)`|\"([^\"]+)\"|(\w+))",
    re.IGNORECASE,
)

_RE_INSERT_INTO = re.compile(
    r"^\s*INSERT\s+(?:INTO\s+)?(?:`[^`]+`|\"[^\"]+\"|\w+)",
    re.IGNORECASE | re.MULTILINE,
)

_RE_COLUMN_DEF = re.compile(
    r"^\s+(?:`([^`]+)`|\"([^\"]+)\"|(\w+))\s+\w",
    re.IGNORECASE | re.MULTILINE,
)

# SQL comment stripper (single-line only, safe bounded pattern)
_RE_SINGLE_LINE_COMMENT = re.compile(r"--[^\n]*")


# ---------------------------------------------------------------------------
# SqlParser
# ---------------------------------------------------------------------------

class SqlParser(AbstractParser):
    """
    Reads SQL export files and extracts schema + row estimate metadata.

    Returns ParseResult with:
      - table_count:         Number of CREATE TABLE statements found
      - estimated_row_count: Number of INSERT statements found
      - schema_hints:        {table_name: [column_name, ...]}
      - metadata:            SQL-specific hints (comment blocks, etc.)
    """

    def __init__(self, max_parse_bytes: int = MAX_PARSE_BYTES) -> None:
        self._max_parse_bytes = max_parse_bytes

    def can_parse(self, extension: str) -> bool:
        return extension.lower() == ".sql"

    def parse(self, file_path: str) -> ParseResult:
        """
        Stream-parse a SQL export file and extract metadata.

        Returns ParseResult(success=False) on unrecoverable errors.
        """
        warnings: List[str] = []
        try:
            content = self._stream_read(file_path, warnings)
        except (IOError, OSError) as exc:
            return ParseResult(
                success=False,
                error_message=f"Cannot read SQL file: {exc}",
            )

        if not content:
            return ParseResult(
                success=False,
                error_message="SQL file is empty or unreadable.",
            )

        # Strip single-line comments for cleaner pattern matching
        cleaned = _RE_SINGLE_LINE_COMMENT.sub("", content)

        # Extract tables and columns
        schema_hints, table_names = self._extract_tables_and_columns(cleaned, warnings)

        # Count INSERT statements as row estimate
        insert_count = len(_RE_INSERT_INTO.findall(cleaned))

        # Detect if content was truncated (file larger than max parse bytes)
        path = Path(file_path)
        try:
            actual_size = path.stat().st_size
            if actual_size > self._max_parse_bytes:
                warnings.append(
                    f"File is {actual_size:,} bytes. Only the first "
                    f"{self._max_parse_bytes:,} bytes were scanned for schema extraction. "
                    "Row count estimate may be lower than actual."
                )
        except OSError:
            pass

        logger.debug(
            "[SqlParser] tables=%d inserts=%d schema_keys=%s",
            len(schema_hints), insert_count, list(schema_hints.keys())[:5],
        )

        return ParseResult(
            success=True,
            table_count=len(schema_hints),
            estimated_row_count=insert_count,
            schema_hints=schema_hints,
            metadata={
                "table_names": table_names,
                "insert_statement_count": insert_count,
            },
            warnings=warnings,
        )

    # ----------------------------------------------------------------
    # Internal helpers
    # ----------------------------------------------------------------

    def _stream_read(self, file_path: str, warnings: List[str]) -> str:
        """
        Stream-read up to MAX_PARSE_BYTES from the file.
        Returns the text content as a string.
        """
        chunks: List[str] = []
        bytes_read = 0

        with open(file_path, "rb") as fh:
            while bytes_read < self._max_parse_bytes:
                chunk = fh.read(CHUNK_SIZE)
                if not chunk:
                    break
                try:
                    chunks.append(chunk.decode("utf-8", errors="replace"))
                except Exception:
                    chunks.append(chunk.decode("latin-1", errors="replace"))
                bytes_read += len(chunk)

        return "".join(chunks)

    def _extract_tables_and_columns(
        self, content: str, warnings: List[str]
    ) -> Tuple[Dict[str, List[str]], List[str]]:
        """
        Extract CREATE TABLE blocks and column names.

        Returns (schema_hints, table_names_in_order).
        """
        schema_hints: Dict[str, List[str]] = {}
        table_names: List[str] = []

        for match in _RE_CREATE_TABLE.finditer(content):
            # Table name from backtick, double-quote, or plain identifier group
            table_name = match.group(1) or match.group(2) or match.group(3)
            if not table_name:
                continue

            table_names.append(table_name)

            # Extract the CREATE TABLE block body (text after the opening paren)
            start = match.end()
            paren_pos = content.find("(", start)
            if paren_pos == -1:
                schema_hints[table_name] = []
                continue

            # Find the matching closing paren (handles nesting)
            block = self._extract_paren_block(content, paren_pos)
            if block is None:
                warnings.append(
                    f"Could not extract column definitions for table '{table_name}'."
                )
                schema_hints[table_name] = []
                continue

            columns = self._extract_columns(block)
            schema_hints[table_name] = columns

        return schema_hints, table_names

    @staticmethod
    def _extract_paren_block(content: str, open_paren: int) -> str:
        """
        Extract text inside the outermost parentheses starting at open_paren.
        Returns the content between the parens (exclusive), or None if unmatched.
        """
        depth = 0
        start = open_paren
        for i in range(open_paren, min(open_paren + MAX_PARSE_BYTES, len(content))):
            ch = content[i]
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
                if depth == 0:
                    return content[start + 1 : i]
        return None

    @staticmethod
    def _extract_columns(block: str) -> List[str]:
        """
        Extract column/field names from inside a CREATE TABLE (...) block.
        Filters out constraint keywords (PRIMARY, UNIQUE, INDEX, KEY, FOREIGN, CHECK).
        """
        CONSTRAINT_KEYWORDS = {
            "primary", "unique", "index", "key", "foreign",
            "check", "constraint", "fulltext", "spatial",
        }

        columns: List[str] = []
        for match in _RE_COLUMN_DEF.finditer(block):
            col_name = match.group(1) or match.group(2) or match.group(3)
            if col_name and col_name.lower() not in CONSTRAINT_KEYWORDS:
                columns.append(col_name)
        return columns

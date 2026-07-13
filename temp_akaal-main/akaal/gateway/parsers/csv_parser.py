"""
NexusForge — CSV File Parser
================================
Extracts structural metadata from CSV export files (.csv).

Strategy:
  - Uses Python's built-in csv module (no external dependencies)
  - Reads header row for column names
  - Samples first MAX_SAMPLE_ROWS rows for type inference
  - Estimates total row count from file size / average row size
  - Auto-detects delimiter (comma, tab, pipe, semicolon)
  - Handles BOM (UTF-8 BOM from Excel exports)

Security:
  - No eval(), exec(), or code generation
  - csv.reader is safe (no formula injection — we read metadata only)
  - File read bounded by MAX_SAMPLE_ROWS for in-memory safety
"""

import csv
import io
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from akaal.gateway.parsers.base_parser import AbstractParser, ParseResult


logger = logging.getLogger("nexusforge.gateway.parsers.csv")


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Maximum rows to sample for schema inference and type detection
MAX_SAMPLE_ROWS: int = 200

# Delimiters to try during auto-detection
CANDIDATE_DELIMITERS: Tuple[str, ...] = (",", "\t", "|", ";")

# Bytes to read for delimiter sniffing
SNIFF_BYTES: int = 4096

# Conservative estimate: average bytes per CSV row
BYTES_PER_ROW_ESTIMATE: int = 128


# ---------------------------------------------------------------------------
# CsvParser
# ---------------------------------------------------------------------------

class CsvParser(AbstractParser):
    """
    Reads CSV export files and extracts schema + row estimate metadata.

    Returns ParseResult with:
      - table_count:         Always 1 (CSV represents a single table)
      - estimated_row_count: Estimated from file size / avg row size
      - schema_hints:        {"default": [column_name, ...]}
      - metadata:            Delimiter, encoding, row sample count
    """

    def __init__(
        self,
        max_sample_rows: int = MAX_SAMPLE_ROWS,
    ) -> None:
        self._max_sample_rows = max_sample_rows

    def can_parse(self, extension: str) -> bool:
        return extension.lower() == ".csv"

    def parse(self, file_path: str) -> ParseResult:
        """
        Parse a CSV file and extract structural metadata.
        """
        warnings: List[str] = []

        # Read a sample for dialect detection and header extraction
        try:
            raw_bytes, file_size = self._read_sample_bytes(file_path)
        except (IOError, OSError) as exc:
            return ParseResult(
                success=False,
                error_message=f"Cannot read CSV file: {exc}",
            )

        if not raw_bytes:
            return ParseResult(success=False, error_message="CSV file is empty.")

        # Decode — handle BOM
        try:
            content = raw_bytes.decode("utf-8-sig")  # strips BOM if present
            encoding = "utf-8"
        except UnicodeDecodeError:
            content = raw_bytes.decode("latin-1", errors="replace")
            encoding = "latin-1"
            warnings.append("File is not UTF-8 encoded. Decoded as latin-1.")

        # Auto-detect delimiter
        delimiter, dialect_confidence = self._detect_delimiter(content[:SNIFF_BYTES])
        if dialect_confidence < 0.5:
            warnings.append(
                f"Low confidence in delimiter detection (confidence={dialect_confidence:.2f}). "
                f"Using delimiter: {delimiter!r}"
            )

        # Parse header row + sample rows
        try:
            columns, sample_rows, parse_warnings = self._parse_csv_content(
                content, delimiter
            )
            warnings.extend(parse_warnings)
        except Exception as exc:
            return ParseResult(
                success=False,
                error_message=f"CSV parsing failed: {exc}",
            )

        if not columns:
            return ParseResult(
                success=False,
                error_message="CSV file has no header row or is malformed.",
            )

        # Estimate total row count from file size
        avg_row_bytes = self._estimate_avg_row_bytes(content, sample_rows)
        estimated_rows = self._estimate_total_rows(file_size, avg_row_bytes)

        # Type inference (optional metadata, best-effort)
        column_types = self._infer_column_types(columns, sample_rows, warnings)

        logger.debug(
            "[CsvParser] columns=%d est_rows=%d delimiter=%r",
            len(columns), estimated_rows, delimiter,
        )

        return ParseResult(
            success=True,
            table_count=1,
            estimated_row_count=estimated_rows,
            schema_hints={"default": columns},
            metadata={
                "delimiter": delimiter,
                "encoding": encoding,
                "column_count": len(columns),
                "sampled_rows": len(sample_rows),
                "column_types": column_types,
            },
            warnings=warnings,
        )

    # ----------------------------------------------------------------
    # Internal helpers
    # ----------------------------------------------------------------

    def _read_sample_bytes(self, file_path: str) -> Tuple[bytes, int]:
        """
        Read enough bytes for full header + MAX_SAMPLE_ROWS parsing.
        Also returns total file size.
        """
        path = Path(file_path)
        file_size = path.stat().st_size
        # Read generously: BYTES_PER_ROW_ESTIMATE * MAX_SAMPLE_ROWS + header overhead
        read_limit = BYTES_PER_ROW_ESTIMATE * self._max_sample_rows * 4
        with open(file_path, "rb") as fh:
            raw = fh.read(read_limit)
        return raw, file_size

    def _detect_delimiter(self, sample: str) -> Tuple[str, float]:
        """
        Auto-detect CSV delimiter using count-based heuristic.

        Returns (delimiter, confidence) where confidence ∈ [0, 1].
        """
        # Try Python's csv.Sniffer first
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters="".join(CANDIDATE_DELIMITERS))
            return dialect.delimiter, 0.9
        except csv.Error:
            pass

        # Fallback: count occurrences of each candidate on the first line
        first_line = sample.split("\n")[0]
        counts = {d: first_line.count(d) for d in CANDIDATE_DELIMITERS}
        best_delim = max(counts, key=lambda d: counts[d])
        best_count = counts[best_delim]

        if best_count == 0:
            # No delimiter found — assume comma
            return ",", 0.3
        # Normalize confidence: more occurrences = higher confidence (cap at 0.9)
        confidence = min(0.9, best_count / (best_count + 5))
        return best_delim, confidence

    def _parse_csv_content(
        self, content: str, delimiter: str
    ) -> Tuple[List[str], List[Dict[str, str]], List[str]]:
        """
        Parse header row and up to MAX_SAMPLE_ROWS data rows.

        Returns (column_names, sample_rows, warnings).
        """
        warnings: List[str] = []
        reader = csv.reader(io.StringIO(content), delimiter=delimiter)

        # Header row
        try:
            header = next(reader)
        except StopIteration:
            return [], [], ["CSV file has no rows."]

        # Clean column names (strip whitespace)
        columns = [col.strip() for col in header]

        # Check for duplicate column names
        seen: set = set()
        for col in columns:
            if col in seen:
                warnings.append(f"Duplicate column name detected: {col!r}")
            seen.add(col)

        # Sample data rows
        sample_rows: List[Dict[str, str]] = []
        for i, row in enumerate(reader):
            if i >= self._max_sample_rows:
                break
            # Map to dict using column names (handle row/col count mismatch)
            row_dict: Dict[str, str] = {}
            for j, col in enumerate(columns):
                row_dict[col] = row[j] if j < len(row) else ""
            sample_rows.append(row_dict)

        return columns, sample_rows, warnings

    @staticmethod
    def _estimate_avg_row_bytes(content: str, sample_rows: List[Dict[str, str]]) -> int:
        """Estimate average row size in bytes from the sampled content."""
        if not sample_rows:
            return BYTES_PER_ROW_ESTIMATE
        # Count lines in sample content
        lines = [l for l in content.split("\n") if l.strip()]
        if len(lines) <= 1:
            return BYTES_PER_ROW_ESTIMATE
        # Average line length (excluding header)
        data_lines = lines[1:]
        if not data_lines:
            return BYTES_PER_ROW_ESTIMATE
        avg = sum(len(l) for l in data_lines) / len(data_lines)
        return max(10, int(avg))

    @staticmethod
    def _estimate_total_rows(file_size: int, avg_row_bytes: int) -> int:
        """Estimate total row count from file size and average row size."""
        if avg_row_bytes <= 0:
            return 0
        return max(0, file_size // avg_row_bytes)

    @staticmethod
    def _infer_column_types(
        columns: List[str],
        sample_rows: List[Dict[str, str]],
        warnings: List[str],
    ) -> Dict[str, str]:
        """
        Best-effort type inference from sample data.

        Returns {column_name: inferred_type_str}.
        Types: "integer", "float", "boolean", "text" (default).
        """
        if not sample_rows:
            return {col: "text" for col in columns}

        types: Dict[str, str] = {}

        for col in columns:
            values = [row.get(col, "").strip() for row in sample_rows if row.get(col, "").strip()]
            if not values:
                types[col] = "text"
                continue

            # Try integer
            try:
                for v in values:
                    int(v.replace(",", ""))
                types[col] = "integer"
                continue
            except ValueError:
                pass

            # Try float
            try:
                for v in values:
                    float(v.replace(",", ""))
                types[col] = "float"
                continue
            except ValueError:
                pass

            # Try boolean
            bool_values = {"true", "false", "yes", "no", "1", "0", "t", "f"}
            if all(v.lower() in bool_values for v in values):
                types[col] = "boolean"
                continue

            types[col] = "text"

        return types

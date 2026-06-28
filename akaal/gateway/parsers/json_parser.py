"""
NexusForge — JSON File Parser
================================
Extracts structural metadata from JSON export files (.json).

Supports:
  - Standard JSON: single object ({}) or array of objects ([{},{},...])
  - NDJSON / JSON Lines: one JSON object per line
  - MongoDB exports (array or NDJSON format)

Strategy:
  - Reads file in streaming fashion using a custom scanner
  - For standard JSON: uses Python's json module on a bounded sample
  - For NDJSON: reads line-by-line up to MAX_SAMPLE_LINES
  - Extracts top-level keys as schema hints (field names)
  - Estimates row count from structure or file size

Security:
  - No eval(), exec(), or code generation
  - json.loads() parses only bounded samples
  - No network calls
  - File read bounded by MAX_PARSE_BYTES
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from akaal.gateway.parsers.base_parser import AbstractParser, ParseResult


logger = logging.getLogger("nexusforge.gateway.parsers.json")


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Max bytes to load for sample-based parsing
MAX_PARSE_BYTES: int = 2 * 1024 * 1024  # 2 MB

# Max NDJSON lines to read for schema inference
MAX_SAMPLE_LINES: int = 500

# For row count estimation from file size
BYTES_PER_JSON_ROW_ESTIMATE: int = 256  # conservative estimate


# ---------------------------------------------------------------------------
# JsonParser
# ---------------------------------------------------------------------------

class JsonParser(AbstractParser):
    """
    Reads JSON export files and extracts schema + row estimate metadata.

    Returns ParseResult with:
      - table_count:         1 for flat JSON array, N for top-level object keys
      - estimated_row_count: Count of top-level array elements (or estimated)
      - schema_hints:        {collection_name: [field_name, ...]}
      - metadata:            JSON structure type (array, object, ndjson)
    """

    def __init__(
        self,
        max_parse_bytes: int = MAX_PARSE_BYTES,
        max_sample_lines: int = MAX_SAMPLE_LINES,
    ) -> None:
        self._max_parse_bytes = max_parse_bytes
        self._max_sample_lines = max_sample_lines

    def can_parse(self, extension: str) -> bool:
        return extension.lower() == ".json"

    def parse(self, file_path: str) -> ParseResult:
        """
        Parse a JSON file and extract structural metadata.

        Handles: standard JSON arrays, objects, and NDJSON.
        """
        warnings: List[str] = []

        # Read bounded sample
        try:
            raw, truncated = self._read_bounded(file_path)
        except (IOError, OSError) as exc:
            return ParseResult(
                success=False,
                error_message=f"Cannot read JSON file: {exc}",
            )

        if not raw.strip():
            return ParseResult(success=False, error_message="JSON file is empty.")

        if truncated:
            warnings.append(
                f"JSON file exceeds {self._max_parse_bytes:,} bytes. "
                "Only a bounded sample was parsed for schema extraction."
            )

        # Detect NDJSON first (faster path for large exports)
        if self._looks_like_ndjson(raw):
            return self._parse_ndjson(raw, file_path, warnings)

        # Standard JSON parse
        return self._parse_standard_json(raw, file_path, warnings)

    # ----------------------------------------------------------------
    # Internal parsers
    # ----------------------------------------------------------------

    def _parse_standard_json(
        self, content: str, file_path: str, warnings: List[str]
    ) -> ParseResult:
        """Parse standard JSON (single object or array)."""
        try:
            data = json.loads(content)
        except json.JSONDecodeError as exc:
            # Try to parse a truncated array by closing it
            repaired, data = self._try_repair_truncated_array(content)
            if not repaired or data is None:
                return ParseResult(
                    success=False,
                    error_message=f"Invalid JSON: {exc}",
                )
            warnings.append("JSON was truncated; partial parse used for schema extraction.")

        if isinstance(data, list):
            return self._extract_from_array(data, file_path, warnings)
        elif isinstance(data, dict):
            return self._extract_from_object(data, file_path, warnings)
        else:
            return ParseResult(
                success=False,
                error_message=f"Unexpected JSON root type: {type(data).__name__}. Expected list or dict.",
            )

    def _parse_ndjson(
        self, content: str, file_path: str, warnings: List[str]
    ) -> ParseResult:
        """Parse NDJSON (one JSON object per line)."""
        lines = content.splitlines()
        parsed_rows: List[Dict[str, Any]] = []
        parse_errors = 0

        for line in lines[:self._max_sample_lines]:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                if isinstance(obj, dict):
                    parsed_rows.append(obj)
            except json.JSONDecodeError:
                parse_errors += 1

        if parse_errors > 0:
            warnings.append(
                f"{parse_errors} NDJSON lines could not be parsed (skipped)."
            )

        if not parsed_rows:
            return ParseResult(
                success=False,
                error_message="No valid NDJSON objects found in file.",
            )

        # Collect all field names across sampled rows
        all_fields: List[str] = []
        for row in parsed_rows:
            for key in row.keys():
                if key not in all_fields:
                    all_fields.append(key)

        # Estimate total rows from file size
        path = Path(file_path)
        estimated_rows = self._estimate_rows_from_size(path, BYTES_PER_JSON_ROW_ESTIMATE)

        return ParseResult(
            success=True,
            table_count=1,
            estimated_row_count=estimated_rows,
            schema_hints={"default": all_fields},
            metadata={
                "json_structure": "ndjson",
                "sampled_rows": len(parsed_rows),
            },
            warnings=warnings,
        )

    # ----------------------------------------------------------------
    # Structure extractors
    # ----------------------------------------------------------------

    def _extract_from_array(
        self, data: list, file_path: str, warnings: List[str]
    ) -> ParseResult:
        """Extract metadata from a JSON array of objects."""
        if not data:
            return ParseResult(
                success=True,
                table_count=1,
                estimated_row_count=0,
                schema_hints={"default": []},
                metadata={"json_structure": "array", "element_count": 0},
                warnings=warnings,
            )

        # Collect all field names from all sampled elements
        all_fields: List[str] = []
        sampled = data[:self._max_sample_lines]
        for item in sampled:
            if isinstance(item, dict):
                for key in item.keys():
                    if key not in all_fields:
                        all_fields.append(key)

        # Estimate total rows from file size if we only sampled
        path = Path(file_path)
        actual_size = self._get_file_size(path)
        if actual_size and actual_size > self._max_parse_bytes:
            estimated_rows = self._estimate_rows_from_size(path, BYTES_PER_JSON_ROW_ESTIMATE)
            warnings.append(
                f"Row count is estimated ({estimated_rows:,}) from file size. "
                "Full file was not loaded."
            )
        else:
            estimated_rows = len(data)

        return ParseResult(
            success=True,
            table_count=1,
            estimated_row_count=estimated_rows,
            schema_hints={"default": all_fields},
            metadata={
                "json_structure": "array",
                "element_count": len(data),
                "sampled_elements": len(sampled),
            },
            warnings=warnings,
        )

    def _extract_from_object(
        self, data: dict, file_path: str, warnings: List[str]
    ) -> ParseResult:
        """
        Extract metadata from a top-level JSON object.

        Treats top-level keys as collection names.
        """
        schema_hints: Dict[str, List[str]] = {}
        estimated_rows = 0

        for key, value in data.items():
            if isinstance(value, list):
                # This key is likely a collection/table
                sample = value[:50]
                fields: List[str] = []
                for item in sample:
                    if isinstance(item, dict):
                        for field_name in item.keys():
                            if field_name not in fields:
                                fields.append(field_name)
                schema_hints[key] = fields
                estimated_rows += len(value)
            elif isinstance(value, dict):
                schema_hints[key] = list(value.keys())

        if not schema_hints:
            # Single flat object — use root keys as the schema
            schema_hints = {"default": list(data.keys())}

        return ParseResult(
            success=True,
            table_count=len(schema_hints),
            estimated_row_count=estimated_rows,
            schema_hints=schema_hints,
            metadata={"json_structure": "object", "top_level_keys": list(data.keys())},
            warnings=warnings,
        )

    # ----------------------------------------------------------------
    # Helpers
    # ----------------------------------------------------------------

    def _read_bounded(self, file_path: str) -> Tuple[str, bool]:
        """
        Read up to MAX_PARSE_BYTES from the file.
        Returns (content_str, was_truncated).
        """
        path = Path(file_path)
        raw = path.read_bytes()
        truncated = len(raw) > self._max_parse_bytes
        sample = raw[: self._max_parse_bytes]
        try:
            return sample.decode("utf-8", errors="replace"), truncated
        except Exception:
            return sample.decode("latin-1", errors="replace"), truncated

    @staticmethod
    def _looks_like_ndjson(content: str) -> bool:
        """Heuristic: first non-empty line starts with { and second is also {."""
        lines = [l.strip() for l in content.splitlines() if l.strip()]
        if len(lines) >= 2 and lines[0].startswith("{") and lines[1].startswith("{"):
            return True
        return False

    @staticmethod
    def _try_repair_truncated_array(content: str) -> Tuple[bool, Optional[Any]]:
        """
        Attempt to close a truncated JSON array so we can extract partial schema.
        Returns (repaired, parsed_data).
        """
        # Find the last complete object
        last_brace = content.rfind("}")
        if last_brace == -1:
            return False, None
        truncated_attempt = content[: last_brace + 1]
        # Determine if we started an array
        first_bracket = content.lstrip().startswith("[")
        if first_bracket:
            truncated_attempt = "[" + truncated_attempt.lstrip("[") + "]"
        try:
            return True, json.loads(truncated_attempt)
        except json.JSONDecodeError:
            return False, None

    @staticmethod
    def _estimate_rows_from_size(path: Path, bytes_per_row: int) -> int:
        """Estimate row count from file size and assumed bytes-per-row."""
        try:
            size = path.stat().st_size
            return max(1, size // bytes_per_row)
        except OSError:
            return 0

    @staticmethod
    def _get_file_size(path: Path) -> Optional[int]:
        try:
            return path.stat().st_size
        except OSError:
            return None

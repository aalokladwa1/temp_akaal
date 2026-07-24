"""Validation fingerprint generator for dataset and schema state."""

import hashlib
import json
from typing import Any, Dict, List


class ValidationFingerprint:
    """Generates cryptographic fingerprints for tables, schemas, and dataset snapshots."""

    @staticmethod
    def generate_schema_fingerprint(tables_metadata: List[Dict[str, Any]]) -> str:
        """Create SHA256 fingerprint representing schema definition state."""
        normalized = sorted(tables_metadata, key=lambda x: str(x.get("table_name", "")))
        serialized = json.dumps(normalized, sort_keys=True)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    @staticmethod
    def generate_table_fingerprint(table_name: str, row_count: int, max_id: Any = None) -> str:
        """Generate fingerprint representing table data state."""
        raw = f"{table_name}:{row_count}:{max_id}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

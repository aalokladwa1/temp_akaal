from __future__ import annotations

import re
from typing import Any


class OracleParser:

    def parse(self, source_type: str) -> dict[str, Any]:
        raw = self._normalize(source_type)

        base_type, args, flags = self._extract(raw)

        return {
            "base_type": base_type,
            "args": args,
            "flags": flags,

            # V1 REQUIRED FIELDS
            "constraints": {},
            "extras": {},
        }

    def _normalize(self, source_type: str) -> str:
        return " ".join(source_type.strip().upper().split())

    def _extract(self, raw: str):
        if raw.startswith("NUMBER"):
            return self._parse_number(raw)

        if raw.startswith(("CHAR", "NCHAR", "VARCHAR2", "NVARCHAR2")):
            return self._parse_character(raw)

        if raw.startswith("TIMESTAMP"):
            return self._parse_timestamp(raw)

        if raw.startswith("INTERVAL"):
            return ("INTERVAL", {}, {})

        if raw in ("BLOB", "CLOB", "NCLOB"):
            # KEEP STRUCTURAL ONLY (no semantic decision here)
            return ("BLOB", {}, {})

        if raw.startswith("RAW"):
            return self._parse_raw(raw)

        if raw == "DATE":
            return ("DATE", {}, {})

        if raw == "JSON":
            return ("JSON", {}, {})

        if raw == "XMLTYPE":
            return ("XML", {}, {})

        if raw in ("ROWID", "UROWID"):
            return ("IDENTIFIER", {}, {})

        if raw == "SDO_GEOMETRY":
            return ("GEOMETRY", {}, {})

        raise ValueError(f"[OracleParser] Unsupported type: {raw}")

    def _parse_number(self, raw: str):
        match = re.match(r"NUMBER(?:\((\d+)(?:,(\d+))?\))?", raw)

        precision = int(match.group(1)) if match and match.group(1) else None
        scale = int(match.group(2)) if match and match.group(2) else None

        args = {}
        if precision is not None:
            args["precision"] = precision
        if scale is not None:
            args["scale"] = scale

        return ("NUMBER", args, {})

    def _parse_character(self, raw: str):
        match = re.match(r"([A-Z0-9]+)(?:\((\d+)\))?", raw)

        length = int(match.group(2)) if match and match.group(2) else None

        args = {}
        if length is not None:
            args["length"] = length

        return ("STRING", args, {})

    def _parse_timestamp(self, raw: str):
        flags = {}

        if "TIME ZONE" in raw:
            flags["timezone"] = True

        return ("TIMESTAMP", {}, flags)

    def _parse_raw(self, raw: str):
        match = re.match(r"RAW\((\d+)\)", raw)

        length = int(match.group(1)) if match else None

        args = {}
        if length is not None:
            args["length"] = length

        return ("BINARY", args, {})
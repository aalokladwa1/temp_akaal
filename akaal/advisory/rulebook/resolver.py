from __future__ import annotations

from akaal.advisory.rulebook.exceptions import UnknownConceptError


class SemanticResolver:
    """
    V1 COMPLIANT RESOLVER

    Responsibilities:
    - Map parsed base_type → semantic concept
    - Apply deterministic metadata enrichment
    - NO registry dependency
    - NO guessing
    """

    def resolve(self, parsed: dict) -> dict:
        base = parsed["base_type"]
        args = parsed.get("args", {})
        flags = parsed.get("flags", {})

        concept, family = self._resolve_concept(base)

        result = {
            "concept": concept,
            "family": family,
            "status": "mapped",
        }

        result.update(self._apply_args(args))
        result.update(self._apply_flags(flags))

        return result

    # -------------------------------------------------
    # PURE SEMANTIC RULES (NO REGISTRY)
    # -------------------------------------------------
    def _resolve_concept(self, base: str) -> tuple[str, str]:

        # numeric
        if base in ("INT", "INTEGER", "BIGINT", "SMALLINT"):
            return "INTEGER", "numeric"

        if base in ("DECIMAL", "NUMERIC", "NUMBER"):
            return "DECIMAL", "numeric"

        if base in ("FLOAT", "DOUBLE", "REAL"):
            return "FLOAT", "numeric"

        # string
        if base in ("CHAR", "VARCHAR", "VARCHAR2", "NCHAR", "NVARCHAR2", "STRING"):
            return "STRING", "string"

        if base in ("TEXT", "CLOB", "NCLOB"):
            return "TEXT", "string"

        # boolean
        if base in ("BOOL", "BOOLEAN"):
            return "BOOLEAN", "boolean"

        # temporal
        if base == "DATE":
            return "DATE", "temporal"

        # TIMESTAMP
        if base == "TIMESTAMP":
            return "TIMESTAMP", "temporal"

        if base == "INTERVAL":
            return "INTERVAL", "temporal"

        # structured
        if base == "JSON":
            return "JSON", "structured"

        if base == "XML":
            return "XML", "structured"

        # binary
        if base in ("BINARY", "BLOB", "RAW"):
            return "BINARY", "binary"

        # spatial
        if base in ("GEOMETRY", "GEOGRAPHY"):
            return "GEOMETRY", "spatial"

        # network
        if base in ("INET", "CIDR", "MACADDR", "MACADDR8"):
            return "NETWORK", "network"

        # identifier
        if base in ("ROWID", "UROWID", "IDENTIFIER"):
            return "IDENTIFIER", "identifier"

        raise UnknownConceptError(f"Unsupported base type: {base}")

    # -------------------------------------------------
    # ARG ENRICHMENT (SAFE)
    # -------------------------------------------------
    def _apply_args(self, args: dict) -> dict:
        out = {}

        if "precision" in args:
            out["precision"] = args["precision"]

        if "scale" in args:
            out["scale"] = args["scale"]

        if "length" in args:
            out["length"] = args["length"]

        return out

    # -------------------------------------------------
    # FLAGS
    # -------------------------------------------------
    def _apply_flags(self, flags: dict) -> dict:
        out = {}

        if flags.get("timezone") is True:
            out["timezone"] = True

        return out
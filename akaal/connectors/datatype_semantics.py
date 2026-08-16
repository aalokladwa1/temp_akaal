"""
Akaal — Canonical Datatype Semantic Model & Type Capability Intersections (P4.8)
==============================================================================
Defines canonical semantic datatype families, dimension metadata (precision, scale, timezone, etc.),
and vendor-neutral semantic mapping rules for universal cross-system compatibility.
"""

from enum import Enum
from typing import Dict, Any, Optional, List


class SemanticDatatypeFamily(str, Enum):
    """Canonical, vendor-neutral semantic datatype classifications."""
    INTEGER                     = "INTEGER"
    UNSIGNED_INTEGER            = "UNSIGNED_INTEGER"
    FIXED_DECIMAL               = "FIXED_DECIMAL"
    FLOATING_POINT              = "FLOATING_POINT"
    BOOLEAN                     = "BOOLEAN"
    FIXED_STRING                = "FIXED_STRING"
    VARIABLE_STRING             = "VARIABLE_STRING"
    UNICODE_STRING              = "UNICODE_STRING"
    BINARY                      = "BINARY"
    LARGE_BINARY                = "LARGE_BINARY"
    LARGE_TEXT                  = "LARGE_TEXT"
    DATE                        = "DATE"
    TIME                        = "TIME"
    TIMESTAMP                   = "TIMESTAMP"
    TIMESTAMP_WITH_TIMEZONE     = "TIMESTAMP_WITH_TIMEZONE"
    INTERVAL                    = "INTERVAL"
    UUID                        = "UUID"
    JSON                        = "JSON"
    XML                         = "XML"
    ARRAY                       = "ARRAY"
    MAP                         = "MAP"
    STRUCT                      = "STRUCT"
    ENUM                        = "ENUM"
    GEOMETRY                    = "GEOMETRY"
    GEOGRAPHY                   = "GEOGRAPHY"
    VECTOR                      = "VECTOR"
    DOCUMENT                    = "DOCUMENT"
    VARIANT                     = "VARIANT"
    UNKNOWN_VENDOR_TYPE         = "UNKNOWN_VENDOR_TYPE"


class DatatypeDimensions:
    """Captures numeric, string, temporal, and structural dimensions of a datatype."""

    def __init__(
        self,
        precision: Optional[int] = None,
        scale: Optional[int] = None,
        signed: bool = True,
        width_bytes: Optional[int] = None,
        max_length: Optional[int] = None,
        encoding: str = "UTF-8",
        collation: Optional[str] = None,
        timezone_aware: bool = False,
        nullable: bool = True,
        dimensionality: int = 0,
    ) -> None:
        self.precision = precision
        self.scale = scale
        self.signed = signed
        self.width_bytes = width_bytes
        self.max_length = max_length
        self.encoding = encoding
        self.collation = collation
        self.timezone_aware = timezone_aware
        self.nullable = nullable
        self.dimensionality = dimensionality

    def to_dict(self) -> Dict[str, Any]:
        return {
            "precision": self.precision,
            "scale": self.scale,
            "signed": self.signed,
            "width_bytes": self.width_bytes,
            "max_length": self.max_length,
            "encoding": self.encoding,
            "collation": self.collation,
            "timezone_aware": self.timezone_aware,
            "nullable": self.nullable,
            "dimensionality": self.dimensionality,
        }


class DatatypeSemanticSpec:
    """Represents a vendor datatype mapped to a canonical semantic family and dimensions."""

    def __init__(
        self,
        native_type_name: str,
        semantic_family: SemanticDatatypeFamily,
        dimensions: Optional[DatatypeDimensions] = None,
        vendor_notes: str = "",
    ) -> None:
        self.native_type_name = native_type_name.upper()
        self.semantic_family = SemanticDatatypeFamily(semantic_family)
        self.dimensions = dimensions or DatatypeDimensions()
        self.vendor_notes = vendor_notes

    def to_dict(self) -> Dict[str, Any]:
        return {
            "native_type_name": self.native_type_name,
            "semantic_family": self.semantic_family.value,
            "dimensions": self.dimensions.to_dict(),
            "vendor_notes": self.vendor_notes,
        }


# Canonical Vendor Type Registry Map (O(1) lookup per vendor)
VENDOR_TYPE_MAPS: Dict[str, Dict[str, SemanticDatatypeFamily]] = {
    "ORACLE": {
        "NUMBER": SemanticDatatypeFamily.FIXED_DECIMAL,
        "VARCHAR2": SemanticDatatypeFamily.VARIABLE_STRING,
        "NVARCHAR2": SemanticDatatypeFamily.UNICODE_STRING,
        "CHAR": SemanticDatatypeFamily.FIXED_STRING,
        "DATE": SemanticDatatypeFamily.TIMESTAMP,  # Oracle DATE stores time component
        "TIMESTAMP": SemanticDatatypeFamily.TIMESTAMP,
        "TIMESTAMP WITH TIME ZONE": SemanticDatatypeFamily.TIMESTAMP_WITH_TIMEZONE,
        "CLOB": SemanticDatatypeFamily.LARGE_TEXT,
        "BLOB": SemanticDatatypeFamily.LARGE_BINARY,
        "RAW": SemanticDatatypeFamily.BINARY,
        "FLOAT": SemanticDatatypeFamily.FLOATING_POINT,
        "JSON": SemanticDatatypeFamily.JSON,
        "SDO_GEOMETRY": SemanticDatatypeFamily.GEOMETRY,
    },
    "POSTGRESQL": {
        "INTEGER": SemanticDatatypeFamily.INTEGER,
        "BIGINT": SemanticDatatypeFamily.INTEGER,
        "SMALLINT": SemanticDatatypeFamily.INTEGER,
        "NUMERIC": SemanticDatatypeFamily.FIXED_DECIMAL,
        "DECIMAL": SemanticDatatypeFamily.FIXED_DECIMAL,
        "REAL": SemanticDatatypeFamily.FLOATING_POINT,
        "DOUBLE PRECISION": SemanticDatatypeFamily.FLOATING_POINT,
        "VARCHAR": SemanticDatatypeFamily.VARIABLE_STRING,
        "TEXT": SemanticDatatypeFamily.LARGE_TEXT,
        "CHAR": SemanticDatatypeFamily.FIXED_STRING,
        "BYTEA": SemanticDatatypeFamily.LARGE_BINARY,
        "DATE": SemanticDatatypeFamily.DATE,
        "TIME": SemanticDatatypeFamily.TIME,
        "TIMESTAMP": SemanticDatatypeFamily.TIMESTAMP,
        "TIMESTAMPTZ": SemanticDatatypeFamily.TIMESTAMP_WITH_TIMEZONE,
        "TIMESTAMP WITH TIME ZONE": SemanticDatatypeFamily.TIMESTAMP_WITH_TIMEZONE,
        "BOOLEAN": SemanticDatatypeFamily.BOOLEAN,
        "UUID": SemanticDatatypeFamily.UUID,
        "JSON": SemanticDatatypeFamily.JSON,
        "JSONB": SemanticDatatypeFamily.JSON,
        "ARRAY": SemanticDatatypeFamily.ARRAY,
        "GEOMETRY": SemanticDatatypeFamily.GEOMETRY,
        "VECTOR": SemanticDatatypeFamily.VECTOR,
    },
    "MYSQL": {
        "INT": SemanticDatatypeFamily.INTEGER,
        "BIGINT": SemanticDatatypeFamily.INTEGER,
        "TINYINT": SemanticDatatypeFamily.INTEGER,
        "DECIMAL": SemanticDatatypeFamily.FIXED_DECIMAL,
        "FLOAT": SemanticDatatypeFamily.FLOATING_POINT,
        "DOUBLE": SemanticDatatypeFamily.FLOATING_POINT,
        "VARCHAR": SemanticDatatypeFamily.VARIABLE_STRING,
        "TEXT": SemanticDatatypeFamily.LARGE_TEXT,
        "LONGTEXT": SemanticDatatypeFamily.LARGE_TEXT,
        "CHAR": SemanticDatatypeFamily.FIXED_STRING,
        "BLOB": SemanticDatatypeFamily.LARGE_BINARY,
        "LONGBLOB": SemanticDatatypeFamily.LARGE_BINARY,
        "DATE": SemanticDatatypeFamily.DATE,
        "DATETIME": SemanticDatatypeFamily.TIMESTAMP,
        "TIMESTAMP": SemanticDatatypeFamily.TIMESTAMP_WITH_TIMEZONE,
        "BOOLEAN": SemanticDatatypeFamily.BOOLEAN,
        "JSON": SemanticDatatypeFamily.JSON,
    },
    "MSSQL": {
        "INT": SemanticDatatypeFamily.INTEGER,
        "BIGINT": SemanticDatatypeFamily.INTEGER,
        "NUMERIC": SemanticDatatypeFamily.FIXED_DECIMAL,
        "DECIMAL": SemanticDatatypeFamily.FIXED_DECIMAL,
        "FLOAT": SemanticDatatypeFamily.FLOATING_POINT,
        "VARCHAR": SemanticDatatypeFamily.VARIABLE_STRING,
        "NVARCHAR": SemanticDatatypeFamily.UNICODE_STRING,
        "TEXT": SemanticDatatypeFamily.LARGE_TEXT,
        "VARBINARY": SemanticDatatypeFamily.LARGE_BINARY,
        "DATETIME2": SemanticDatatypeFamily.TIMESTAMP,
        "DATETIMEOFFSET": SemanticDatatypeFamily.TIMESTAMP_WITH_TIMEZONE,
        "BIT": SemanticDatatypeFamily.BOOLEAN,
        "UNIQUEIDENTIFIER": SemanticDatatypeFamily.UUID,
    },
    "SNOWFLAKE": {
        "NUMBER": SemanticDatatypeFamily.FIXED_DECIMAL,
        "FLOAT": SemanticDatatypeFamily.FLOATING_POINT,
        "VARCHAR": SemanticDatatypeFamily.VARIABLE_STRING,
        "TEXT": SemanticDatatypeFamily.LARGE_TEXT,
        "BINARY": SemanticDatatypeFamily.LARGE_BINARY,
        "DATE": SemanticDatatypeFamily.DATE,
        "TIMESTAMP_NTZ": SemanticDatatypeFamily.TIMESTAMP,
        "TIMESTAMP_TZ": SemanticDatatypeFamily.TIMESTAMP_WITH_TIMEZONE,
        "BOOLEAN": SemanticDatatypeFamily.BOOLEAN,
        "VARIANT": SemanticDatatypeFamily.VARIANT,
        "ARRAY": SemanticDatatypeFamily.ARRAY,
        "OBJECT": SemanticDatatypeFamily.STRUCT,
    },
    "MONGODB": {
        "INT": SemanticDatatypeFamily.INTEGER,
        "LONG": SemanticDatatypeFamily.INTEGER,
        "DECIMAL128": SemanticDatatypeFamily.FIXED_DECIMAL,
        "DOUBLE": SemanticDatatypeFamily.FLOATING_POINT,
        "STRING": SemanticDatatypeFamily.UNICODE_STRING,
        "BIN_DATA": SemanticDatatypeFamily.LARGE_BINARY,
        "DATE": SemanticDatatypeFamily.TIMESTAMP_WITH_TIMEZONE,
        "BOOL": SemanticDatatypeFamily.BOOLEAN,
        "OBJECT_ID": SemanticDatatypeFamily.UUID,
        "DOCUMENT": SemanticDatatypeFamily.DOCUMENT,
        "ARRAY": SemanticDatatypeFamily.ARRAY,
    },
}


def map_vendor_type_to_semantic_family(vendor_name: str, native_type_name: str) -> SemanticDatatypeFamily:
    """Maps a vendor native type name to its canonical semantic family in O(1) time."""
    v_key = vendor_name.upper()
    t_key = native_type_name.upper().split("(")[0].strip()
    if v_key in VENDOR_TYPE_MAPS and t_key in VENDOR_TYPE_MAPS[v_key]:
        return VENDOR_TYPE_MAPS[v_key][t_key]
    return SemanticDatatypeFamily.UNKNOWN_VENDOR_TYPE

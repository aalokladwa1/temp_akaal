"""
Akaal — Type Normalizer
=======================
Standardizes dialect-specific database column types to canonical tokens.
"""


def normalize_data_type(raw_type: str) -> str:
    """
    Standardize a raw database-specific column data type string to a canonical token.

    Examples:
        - TINYINT(1) -> BOOLEAN (special MySQL boolean representation)
        - VARCHAR(255), CHARACTER VARYING -> STRING
        - BIGINT, INTEGER, SERIAL -> INTEGER
        - TEXT, JSONB -> LARGE_TEXT_OR_JSON
    """
    if not raw_type:
        return ""
    
    t = raw_type.upper().strip()
    
    # 1. Large Text & JSON
    if t in ("TEXT", "NVARCHAR(-1)", "NVARCHAR(MAX)", "VARCHAR(-1)", "VARCHAR(MAX)", "JSON", "JSONB", "CLOB"):
        return "LARGE_TEXT_OR_JSON"
    
    # 2. Boolean Aliases (MySQL utilizes TINYINT(1) as boolean)
    if t in ("TINYINT(1)", "BOOL", "BOOLEAN", "BIT", "BIT(1)"):
        return "BOOLEAN"
        
    # 3. String & Character varying
    if "VARCHAR" in t or "CHARACTER VARYING" in t or "CHAR" in t or "NVARCHAR" in t:
        return "STRING"
        
    # 4. Integers
    if "INT" in t or "SERIAL" in t or "COUNTER" in t or "IDENTITY" in t:
        return "INTEGER"
        
    # 5. Temporal
    if "TIME" in t or "DATE" in t or "TIMESTAMP" in t:
        return "DATETIME"
        
    # 6. Binary / Blob
    if "BYTEA" in t or "BLOB" in t or "BINARY" in t or "IMAGE" in t:
        return "BLOB"
        
    # 7. Numeric / Decimal
    if "NUMERIC" in t or "DECIMAL" in t or "FLOAT" in t or "DOUBLE" in t or "REAL" in t:
        return "DECIMAL"
        
    return t

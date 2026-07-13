"""
Akaal — Default Value Normalizer
================================
Standardizes default value expressions across database dialects.
"""

from typing import Any


def normalize_default_value(raw_default: Any) -> str:
    """
    Normalizes a default value representation string from raw database syntax
    to standard tokens like NULL, NEXTVAL, NOW, TRUE, FALSE, or simplified strings.
    """
    if raw_default is None:
        return "NULL"
        
    d_str = str(raw_default).upper().strip()
    
    # Strip double/single quotes and parentheses
    d_str = d_str.replace("(", "").replace(")", "").replace("'", "").replace('"', '').strip()
    
    # Strip cast suffixes (e.g. '::regclass', '::text' in PostgreSQL)
    if "::" in d_str:
        d_str = d_str.split("::")[0].strip()
        
    if not d_str or d_str in ("NONE", "NULL"):
        return "NULL"
        
    if d_str.startswith("NEXTVAL") or "NEXT VALUE FOR" in d_str or "IDENTITY" in d_str:
        return "NEXTVAL"
        
    timestamp_defaults = {"CURRENT_TIMESTAMP", "GETDATE", "NOW", "NOW()"}
    if d_str in timestamp_defaults or "GETDATE" in d_str or "CURRENT_TIMESTAMP" in d_str:
        return "NOW"
        
    bool_true = {"TRUE", "1", "((1))"}
    bool_false = {"FALSE", "0", "((0))"}
    if d_str in bool_true:
        return "TRUE"
    if d_str in bool_false:
        return "FALSE"
        
    return d_str

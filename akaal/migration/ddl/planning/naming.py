"""
Akaal — Identifier Naming Service
==================================
Provides byte-aware deterministic naming, Unicode normalization,
control character rejection, qualified path splitting, and collision checking.
"""

import hashlib
import unicodedata
from typing import Dict, List, Optional, Tuple
from akaal.migration.models import ObjectType
from akaal.migration.ddl.translators.identity import quote_identifier, parse_version
from akaal.migration.ddl.planning.models import DatabaseDialect, ObjectIdentity, ObjectInventory, NamingProvenance


def split_qualified_identifier(identifier: str) -> List[str]:
    """
    Splits a raw qualified identifier by dots, respecting quotes.
    E.g. '"my.schema"."my_table"' -> ['"my.schema"', '"my_table"']
    """
    if not identifier:
        return []
        
    parts = []
    current = []
    in_quote = False
    quote_char = None
    in_bracket = False
    
    for char in identifier:
        if char == '"' or char == '`':
            if in_quote and char == quote_char:
                # Check for escaped quote by looking ahead (implied simple check)
                in_quote = False
                quote_char = None
            elif not in_quote and not in_bracket:
                in_quote = True
                quote_char = char
            current.append(char)
        elif char == '[':
            if not in_quote:
                in_bracket = True
            current.append(char)
        elif char == ']':
            if not in_quote:
                in_bracket = False
            current.append(char)
        elif char == '.' and not in_quote and not in_bracket:
            parts.append("".join(current).strip())
            current = []
        else:
            current.append(char)
            
    if current:
        parts.append("".join(current).strip())
        
    return parts


def clean_unquoted_component(part: str) -> str:
    """Removes outer quote wrappers to get the raw unquoted name component."""
    cleaned = part.strip()
    if cleaned.startswith('"') and cleaned.endswith('"'):
        return cleaned[1:-1].replace('""', '"')
    if cleaned.startswith('`') and cleaned.endswith('`'):
        return cleaned[1:-1].replace('``', '`')
    if cleaned.startswith('[') and cleaned.endswith(']'):
        return cleaned[1:-1].replace(']]', ']')
    return cleaned


def get_dialect_byte_limit(dialect: DatabaseDialect, version_str: str) -> int:
    """Returns the version-aware identifier byte limit."""
    parsed_ver = parse_version(version_str)
    
    if dialect == DatabaseDialect.ORACLE:
        # Oracle 12.2 (parsed as 12, 2) increased limit from 30 to 128 bytes
        if parsed_ver >= (12, 2):
            return 128
        return 30
    elif dialect == DatabaseDialect.POSTGRESQL:
        return 63
    elif dialect == DatabaseDialect.MYSQL:
        return 64
    elif dialect == DatabaseDialect.MSSQL:
        return 128
    return 128


def validate_identifier_safety(name: str) -> None:
    """Rejects NUL and control characters from the identifier string."""
    for char in name:
        code = ord(char)
        if code == 0 or code <= 31 or code == 127:
            raise ValueError(f"Identifier contains invalid control or NUL character: {repr(char)}")


def generate_fallback_name(
    dialect: DatabaseDialect,
    version_str: str,
    schema: str,
    table: str,
    column: str,
    object_type_suffix: str,
    original_candidate: Optional[str] = None,
    inventory: Optional[ObjectInventory] = None
) -> Tuple[str, NamingProvenance]:
    """
    Generates a deterministic, byte-aware fallback identifier, Normalizing UTF-8 characters.
    Truncates strictly at Unicode character boundaries and appends a SHA-256 based suffix.
    """
    validate_identifier_safety(schema)
    validate_identifier_safety(table)
    validate_identifier_safety(column)
    
    # 1. Formulation
    base_name = f"{table}_{column}_{object_type_suffix}"
    
    # 2. Unicode Normalization
    normalized = unicodedata.normalize('NFC', base_name)
    
    # 3. Encoding & Byte Measurement
    limit = get_dialect_byte_limit(dialect, version_str)
    encoded = normalized.encode('utf-8')
    
    if len(encoded) <= limit:
        final_name = normalized
        provenance = NamingProvenance.GENERATED
    else:
        # 4. Hash Suffix
        hash_seed = f"{dialect.value}:{version_str}:{schema}:{table}:{column}:{object_type_suffix}:{original_candidate or base_name}"
        sha_hash = hashlib.sha256(hash_seed.encode('utf-8')).hexdigest()
        suffix = sha_hash[:8]
        
        # We need space for "_" + suffix (9 bytes)
        target_byte_limit = limit - 9
        
        # Truncate at valid Unicode character boundaries
        truncated_chars = []
        current_bytes = 0
        for char in normalized:
            char_bytes = len(char.encode('utf-8'))
            if current_bytes + char_bytes > target_byte_limit:
                break
            truncated_chars.append(char)
            current_bytes += char_bytes
            
        final_name = "".join(truncated_chars) + "_" + suffix
        provenance = NamingProvenance.GENERATED
        
    # Double check final length
    final_encoded = final_name.encode('utf-8')
    if len(final_encoded) > limit:
        # In case normalization expanded it, force hard byte-level truncation
        final_name = final_encoded[:limit].decode('utf-8', errors='ignore')
        
    # Quote via dialect quoter
    quoted_schema = quote_identifier(schema, dialect.value)
    quoted_name = quote_identifier(final_name, dialect.value)
    
    # Check inventory collision
    if inventory:
        obj_type = ObjectType.SEQUENCE if object_type_suffix == "seq" else ObjectType.TRIGGER
        identity = ObjectIdentity(schema=schema, name=final_name, object_type=obj_type)
        if identity in inventory.inventory_map:
            # Resolve collision deterministically by altering the hash seed
            alt_seed = f"collision:{hash_seed}"
            alt_hash = hashlib.sha256(alt_seed.encode('utf-8')).hexdigest()[:8]
            final_name = final_name[:-8] + alt_hash
            provenance = NamingProvenance.GENERATED
            
    return final_name, provenance

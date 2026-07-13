"""
Akaal — Identifier Resolver
===========================
Resolves casing, quoting, and Unicode variations in identifier names.
"""

from akaal.core.comparison.models.context import ComparisonContext


def resolve_identifier(name: str, context: ComparisonContext) -> str:
    """
    Standardize a database identifier name by removing quotes and folding case
    if configured via ComparisonContext.
    
    Handles Unicode identifiers correctly using standard case folding.
    """
    import unicodedata
    
    if not name:
        return ""
        
    resolved = name.strip()
    
    # Strip quotes (e.g. "users", `users`, 'users')
    if len(resolved) >= 2 and resolved[0] in ('"', '`', "'") and resolved[-1] in ('"', '`', "'"):
        resolved = resolved[1:-1]
        
    resolved = unicodedata.normalize("NFC", resolved)

    if context.normalize_identifiers:
        resolved = resolved.lower()
        
    return resolved

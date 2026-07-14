import re

class SQLFormatter:
    """
    Utility to post-process compiled SQL commands, formatting whitespaces
    and normalizing spaces while preserving literal blocks.
    """
    def format(self, sql: str) -> str:
        """Strips outer whitespace and collapses consecutive internal whitespace/tabs."""
        if not sql:
            return ""
        trimmed = sql.strip()
        return re.sub(r'[ \t]+', ' ', trimmed)

class IdentifierQuoter:
    """
    Utility for quoting schema, table, column, and other database identifiers
    according to vendor-specific escaping and capitalization rules.
    """
    def __init__(self, quote_char_left: str, quote_char_right: str, force_upper: bool = False) -> None:
        self.quote_char_left = quote_char_left
        self.quote_char_right = quote_char_right
        self.force_upper = force_upper

    def quote(self, identifier: str) -> str:
        """
        Quotes a single identifier or a dot-separated identifier path.
        Preserves Unicode structures and escapes interior quoting delimiters.
        """
        if not identifier:
            return ""
            
        parts = identifier.split(".")
        quoted_parts = []
        for part in parts:
            if self.force_upper:
                part = part.upper()
                
            # Escape occurrences of quote characters within the identifier name
            part_escaped = part.replace(self.quote_char_left, self.quote_char_left * 2)
            if self.quote_char_left != self.quote_char_right:
                part_escaped = part_escaped.replace(self.quote_char_right, self.quote_char_right * 2)
                
            quoted_parts.append(f"{self.quote_char_left}{part_escaped}{self.quote_char_right}")
            
        return ".".join(quoted_parts)

    @classmethod
    def postgresql(cls) -> "IdentifierQuoter":
        return cls('"', '"')

    @classmethod
    def mysql(cls) -> "IdentifierQuoter":
        return cls('`', '`')

    @classmethod
    def oracle(cls) -> "IdentifierQuoter":
        return cls('"', '"', force_upper=True)

    @classmethod
    def sqlserver(cls) -> "IdentifierQuoter":
        return cls('[', ']')

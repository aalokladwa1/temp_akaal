"""
akaalEngine.schema.procedural.lexer
===================================
Lexer, tokenizer, literal masking, and source-location tracking for procedural SQL code.
Ensures quoted strings, comments, and identifiers are masked during tokenization.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import re
from typing import List, Optional, Tuple


class TokenType(str, Enum):
    """Procedural SQL Token Types."""
    KEYWORD = "KEYWORD"
    IDENTIFIER = "IDENTIFIER"
    STRING_LITERAL = "STRING_LITERAL"
    NUMERIC_LITERAL = "NUMERIC_LITERAL"
    OPERATOR = "OPERATOR"
    DELIMITER = "DELIMITER"
    COMMENT = "COMMENT"
    WHITESPACE = "WHITESPACE"
    EOF = "EOF"


@dataclass(frozen=True)
class SourceLocation:
    """Zero-based index and 1-based line/column position in source code."""
    line: int
    column: int
    offset: int

    def __str__(self) -> str:
        return f"Line {self.line}, Col {self.column}"


@dataclass(frozen=True)
class ParsedTokenRange:
    """Range of tokens spanning a parsed AST node."""
    start_location: SourceLocation
    end_location: SourceLocation
    raw_text: str


@dataclass(frozen=True)
class Token:
    """A single token produced by ProceduralLexer."""
    token_type: TokenType
    value: str
    location: SourceLocation

    def __str__(self) -> str:
        return f"Token({self.token_type.value}, '{self.value}', {self.location})"


class ProceduralLexer:
    """Tokenizes procedural SQL with literal and comment masking."""

    KEYWORDS = {
        "CREATE", "OR", "REPLACE", "PROCEDURE", "FUNCTION", "PACKAGE", "BODY", "IS", "AS",
        "BEGIN", "END", "IF", "THEN", "ELSIF", "ELSE", "CASE", "WHEN", "LOOP", "WHILE", "FOR",
        "IN", "OUT", "INOUT", "OUTPUT", "RETURN", "DECLARE", "EXCEPTION", "RAISE", "CURSOR", "OPEN",
        "FETCH", "INTO", "CLOSE", "EXIT", "CONTINUE", "NULL", "SELECT", "INSERT", "UPDATE",
        "DELETE", "MERGE", "FROM", "WHERE", "AND", "OR", "NOT", "SET", "VALUES", "EXECUTE",
        "IMMEDIATE", "PRAGMA", "AUTONOMOUS_TRANSACTION", "TRY", "CATCH", "TRANSACTION", "COMMIT", "ROLLBACK"
    }

    @classmethod
    def tokenize(cls, sql: str) -> List[Token]:
        """Converts raw procedural SQL string into a stream of Token objects."""
        tokens: List[Token] = []
        i = 0
        line = 1
        col = 1
        length = len(sql)

        while i < length:
            char = sql[i]
            loc = SourceLocation(line=line, column=col, offset=i)

            # 1. Whitespace
            if char.isspace():
                if char == '\n':
                    line += 1
                    col = 1
                else:
                    col += 1
                i += 1
                continue

            # 2. Line Comment: -- ...
            if char == '-' and i + 1 < length and sql[i + 1] == '-':
                start = i
                while i < length and sql[i] != '\n':
                    i += 1
                    col += 1
                val = sql[start:i]
                tokens.append(Token(TokenType.COMMENT, val, loc))
                continue

            # 3. Block Comment: /* ... */
            if char == '/' and i + 1 < length and sql[i + 1] == '*':
                start = i
                i += 2
                col += 2
                while i + 1 < length and not (sql[i] == '*' and sql[i + 1] == '/'):
                    if sql[i] == '\n':
                        line += 1
                        col = 1
                    else:
                        col += 1
                    i += 1
                if i + 1 < length:
                    i += 2
                    col += 2
                val = sql[start:i]
                tokens.append(Token(TokenType.COMMENT, val, loc))
                continue

            # 3.5. Oracle Alternative Quote String: q'[...]' or Q'(...)'
            if (char in ('q', 'Q')) and i + 2 < length and sql[i + 1] == "'":
                start = i
                open_delim = sql[i + 2]
                close_delim = open_delim
                if open_delim == '[':
                    close_delim = ']'
                elif open_delim == '(':
                    close_delim = ')'
                elif open_delim == '{':
                    close_delim = '}'
                elif open_delim == '<':
                    close_delim = '>'

                i += 3
                col += 3
                while i + 1 < length:
                    if sql[i] == close_delim and sql[i + 1] == "'":
                        i += 2
                        col += 2
                        break
                    if sql[i] == '\n':
                        line += 1
                        col = 1
                        i += 1
                    else:
                        col += 1
                        i += 1
                val = sql[start:i]
                tokens.append(Token(TokenType.STRING_LITERAL, val, loc))
                continue

            # 4. Single-Quoted String Literal: '...'
            if char == "'":
                start = i
                i += 1
                col += 1
                while i < length:
                    if sql[i] == "'":
                        if i + 1 < length and sql[i + 1] == "'":
                            # Escaped single quote
                            i += 2
                            col += 2
                            continue
                        else:
                            i += 1
                            col += 1
                            break
                    elif sql[i] == '\n':
                        line += 1
                        col = 1
                        i += 1
                    else:
                        i += 1
                        col += 1
                val = sql[start:i]
                tokens.append(Token(TokenType.STRING_LITERAL, val, loc))
                continue

            # 5. Quoted Identifiers: "..." or `...` or [...]
            if char in ('"', '`', '['):
                closing = ']' if char == '[' else char
                start = i
                i += 1
                col += 1
                while i < length and sql[i] != closing:
                    if sql[i] == '\n':
                        line += 1
                        col = 1
                    else:
                        col += 1
                    i += 1
                if i < length and sql[i] == closing:
                    i += 1
                    col += 1
                val = sql[start:i]
                tokens.append(Token(TokenType.IDENTIFIER, val, loc))
                continue

            # 6. Multi-char operators: :=, <=, >=, <>, !=, ||, ..
            if i + 1 < length and sql[i:i + 2] in (":=", "<=", ">=", "<>", "!=", "||", ".."):
                val = sql[i:i + 2]
                tokens.append(Token(TokenType.OPERATOR, val, loc))
                i += 2
                col += 2
                continue

            # 7. Numeric Literals
            if char.isdigit():
                start = i
                while i < length and (sql[i].isdigit() or sql[i] == '.'):
                    i += 1
                    col += 1
                val = sql[start:i]
                tokens.append(Token(TokenType.NUMERIC_LITERAL, val, loc))
                continue

            # 8. Word / Identifier / Keyword (including :NEW and :OLD bind variables)
            if char.isalpha() or char in ('_', ':', '@', '$', '#', '%'):
                start = i
                while i < length and (sql[i].isalnum() or sql[i] in ('_', '@', '$', '#', '%', '.')):
                    i += 1
                    col += 1
                val = sql[start:i]
                upper_val = val.upper()
                if upper_val in cls.KEYWORDS:
                    tokens.append(Token(TokenType.KEYWORD, upper_val, loc))
                else:
                    tokens.append(Token(TokenType.IDENTIFIER, val, loc))
                continue

            # 9. Single-character Delimiters and Operators
            if char in (';', ',', '(', ')', '+', '-', '*', '/', '=', '<', '>', '.', '%'):
                tok_type = TokenType.DELIMITER if char in (';', ',', '(', ')') else TokenType.OPERATOR
                tokens.append(Token(tok_type, char, loc))
                i += 1
                col += 1
                continue

            # Fallback single character
            tokens.append(Token(TokenType.OPERATOR, char, loc))
            i += 1
            col += 1

        tokens.append(Token(TokenType.EOF, "", SourceLocation(line=line, column=col, offset=length)))
        return tokens

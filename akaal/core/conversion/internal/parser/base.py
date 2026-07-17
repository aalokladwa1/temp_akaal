"""
Akaal — Base Parser & Tokenizer Infrastructure
==============================================
Provides high-performance lexical tokenization, source range tracking,
and comments collection.
"""

from dataclasses import dataclass
from typing import List, Tuple, Optional
from akaal.core.conversion.api.aoir import SourceLocation, ParsedTokenRange

class TokenType:
    KEYWORD = "KEYWORD"
    IDENTIFIER = "IDENTIFIER"
    STRING = "STRING"
    NUMBER = "NUMBER"
    OPERATOR = "OPERATOR"
    DELIMITER = "DELIMITER"
    COMMENT = "COMMENT"
    EOF = "EOF"

@dataclass(frozen=True)
class Token:
    type: str
    value: str
    line: int
    column: int
    offset: int

    def to_location(self) -> SourceLocation:
        return SourceLocation(line=self.line, column=self.column, offset=self.offset)

    def to_range(self, end_token: Optional['Token'] = None) -> ParsedTokenRange:
        end = end_token if end_token else self
        end_loc = SourceLocation(
            line=end.line,
            column=end.column + len(end.value),
            offset=end.offset + len(end.value)
        )
        return ParsedTokenRange(start=self.to_location(), end=end_loc, raw_text=self.value)

class Tokenizer:
    def __init__(self, source: str):
        self.source = source
        self.length = len(source)
        self.offset = 0
        self.line = 1
        self.column = 1

    def _peek_char(self, offset: int = 0) -> str:
        idx = self.offset + offset
        if idx >= self.length:
            return ""
        return self.source[idx]

    def _advance_char(self) -> str:
        if self.offset >= self.length:
            return ""
        char = self.source[self.offset]
        self.offset += 1
        if char == '\n':
            self.line += 1
            self.column = 1
        else:
            self.column += 1
        return char

    def tokenize(self) -> List[Token]:
        tokens: List[Token] = []
        while self.offset < self.length:
            char = self._peek_char()

            # Whitespace handling
            if char.isspace():
                self._advance_char()
                continue

            # Line comments
            if char == '-' and self._peek_char(1) == '-':
                line = self.line
                col = self.column
                offset = self.offset
                val = ""
                while self.offset < self.length and self._peek_char() != '\n':
                    val += self._advance_char()
                tokens.append(Token(TokenType.COMMENT, val, line, col, offset))
                continue

            # Block comments
            if char == '/' and self._peek_char(1) == '*':
                line = self.line
                col = self.column
                offset = self.offset
                val = self._advance_char() + self._advance_char()
                while self.offset < self.length:
                    if self._peek_char() == '*' and self._peek_char(1) == '/':
                        val += self._advance_char() + self._advance_char()
                        break
                    val += self._advance_char()
                tokens.append(Token(TokenType.COMMENT, val, line, col, offset))
                continue

            # Strings
            if char == "'":
                line = self.line
                col = self.column
                offset = self.offset
                val = self._advance_char()  # Consume starting quote
                while self.offset < self.length:
                    c = self._peek_char()
                    if c == "'" and self._peek_char(1) == "'":
                        val += self._advance_char() + self._advance_char()  # Escaped single quote
                    elif c == "'":
                        val += self._advance_char()  # End quote
                        break
                    else:
                        val += self._advance_char()
                tokens.append(Token(TokenType.STRING, val, line, col, offset))
                continue

            # Quoted identifiers
            if char == '"':
                line = self.line
                col = self.column
                offset = self.offset
                val = self._advance_char()
                while self.offset < self.length:
                    c = self._peek_char()
                    if c == '"':
                        val += self._advance_char()
                        break
                    else:
                        val += self._advance_char()
                tokens.append(Token(TokenType.IDENTIFIER, val, line, col, offset))
                continue

            # Numbers
            if char.isdigit():
                line = self.line
                col = self.column
                offset = self.offset
                val = ""
                while self.offset < self.length and (self._peek_char().isdigit() or self._peek_char() == '.'):
                    val += self._advance_char()
                tokens.append(Token(TokenType.NUMBER, val, line, col, offset))
                continue

            # Identifiers & Keywords
            if char.isalpha() or char == '_':
                line = self.line
                col = self.column
                offset = self.offset
                val = ""
                while self.offset < self.length and (self._peek_char().isalnum() or self._peek_char() in ('_', '$', '#')):
                    val += self._advance_char()
                
                # Simple keyword detection
                kw = val.upper()
                if kw in ("DECLARE", "BEGIN", "END", "PROCEDURE", "FUNCTION", "IN", "OUT", "INOUT", "DEFAULT",
                          "IF", "THEN", "ELSIF", "ELSE", "CASE", "WHEN", "WHILE", "LOOP", "FOR", "CURSOR",
                          "IS", "AS", "EXCEPTION", "PRAGMA", "COMMIT", "ROLLBACK", "SAVEPOINT", "EXECUTE", "IMMEDIATE"):
                    tokens.append(Token(TokenType.KEYWORD, val, line, col, offset))
                else:
                    tokens.append(Token(TokenType.IDENTIFIER, val, line, col, offset))
                continue

            # Multicharacter Operators
            if char in (':', '=', '<', '>', '!'):
                line = self.line
                col = self.column
                offset = self.offset
                val = self._advance_char()
                next_c = self._peek_char()
                if val == ':' and next_c == '=':
                    val += self._advance_char()
                    tokens.append(Token(TokenType.OPERATOR, val, line, col, offset))
                elif val == '<' and next_c == '=':
                    val += self._advance_char()
                    tokens.append(Token(TokenType.OPERATOR, val, line, col, offset))
                elif val == '>' and next_c == '=':
                    val += self._advance_char()
                    tokens.append(Token(TokenType.OPERATOR, val, line, col, offset))
                elif val == '!' and next_c == '=':
                    val += self._advance_char()
                    tokens.append(Token(TokenType.OPERATOR, val, line, col, offset))
                elif val == '<' and next_c == '>':
                    val += self._advance_char()
                    tokens.append(Token(TokenType.OPERATOR, val, line, col, offset))
                else:
                    tokens.append(Token(TokenType.DELIMITER if val in (':',) else TokenType.OPERATOR, val, line, col, offset))
                continue

            # Single delimiters
            if char in (';', '(', ')', ',', '.'):
                line = self.line
                col = self.column
                offset = self.offset
                val = self._advance_char()
                tokens.append(Token(TokenType.DELIMITER, val, line, col, offset))
                continue

            # Anything else is operator
            line = self.line
            col = self.column
            offset = self.offset
            val = self._advance_char()
            tokens.append(Token(TokenType.OPERATOR, val, line, col, offset))

        return tokens

class ParserBase:
    def __init__(self, tokens: List[Token], source_text: str):
        self.tokens = [t for t in tokens if t.type != TokenType.COMMENT]
        self.all_tokens = tokens
        self.source_text = source_text
        self.pos = 0
        self.length = len(self.tokens)

    def peek(self, offset: int = 0) -> Token:
        idx = self.pos + offset
        if idx >= self.length:
            return Token(TokenType.EOF, "", -1, -1, -1)
        return self.tokens[idx]

    def consume(self) -> Token:
        tok = self.peek()
        if tok.type != TokenType.EOF:
            self.pos += 1
        return tok

    def match(self, t_type: str, value: Optional[str] = None) -> bool:
        tok = self.peek()
        if tok.type == t_type or (value is not None and tok.type in (TokenType.KEYWORD, TokenType.IDENTIFIER)):
            if value is None or tok.value.upper() == value.upper():
                self.consume()
                return True
        return False

    def expect(self, t_type: str, value: Optional[str] = None, err_msg: str = "") -> Token:
        tok = self.peek()
        if tok.type == t_type or (value is not None and tok.type in (TokenType.KEYWORD, TokenType.IDENTIFIER)):
            if value is None or tok.value.upper() == value.upper():
                return self.consume()
        raise ValueError(err_msg or f"Expected {t_type} with value {value}, but got {tok}")

    def get_source_range(self, start_tok: Token, end_tok: Token) -> ParsedTokenRange:
        start_loc = start_tok.to_location()
        end_loc = SourceLocation(
            line=end_tok.line,
            column=end_tok.column + len(end_tok.value),
            offset=end_tok.offset + len(end_tok.value)
        )
        raw_text = self.source_text[start_loc.offset : end_loc.offset]
        return ParsedTokenRange(start=start_loc, end=end_loc, raw_text=raw_text)

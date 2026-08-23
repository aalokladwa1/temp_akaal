"""
tests.unit.engine_schema.test_procedural_lexer_masking
======================================================
Hostile negative and unit tests for ProceduralLexer masking strings, comments, and semicolons (SCH-041).
"""

import pytest

from akaalEngine.schema.procedural.lexer import ProceduralLexer, TokenType


def test_string_literal_with_semicolons():
    sql = "SELECT 'first; second; third;' AS msg, 123 FROM dual;"
    tokens = ProceduralLexer.tokenize(sql)

    string_toks = [t for t in tokens if t.token_type == TokenType.STRING_LITERAL]
    assert len(string_toks) == 1
    assert string_toks[0].value == "'first; second; third;'"

    # The only delimiters should be comma and final semicolon
    delims = [t.value for t in tokens if t.value == ';']
    assert len(delims) == 1  # Only 1 true SQL semicolon statement terminator


def test_escaped_quotes_inside_literal():
    sql = "SET v_text = 'O''Reilly''s book;';"
    tokens = ProceduralLexer.tokenize(sql)

    str_tok = next(t for t in tokens if t.token_type == TokenType.STRING_LITERAL)
    assert str_tok.value == "'O''Reilly''s book;'"

    delims = [t.value for t in tokens if t.value == ';']
    assert len(delims) == 1


def test_comment_masking():
    sql = """
    -- This is a line comment containing ; and END; and CREATE TABLE
    /* Block comment
       containing ; and IF THEN ELSE
    */
    v_val := 42;
    """
    tokens = ProceduralLexer.tokenize(sql)
    comments = [t for t in tokens if t.token_type == TokenType.COMMENT]
    assert len(comments) == 2

    # Verify no false keyword tokens inside comments
    kw_tokens = [t.value for t in tokens if t.token_type == TokenType.KEYWORD]
    assert "TABLE" not in kw_tokens
    assert "IF" not in kw_tokens

    delims = [t.value for t in tokens if t.value == ';']
    assert len(delims) == 1


def test_quoted_identifiers_with_semicolons():
    sql = 'SELECT "weird;col;name" FROM [strange;table];'
    tokens = ProceduralLexer.tokenize(sql)

    id_tokens = [t.value for t in tokens if t.token_type == TokenType.IDENTIFIER]
    assert '"weird;col;name"' in id_tokens
    assert '[strange;table]' in id_tokens

    delims = [t.value for t in tokens if t.value == ';']
    assert len(delims) == 1

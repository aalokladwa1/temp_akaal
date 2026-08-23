"""
akaalEngine.schema.procedural.parsers.tsql
==========================================
Abstract Syntax Tree parser for Microsoft SQL Server T-SQL stored procedures, functions, and triggers.
"""

from __future__ import annotations

from typing import List, Optional, Tuple

from akaalEngine.schema.models.programmables import ParameterMode, RoutineKind
from akaalEngine.schema.procedural.ast_nodes import (
    AOIRNode,
    AssignmentStatement,
    BlockNode,
    CallStatement,
    DMLStatement,
    DynamicSQLNode,
    ExceptionHandler,
    IfStatement,
    NullStatement,
    ParameterDeclaration,
    ReturnStatement,
    RoutineAST,
    VariableDeclaration,
    WhileStatement,
)
from akaalEngine.schema.procedural.lexer import ProceduralLexer, Token, TokenType


class TSQLParser:
    """Parser that transforms Microsoft T-SQL source code into an AOIR typed AST."""

    def __init__(self, sql: str):
        self.raw_sql = sql
        self.tokens: List[Token] = ProceduralLexer.tokenize(sql)
        self.pos = 0
        self.length = len(self.tokens)

    def current(self) -> Token:
        if self.pos < self.length:
            return self.tokens[self.pos]
        return self.tokens[-1]

    def advance(self) -> Token:
        tok = self.current()
        self.pos += 1
        return tok

    def match_keyword(self, *keywords: str) -> bool:
        if self.pos < self.length:
            tok = self.tokens[self.pos]
            if tok.value.upper() in [k.upper() for k in keywords]:
                self.advance()
                return True
        return False

    def check_keyword(self, *keywords: str) -> bool:
        if self.pos < self.length:
            tok = self.tokens[self.pos]
            if tok.value.upper() in [k.upper() for k in keywords]:
                return True
        return False

    def skip_semicolons(self) -> None:
        while self.pos < self.length and self.current().value == ';':
            self.advance()

    def parse(self) -> RoutineAST:
        """Parses T-SQL routine into RoutineAST."""
        # 1. Skip CREATE [OR ALTER]
        self.match_keyword("CREATE")
        self.match_keyword("OR")
        self.match_keyword("ALTER")

        # 2. Routine Kind
        if self.match_keyword("FUNCTION"):
            routine_kind = RoutineKind.FUNCTION
        elif self.match_keyword("PROCEDURE", "PROC"):
            routine_kind = RoutineKind.PROCEDURE
        else:
            raise SyntaxError(f"Expected PROCEDURE, PROC, or FUNCTION in T-SQL source: '{self.raw_sql[:60]}...'")

        # 3. Routine Name
        name_tok = self.advance()
        name = name_tok.value.strip("[]")

        # 4. Parameters
        parameters: List[ParameterDeclaration] = []
        if self.current().value == '(':
            self.advance()
            parameters = self._parse_parameters()
            if self.current().value == ')':
                self.advance()
        elif self.current().value.startswith("@"):
            parameters = self._parse_parameters_unparenthesized()

        # 5. AS / IS
        self.match_keyword("AS", "IS")

        # 6. Body Block
        body_block = self._parse_block()

        return RoutineAST(
            name=name,
            routine_type=routine_kind,
            parameters=tuple(parameters),
            body=body_block,
        )

    def _parse_parameters(self) -> List[ParameterDeclaration]:
        params = []
        while self.pos < self.length and self.current().value != ')':
            p_name = self.advance().value
            p_type = self.advance().value
            if self.current().value == '(':
                self.advance()
                while self.pos < self.length and self.current().value != ')':
                    self.advance()
                if self.current().value == ')':
                    self.advance()

            mode = ParameterMode.OUT if self.match_keyword("OUTPUT", "OUT") else ParameterMode.IN
            default_val = None
            if self.current().value == '=':
                self.advance()
                default_val = self.advance().value

            params.append(ParameterDeclaration(name=p_name, data_type=p_type, mode=mode, default_value=default_val))
            if self.current().value == ',':
                self.advance()
        return params

    def _parse_parameters_unparenthesized(self) -> List[ParameterDeclaration]:
        params = []
        while self.pos < self.length and not self.check_keyword("AS", "IS"):
            p_name = self.advance().value
            p_type = self.advance().value
            if self.current().value == '(':
                self.advance()
                while self.pos < self.length and self.current().value != ')':
                    self.advance()
                if self.current().value == ')':
                    self.advance()

            mode = ParameterMode.OUT if self.match_keyword("OUTPUT", "OUT") else ParameterMode.IN
            default_val = None
            if self.current().value == '=':
                self.advance()
                default_val = self.advance().value

            params.append(ParameterDeclaration(name=p_name, data_type=p_type, mode=mode, default_value=default_val))
            if self.current().value == ',':
                self.advance()
        return params

    def _parse_block(self) -> BlockNode:
        has_begin = self.match_keyword("BEGIN")
        declarations: List[AOIRNode] = []
        statements: List[AOIRNode] = []
        exception_handlers: List[ExceptionHandler] = []

        while self.pos < self.length:
            if has_begin and self.check_keyword("END"):
                self.advance()
                break

            # Handle DECLARE @var TYPE
            if self.match_keyword("DECLARE"):
                var_name = self.advance().value
                var_type = self.advance().value
                if self.current().value == '(':
                    self.advance()
                    while self.pos < self.length and self.current().value != ')':
                        self.advance()
                    if self.current().value == ')':
                        self.advance()

                default_val = None
                if self.current().value == '=':
                    self.advance()
                    val_parts = []
                    while self.pos < self.length and self.current().value != ';':
                        val_parts.append(self.advance().value)
                    default_val = " ".join(val_parts)

                self.skip_semicolons()
                declarations.append(VariableDeclaration(name=var_name, data_type=var_type, default_value=default_val))
                continue

            # Handle TRY ... CATCH
            if self.match_keyword("BEGIN"):
                if self.match_keyword("TRY"):
                    try_stmts = []
                    while self.pos < self.length and not self.check_keyword("END"):
                        stmt = self._parse_statement()
                        if stmt:
                            try_stmts.append(stmt)
                    self.match_keyword("END")
                    self.match_keyword("TRY")

                    self.match_keyword("BEGIN")
                    self.match_keyword("CATCH")
                    catch_stmts = []
                    while self.pos < self.length and not self.check_keyword("END"):
                        stmt = self._parse_statement()
                        if stmt:
                            catch_stmts.append(stmt)
                    self.match_keyword("END")
                    self.match_keyword("CATCH")

                    statements.extend(try_stmts)
                    exception_handlers.append(ExceptionHandler(exception_names=("OTHERS",), statements=tuple(catch_stmts)))
                    continue
                else:
                    # Regular inner BEGIN ... END block
                    inner_block = self._parse_block()
                    statements.append(inner_block)
                    continue

            stmt = self._parse_statement()
            if stmt:
                statements.append(stmt)

        return BlockNode(
            declarations=tuple(declarations),
            statements=tuple(statements),
            exception_handlers=tuple(exception_handlers),
        )

    def _parse_statement(self) -> Optional[AOIRNode]:
        if self.pos >= self.length:
            return None

        # 1. SET @var = expr;
        if self.match_keyword("SET"):
            target_var = self.advance().value
            self.match_keyword("=")
            expr_parts = []
            while self.pos < self.length and self.current().value != ';':
                expr_parts.append(self.advance().value)
            self.skip_semicolons()
            return AssignmentStatement(target=target_var, expression=" ".join(expr_parts))

        # 2. IF statement
        if self.match_keyword("IF"):
            cond_parts = []
            while self.pos < self.length and not self.check_keyword("BEGIN"):
                cond_parts.append(self.advance().value)
            then_block = self._parse_block()
            else_stmts = []
            if self.match_keyword("ELSE"):
                else_block = self._parse_block()
                else_stmts = [else_block]
            return IfStatement(
                condition=" ".join(cond_parts),
                then_statements=(then_block,),
                else_statements=tuple(else_stmts),
            )

        # 3. WHILE statement
        if self.match_keyword("WHILE"):
            cond_parts = []
            while self.pos < self.length and not self.check_keyword("BEGIN"):
                cond_parts.append(self.advance().value)
            while_block = self._parse_block()
            return WhileStatement(
                condition=" ".join(cond_parts),
                statements=(while_block,),
            )

        # 4. EXEC / EXECUTE
        if self.match_keyword("EXEC", "EXECUTE"):
            first_tok = self.advance().value
            if first_tok.lower() == "sp_executesql":
                sql_expr = self.advance().value
                self.skip_semicolons()
                return DynamicSQLNode(sql_expression=sql_expr)
            args = []
            while self.pos < self.length and self.current().value != ';':
                args.append(self.advance().value)
            self.skip_semicolons()
            return CallStatement(routine_name=first_tok, arguments=tuple(args))

        # 5. RETURN
        if self.match_keyword("RETURN"):
            expr_parts = []
            while self.pos < self.length and self.current().value != ';':
                expr_parts.append(self.advance().value)
            self.skip_semicolons()
            return ReturnStatement(expression=" ".join(expr_parts) if expr_parts else None)

        # 6. DML
        first_tok = self.advance()
        upper_first = first_tok.value.upper()
        if upper_first in ("SELECT", "INSERT", "UPDATE", "DELETE", "MERGE"):
            dml_parts = [first_tok.value]
            while self.pos < self.length and self.current().value != ';':
                dml_parts.append(self.advance().value)
            self.skip_semicolons()
            return DMLStatement(dml_type=upper_first, sql=" ".join(dml_parts))

        self.skip_semicolons()
        return None

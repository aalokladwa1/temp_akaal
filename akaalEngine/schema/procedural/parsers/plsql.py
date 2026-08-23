"""
akaalEngine.schema.procedural.parsers.plsql
===========================================
Token-aware Abstract Syntax Tree parser for Oracle PL/SQL stored procedures, functions, packages, and triggers.
Explicitly avoids regex splitting on semicolons and operates on structured tokens from ProceduralLexer.
"""

from __future__ import annotations

import re
from typing import List, Optional, Tuple

from akaalEngine.schema.models.programmables import ParameterMode, RoutineKind
from akaalEngine.schema.procedural.ast_nodes import (
    AOIRNode,
    AssignmentStatement,
    AutonomousTxNode,
    BlockNode,
    CallStatement,
    CaseStatement,
    CursorCloseStatement,
    CursorDefinition,
    CursorFetchStatement,
    CursorForLoopStatement,
    CursorOpenStatement,
    DMLStatement,
    DynamicSQLNode,
    ElsifClause,
    ExceptionHandler,
    ForLoopStatement,
    IfStatement,
    LoopStatement,
    NullStatement,
    PackageAST,
    ParameterDeclaration,
    RaiseStatement,
    ReturnStatement,
    RoutineAST,
    UnsupportedConstruct,
    VariableDeclaration,
    WhenClause,
    WhileStatement,
)
from akaalEngine.schema.procedural.lexer import ProceduralLexer, Token, TokenType


class PLSQLParser:
    """Parser that transforms Oracle PL/SQL source code into an AOIR typed AST."""

    def __init__(self, sql: str):
        self.raw_sql = sql
        self.tokens: List[Token] = ProceduralLexer.tokenize(sql)
        self.pos = 0
        self.length = len(self.tokens)

    def current(self) -> Token:
        if self.pos < self.length:
            return self.tokens[self.pos]
        return self.tokens[-1]

    def peek(self, offset: int = 1) -> Token:
        target = self.pos + offset
        if target < self.length:
            return self.tokens[target]
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

    def expect_delimiter(self, delim: str) -> bool:
        if self.pos < self.length:
            tok = self.tokens[self.pos]
            if tok.value == delim:
                self.advance()
                return True
        return False

    def skip_semicolons(self) -> None:
        while self.pos < self.length and self.current().value == ';':
            self.advance()

    def parse(self) -> RoutineAST:
        """Parses procedure or function into RoutineAST."""
        # 1. Skip CREATE [OR REPLACE]
        self.match_keyword("CREATE")
        self.match_keyword("OR")
        self.match_keyword("REPLACE")

        # 2. Determine Routine Type
        if self.match_keyword("FUNCTION"):
            routine_kind = RoutineKind.FUNCTION
        elif self.match_keyword("PROCEDURE"):
            routine_kind = RoutineKind.PROCEDURE
        else:
            raise SyntaxError(f"Expected PROCEDURE or FUNCTION in PL/SQL source: '{self.raw_sql[:60]}...'")

        # 3. Routine Name
        name_tok = self.advance()
        name = name_tok.value.strip('"')

        # 4. Parameters
        parameters: List[ParameterDeclaration] = []
        if self.current().value == '(':
            self.advance()
            parameters = self._parse_parameters()
            if self.current().value == ')':
                self.advance()

        # 5. Return Type (for functions)
        return_type = None
        if routine_kind == RoutineKind.FUNCTION and self.match_keyword("RETURN"):
            ret_tok = self.advance()
            return_type = ret_tok.value
            # handle types like VARCHAR2(100)
            if self.current().value == '(':
                self.advance()
                while self.pos < self.length and self.current().value != ')':
                    self.advance()
                if self.current().value == ')':
                    self.advance()

        # 6. IS / AS
        self.match_keyword("IS", "AS")

        # 7. Declarations & Autonomous transaction check
        declarations, is_autonomous = self._parse_declarations()

        # 8. Body Block (BEGIN ... END;)
        body_block = self._parse_block(declarations=declarations)

        return RoutineAST(
            name=name,
            routine_type=routine_kind,
            parameters=tuple(parameters),
            return_type=return_type,
            body=body_block,
            is_autonomous=is_autonomous,
        )

    def _parse_parameters(self) -> List[ParameterDeclaration]:
        params = []
        while self.pos < self.length and self.current().value != ')':
            param_name = self.advance().value.strip('"')
            mode = ParameterMode.IN
            if self.match_keyword("IN", "OUT", "INOUT"):
                mode_str = self.tokens[self.pos - 1].value.upper()
                if mode_str == "IN" and self.check_keyword("OUT"):
                    self.advance()
                    mode = ParameterMode.INOUT
                elif mode_str == "OUT":
                    mode = ParameterMode.OUT
                elif mode_str == "INOUT":
                    mode = ParameterMode.INOUT

            type_name = self.advance().value
            if self.current().value == '(':
                self.advance()
                while self.pos < self.length and self.current().value != ')':
                    self.advance()
                if self.current().value == ')':
                    self.advance()

            default_val = None
            if self.match_keyword("DEFAULT") or self.current().value in (":=", "="):
                self.advance()
                val_parts = []
                while self.pos < self.length and self.current().value not in (',', ')'):
                    val_parts.append(self.advance().value)
                default_val = " ".join(val_parts)

            params.append(
                ParameterDeclaration(
                    name=param_name,
                    data_type=type_name,
                    mode=mode,
                    default_value=default_val,
                )
            )
            if self.current().value == ',':
                self.advance()
        return params

    def _parse_declarations(self) -> Tuple[List[AOIRNode], bool]:
        declarations: List[AOIRNode] = []
        is_autonomous = False

        while self.pos < self.length and not self.check_keyword("BEGIN"):
            # Check PRAGMA AUTONOMOUS_TRANSACTION
            if self.match_keyword("PRAGMA"):
                if self.match_keyword("AUTONOMOUS_TRANSACTION"):
                    is_autonomous = True
                    declarations.append(AutonomousTxNode(is_autonomous=True))
                    self.skip_semicolons()
                    continue

            # Check CURSOR name IS SELECT ...
            if self.match_keyword("CURSOR"):
                cur_name = self.advance().value
                self.match_keyword("IS")
                sql_parts = []
                while self.pos < self.length and self.current().value != ';':
                    sql_parts.append(self.advance().value)
                self.skip_semicolons()
                declarations.append(
                    CursorDefinition(
                        name=cur_name,
                        query_sql=" ".join(sql_parts),
                    )
                )
                continue

            # Standard variable / constant declaration
            var_name = self.advance().value
            if var_name.upper() == "BEGIN":
                self.pos -= 1
                break

            is_constant = self.match_keyword("CONSTANT")
            type_name = self.advance().value
            if self.current().value == '(':
                self.advance()
                params = []
                while self.pos < self.length and self.current().value != ')':
                    params.append(self.advance().value)
                if self.current().value == ')':
                    self.advance()
                type_name += f"({','.join(params)})"

            default_val = None
            if self.current().value in (":=", "=") or self.match_keyword("DEFAULT"):
                if self.current().value in (":=", "="):
                    self.advance()
                val_parts = []
                while self.pos < self.length and self.current().value != ';':
                    val_parts.append(self.advance().value)
                default_val = " ".join(val_parts)

            self.skip_semicolons()
            declarations.append(
                VariableDeclaration(
                    name=var_name,
                    data_type=type_name,
                    default_value=default_val,
                    is_constant=is_constant,
                )
            )

        return declarations, is_autonomous

    def _parse_block(self, declarations: Sequence[AOIRNode] = tuple()) -> BlockNode:
        self.match_keyword("BEGIN")
        statements: List[AOIRNode] = []
        exception_handlers: List[ExceptionHandler] = []

        while self.pos < self.length and not self.check_keyword("END"):
            if self.match_keyword("EXCEPTION"):
                exception_handlers = self._parse_exception_handlers()
                break

            stmt = self._parse_statement()
            if stmt:
                statements.append(stmt)

        self.match_keyword("END")
        # Optional routine name or label after END
        if self.pos < self.length and self.current().value != ';':
            self.advance()
        self.skip_semicolons()

        return BlockNode(
            declarations=tuple(declarations),
            statements=tuple(statements),
            exception_handlers=tuple(exception_handlers),
        )

    def _parse_statement(self) -> Optional[AOIRNode]:
        if self.pos >= self.length:
            return None

        # 1. NULL;
        if self.match_keyword("NULL"):
            self.skip_semicolons()
            return NullStatement()

        # 2. IF statement
        if self.match_keyword("IF"):
            return self._parse_if_statement()

        # 3. CASE statement
        if self.match_keyword("CASE"):
            return self._parse_case_statement()

        # 4. WHILE loop
        if self.match_keyword("WHILE"):
            return self._parse_while_statement()

        # 5. FOR loop (integer or cursor)
        if self.match_keyword("FOR"):
            return self._parse_for_statement()

        # 6. Basic LOOP
        if self.match_keyword("LOOP"):
            return self._parse_loop_statement()

        # 7. Cursor OPEN / FETCH / CLOSE
        if self.match_keyword("OPEN"):
            cur_name = self.advance().value
            self.skip_semicolons()
            return CursorOpenStatement(cursor_name=cur_name)

        if self.match_keyword("FETCH"):
            cur_name = self.advance().value
            self.match_keyword("INTO")
            into_vars = []
            while self.pos < self.length and self.current().value != ';':
                v = self.advance().value
                if v != ',':
                    into_vars.append(v)
            self.skip_semicolons()
            return CursorFetchStatement(cursor_name=cur_name, target_variables=tuple(into_vars))

        if self.match_keyword("CLOSE"):
            cur_name = self.advance().value
            self.skip_semicolons()
            return CursorCloseStatement(cursor_name=cur_name)

        # 8. Dynamic SQL (EXECUTE IMMEDIATE)
        if self.match_keyword("EXECUTE"):
            if self.match_keyword("IMMEDIATE"):
                sql_expr_tok = self.advance()
                into_vars = []
                using_vars = []
                if self.match_keyword("INTO"):
                    while self.pos < self.length and self.current().value not in (';', 'USING'):
                        v = self.advance().value
                        if v != ',':
                            into_vars.append(v)
                if self.match_keyword("USING"):
                    while self.pos < self.length and self.current().value != ';':
                        v = self.advance().value
                        if v != ',':
                            using_vars.append(v)
                self.skip_semicolons()
                return DynamicSQLNode(
                    sql_expression=sql_expr_tok.value,
                    into_variables=tuple(into_vars),
                    using_variables=tuple(using_vars),
                )

        # 9. RETURN statement
        if self.match_keyword("RETURN"):
            expr_parts = []
            while self.pos < self.length and self.current().value != ';':
                expr_parts.append(self.advance().value)
            self.skip_semicolons()
            return ReturnStatement(expression=" ".join(expr_parts) if expr_parts else None)

        # 10. RAISE statement
        if self.match_keyword("RAISE"):
            exc_name = self.advance().value if self.current().value != ';' else None
            self.skip_semicolons()
            return RaiseStatement(exception_name=exc_name)

        # 11. RAISE_APPLICATION_ERROR
        if self.current().value.upper() == "RAISE_APPLICATION_ERROR":
            self.advance()
            if self.current().value == '(':
                self.advance()
            code_parts = []
            while self.pos < self.length and self.current().value != ',':
                code_parts.append(self.advance().value)
            if self.current().value == ',':
                self.advance()
            msg_parts = []
            while self.pos < self.length and self.current().value != ')':
                msg_parts.append(self.advance().value)
            if self.current().value == ')':
                self.advance()
            self.skip_semicolons()
            code_val = "".join(code_parts)
            msg_val = " ".join(msg_parts).strip("'\"")
            try:
                code_int = int(code_val)
            except ValueError:
                code_int = -20000
            return RaiseStatement(error_code=code_int, message=msg_val)

        # 12. DML or Assignment or Procedure Call
        first_tok = self.advance()

        # Check Assignment: target := expr;
        if self.current().value == ":=":
            self.advance()
            expr_parts = []
            while self.pos < self.length and self.current().value != ';':
                expr_parts.append(self.advance().value)
            self.skip_semicolons()
            return AssignmentStatement(target=first_tok.value, expression=" ".join(expr_parts))

        # Check DML: SELECT ... INTO ..., INSERT, UPDATE, DELETE, MERGE
        upper_first = first_tok.value.upper()
        if upper_first in ("SELECT", "INSERT", "UPDATE", "DELETE", "MERGE"):
            dml_parts = [first_tok.value]
            into_vars = []
            while self.pos < self.length and self.current().value != ';':
                tok = self.advance()
                if tok.value.upper() == "INTO" and upper_first == "SELECT":
                    # Capture SELECT INTO variables
                    dml_parts.append(tok.value)
                    while self.pos < self.length and self.current().value.upper() != "FROM" and self.current().value != ';':
                        v = self.advance().value
                        dml_parts.append(v)
                        if v != ',':
                            into_vars.append(v)
                else:
                    dml_parts.append(tok.value)
            self.skip_semicolons()
            return DMLStatement(
                dml_type=upper_first,
                sql=" ".join(dml_parts),
                into_variables=tuple(into_vars),
            )

        # Fallback Procedure Call: name(args);
        args = []
        if self.current().value == '(':
            self.advance()
            while self.pos < self.length and self.current().value != ')':
                v = self.advance().value
                if v != ',':
                    args.append(v)
            if self.current().value == ')':
                self.advance()
        self.skip_semicolons()
        return CallStatement(routine_name=first_tok.value, arguments=tuple(args))

    def _parse_if_statement(self) -> IfStatement:
        # Collect condition until THEN
        cond_parts = []
        while self.pos < self.length and not self.check_keyword("THEN"):
            cond_parts.append(self.advance().value)
        self.match_keyword("THEN")

        then_stmts = []
        while self.pos < self.length and not self.check_keyword("ELSIF", "ELSE", "END"):
            stmt = self._parse_statement()
            if stmt:
                then_stmts.append(stmt)

        elsifs: List[ElsifClause] = []
        while self.match_keyword("ELSIF"):
            e_cond_parts = []
            while self.pos < self.length and not self.check_keyword("THEN"):
                e_cond_parts.append(self.advance().value)
            self.match_keyword("THEN")
            e_stmts = []
            while self.pos < self.length and not self.check_keyword("ELSIF", "ELSE", "END"):
                stmt = self._parse_statement()
                if stmt:
                    e_stmts.append(stmt)
            elsifs.append(ElsifClause(condition=" ".join(e_cond_parts), statements=tuple(e_stmts)))

        else_stmts = []
        if self.match_keyword("ELSE"):
            while self.pos < self.length and not self.check_keyword("END"):
                stmt = self._parse_statement()
                if stmt:
                    else_stmts.append(stmt)

        self.match_keyword("END")
        self.match_keyword("IF")
        self.skip_semicolons()

        return IfStatement(
            condition=" ".join(cond_parts),
            then_statements=tuple(then_stmts),
            elsif_clauses=tuple(elsifs),
            else_statements=tuple(else_stmts),
        )

    def _parse_case_statement(self) -> CaseStatement:
        expr_parts = []
        while self.pos < self.length and not self.check_keyword("WHEN"):
            expr_parts.append(self.advance().value)

        when_clauses: List[WhenClause] = []
        while self.match_keyword("WHEN"):
            w_cond = []
            while self.pos < self.length and not self.check_keyword("THEN"):
                w_cond.append(self.advance().value)
            self.match_keyword("THEN")
            w_stmts = []
            while self.pos < self.length and not self.check_keyword("WHEN", "ELSE", "END"):
                stmt = self._parse_statement()
                if stmt:
                    w_stmts.append(stmt)
            when_clauses.append(WhenClause(condition=" ".join(w_cond), statements=tuple(w_stmts)))

        else_stmts = []
        if self.match_keyword("ELSE"):
            while self.pos < self.length and not self.check_keyword("END"):
                stmt = self._parse_statement()
                if stmt:
                    else_stmts.append(stmt)

        self.match_keyword("END")
        self.match_keyword("CASE")
        self.skip_semicolons()

        return CaseStatement(
            expression=" ".join(expr_parts) if expr_parts else None,
            when_clauses=tuple(when_clauses),
            else_statements=tuple(else_stmts),
        )

    def _parse_while_statement(self) -> WhileStatement:
        cond_parts = []
        while self.pos < self.length and not self.check_keyword("LOOP"):
            cond_parts.append(self.advance().value)
        self.match_keyword("LOOP")

        stmts = []
        while self.pos < self.length and not self.check_keyword("END"):
            stmt = self._parse_statement()
            if stmt:
                stmts.append(stmt)

        self.match_keyword("END")
        self.match_keyword("LOOP")
        self.skip_semicolons()

        return WhileStatement(
            condition=" ".join(cond_parts),
            statements=tuple(stmts),
        )

    def _parse_for_statement(self) -> AOIRNode:
        iter_name = self.advance().value
        self.match_keyword("IN")
        is_reverse = self.match_keyword("REVERSE")

        # Check if cursor for loop or range for loop
        if self.current().value == '(':
            # Cursor FOR loop
            query_parts = []
            self.advance()
            paren_count = 1
            while self.pos < self.length and paren_count > 0:
                tok = self.advance()
                if tok.value == '(':
                    paren_count += 1
                elif tok.value == ')':
                    paren_count -= 1
                if paren_count > 0:
                    query_parts.append(tok.value)
            self.match_keyword("LOOP")
            stmts = []
            while self.pos < self.length and not self.check_keyword("END"):
                stmt = self._parse_statement()
                if stmt:
                    stmts.append(stmt)
            self.match_keyword("END")
            self.match_keyword("LOOP")
            self.skip_semicolons()
            return CursorForLoopStatement(
                record_name=iter_name,
                cursor_or_query=" ".join(query_parts),
                statements=tuple(stmts),
            )
        else:
            # Integer Range FOR loop: lower..upper
            lower_tok = self.advance().value
            self.expect_delimiter("..")
            upper_tok = self.advance().value
            self.match_keyword("LOOP")
            stmts = []
            while self.pos < self.length and not self.check_keyword("END"):
                stmt = self._parse_statement()
                if stmt:
                    stmts.append(stmt)
            self.match_keyword("END")
            self.match_keyword("LOOP")
            self.skip_semicolons()
            return ForLoopStatement(
                iterator_name=iter_name,
                lower_bound=lower_tok,
                upper_bound=upper_tok,
                is_reverse=is_reverse,
                statements=tuple(stmts),
            )

    def _parse_loop_statement(self) -> LoopStatement:
        stmts = []
        while self.pos < self.length and not self.check_keyword("END"):
            stmt = self._parse_statement()
            if stmt:
                stmts.append(stmt)
        self.match_keyword("END")
        self.match_keyword("LOOP")
        self.skip_semicolons()
        return LoopStatement(statements=tuple(stmts))

    def _parse_exception_handlers(self) -> List[ExceptionHandler]:
        handlers: List[ExceptionHandler] = []
        while self.match_keyword("WHEN"):
            exc_names = []
            while self.pos < self.length and not self.check_keyword("THEN"):
                v = self.advance().value
                if v.upper() != "OR":
                    exc_names.append(v.upper())
            self.match_keyword("THEN")
            stmts = []
            while self.pos < self.length and not self.check_keyword("WHEN", "END"):
                stmt = self._parse_statement()
                if stmt:
                    stmts.append(stmt)
            handlers.append(ExceptionHandler(exception_names=tuple(exc_names), statements=tuple(stmts)))
        return handlers

"""
Akaal — Oracle PL/SQL Procedure Parser
======================================
Parses Oracle PL/SQL procedure DDL into the neutral AOIR representation.
"""

from typing import List, Tuple, Optional
from akaal.core.conversion.api.aoir import (
    AOIRNode,
    RoutineKind,
    ParameterMode,
    SourceLocation,
    ParsedTokenRange,
    RoutineParameter,
    ExceptionHandler,
    CursorDefinition,
    DynamicSQLNode,
    DependencyReference,
    UnsupportedConstruct,
    VolatilitySemantics,
    SecurityExecutionContext
)
from akaal.core.conversion.internal.parser.base import Token, TokenType, Tokenizer, ParserBase

class ProcedureParser(ParserBase):
    def __init__(self, source_text: str):
        tokenizer = Tokenizer(source_text)
        tokens = tokenizer.tokenize()
        super().__init__(tokens, source_text)
        self.diagnostics_log: List[str] = []

    def parse_routine(self) -> AOIRNode:
        # Check optional CREATE OR REPLACE
        self.match(TokenType.KEYWORD, "CREATE")
        self.match(TokenType.KEYWORD, "OR")
        self.match(TokenType.KEYWORD, "REPLACE")

        start_tok = self.expect(TokenType.KEYWORD, "PROCEDURE", "Missing PROCEDURE keyword")
        name_tok = self.expect(TokenType.IDENTIFIER, err_msg="Missing procedure name")
        proc_name = name_tok.value

        # Parse parameter list
        parameters = []
        if self.match(TokenType.DELIMITER, "("):
            while True:
                p_name_tok = self.expect(TokenType.IDENTIFIER, err_msg="Expected parameter name")
                
                # Mode parsing
                mode = ParameterMode.IN
                if self.peek().type == TokenType.KEYWORD:
                    kw = self.peek().value.upper()
                    if kw == "IN":
                        self.consume()
                        if self.peek().type == TokenType.KEYWORD and self.peek().value.upper() == "OUT":
                            self.consume()
                            mode = ParameterMode.INOUT
                        else:
                            mode = ParameterMode.IN
                    elif kw == "OUT":
                        self.consume()
                        mode = ParameterMode.OUT
                    elif kw == "INOUT":
                        self.consume()
                        mode = ParameterMode.INOUT

                # Data type parsing
                p_type_tok = self.expect(TokenType.IDENTIFIER, err_msg="Expected parameter data type")
                p_type = p_type_tok.value
                # Handle types like VARCHAR2(100) or NUMBER(10,2)
                if self.match(TokenType.DELIMITER, "("):
                    p_type += "("
                    while self.peek().type != TokenType.DELIMITER or self.peek().value != ")":
                        p_type += self.consume().value
                    p_type += self.expect(TokenType.DELIMITER, ")").value

                # Default value parsing
                default_expr = None
                if self.match(TokenType.KEYWORD, "DEFAULT") or self.match(TokenType.OPERATOR, ":="):
                    # Consume expression until comma or closing parenthesis
                    expr_tokens = []
                    paren_depth = 0
                    while self.peek().type != TokenType.EOF:
                        tok = self.peek()
                        if tok.type == TokenType.DELIMITER and tok.value in ("(", ")"):
                            if tok.value == "(":
                                paren_depth += 1
                            elif tok.value == ")":
                                paren_depth -= 1
                                if paren_depth < 0:
                                    break
                        elif tok.type == TokenType.DELIMITER and tok.value == "," and paren_depth == 0:
                            break
                        elif tok.type == TokenType.DELIMITER and tok.value == ")" and paren_depth == 0:
                            break
                        expr_tokens.append(self.consume().value)
                    default_expr = " ".join(expr_tokens)

                p_range = self.get_source_range(p_name_tok, p_type_tok)
                parameters.append(RoutineParameter(
                    name=p_name_tok.value,
                    data_type=p_type,
                    mode=mode,
                    source_range=p_range,
                    default_expression=default_expr
                ))

                if self.match(TokenType.DELIMITER, ","):
                    continue
                else:
                    self.expect(TokenType.DELIMITER, ")", "Expected closing parenthesis for parameters")
                    break

        signature_end = self.peek()
        # Expect IS or AS keyword
        if not (self.match(TokenType.KEYWORD, "IS") or self.match(TokenType.KEYWORD, "AS")):
            raise ValueError(f"Expected IS or AS after procedure signature, got: {signature_end}")

        sig_range = self.get_source_range(start_tok, signature_end)

        # Local variables and cursors
        local_vars = []
        cursors = []
        unsupported = []
        dependencies = []
        exception_handlers = []
        dynamic_sqls = []

        # Parse local declarations block until BEGIN
        while self.peek().type != TokenType.KEYWORD or self.peek().value.upper() != "BEGIN":
            if self.peek().type == TokenType.EOF:
                raise ValueError("Unexpected EOF before BEGIN block")

            # Check for CURSOR
            if self.match(TokenType.KEYWORD, "CURSOR"):
                c_name_tok = self.expect(TokenType.IDENTIFIER, err_msg="Expected cursor name")
                self.expect(TokenType.KEYWORD, "IS", "Expected IS keyword in cursor declaration")
                
                # Consume SELECT query until semicolon
                select_start = self.peek()
                select_end = select_start
                while self.peek().type != TokenType.EOF and (self.peek().type != TokenType.DELIMITER or self.peek().value != ";"):
                    select_end = self.consume()
                self.expect(TokenType.DELIMITER, ";")
                
                c_range = self.get_source_range(select_start, select_end)
                cursors.append(CursorDefinition(
                    name=c_name_tok.value,
                    select_query_range=c_range,
                    is_scrollable=False
                ))
                continue

            # Check for PRAGMA
            if self.match(TokenType.KEYWORD, "PRAGMA"):
                p_name_tok = self.expect(TokenType.IDENTIFIER, err_msg="Expected pragma name")
                if p_name_tok.value.upper() == "AUTONOMOUS_TRANSACTION":
                    # Handled in transaction analyzer
                    pass
                self.match(TokenType.DELIMITER, ";")
                continue

            # Default to local variable declaration
            v_name_tok = self.consume()
            if v_name_tok.type != TokenType.IDENTIFIER:
                # If we encounter an unexpected token, log recovery and proceed
                self.diagnostics_log.append(f"Unexpected token in local declaration block: {v_name_tok.value}")
                continue

            # Expect data type
            v_type_tok = self.expect(TokenType.IDENTIFIER, err_msg="Expected variable data type")
            v_type = v_type_tok.value
            if self.match(TokenType.DELIMITER, "("):
                v_type += "("
                while self.peek().type != TokenType.DELIMITER or self.peek().value != ")":
                    v_type += self.consume().value
                v_type += self.expect(TokenType.DELIMITER, ")").value

            # Optional default expression
            v_default = None
            if self.match(TokenType.KEYWORD, "DEFAULT") or self.match(TokenType.OPERATOR, ":="):
                expr_tokens = []
                while self.peek().type != TokenType.EOF and (self.peek().type != TokenType.DELIMITER or self.peek().value != ";"):
                    expr_tokens.append(self.consume().value)
                v_default = " ".join(expr_tokens)

            self.expect(TokenType.DELIMITER, ";")

            local_vars.append(RoutineParameter(
                name=v_name_tok.value,
                data_type=v_type,
                mode=ParameterMode.IN,
                source_range=self.get_source_range(v_name_tok, v_type_tok),
                default_expression=v_default
            ))

        body_start = self.expect(TokenType.KEYWORD, "BEGIN")
        
        # Parse body and extract dependencies / dynamic SQL nodes / exception handlers
        paren_depth = 0
        block_depth = 1  # Standard procedure body block
        body_tokens = []

        while self.peek().type != TokenType.EOF:
            tok = self.peek()
            val_upper = tok.value.upper()

            if tok.type == TokenType.KEYWORD:
                if val_upper == "BEGIN":
                    block_depth += 1
                elif val_upper == "END":
                    block_depth -= 1
                    if block_depth == 0:
                        # Reached main END of procedure
                        self.consume()
                        # Match optional procedure name and final semicolon
                        self.match(TokenType.IDENTIFIER, proc_name)
                        self.match(TokenType.DELIMITER, ";")
                        break
                elif val_upper == "EXECUTE":
                    # Dynamic SQL EXECUTE IMMEDIATE checking
                    next_tok = self.peek(1)
                    if next_tok and next_tok.value.upper() == "IMMEDIATE":
                        exec_tok = self.consume()
                        imm_tok = self.consume()
                        
                        # Consume string expression until semicolon
                        expr_start = self.peek()
                        expr_end = expr_start
                        while self.peek().type != TokenType.EOF and (self.peek().type != TokenType.DELIMITER or self.peek().value != ";"):
                            expr_end = self.consume()
                        
                        dynamic_sqls.append(DynamicSQLNode(
                            query_expression_range=self.get_source_range(expr_start, expr_end),
                            using_parameters=()
                        ))
                        continue
            elif tok.type == TokenType.IDENTIFIER:
                # Dependency extraction: any qualified identifier or uppercase reference (e.g. PKG_NAME.PROC_NAME)
                # represents a routine dependency. We exclude parameter/local variable names.
                is_dependency = True
                # Case-insensitive matches against parameters/local variables
                all_local_names = {p.name.upper() for p in parameters} | {v.name.upper() for v in local_vars}
                if val_upper in all_local_names:
                    is_dependency = False
                
                # Exclude SQL functions or keywords that are tokenized as identifiers
                if val_upper in ("RAISE", "INSERT", "UPDATE", "DELETE", "SELECT", "INTO", "FROM", "WHERE", "NULL", "TRUE", "FALSE"):
                    is_dependency = False

                if is_dependency:
                    # Capture qualified chain if exists (e.g. SCHEMA.OBJECT)
                    dep_start = tok
                    dep_name = tok.value
                    self.consume()
                    while self.match(TokenType.DELIMITER, "."):
                        dep_name += "." + self.expect(TokenType.IDENTIFIER).value
                    dep_end = self.tokens[self.pos - 1]
                    
                    dependencies.append(DependencyReference(
                        object_name=dep_name,
                        object_type="UNKNOWN",
                        source_range=self.get_source_range(dep_start, dep_end)
                    ))
                    continue

            body_tokens.append(self.consume())

        body_end = self.tokens[self.pos - 1] if self.pos > 0 else body_start
        body_range = self.get_source_range(body_start, body_end)

        return AOIRNode(
            name=proc_name,
            kind=RoutineKind.PROCEDURE,
            signature_range=sig_range,
            body_range=body_range,
            parameters=tuple(parameters),
            return_spec=None,
            local_variables=tuple(local_vars),
            exception_handlers=tuple(exception_handlers),
            cursors=tuple(cursors),
            dynamic_sql_nodes=tuple(dynamic_sqls),
            dependencies=tuple(dependencies),
            control_flow=None,
            unsupported_constructs=tuple(unsupported),
            volatility=VolatilitySemantics.VOLATILE,
            security_context=SecurityExecutionContext.INVOKER,
            source_text=self.source_text
        )

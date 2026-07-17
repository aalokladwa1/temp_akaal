from typing import List, Tuple, Optional
from akaal.core.conversion.api.aoir import (
    AOIRNode,
    RoutineKind,
    ParameterMode,
    SourceLocation,
    ParsedTokenRange,
    RoutineParameter,
    ReturnSpecification,
    ExceptionHandler,
    CursorDefinition,
    DynamicSQLNode,
    DependencyReference,
    UnsupportedConstruct,
    VolatilitySemantics,
    SecurityExecutionContext
)
from akaal.core.conversion.internal.parser.base import Token, TokenType, Tokenizer, ParserBase

class RoutineParser(ParserBase):
    def __init__(self, source_text: str, source_dialect: str = "oracle", target_dialect: str = "postgresql"):
        tokenizer = Tokenizer(source_text)
        tokens = tokenizer.tokenize()
        super().__init__(tokens, source_text)
        self.diagnostics_log: List[str] = []
        self.source_dialect = source_dialect
        self.target_dialect = target_dialect

    def parse_routine(self) -> AOIRNode:
        # Check optional CREATE OR REPLACE
        self.match(TokenType.KEYWORD, "CREATE")
        self.match(TokenType.KEYWORD, "OR")
        self.match(TokenType.KEYWORD, "REPLACE")

        kind = RoutineKind.PROCEDURE
        start_tok = self.peek()
        
        if self.match(TokenType.KEYWORD, "PROCEDURE"):
            kind = RoutineKind.PROCEDURE
        elif self.match(TokenType.KEYWORD, "FUNCTION"):
            kind = RoutineKind.FUNCTION
        else:
            raise ValueError(f"Expected PROCEDURE or FUNCTION keyword, got: {start_tok.value}")

        name_tok = self.expect(TokenType.IDENTIFIER, err_msg="Missing routine name")
        routine_name = name_tok.value

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
                if self.match(TokenType.DELIMITER, "("):
                    p_type += "("
                    while self.peek().type != TokenType.DELIMITER or self.peek().value != ")":
                        p_type += self.consume().value
                    p_type += self.expect(TokenType.DELIMITER, ")").value

                # Default value
                default_expr = None
                if self.match(TokenType.KEYWORD, "DEFAULT") or self.match(TokenType.OPERATOR, ":="):
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

        return_spec = None
        if kind == RoutineKind.FUNCTION:
            self.expect(TokenType.KEYWORD, "RETURN", "Missing RETURN keyword for Function")
            ret_type_tok = self.expect(TokenType.IDENTIFIER, err_msg="Expected return type")
            ret_type = ret_type_tok.value
            if self.match(TokenType.DELIMITER, "("):
                ret_type += "("
                while self.peek().type != TokenType.DELIMITER or self.peek().value != ")":
                    ret_type += self.consume().value
                ret_type += self.expect(TokenType.DELIMITER, ")").value
            
            return_spec = ReturnSpecification(
                data_type=ret_type,
                is_table_type=False,
                source_range=self.get_source_range(ret_type_tok, ret_type_tok)
            )

        signature_end = self.peek()
        if not (self.match(TokenType.KEYWORD, "IS") or self.match(TokenType.KEYWORD, "AS")):
            raise ValueError(f"Expected IS or AS after routine signature, got: {signature_end.value}")

        sig_range = self.get_source_range(start_tok, signature_end)

        # Local variables and cursors
        local_vars = []
        cursors = []
        unsupported = []
        dependencies = []
        exception_handlers = []
        dynamic_sqls = []

        while self.peek().type != TokenType.KEYWORD or self.peek().value.upper() != "BEGIN":
            if self.peek().type == TokenType.EOF:
                raise ValueError("Unexpected EOF before BEGIN block")

            # Check for CURSOR
            if self.match(TokenType.KEYWORD, "CURSOR"):
                c_name_tok = self.expect(TokenType.IDENTIFIER, err_msg="Expected cursor name")
                self.expect(TokenType.KEYWORD, "IS", "Expected IS keyword in cursor declaration")
                
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
                self.match(TokenType.DELIMITER, ";")
                continue

            # Variable declaration
            v_name_tok = self.consume()
            if v_name_tok.type != TokenType.IDENTIFIER:
                self.diagnostics_log.append(f"Unexpected token in local declaration: {v_name_tok.value}")
                continue

            v_type_tok = self.expect(TokenType.IDENTIFIER, err_msg="Expected variable data type")
            v_type = v_type_tok.value
            if self.match(TokenType.DELIMITER, "("):
                v_type += "("
                while self.peek().type != TokenType.DELIMITER or self.peek().value != ")":
                    v_type += self.consume().value
                v_type += self.expect(TokenType.DELIMITER, ")").value

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
        block_depth = 1
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
                        self.consume()
                        self.match(TokenType.IDENTIFIER, routine_name)
                        self.match(TokenType.DELIMITER, ";")
                        break
                elif val_upper == "EXECUTE":
                    next_tok = self.peek(1)
                    if next_tok and next_tok.value.upper() == "IMMEDIATE":
                        self.consume()
                        self.consume()
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
                is_dependency = True
                all_local_names = {p.name.upper() for p in parameters} | {v.name.upper() for v in local_vars}
                if val_upper in all_local_names:
                    is_dependency = False
                if val_upper in ("RAISE", "INSERT", "UPDATE", "DELETE", "SELECT", "INTO", "FROM", "WHERE", "NULL", "TRUE", "FALSE", "RETURN"):
                    is_dependency = False

                if is_dependency:
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
            name=routine_name,
            kind=kind,
            signature_range=sig_range,
            body_range=body_range,
            parameters=tuple(parameters),
            return_spec=return_spec,
            local_variables=tuple(local_vars),
            exception_handlers=tuple(exception_handlers),
            cursors=tuple(cursors),
            dynamic_sql_nodes=tuple(dynamic_sqls),
            dependencies=tuple(dependencies),
            control_flow=None,
            unsupported_constructs=tuple(unsupported),
            volatility=VolatilitySemantics.VOLATILE,
            security_context=SecurityExecutionContext.INVOKER,
            source_text=self.source_text,
            aoir_version="1.0.0",
            source_dialect=self.source_dialect,
            target_dialect=self.target_dialect,
            routine_type=kind.value
        )

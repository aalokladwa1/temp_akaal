from typing import List
from akaal.core.conversion.api.aoir import AOIRNode, ParameterMode, RoutineKind
from akaal.core.conversion.internal.renderer.base import BaseRoutineRenderer
from akaal.core.conversion.internal.procedure.rules import ProcedureRuleRegistry
from akaal.core.conversion.internal.parser.base import Token, TokenType, Tokenizer

class PostgreSQLRoutineRenderer(BaseRoutineRenderer):
    def render(self) -> str:
        # Build parameter string
        params_list = []
        for p in self.aoir.parameters:
            mode_str = ""
            if p.mode == ParameterMode.OUT:
                mode_str = "OUT "
            elif p.mode == ParameterMode.INOUT:
                mode_str = "INOUT "
            
            target_type = ProcedureRuleRegistry.map_datatype(p.data_type)
            p_str = f"{p.name} {mode_str}{target_type}"
            if p.default_expression:
                p_str += f" DEFAULT {p.default_expression}"
            params_list.append(p_str)
        
        params_decl = ", ".join(params_list)

        # Assemble DDL signature
        if self.aoir.kind == RoutineKind.FUNCTION:
            ret_type = "VOID"
            if self.aoir.return_spec:
                ret_type = ProcedureRuleRegistry.map_datatype(self.aoir.return_spec.data_type)
            sql = f"CREATE OR REPLACE FUNCTION {self.aoir.name}({params_decl}) RETURNS {ret_type}\n"
        else:
            sql = f"CREATE OR REPLACE PROCEDURE {self.aoir.name}({params_decl})\n"
        
        # Declare section
        sql += "LANGUAGE plpgsql\nAS $$\n"
        if self.aoir.local_variables or self.aoir.cursors:
            sql += "DECLARE\n"
            for v in self.aoir.local_variables:
                v_type = ProcedureRuleRegistry.map_datatype(v.data_type)
                default_str = f" := {v.default_expression}" if v.default_expression else ""
                sql += f"    {v.name} {v_type}{default_str};\n"
            for c in self.aoir.cursors:
                sql += f"    {c.name} CURSOR FOR {c.select_query_range.raw_text};\n"

        sql += "BEGIN\n"
        
        # Body translation
        body_sql = self._translate_body()
        sql += body_sql
        
        # Main exception handlers (if any)
        if self.aoir.exception_handlers:
            sql += "EXCEPTION\n"
            for h in self.aoir.exception_handlers:
                sql += f"    WHEN {h.exception_name} THEN\n"
                sql += f"        {h.handler_body_range.raw_text};\n"

        sql += "END;\n$$;"
        return sql

    def _translate_body(self) -> str:
        raw_body = self.aoir.body_range.raw_text
        tokenizer = Tokenizer(raw_body)
        tokens = tokenizer.tokenize()
        
        output = []
        idx = 0
        limit = len(tokens)
        
        if limit > 0 and tokens[0].value.upper() == "BEGIN":
            idx = 1
            
        while idx < limit:
            t = tokens[idx]
            val_upper = t.value.upper()

            # Translate dynamic functions
            if t.type == TokenType.IDENTIFIER and val_upper == "DBMS_OUTPUT":
                if idx + 2 < limit and tokens[idx + 1].value == "." and tokens[idx + 2].value.upper() == "PUT_LINE":
                    output.append("RAISE NOTICE")
                    idx += 3
                    continue
            
            # Map Oracle datatype keywords in statements
            if t.type == TokenType.KEYWORD and val_upper in ProcedureRuleRegistry.TYPE_MAP:
                output.append(ProcedureRuleRegistry.map_datatype(t.value))
                idx += 1
                continue

            # Standard tokens
            if t.type == TokenType.COMMENT:
                output.append(t.value)
            else:
                output.append(t.value)
            idx += 1

        body_text = ""
        last_was_newline = True
        prev_part = ""
        for part in output:
            if part == ";":
                body_text += ";\n"
                last_was_newline = True
                prev_part = ";"
            elif part.startswith("--") or part.startswith("/*"):
                body_text += "    " + part + "\n"
                last_was_newline = True
                prev_part = part
            elif part == "\n":
                body_text += "\n"
                last_was_newline = True
                prev_part = "\n"
            else:
                if last_was_newline:
                    body_text += "    "
                    last_was_newline = False
                else:
                    needs_space = True
                    if part in (".", "(", ")", ",", "||", "|") or prev_part in (".", "(", "||", "|"):
                        needs_space = False
                    if needs_space:
                        body_text += " "
                body_text += part
                prev_part = part

        return body_text

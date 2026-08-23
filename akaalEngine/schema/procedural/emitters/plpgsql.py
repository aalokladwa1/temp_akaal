"""
akaalEngine.schema.procedural.emitters.plpgsql
=============================================
PL/pgSQL target code generator from typed AOIR AST nodes.
Produces syntax-exact PostgreSQL functions and procedures with error handling and variable declarations.
"""

from __future__ import annotations

from typing import List, Tuple

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
    ExceptionHandler,
    ForLoopStatement,
    IfStatement,
    LoopStatement,
    NullStatement,
    RaiseStatement,
    ReturnStatement,
    RoutineAST,
    UnsupportedConstruct,
    VariableDeclaration,
    WhileStatement,
)
from akaalEngine.schema.procedural.diagnostics import (
    ConversionState,
    ProceduralConversionResult,
    ProceduralDiagnostic,
)
from akaalEngine.schema.procedural.transforms.exceptions import ExceptionTransformer


class PLpgSQLEmitter:
    """Emits syntax-exact PostgreSQL PL/pgSQL code from RoutineAST."""

    @classmethod
    def emit_routine(cls, ast: RoutineAST, schema_name: str = "public") -> ProceduralConversionResult:
        diagnostics: List[ProceduralDiagnostic] = []
        required_helpers: List[str] = []

        if ast.is_autonomous:
            diagnostics.append(
                ProceduralDiagnostic(
                    severity="WARNING",
                    category="AUTONOMOUS_TRANSACTION",
                    message="PRAGMA AUTONOMOUS_TRANSACTION detected: PostgreSQL functions execute in current transaction. Use dblink or pg_background for isolated commits.",
                    suggested_remediation="Consider using dblink_connect / dblink_exec if isolated transaction commits are mandatory.",
                )
            )

        # 1. Signature & Parameters
        param_defs = []
        out_params = []
        for p in ast.parameters:
            mode_str = ""
            if p.mode == ParameterMode.OUT:
                mode_str = "OUT "
                out_params.append(p)
            elif p.mode == ParameterMode.INOUT:
                mode_str = "INOUT "
            
            p_type = cls._map_datatype(p.data_type)
            default_str = f" DEFAULT {p.default_value}" if p.default_value else ""
            param_defs.append(f"{mode_str}{p.name} {p_type}{default_str}")

        qual_name = f'"{schema_name}"."{ast.name}"' if schema_name else f'"{ast.name}"'
        sig_str = f"({', '.join(param_defs)})"

        # 2. Return Type
        if ast.routine_type == RoutineKind.FUNCTION:
            ret_type = cls._map_datatype(ast.return_type or "VOID")
            header = f"CREATE OR REPLACE FUNCTION {qual_name}{sig_str}\nRETURNS {ret_type}\nLANGUAGE plpgsql\nAS $$"
        else:
            header = f"CREATE OR REPLACE PROCEDURE {qual_name}{sig_str}\nLANGUAGE plpgsql\nAS $$"

        # 3. DECLARE Section
        declare_lines = []
        for d in ast.body.declarations:
            if isinstance(d, VariableDeclaration):
                v_type = cls._map_datatype(d.data_type)
                const_str = "CONSTANT " if d.is_constant else ""
                def_str = f" := {d.default_value}" if d.default_value else ""
                declare_lines.append(f"    {d.name} {const_str}{v_type}{def_str};")
            elif isinstance(d, CursorDefinition):
                declare_lines.append(f"    {d.name} CURSOR FOR {d.query_sql};")

        # 4. Statements Section
        body_lines = []
        for stmt in ast.body.statements:
            stmt_sql = cls._emit_statement(stmt, indent_level=1)
            body_lines.append(stmt_sql)

        # 5. EXCEPTION Section
        exception_lines = []
        if ast.body.exception_handlers:
            exception_lines.append("EXCEPTION")
            for h in ast.body.exception_handlers:
                transformed_h = ExceptionTransformer.transform_handler(h)
                exc_str = " OR ".join(transformed_h.exception_names)
                exception_lines.append(f"    WHEN {exc_str} THEN")
                for s in transformed_h.statements:
                    exception_lines.append(cls._emit_statement(s, indent_level=2))

        # Assemble Complete Function
        parts = [header]
        if declare_lines:
            parts.append("DECLARE")
            parts.extend(declare_lines)

        parts.append("BEGIN")
        if body_lines:
            parts.extend(body_lines)
        else:
            parts.append("    NULL;")

        if exception_lines:
            parts.extend(exception_lines)

        parts.append("END;\n$$;")
        full_sql = "\n".join(parts)

        # State evaluation
        has_warnings = any(d.severity in ("WARNING", "MANUAL_INTERVENTION") for d in diagnostics)
        state = ConversionState.MANUAL_REVIEW_REQUIRED if has_warnings else ConversionState.TRANSPILED

        return ProceduralConversionResult(
            routine_name=ast.name,
            target_engine="POSTGRESQL",
            state=state,
            target_sql=full_sql,
            diagnostics=tuple(diagnostics),
            required_compat_helpers=tuple(required_helpers),
        )

    @classmethod
    def _emit_statement(cls, node: AOIRNode, indent_level: int = 1) -> str:
        indent = "    " * indent_level

        if isinstance(node, NullStatement):
            return f"{indent}NULL;"

        elif isinstance(node, AssignmentStatement):
            return f"{indent}{node.target} := {node.expression};"

        elif isinstance(node, ReturnStatement):
            if node.expression:
                return f"{indent}RETURN {node.expression};"
            return f"{indent}RETURN;"

        elif isinstance(node, CallStatement):
            args_str = f"({', '.join(node.arguments)})" if node.arguments else "()"
            return f"{indent}CALL {node.routine_name}{args_str};"

        elif isinstance(node, RaiseStatement):
            if node.message:
                return f"{indent}RAISE EXCEPTION '{node.message}';"
            elif node.exception_name:
                return f"{indent}RAISE EXCEPTION '%', '{node.exception_name}';"
            return f"{indent}RAISE;"

        elif isinstance(node, IfStatement):
            lines = [f"{indent}IF {node.condition} THEN"]
            for s in node.then_statements:
                lines.append(cls._emit_statement(s, indent_level + 1))
            for e in node.elsif_clauses:
                lines.append(f"{indent}ELSIF {e.condition} THEN")
                for s in e.statements:
                    lines.append(cls._emit_statement(s, indent_level + 1))
            if node.else_statements:
                lines.append(f"{indent}ELSE")
                for s in node.else_statements:
                    lines.append(cls._emit_statement(s, indent_level + 1))
            lines.append(f"{indent}END IF;")
            return "\n".join(lines)

        elif isinstance(node, CaseStatement):
            expr_str = f" {node.expression}" if node.expression else ""
            lines = [f"{indent}CASE{expr_str}"]
            for w in node.when_clauses:
                lines.append(f"{indent}    WHEN {w.condition} THEN")
                for s in w.statements:
                    lines.append(cls._emit_statement(s, indent_level + 2))
            if node.else_statements:
                lines.append(f"{indent}    ELSE")
                for s in node.else_statements:
                    lines.append(cls._emit_statement(s, indent_level + 2))
            lines.append(f"{indent}END CASE;")
            return "\n".join(lines)

        elif isinstance(node, WhileStatement):
            lines = [f"{indent}WHILE {node.condition} LOOP"]
            for s in node.statements:
                lines.append(cls._emit_statement(s, indent_level + 1))
            lines.append(f"{indent}END LOOP;")
            return "\n".join(lines)

        elif isinstance(node, ForLoopStatement):
            rev_str = "REVERSE " if node.is_reverse else ""
            lines = [f"{indent}FOR {node.iterator_name} IN {rev_str}{node.lower_bound}..{node.upper_bound} LOOP"]
            for s in node.statements:
                lines.append(cls._emit_statement(s, indent_level + 1))
            lines.append(f"{indent}END LOOP;")
            return "\n".join(lines)

        elif isinstance(node, CursorForLoopStatement):
            lines = [f"{indent}FOR {node.record_name} IN ({node.cursor_or_query}) LOOP"]
            for s in node.statements:
                lines.append(cls._emit_statement(s, indent_level + 1))
            lines.append(f"{indent}END LOOP;")
            return "\n".join(lines)

        elif isinstance(node, LoopStatement):
            lines = [f"{indent}LOOP"]
            for s in node.statements:
                lines.append(cls._emit_statement(s, indent_level + 1))
            lines.append(f"{indent}END LOOP;")
            return "\n".join(lines)

        elif isinstance(node, CursorOpenStatement):
            return f"{indent}OPEN {node.cursor_name};"

        elif isinstance(node, CursorFetchStatement):
            vars_str = ", ".join(node.target_variables)
            return f"{indent}FETCH {node.cursor_name} INTO {vars_str};"

        elif isinstance(node, CursorCloseStatement):
            return f"{indent}CLOSE {node.cursor_name};"

        elif isinstance(node, DynamicSQLNode):
            into_str = f" INTO {', '.join(node.into_variables)}" if node.into_variables else ""
            using_str = f" USING {', '.join(node.using_variables)}" if node.using_variables else ""
            return f"{indent}EXECUTE {node.sql_expression}{into_str}{using_str};"

        elif isinstance(node, DMLStatement):
            sql_clean = node.sql.strip().rstrip(';')
            return f"{indent}{sql_clean};"

        elif isinstance(node, BlockNode):
            lines = [f"{indent}BEGIN"]
            for s in node.statements:
                lines.append(cls._emit_statement(s, indent_level + 1))
            lines.append(f"{indent}END;")
            return "\n".join(lines)

        return f"{indent}-- Unsupported or unhandled construct;"

    @staticmethod
    def _map_datatype(type_str: str) -> str:
        t = type_str.strip().upper()
        if "VARCHAR2" in t or "NVARCHAR2" in t:
            return t.replace("VARCHAR2", "VARCHAR").replace("NVARCHAR2", "VARCHAR")
        elif t == "NUMBER":
            return "NUMERIC"
        elif "NUMBER" in t:
            return t.replace("NUMBER", "NUMERIC")
        elif t in ("INT", "INTEGER", "BINARY_INTEGER", "PLS_INTEGER"):
            return "INTEGER"
        elif t == "CLOB":
            return "TEXT"
        elif t == "BLOB":
            return "BYTEA"
        elif t == "DATE":
            return "TIMESTAMP"
        elif t == "BOOLEAN":
            return "BOOLEAN"
        return type_str

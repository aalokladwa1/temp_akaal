"""
AKAAL PL/SQL Transpiler — PL/pgSQL Code Generator
===================================================
Generates clean, executable PostgreSQL PL/pgSQL DDL statements from AST structures.
"""

from akaal.transpiler.ast.nodes import (
    ProcedureNode,
    FunctionNode,
    TriggerNode,
    PackageNode,
)
from akaal.transpiler.rules.builtin_rules import BuiltinRulesEngine


class PLpgSQLGenerator:
    """Generates PostgreSQL DDL statements."""

    @staticmethod
    def generate_procedure(node: ProcedureNode) -> str:
        param_strs = []
        for p in node.parameters:
            mode_str = f"{p.mode} " if p.mode != "IN" else ""
            param_strs.append(f"{p.name} {mode_str}{p.data_type}")
        params_decl = ", ".join(param_strs)

        var_strs = [f"    {v.name} {v.data_type};" for v in node.variables]
        vars_decl = "\n".join(var_strs) if var_strs else "    -- No local variables"

        body_lines = []
        for stmt in node.body_statements:
            translated = BuiltinRulesEngine.translate_expression(stmt)
            if not translated.endswith(';'):
                translated += ';'
            body_lines.append(f"    {translated}")
        body_code = "\n".join(body_lines) if body_lines else "    NULL;"

        sql = f"""CREATE OR REPLACE PROCEDURE {node.name.lower()}({params_decl})
LANGUAGE plpgsql
AS $$
DECLARE
{vars_decl}
BEGIN
{body_code}
END;
$$;"""
        return sql

    @staticmethod
    def generate_function(node: FunctionNode) -> str:
        param_strs = [f"{p.name} {p.data_type}" for p in node.parameters]
        params_decl = ", ".join(param_strs)

        var_strs = [f"    {v.name} {v.data_type};" for v in node.variables]
        vars_decl = "\n".join(var_strs) if var_strs else "    -- No local variables"

        body_lines = []
        for stmt in node.body_statements:
            translated = BuiltinRulesEngine.translate_expression(stmt)
            if not translated.endswith(';'):
                translated += ';'
            body_lines.append(f"    {translated}")
        body_code = "\n".join(body_lines) if body_lines else "    RETURN NULL;"

        sql = f"""CREATE OR REPLACE FUNCTION {node.name.lower()}({params_decl})
RETURNS {node.return_type}
LANGUAGE plpgsql
AS $$
DECLARE
{vars_decl}
BEGIN
{body_code}
END;
$$;"""
        return sql

    @staticmethod
    def generate_trigger(node: TriggerNode) -> str:
        func_name = f"fn_trig_{node.name.lower()}"
        events_str = " OR ".join(node.events)

        body_lines = []
        for stmt in node.body_statements:
            translated = BuiltinRulesEngine.translate_expression(stmt)
            # Replace :NEW / :OLD bind variables with NEW / OLD
            translated = translated.replace(":NEW.", "NEW.").replace(":OLD.", "OLD.")
            if not translated.endswith(';'):
                translated += ';'
            body_lines.append(f"    {translated}")
        body_code = "\n".join(body_lines) if body_lines else "    RETURN NEW;"

        if "RETURN" not in body_code:
            body_code += "\n    RETURN NEW;"

        func_sql = f"""CREATE OR REPLACE FUNCTION {func_name}()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
{body_code}
END;
$$;"""

        trig_sql = f"""CREATE OR REPLACE TRIGGER trg_{node.name.lower()}
{node.timing} {events_str} ON {node.table_name.lower()}
FOR EACH ROW
EXECUTE FUNCTION {func_name}();"""

        return f"{func_sql}\n\n{trig_sql}"

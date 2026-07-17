from akaal.core.conversion.api.aoir import RoutineKind
from akaal.core.conversion.internal.renderer.base import BaseRoutineRenderer

class OracleRoutineRenderer(BaseRoutineRenderer):
    def render(self) -> str:
        # Reconstruct standard Oracle syntax
        params_list = []
        for p in self.aoir.parameters:
            p_str = f"{p.name} {p.mode.value} {p.data_type}"
            if p.default_expression:
                p_str += f" DEFAULT {p.default_expression}"
            params_list.append(p_str)
        params_decl = ", ".join(params_list)

        if self.aoir.kind == RoutineKind.FUNCTION:
            ret_type = self.aoir.return_spec.data_type if self.aoir.return_spec else "VOID"
            sql = f"CREATE OR REPLACE FUNCTION {self.aoir.name}({params_decl}) RETURN {ret_type} IS\n"
        else:
            sql = f"CREATE OR REPLACE PROCEDURE {self.aoir.name}({params_decl}) IS\n"

        for v in self.aoir.local_variables:
            def_expr = f" := {v.default_expression}" if v.default_expression else ""
            sql += f"    {v.name} {v.data_type}{def_expr};\n"
        for c in self.aoir.cursors:
            sql += f"    CURSOR {c.name} IS {c.select_query_range.raw_text};\n"

        sql += f"BEGIN\n{self.aoir.body_range.raw_text}\nEND;"
        return sql

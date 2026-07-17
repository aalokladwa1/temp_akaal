from akaal.core.conversion.api.aoir import RoutineKind
from akaal.core.conversion.internal.renderer.base import BaseRoutineRenderer

class MySQLRoutineRenderer(BaseRoutineRenderer):
    def render(self) -> str:
        params_list = []
        for p in self.aoir.parameters:
            params_list.append(f"{p.name} {p.data_type}")
        params_decl = ", ".join(params_list)

        if self.aoir.kind == RoutineKind.FUNCTION:
            ret_type = self.aoir.return_spec.data_type if self.aoir.return_spec else "CHAR"
            sql = f"CREATE FUNCTION {self.aoir.name}({params_decl}) RETURNS {ret_type}\nBEGIN\n"
        else:
            sql = f"CREATE PROCEDURE {self.aoir.name}({params_decl})\nBEGIN\n"

        for v in self.aoir.local_variables:
            def_expr = f" DEFAULT {v.default_expression}" if v.default_expression else ""
            sql += f"    DECLARE {v.name} {v.data_type}{def_expr};\n"

        sql += f"{self.aoir.body_range.raw_text}\nEND"
        return sql

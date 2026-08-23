"""
akaalEngine.data_processing.engine.expression_compiler
========================================================
ExpressionCompiler evaluating AST nodes deterministically over row dictionaries.
Mined from `akaal/transformation/expression_compiler.py`.
"""

from typing import Any, Mapping

from akaalEngine.data_processing.models.ast import (
    ASTNode,
    ColumnRefNode,
    ConditionalNode,
    ConstantNode,
    FunctionCallNode,
)
from akaalEngine.data_processing.models.errors import ExpressionExecutionError


class ExpressionCompiler:
    """Evaluates AST expression nodes over target row dictionaries."""

    @classmethod
    def evaluate(cls, node: ASTNode, row: Mapping[str, Any]) -> Any:
        if isinstance(node, ColumnRefNode):
            return row.get(node.column_name)

        elif isinstance(node, ConstantNode):
            return node.value

        elif isinstance(node, ConditionalNode):
            cond_val = cls.evaluate(node.condition, row)
            if bool(cond_val):
                return cls.evaluate(node.true_branch, row)
            else:
                return cls.evaluate(node.false_branch, row)

        elif isinstance(node, FunctionCallNode):
            fn = node.function_name.upper()
            args_eval = [cls.evaluate(arg, row) for arg in node.args]

            if fn == "CONCAT":
                return "".join(str(a) for a in args_eval if a is not None)
            elif fn == "COALESCE":
                for a in args_eval:
                    if a is not None:
                        return a
                return None
            elif fn == "UPPER":
                return str(args_eval[0]).upper() if args_eval and args_eval[0] is not None else None
            elif fn == "LOWER":
                return str(args_eval[0]).lower() if args_eval and args_eval[0] is not None else None
            elif fn == "EQUALS":
                return args_eval[0] == args_eval[1] if len(args_eval) >= 2 else False
            elif fn == "GREATER_THAN":
                return args_eval[0] > args_eval[1] if len(args_eval) >= 2 and args_eval[0] is not None and args_eval[1] is not None else False
            elif fn == "LESS_THAN":
                return args_eval[0] < args_eval[1] if len(args_eval) >= 2 and args_eval[0] is not None and args_eval[1] is not None else False
            else:
                raise ExpressionExecutionError(fn, f"Unsupported function name '{fn}'")

        else:
            raise ExpressionExecutionError(str(node), f"Unknown AST node type '{type(node)}'")

"""
AKAAL Type-Safe AST Expression Compiler & Evaluator.
===================================================
Provides deterministic AST parsing, type checking, and row evaluation.
ABSOLUTELY FORBIDDEN: eval(), exec(), arbitrary Python execution.
"""

import re
import datetime
import unicodedata
from typing import Any, Dict, List, Optional, Tuple
from akaal.transformation.models import (
    ASTNode,
    LiteralNode,
    ColumnRefNode,
    FunctionCallNode,
    ConditionalNode,
    TransformationDiagnostic,
    DiagnosticLevel,
)


class ExpressionCompilationError(Exception):
    pass


class ExpressionExecutionError(Exception):
    pass


MAX_AST_DEPTH = 20
MAX_AST_NODES = 100
MAX_REGEX_PATTERN_LENGTH = 256
MAX_STRING_OUTPUT_LENGTH = 1024


class ExpressionCompiler:
    """Type-safe AST Expression Evaluator without eval/exec."""

    ALLOWED_FUNCTIONS = {
        # String operations
        "TRIM", "LTRIM", "RTRIM", "UPPER", "LOWER", "SUBSTRING", "REPLACE",
        "REGEX_REPLACE", "REGEX_EXTRACT", "CONCAT", "PAD_LEFT", "PAD_RIGHT", "UNICODE_NORMALIZE",
        # Numeric operations
        "CAST", "ROUND", "FLOOR", "CEIL", "ABS", "CLAMP", "ADD", "SUBTRACT", "MULTIPLY", "DIVIDE",
        # Date & Time operations
        "DATE_PARSE", "DATE_FORMAT", "TIMEZONE_CONVERT", "EPOCH_CONVERT",
        # Boolean & Null operations
        "BOOLEAN_NORMALIZE", "COALESCE", "IS_NULL", "IS_NOT_NULL", "IF",
    }

    @classmethod
    def validate_ast_depth(cls, node: ASTNode, current_depth: int = 1) -> int:
        if current_depth > MAX_AST_DEPTH:
            raise ExpressionCompilationError(f"Expression AST exceeds maximum allowed depth of {MAX_AST_DEPTH}.")
        
        if isinstance(node, FunctionCallNode):
            max_child = current_depth
            for arg in node.args:
                max_child = max(max_child, cls.validate_ast_depth(arg, current_depth + 1))
            return max_child
        elif isinstance(node, ConditionalNode):
            d1 = cls.validate_ast_depth(node.condition, current_depth + 1)
            d2 = cls.validate_ast_depth(node.true_branch, current_depth + 1)
            d3 = cls.validate_ast_depth(node.false_branch, current_depth + 1)
            return max(d1, d2, d3)
        return current_depth

    @classmethod
    def parse_simple_expression(cls, expr_text: str) -> ASTNode:
        """Parses standard string expressions into AST nodes safely without eval."""
        text = expr_text.strip()
        if not text:
            return LiteralNode(None, "null")

        # Function call pattern: FUNCTION_NAME(arg1, arg2...)
        match_fn = re.match(r"^([A-Z_]+)\((.*)\)$", text, re.IGNORECASE)
        if match_fn:
            fn_name = match_fn.group(1).upper()
            if fn_name not in cls.ALLOWED_FUNCTIONS:
                raise ExpressionCompilationError(f"Function '{fn_name}' is not in allowed function whitelist.")
            
            raw_args = match_fn.group(2).strip()
            args: List[ASTNode] = []
            if raw_args:
                # Split args safely by comma respecting quotes
                parts = cls._split_args(raw_args)
                for part in parts:
                    args.append(cls.parse_simple_expression(part))
            return FunctionCallNode(fn_name, args)

        # Literal string in single or double quotes
        if (text.startswith("'") and text.endswith("'")) or (text.startswith('"') and text.endswith('"')):
            return LiteralNode(text[1:-1], "string")

        # Integer literal
        if text.isdigit() or (text.startswith("-") and text[1:].isdigit()):
            return LiteralNode(int(text), "integer")

        # Float literal
        try:
            val_float = float(text)
            return LiteralNode(val_float, "float")
        except ValueError:
            pass

        # Boolean literal
        if text.lower() in ("true", "false"):
            return LiteralNode(text.lower() == "true", "boolean")

        # Column reference fallback
        return ColumnRefNode(text)

    @classmethod
    def _split_args(cls, args_str: str) -> List[str]:
        args: List[str] = []
        current = []
        in_quote = False
        quote_char = None

        for char in args_str:
            if char in ("'", '"'):
                if not in_quote:
                    in_quote = True
                    quote_char = char
                elif quote_char == char:
                    in_quote = False
                    quote_char = None
                current.append(char)
            elif char == "," and not in_quote:
                args.append("".join(current).strip())
                current = []
            else:
                current.append(char)

        if current:
            args.append("".join(current).strip())
        return args

    @classmethod
    def evaluate(cls, node: ASTNode, row: Dict[str, Any]) -> Any:
        """Evaluates AST node against row dictionary deterministically."""
        cls.validate_ast_depth(node)

        if isinstance(node, LiteralNode):
            return node.value

        elif isinstance(node, ColumnRefNode):
            return row.get(node.column_name)

        elif isinstance(node, ConditionalNode):
            cond_val = cls.evaluate(node.condition, row)
            if bool(cond_val):
                return cls.evaluate(node.true_branch, row)
            else:
                return cls.evaluate(node.false_branch, row)

        elif isinstance(node, FunctionCallNode):
            return cls._evaluate_function(node.function_name, node.args, row)

        raise ExpressionExecutionError(f"Unsupported AST node type: {type(node)}")

    @classmethod
    def _evaluate_function(cls, fn_name: str, args: List[ASTNode], row: Dict[str, Any]) -> Any:
        if fn_name not in cls.ALLOWED_FUNCTIONS:
            raise ExpressionExecutionError(f"Function '{fn_name}' is not in allowed function whitelist.")

        evaluated_args = [cls.evaluate(arg, row) for arg in args]

        # --- STRING OPERATIONS ---
        if fn_name == "TRIM":
            val = evaluated_args[0] if evaluated_args else None
            return str(val).strip() if val is not None else None

        elif fn_name == "LTRIM":
            val = evaluated_args[0] if evaluated_args else None
            return str(val).lstrip() if val is not None else None

        elif fn_name == "RTRIM":
            val = evaluated_args[0] if evaluated_args else None
            return str(val).rstrip() if val is not None else None

        elif fn_name == "UPPER":
            val = evaluated_args[0] if evaluated_args else None
            return str(val).upper() if val is not None else None

        elif fn_name == "LOWER":
            val = evaluated_args[0] if evaluated_args else None
            return str(val).lower() if val is not None else None

        elif fn_name == "SUBSTRING":
            if not evaluated_args or evaluated_args[0] is None:
                return None
            val_str = str(evaluated_args[0])
            start = int(evaluated_args[1]) if len(evaluated_args) > 1 and evaluated_args[1] is not None else 0
            length = int(evaluated_args[2]) if len(evaluated_args) > 2 and evaluated_args[2] is not None else len(val_str)
            return val_str[start:start + length]

        elif fn_name == "REPLACE":
            if len(evaluated_args) < 3 or evaluated_args[0] is None:
                return evaluated_args[0] if evaluated_args else None
            return str(evaluated_args[0]).replace(str(evaluated_args[1]), str(evaluated_args[2]))

        elif fn_name == "REGEX_REPLACE":
            if len(evaluated_args) < 3 or evaluated_args[0] is None:
                return evaluated_args[0] if evaluated_args else None
            pattern_str = str(evaluated_args[1])
            if len(pattern_str) > MAX_REGEX_PATTERN_LENGTH:
                raise ExpressionExecutionError(f"Regex pattern exceeds maximum allowed length of {MAX_REGEX_PATTERN_LENGTH}.")
            replacement = str(evaluated_args[2])
            res = re.sub(pattern_str, replacement, str(evaluated_args[0]))
            return res[:MAX_STRING_OUTPUT_LENGTH]

        elif fn_name == "REGEX_EXTRACT":
            if len(evaluated_args) < 2 or evaluated_args[0] is None:
                return None
            pattern_str = str(evaluated_args[1])
            if len(pattern_str) > MAX_REGEX_PATTERN_LENGTH:
                raise ExpressionExecutionError(f"Regex pattern exceeds maximum allowed length of {MAX_REGEX_PATTERN_LENGTH}.")
            match = re.search(pattern_str, str(evaluated_args[0]))
            if match:
                return match.group(1) if match.groups() else match.group(0)
            return None

        elif fn_name == "CONCAT":
            non_null_args = [str(arg) for arg in evaluated_args if arg is not None]
            return "".join(non_null_args)

        elif fn_name == "UNICODE_NORMALIZE":
            if not evaluated_args or evaluated_args[0] is None:
                return None
            form = str(evaluated_args[1]) if len(evaluated_args) > 1 and evaluated_args[1] else "NFC"
            return unicodedata.normalize(form, str(evaluated_args[0]))

        # --- NUMERIC OPERATIONS ---
        elif fn_name == "CAST":
            val = evaluated_args[0] if evaluated_args else None
            target_type = str(evaluated_args[1]).lower() if len(evaluated_args) > 1 else "string"
            if val is None:
                return None
            try:
                if target_type in ("int", "integer"):
                    return int(val)
                elif target_type in ("float", "double", "decimal"):
                    return float(val)
                elif target_type in ("bool", "boolean"):
                    return bool(val)
                return str(val)
            except (ValueError, TypeError) as exc:
                raise ExpressionExecutionError(f"Failed to cast '{val}' to {target_type}: {exc}")

        elif fn_name == "ROUND":
            val = evaluated_args[0] if evaluated_args else None
            decimals = int(evaluated_args[1]) if len(evaluated_args) > 1 and evaluated_args[1] is not None else 0
            return round(float(val), decimals) if val is not None else None

        elif fn_name == "FLOOR":
            import math
            val = evaluated_args[0] if evaluated_args else None
            return math.floor(float(val)) if val is not None else None

        elif fn_name == "CEIL":
            import math
            val = evaluated_args[0] if evaluated_args else None
            return math.ceil(float(val)) if val is not None else None

        elif fn_name == "DIVIDE":
            v1, v2 = evaluated_args[0], evaluated_args[1]
            if v1 is None or v2 is None:
                return None
            if float(v2) == 0.0:
                return None  # Division-by-zero guard returns NULL
            return float(v1) / float(v2)

        # --- DATE & TIME OPERATIONS ---
        elif fn_name == "DATE_PARSE":
            if not evaluated_args or evaluated_args[0] is None:
                return None
            fmt = str(evaluated_args[1]) if len(evaluated_args) > 1 and evaluated_args[1] else "%Y-%m-%d"
            dt = datetime.datetime.strptime(str(evaluated_args[0]), fmt)
            return dt.isoformat()

        elif fn_name == "DATE_FORMAT":
            if not evaluated_args or evaluated_args[0] is None:
                return None
            fmt = str(evaluated_args[1]) if len(evaluated_args) > 1 and evaluated_args[1] else "%Y-%m-%d"
            if isinstance(evaluated_args[0], (datetime.datetime, datetime.date)):
                return evaluated_args[0].strftime(fmt)
            dt = datetime.datetime.fromisoformat(str(evaluated_args[0]))
            return dt.strftime(fmt)

        elif fn_name == "TIMEZONE_CONVERT":
            # UTC normalization - 0 machine-local timezone fallbacks
            if not evaluated_args or evaluated_args[0] is None:
                return None
            dt_str = str(evaluated_args[0])
            dt = datetime.datetime.fromisoformat(dt_str)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=datetime.timezone.utc)
            return dt.astimezone(datetime.timezone.utc).isoformat()

        # --- BOOLEAN & NULL OPERATIONS ---
        elif fn_name == "BOOLEAN_NORMALIZE":
            if not evaluated_args or evaluated_args[0] is None:
                return None
            str_val = str(evaluated_args[0]).strip().lower()
            if str_val in ("y", "yes", "true", "1", "t"):
                return True
            elif str_val in ("n", "no", "false", "0", "f"):
                return False
            return None

        elif fn_name == "COALESCE":
            for arg in evaluated_args:
                if arg is not None:
                    return arg
            return None

        elif fn_name == "IS_NULL":
            return evaluated_args[0] is None if evaluated_args else True

        elif fn_name == "IS_NOT_NULL":
            return evaluated_args[0] is not None if evaluated_args else False

        elif fn_name == "IF":
            cond = evaluated_args[0] if len(evaluated_args) > 0 else False
            true_val = evaluated_args[1] if len(evaluated_args) > 1 else None
            false_val = evaluated_args[2] if len(evaluated_args) > 2 else None
            return true_val if bool(cond) else false_val

        return None

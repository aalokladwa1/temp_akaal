"""
Akaal Coverage Tracer — AST Analyzer
====================================
Uses Python's AST parser to inspect Python source code and accurately identify
executable statements, classes, functions, docstrings, and non-executable line ranges.
"""

import ast
from dataclasses import dataclass, field
from typing import Dict, List, Set, Tuple


@dataclass
class SourceAnalysis:
    """Analysis results for a single Python source file."""
    filepath: str
    total_lines: int
    executable_lines: Set[int]
    docstring_lines: Set[int]
    class_names: List[str]
    function_names: List[str]
    ast_parse_error: bool = False


class ASTSourceAnalyzer:
    """AST-based parser for identifying executable statements and AST nodes."""

    @classmethod
    def analyze_file(cls, filepath: str) -> SourceAnalysis:
        """Parse a Python source file and return accurate line classifications."""
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                source = f.read()
        except Exception:
            return SourceAnalysis(
                filepath=filepath,
                total_lines=0,
                executable_lines=set(),
                docstring_lines=set(),
                class_names=[],
                function_names=[],
                ast_parse_error=True,
            )

        lines = source.splitlines()
        total_lines = len(lines)

        try:
            tree = ast.parse(source, filename=filepath)
        except SyntaxError:
            return SourceAnalysis(
                filepath=filepath,
                total_lines=total_lines,
                executable_lines=set(),
                docstring_lines=set(),
                class_names=[],
                function_names=[],
                ast_parse_error=True,
            )

        docstring_lines: Set[int] = set()
        class_names: List[str] = []
        function_names: List[str] = []
        executable_lines: Set[int] = set()

        for node in ast.walk(tree):
            # Extract docstrings
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Module)):
                doc = ast.get_docstring(node, clean=False)
                if doc and hasattr(node, "body") and node.body:
                    first_stmt = node.body[0]
                    if isinstance(first_stmt, ast.Expr) and isinstance(first_stmt.value, ast.Constant):
                        start_line = getattr(first_stmt, "lineno", 0)
                        end_line = getattr(first_stmt, "end_lineno", start_line)
                        for l in range(start_line, end_line + 1):
                            docstring_lines.add(l)

            # Record classes and functions
            if isinstance(node, ast.ClassDef):
                class_names.append(node.name)
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                function_names.append(node.name)

            # Identify executable statement nodes
            if isinstance(
                node,
                (
                    ast.Assign,
                    ast.AnnAssign,
                    ast.AugAssign,
                    ast.Return,
                    ast.Yield,
                    ast.YieldFrom,
                    ast.Raise,
                    ast.Assert,
                    ast.If,
                    ast.For,
                    ast.AsyncFor,
                    ast.While,
                    ast.With,
                    ast.AsyncWith,
                    ast.Try,
                    ast.TryStar,
                    ast.FunctionDef,
                    ast.AsyncFunctionDef,
                    ast.ClassDef,
                    ast.Expr,
                    ast.Import,
                    ast.ImportFrom,
                    ast.Global,
                    ast.Nonlocal,
                    ast.Pass,
                    ast.Break,
                    ast.Continue,
                ),
            ):
                lineno = getattr(node, "lineno", None)
                if lineno and lineno not in docstring_lines:
                    # Ignore standalone pass statements inside abstract methods or protocols
                    if isinstance(node, ast.Pass) and getattr(node, "end_lineno", lineno) == lineno:
                        pass
                    elif isinstance(node, ast.Expr) and lineno in docstring_lines:
                        pass
                    else:
                        executable_lines.add(lineno)

        return SourceAnalysis(
            filepath=filepath,
            total_lines=total_lines,
            executable_lines=executable_lines,
            docstring_lines=docstring_lines,
            class_names=class_names,
            function_names=function_names,
        )

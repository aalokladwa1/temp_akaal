"""
akaalEngine.schema.procedural.transforms.cursors
================================================
Transforms explicit static cursors, parameterized cursors, and fetch statements.
"""

from __future__ import annotations

from akaalEngine.schema.procedural.ast_nodes import (
    CursorCloseStatement,
    CursorDefinition,
    CursorFetchStatement,
    CursorForLoopStatement,
    CursorOpenStatement,
)


class CursorTransformer:
    """Transforms cursor constructs into target-compatible AST nodes."""

    @classmethod
    def transform_definition(cls, node: CursorDefinition) -> CursorDefinition:
        return node

    @classmethod
    def transform_open(cls, node: CursorOpenStatement) -> CursorOpenStatement:
        return node

    @classmethod
    def transform_fetch(cls, node: CursorFetchStatement) -> CursorFetchStatement:
        return node

    @classmethod
    def transform_close(cls, node: CursorCloseStatement) -> CursorCloseStatement:
        return node

"""
akaalEngine.schema.core.memoization
===================================
Compiled rule index and immutable memoization engine for type normalization, dialect translation, and AST caching.
"""

from __future__ import annotations

import hashlib
from typing import Any, Dict, Optional, Tuple

from akaalEngine.schema.models.types import CanonicalType, TargetTypeEmission
from akaalEngine.schema.procedural.ast_nodes import RoutineAST


class CompiledRuleIndexMemoizationEngine:
    """Thread-safe, process-local immutable memoization engine with clearable caches for isolation."""

    def __init__(self):
        self._type_norm_cache: Dict[Tuple[str, str, Optional[int], Optional[int], Optional[int]], CanonicalType] = {}
        self._type_emit_cache: Dict[Tuple[str, str], TargetTypeEmission] = {}
        self._dialect_cache: Dict[Tuple[str, str, str], str] = {}
        self._ast_cache: Dict[str, RoutineAST] = {}

    def get_normalized_type(
        self,
        provider: str,
        raw_type: str,
        length: Optional[int],
        precision: Optional[int],
        scale: Optional[int],
    ) -> Optional[CanonicalType]:
        key = (provider.lower(), raw_type.upper(), length, precision, scale)
        return self._type_norm_cache.get(key)

    def put_normalized_type(
        self,
        provider: str,
        raw_type: str,
        length: Optional[int],
        precision: Optional[int],
        scale: Optional[int],
        ctype: CanonicalType,
    ) -> None:
        key = (provider.lower(), raw_type.upper(), length, precision, scale)
        self._type_norm_cache[key] = ctype

    def get_translated_expression(self, expr: str, src_dialect: str, tgt_dialect: str) -> Optional[str]:
        key = (src_dialect.upper(), tgt_dialect.upper(), expr)
        return self._dialect_cache.get(key)

    def put_translated_expression(self, expr: str, src_dialect: str, tgt_dialect: str, translated: str) -> None:
        key = (src_dialect.upper(), tgt_dialect.upper(), expr)
        self._dialect_cache[key] = translated

    def get_parsed_ast(self, sql: str) -> Optional[RoutineAST]:
        h = hashlib.sha256(sql.encode("utf-8")).hexdigest()
        return self._ast_cache.get(h)

    def put_parsed_ast(self, sql: str, ast: RoutineAST) -> None:
        h = hashlib.sha256(sql.encode("utf-8")).hexdigest()
        self._ast_cache[h] = ast

    def clear(self) -> None:
        """Clears all caches to ensure test isolation."""
        self._type_norm_cache.clear()
        self._type_emit_cache.clear()
        self._dialect_cache.clear()
        self._ast_cache.clear()


# Default singleton memoization engine
default_memoization_engine = CompiledRuleIndexMemoizationEngine()

"""
akaalEngine.schema.core.memoization
===================================
Compiled rule index and immutable memoization engine for type normalization, dialect translation, and AST caching.
"""

from __future__ import annotations

import hashlib
import threading
from typing import Any, Dict, Optional, Tuple

from akaalEngine.schema.models.types import CanonicalType, TargetTypeEmission
from akaalEngine.schema.procedural.ast_nodes import RoutineAST


class CompiledRuleIndexMemoizationEngine:
    """Thread-safe, process-local immutable memoization engine with clearable caches for isolation."""

    def __init__(self):
        self._lock = threading.RLock()
        self._rule_generation: int = 1
        self._type_norm_cache: Dict[Tuple[str, str, Optional[int], Optional[int], Optional[int], bool, bool, bool, int], CanonicalType] = {}
        self._type_emit_cache: Dict[Tuple[str, str, str, Optional[int], Optional[int], Optional[int], int], TargetTypeEmission] = {}
        self._dialect_cache: Dict[Tuple[str, str, str, int], str] = {}
        self._ast_cache: Dict[Tuple[str, str, str, int], RoutineAST] = {}

    @property
    def rule_generation(self) -> int:
        with self._lock:
            return self._rule_generation

    def bump_generation(self) -> None:
        with self._lock:
            self._rule_generation += 1
            self.clear()

    def get_normalized_type(
        self,
        provider: str,
        raw_type: str,
        length: Optional[int] = None,
        precision: Optional[int] = None,
        scale: Optional[int] = None,
        byte_semantics: bool = False,
        is_signed: bool = True,
        is_timezone_aware: bool = False,
    ) -> Optional[CanonicalType]:
        key = (
            provider.lower(),
            raw_type.upper(),
            length,
            precision,
            scale,
            byte_semantics,
            is_signed,
            is_timezone_aware,
            self._rule_generation,
        )
        with self._lock:
            return self._type_norm_cache.get(key)

    def put_normalized_type(
        self,
        provider: str,
        raw_type: str,
        ctype: CanonicalType,
        length: Optional[int] = None,
        precision: Optional[int] = None,
        scale: Optional[int] = None,
        byte_semantics: bool = False,
        is_signed: bool = True,
        is_timezone_aware: bool = False,
    ) -> None:
        key = (
            provider.lower(),
            raw_type.upper(),
            length,
            precision,
            scale,
            byte_semantics,
            is_signed,
            is_timezone_aware,
            self._rule_generation,
        )
        with self._lock:
            self._type_norm_cache[key] = ctype

    def _compute_canonical_type_key(self, ctype: CanonicalType, target_engine: str) -> Tuple[Any, ...]:
        extra_items = tuple(sorted((str(k), str(v)) for k, v in ctype.extra.items())) if ctype.extra else ()
        return (
            ctype.category.value.upper(),
            ctype.raw_vendor_type.upper(),
            target_engine.upper(),
            ctype.length,
            ctype.precision,
            ctype.scale,
            ctype.bits,
            ctype.byte_semantics,
            ctype.is_signed,
            ctype.is_timezone_aware,
            ctype.dimensions,
            ctype.srid,
            ctype.array_element_type,
            extra_items,
            self._rule_generation,
        )

    def get_emitted_type(
        self,
        canonical_type: CanonicalType,
        target_engine: str,
    ) -> Optional[TargetTypeEmission]:
        key = self._compute_canonical_type_key(canonical_type, target_engine)
        with self._lock:
            return self._type_emit_cache.get(key)

    def put_emitted_type(
        self,
        canonical_type: CanonicalType,
        target_engine: str,
        emission: TargetTypeEmission,
    ) -> None:
        key = self._compute_canonical_type_key(canonical_type, target_engine)
        with self._lock:
            self._type_emit_cache[key] = emission

    def get_translated_expression(self, expr: str, src_dialect: str, tgt_dialect: str) -> Optional[str]:
        key = (src_dialect.upper(), tgt_dialect.upper(), expr, self._rule_generation)
        with self._lock:
            return self._dialect_cache.get(key)

    def put_translated_expression(self, expr: str, src_dialect: str, tgt_dialect: str, translated: str) -> None:
        key = (src_dialect.upper(), tgt_dialect.upper(), expr, self._rule_generation)
        with self._lock:
            self._dialect_cache[key] = translated

    def get_parsed_ast(self, sql: str, source_dialect: str = "PLSQL") -> Optional[RoutineAST]:
        h = hashlib.sha256(sql.encode("utf-8")).hexdigest()
        key = (source_dialect.upper(), "", h, self._rule_generation)
        with self._lock:
            return self._ast_cache.get(key)

    def put_parsed_ast(self, sql: str, ast: RoutineAST, source_dialect: str = "PLSQL") -> None:
        h = hashlib.sha256(sql.encode("utf-8")).hexdigest()
        key = (source_dialect.upper(), "", h, self._rule_generation)
        with self._lock:
            self._ast_cache[key] = ast

    def clear(self) -> None:
        """Clears all caches to ensure test isolation."""
        with self._lock:
            self._type_norm_cache.clear()
            self._type_emit_cache.clear()
            self._dialect_cache.clear()
            self._ast_cache.clear()


# Default singleton memoization engine
default_memoization_engine = CompiledRuleIndexMemoizationEngine()

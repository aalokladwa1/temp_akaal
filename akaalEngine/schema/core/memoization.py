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


def _compute_type_signature(ctype: Any) -> Tuple[Any, ...]:
    """Recursively computes a strictly hashable tuple signature for CanonicalType and nested types."""
    if ctype is None:
        return ()
    if isinstance(ctype, str):
        return ("RAW_STR", ctype.upper())
    if hasattr(ctype, "category") and hasattr(ctype, "raw_vendor_type"):
        extra_items = tuple(sorted((str(k), str(v)) for k, v in ctype.extra.items())) if ctype.extra else ()
        elem_sig = _compute_type_signature(ctype.array_element_type) if ctype.array_element_type else ()
        return (
            ctype.category.value.upper(),
            ctype.raw_vendor_type.upper(),
            ctype.length,
            ctype.precision,
            ctype.scale,
            ctype.bits,
            ctype.byte_semantics,
            ctype.is_signed,
            ctype.is_timezone_aware,
            ctype.dimensions,
            ctype.srid,
            elem_sig,
            extra_items,
        )
    return ("OTHER", str(ctype))


class CompiledRuleIndexMemoizationEngine:
    """Thread-safe synchronized memoization engine with generation-based invalidation."""

    def __init__(self, rule_generation: int = 1):
        self._lock = threading.RLock()
        self._rule_generation = rule_generation
        self._type_norm_cache: Dict[Tuple, CanonicalType] = {}
        self._type_emit_cache: Dict[Tuple, TargetTypeEmission] = {}
        self._dialect_cache: Dict[Tuple, str] = {}
        self._ast_cache: Dict[Tuple, RoutineAST] = {}

    @property
    def rule_generation(self) -> int:
        with self._lock:
            return self._rule_generation

    def bump_generation(self) -> int:
        with self._lock:
            self._rule_generation += 1
            self._type_norm_cache.clear()
            self._type_emit_cache.clear()
            self._dialect_cache.clear()
            self._ast_cache.clear()
            return self._rule_generation

    def clear(self) -> None:
        with self._lock:
            self._type_norm_cache.clear()
            self._type_emit_cache.clear()
            self._dialect_cache.clear()
            self._ast_cache.clear()

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
            provider.upper(),
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
            provider.upper(),
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
        sig = _compute_type_signature(ctype)
        return (target_engine.upper(), sig, self._rule_generation)

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

"""
akaalEngine.schema.core.processor
=================================
Large estate chunked schema compilation processor for SCH-069.
Enables memory-bounded chunked conversion and staged DDL processing for estates exceeding 50,000 objects.
"""

from __future__ import annotations

from collections import deque
from typing import Any, Callable, Dict, Generator, Iterator, List, Optional, Sequence, Set, Tuple

from akaalEngine.schema.ddl.emitter import DDLStage, StagedDDLPackage, StructuredDDLArtifact
from akaalEngine.schema.ddl.generator import DDLGenerator
from akaalEngine.schema.dependency.cycle_breaker import CycleBreaker
from akaalEngine.schema.dependency.graph import MultiDomainDependencyGraph
from akaalEngine.schema.dependency.sorter import TopologicalSorter
from akaalEngine.schema.mapping.engine import MappingEngine
from akaalEngine.schema.models.mapping import CompiledSchemaMapping
from akaalEngine.schema.models.schema import CanonicalSchema, CanonicalSchemaModel
from akaalEngine.schema.models.table import CanonicalTable


class LargeEstateChunkedSchemaProcessor:
    """
    Memory-bounded chunked schema compiler for enterprise estates (SCH-069).
    Splits large estates into deterministic batches (default: 500 tables) to prevent RAM explosion.
    Supports both CanonicalSchemaModel and streaming lazy table iterators.
    """

    DEFAULT_CHUNK_SIZE = 500

    @classmethod
    def build_lightweight_table_order(cls, tables: Sequence[CanonicalTable]) -> List[str]:
        """Builds a lightweight O(V+E) adjacency graph using string IDs to determine dependency order with minimal RAM."""
        adj: Dict[str, Set[str]] = {}
        in_degree: Dict[str, int] = {}
        for t in tables:
            qname = t.qualified_name.lower()
            if qname not in adj:
                adj[qname] = set()
            if qname not in in_degree:
                in_degree[qname] = 0

            for fk in t.foreign_keys:
                ref_qname = f"{fk.referenced_schema}.{fk.referenced_table}".lower()
                if ref_qname != qname:
                    if ref_qname not in adj:
                        adj[ref_qname] = set()
                    if qname not in adj[ref_qname]:
                        adj[ref_qname].add(qname)
                        in_degree[qname] = in_degree.get(qname, 0) + 1

        # Kahn's algorithm with O(1) popleft and deterministic initial order
        queue = deque(sorted(k for k, deg in in_degree.items() if deg == 0))
        sorted_keys: List[str] = []
        while queue:
            node = queue.popleft()
            sorted_keys.append(node)
            for neighbor in sorted(adj.get(node, ())):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        seen = set(sorted_keys)
        for k in sorted(in_degree.keys()):
            if k not in seen:
                sorted_keys.append(k)

        return sorted_keys

    @classmethod
    def stream_chunked_tables(
        cls,
        tables_iter: Iterator[CanonicalTable],
        chunk_size: int = DEFAULT_CHUNK_SIZE,
    ) -> Iterator[Tuple[CanonicalTable, ...]]:
        """Yields successive slices of tables from a generator or stream without materializing the whole estate."""
        chunk: List[CanonicalTable] = []
        for tbl in tables_iter:
            chunk.append(tbl)
            if len(chunk) >= chunk_size:
                yield tuple(chunk)
                chunk = []
        if chunk:
            yield tuple(chunk)

    @classmethod
    def stream_compile_estate(
        cls,
        tables_stream: Iterator[CanonicalTable],
        target_engine: str,
        target_version: Optional[str] = None,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        source_vendor: str = "GENERIC",
        mapping: Optional[CompiledSchemaMapping] = None,
    ) -> Iterator[StagedDDLPackage]:
        """Streams DDL packages chunk by chunk directly from a lazy table generator without materializing all tables."""
        chunk_idx = 0
        for table_chunk in cls.stream_chunked_tables(tables_stream, chunk_size=chunk_size):
            chunk_model = CanonicalSchemaModel(
                model_id=f"stream_chunk_{chunk_idx}",
                source_vendor=source_vendor,
                tables=table_chunk,
            )
            if mapping:
                chunk_model = MappingEngine.apply_mapping(chunk_model, mapping, target_vendor=target_engine)
            pkg = DDLGenerator.generate_ddl_package(chunk_model, target_engine, target_version)
            chunk_idx += 1
            yield pkg

    @classmethod
    def process_chunked_compilation(
        cls,
        model: CanonicalSchemaModel,
        target_engine: str,
        target_version: Optional[str] = None,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> Iterator[StagedDDLPackage]:
        """
        Streams staged DDL packages chunk by chunk in deterministic topological dependency order.
        Memory-bounded: processes table slices without duplicating full estate in DDL memory.
        """
        ordered_keys = cls.build_lightweight_table_order(model.tables)
        table_map = {t.qualified_name.lower(): t for t in model.tables}
        
        ordered_tables: List[CanonicalTable] = []
        for k in ordered_keys:
            if k in table_map:
                ordered_tables.append(table_map[k])

        seen = {t.qualified_name.lower() for t in ordered_tables}
        for t in model.tables:
            if t.qualified_name.lower() not in seen:
                ordered_tables.append(t)

        total_tables = len(ordered_tables)

        for start_idx in range(0, total_tables, chunk_size):
            end_idx = min(start_idx + chunk_size, total_tables)
            chunk_tables = ordered_tables[start_idx:end_idx]

            chunk_model = CanonicalSchemaModel(
                model_id=f"{model.model_id}_chunk_{start_idx // chunk_size}",
                source_vendor=model.source_vendor,
                source_version=model.source_version,
                schemas=model.schemas,
                tables=tuple(chunk_tables),
                views=model.views if start_idx == 0 else (),
                routines=model.routines if start_idx == 0 else (),
                packages=model.packages if start_idx == 0 else (),
                triggers=model.triggers if start_idx == 0 else (),
                sequences=model.sequences if start_idx == 0 else (),
                udts=model.udts if start_idx == 0 else (),
                synonyms=model.synonyms if start_idx == 0 else (),
            )

            chunk_package = DDLGenerator.generate_ddl_package(chunk_model, target_engine, target_version)

            if progress_callback:
                progress_callback(end_idx, total_tables)

            yield chunk_package

    @classmethod
    def compile_large_estate_package(
        cls,
        model: CanonicalSchemaModel,
        target_engine: str,
        target_version: Optional[str] = None,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        procedural_artifacts: Optional[List[StructuredDDLArtifact]] = None,
    ) -> StagedDDLPackage:
        """
        Compiles large estate in chunks and merges resulting artifacts into a single StagedDDLPackage.
        """
        all_artifacts: List[StructuredDDLArtifact] = []
        for pkg in cls.process_chunked_compilation(model, target_engine, target_version, chunk_size=chunk_size):
            all_artifacts.extend(pkg.artifacts)

        if procedural_artifacts:
            all_artifacts.extend(procedural_artifacts)

        return StagedDDLPackage(
            target_engine=target_engine.upper(),
            artifacts=tuple(all_artifacts),
        )

"""
akaalEngine.schema.core.processor
=================================
Large estate chunked schema compilation processor for SCH-069.
Enables memory-bounded chunked conversion and staged DDL processing for estates exceeding 50,000 objects.
"""

from __future__ import annotations

from typing import Any, Callable, Generator, Iterator, List, Optional, Tuple

from akaalEngine.schema.ddl.emitter import DDLStage, StagedDDLPackage, StructuredDDLArtifact
from akaalEngine.schema.ddl.generator import DDLGenerator
from akaalEngine.schema.dependency.cycle_breaker import CycleBreaker
from akaalEngine.schema.dependency.graph import MultiDomainDependencyGraph
from akaalEngine.schema.dependency.sorter import TopologicalSorter
from akaalEngine.schema.models.mapping import CompiledSchemaMapping
from akaalEngine.schema.models.schema import CanonicalSchema, CanonicalSchemaModel
from akaalEngine.schema.models.table import CanonicalTable


class LargeEstateChunkedSchemaProcessor:
    """
    Memory-bounded chunked schema compiler for enterprise estates (SCH-069).
    Splits large estates into deterministic batches (default: 500 tables) to prevent RAM explosion.
    """

    DEFAULT_CHUNK_SIZE = 500

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
        """
        # 1. First resolve overall dependency ordering across tables
        dep_graph = MultiDomainDependencyGraph.build(model)
        pruned_graph = CycleBreaker.break_fk_cycles(dep_graph)
        sorted_keys = TopologicalSorter.sort(pruned_graph)

        # Build table index
        table_map = {t.qualified_name.lower(): t for t in model.tables}
        ordered_tables: List[CanonicalTable] = []
        for k in sorted_keys:
            if k.startswith("table:") and k[6:] in table_map:
                ordered_tables.append(table_map[k[6:]])

        # Include remaining unreferenced tables
        seen = {t.qualified_name.lower() for t in ordered_tables}
        for t in model.tables:
            if t.qualified_name.lower() not in seen:
                ordered_tables.append(t)

        total_tables = len(ordered_tables)
        emitter = DDLGenerator.get_emitter(target_engine, target_version)

        # 2. Process in chunks
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

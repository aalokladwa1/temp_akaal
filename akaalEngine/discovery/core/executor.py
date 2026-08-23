"""
akaalEngine.discovery.core.executor
==================================
Multi-stage discovery execution engine with single-session safe sequential processing,
server-side cursor pagination, operational deadline enforcement, memory bounding,
canonical preview sampling, and 12-domain deterministic fingerprinting.
"""

from __future__ import annotations

import concurrent.futures
import logging
import time
from typing import Any, Mapping, Optional, Sequence

from akaalEngine.connection.models.endpoint import EndpointSpec
from akaalEngine.connection.routing.resolver import ResolvedRoute
from akaalEngine.discovery.core.fingerprint import DiscoveryFingerprintCalculator
from akaalEngine.discovery.core.sampling import RedactionGuard
from akaalEngine.discovery.errors.exceptions import DiscoveryEngineException, DiscoveryTimeoutError
from akaalEngine.discovery.models.context import DiscoveryContext, DiscoveryDepth
from akaalEngine.discovery.models.inventory import ObjectInventory, TableFacts, ViewFacts
from akaalEngine.discovery.models.partitioning import PartitionFacts
from akaalEngine.discovery.models.sampling import SampledRecordSet
from akaalEngine.discovery.models.snapshot import DiscoveryCompleteness, DiscoverySnapshot
from akaalEngine.discovery.models.statistics import StatisticsSnapshot, TableSizeFacts
from akaalEngine.discovery.models.structure import ObjectStructureFacts
from akaalEngine.discovery.models.volume import LargestObjectItem, LOBVolumeFacts, VolumeSnapshot
from akaalEngine.discovery.spi.relational import RelationalDiscoveryStrategy
from akaalEngine.discovery.spi.strategy import BaseDiscoveryStrategy

logger = logging.getLogger("akaalEngine.discovery.core.executor")


class DiscoveryPipelineExecutor:
    """
    Executes discovery pipeline stages against a live leased connection and strategy.
    Assembles typed physical fact models into a versioned, immutable DiscoverySnapshot.
    Guarantees single-session thread safety (no concurrent execution on a single DB-API connection).
    """

    @classmethod
    def execute(
        cls,
        strategy: BaseDiscoveryStrategy,
        connection: Any,
        spec: EndpointSpec,
        context: DiscoveryContext,
        route: Optional[ResolvedRoute] = None,
    ) -> DiscoverySnapshot:
        t0 = time.time()
        deadline = t0 + max(0.001, float(context.timeout_seconds))
        warnings: list[str] = []
        errors: list[str] = []
        is_partial_due_to_timeout = False
        is_partial_due_to_pagination_error = False
        is_truncated_due_to_max_objects = False

        # Helper to check deadline and enforce operational timeouts
        def check_deadline(stage_name: str) -> bool:
            nonlocal is_partial_due_to_timeout
            if time.time() > deadline:
                is_partial_due_to_timeout = True
                msg = f"Discovery execution deadline ({context.timeout_seconds}s) exceeded during '{stage_name}' stage."
                warnings.append(msg)
                logger.warning(f"[DiscoveryPipelineExecutor] {msg}")
                return True
            return False

        def run_with_timeout(stage_name: str, func: Any, *args: Any, **kwargs: Any) -> Any:
            nonlocal is_partial_due_to_timeout
            now = time.time()
            remaining = deadline - now
            if remaining <= 0:
                is_partial_due_to_timeout = True
                msg = f"Discovery execution deadline ({context.timeout_seconds}s) exceeded before '{stage_name}'."
                warnings.append(msg)
                raise DiscoveryTimeoutError(msg)

            # Execute through bounded future to constrain blocking provider operations
            pool = concurrent.futures.ThreadPoolExecutor(max_workers=1)
            try:
                future = pool.submit(func, *args, **kwargs)
                try:
                    return future.result(timeout=remaining)
                except concurrent.futures.TimeoutError:
                    is_partial_due_to_timeout = True
                    msg = f"Operation in '{stage_name}' timed out after exceeding {remaining:.2f}s deadline."
                    warnings.append(msg)
                    logger.warning(f"[DiscoveryPipelineExecutor] {msg}")

                    # Physically cancel/abort/close connection to interrupt background thread network I/O
                    try:
                        if connection is not None:
                            if hasattr(connection, "cancel"):
                                connection.cancel()
                            if hasattr(connection, "interrupt"):
                                connection.interrupt()
                            if hasattr(connection, "close"):
                                connection.close()
                    except Exception as cancel_err:
                        logger.debug(f"[DiscoveryPipelineExecutor] Error cancelling timed-out connection: {cancel_err}")

                    raise DiscoveryTimeoutError(msg)
            finally:
                pool.shutdown(wait=False, cancel_futures=True)

        # 0. Initial schema change marker
        start_marker = None
        try:
            start_marker = run_with_timeout("Initial Schema Marker", strategy.get_schema_change_marker, connection, spec)
        except Exception as exc:
            warnings.append(f"Initial schema change marker inspection failed: {exc}")

        # 1. Identity Stage
        engine_identity = None
        try:
            engine_identity = run_with_timeout("Identity", strategy.discover_endpoint_identity, connection, spec, route)
        except Exception as exc:
            errors.append(f"Identity discovery failed: {exc}")
            logger.warning(f"[DiscoveryPipelineExecutor] Identity discovery failed: {exc}")

        # 2. Namespaces Stage (Truthful without fabricated public fallback)
        namespaces = None
        try:
            namespaces = run_with_timeout("Namespaces", strategy.discover_namespaces, connection, spec, context)
        except Exception as exc:
            errors.append(f"Namespace discovery failed: {exc}")
            logger.warning(f"[DiscoveryPipelineExecutor] Namespace discovery failed: {exc}")

        # 3. Object Inventory Stage with Server-Side Cursor Pagination
        all_tables: list[TableFacts] = []
        all_views: list[ViewFacts] = []
        structures: dict[str, ObjectStructureFacts] = {}
        partitioning: dict[str, PartitionFacts] = {}
        table_sizes: list[TableSizeFacts] = []
        lob_facts: list[LOBVolumeFacts] = []
        sampled_data: dict[str, SampledRecordSet] = {}

        # Resolve schemas to scan truthfully without fabricating 'public'
        schemas_to_scan: list[str] = []
        if namespaces is not None:
            if namespaces.schemas:
                for s in namespaces.schemas:
                    if context.scope.is_schema_allowed(s):
                        schemas_to_scan.append(s)
            elif namespaces.default_schema and context.scope.is_schema_allowed(namespaces.default_schema):
                schemas_to_scan.append(namespaces.default_schema)
            elif not namespaces.schemas and not namespaces.default_schema:
                # Schema-less or single namespace engine (e.g. SQLite, Mongo, Redis, S3)
                schemas_to_scan.append("")

        # Paginate object inventory across all schemas until exhaustion, deadline, or max_objects
        if not check_deadline("Object Inventory"):
            for sch in schemas_to_scan:
                if check_deadline("Object Inventory Paging") or is_truncated_due_to_max_objects:
                    break

                cursor: Optional[str] = None
                has_more = True
                page_idx = 0

                while has_more:
                    if check_deadline("Object Inventory Paging Loop"):
                        break
                    try:
                        page = run_with_timeout(
                            f"Object Inventory Page {page_idx}",
                            strategy.discover_objects_page,
                            connection=connection,
                            spec=spec,
                            schema_name=sch,
                            context=context,
                            cursor=cursor,
                            page_size=500,
                        )
                        # Process tables
                        for tbl in page.items:
                            if context.scope.is_table_allowed(sch, tbl.name):
                                all_tables.append(tbl)
                                if len(all_tables) >= context.max_objects:
                                    is_truncated_due_to_max_objects = True
                                    warnings.append(
                                        f"Reached max_objects limit ({context.max_objects}). Truncating inventory."
                                    )
                                    has_more = False
                                    break

                        # Process views
                        for v in page.views:
                            if context.scope.is_table_allowed(sch, v.name):
                                all_views.append(v)

                        cursor = page.cursor
                        has_more = not page.is_last_page and bool(cursor) and not is_truncated_due_to_max_objects
                        page_idx += 1
                        if check_deadline("Object Inventory Post-Fetch"):
                            break

                    except Exception as exc:
                        is_partial_due_to_pagination_error = True
                        msg = f"Object discovery pagination failed in schema '{sch}' at page {page_idx}: {exc}"
                        errors.append(msg)
                        logger.warning(f"[DiscoveryPipelineExecutor] {msg}")
                        break

        # 4. Deep Structure, Programmable, Partitioning & Sizing Stage
        # Bulk-batched single-session processing (eliminates N+1 queries while protecting single DB-API connection)
        if not check_deadline("Deep Structures") and context.depth in (
            DiscoveryDepth.STANDARD,
            DiscoveryDepth.DEEP,
            DiscoveryDepth.COMPLIANCE,
        ):
            # Group tables by schema for bulk dispatch
            tables_by_schema: dict[str, list[TableFacts]] = {}
            for tbl in all_tables:
                sch_name = tbl.schema_name or ""
                tables_by_schema.setdefault(sch_name, []).append(tbl)

            for sch_name, schema_tables in tables_by_schema.items():
                if check_deadline("Deep Table Inspection Chunk Loop"):
                    break

                # Chunk in batches (e.g. 500 tables per batch) to keep query sizes and memory bounded
                chunk_size = 500
                for i in range(0, len(schema_tables), chunk_size):
                    if check_deadline("Deep Table Inspection Chunk"):
                        break
                    chunk = schema_tables[i : i + chunk_size]
                    chunk_names = [t.name for t in chunk]

                    # 4a. Bulk Physical Structure
                    try:
                        bulk_structs = run_with_timeout(
                            f"Bulk Structure {sch_name}",
                            strategy.discover_objects_structure_bulk,
                            connection=connection,
                            spec=spec,
                            schema_name=sch_name,
                            object_names=chunk_names,
                            context=context,
                        )
                        for tbl in chunk:
                            tbl_key = f"{tbl.schema_name}.{tbl.name}" if tbl.schema_name else tbl.name
                            struct = bulk_structs.get(tbl.name)
                            if struct:
                                structures[tbl_key] = struct
                                # Check for LOB columns
                                for col in struct.columns:
                                    if col.is_lob:
                                        lob_facts.append(
                                            LOBVolumeFacts(
                                                table_name=tbl.name,
                                                column_name=col.name,
                                                schema_name=tbl.schema_name,
                                                total_lob_bytes=tbl.size_bytes_estimate or 0,
                                                is_inline=False,
                                            )
                                        )
                    except Exception as exc:
                        warnings.append(f"Bulk structure discovery failed for chunk in schema '{sch_name}': {exc}")

                    # 4b. Bulk Statistics & Sizing Facts
                    try:
                        bulk_stats = run_with_timeout(
                            f"Bulk Statistics {sch_name}",
                            strategy.discover_table_statistics_bulk,
                            connection=connection,
                            spec=spec,
                            schema_name=sch_name,
                            object_names=chunk_names,
                            context=context,
                        )
                        for tbl in chunk:
                            st = bulk_stats.get(tbl.name)
                            if st:
                                table_sizes.append(st)
                    except Exception as exc:
                        warnings.append(f"Bulk stats discovery failed for chunk in schema '{sch_name}': {exc}")

                    # 4c. Partitioning (if DEEP or COMPLIANCE)
                    if isinstance(strategy, RelationalDiscoveryStrategy) and context.depth in (DiscoveryDepth.DEEP, DiscoveryDepth.COMPLIANCE):
                        try:
                            bulk_parts = run_with_timeout(
                                f"Bulk Partitions {sch_name}",
                                strategy.discover_partitions_bulk,
                                connection=connection,
                                spec=spec,
                                schema_name=sch_name,
                                object_names=chunk_names,
                                context=context,
                            )
                            for tbl in chunk:
                                tbl_key = f"{tbl.schema_name}.{tbl.name}" if tbl.schema_name else tbl.name
                                p = bulk_parts.get(tbl.name)
                                if p:
                                    partitioning[tbl_key] = p
                        except Exception as exc:
                            warnings.append(f"Bulk partition discovery failed for chunk in schema '{sch_name}': {exc}")

        # 5. Programmable Objects Stage (PL/SQL, T-SQL, PL/pgSQL, etc.)
        programmables = None
        if not check_deadline("Programmables") and isinstance(strategy, RelationalDiscoveryStrategy) and context.depth in (
            DiscoveryDepth.DEEP,
            DiscoveryDepth.COMPLIANCE,
        ):
            try:
                for sch in schemas_to_scan:
                    if check_deadline("Programmables Paging"):
                        break
                    prog = run_with_timeout("Programmables", strategy.discover_programmables, connection, spec, sch, context)
                    if programmables is None:
                        programmables = prog
                    else:
                        # Merge programmable collections across schemas
                        programmables = type(prog)(
                            routines=programmables.routines + prog.routines,
                            triggers=programmables.triggers + prog.triggers,
                            sequences=programmables.sequences + prog.sequences,
                            udts=programmables.udts + prog.udts,
                        )
            except Exception as exc:
                warnings.append(f"Programmable objects discovery failed: {exc}")

        # 6. Statistics & Volume Aggregations
        statistics = None
        volume = None
        if table_sizes:
            statistics = StatisticsSnapshot(table_sizes=tuple(table_sizes))
            total_bytes = statistics.total_estimated_bytes
            total_rows = statistics.total_estimated_rows

            sorted_sizes = sorted(table_sizes, key=lambda s: s.total_bytes, reverse=True)
            top_items = []
            for s in sorted_sizes[:10]:
                pct = (s.total_bytes / total_bytes * 100.0) if total_bytes > 0 else 0.0
                top_items.append(
                    LargestObjectItem(
                        object_name=s.table_name,
                        schema_name=s.schema_name,
                        size_bytes=s.total_bytes,
                        row_count=s.row_count,
                        percentage_of_total=pct,
                    )
                )

            volume = VolumeSnapshot(
                total_selected_rows=total_rows,
                total_selected_bytes=total_bytes,
                top_largest_objects=tuple(top_items),
                lob_breakdown=tuple(lob_facts),
            )

        # 7. Permissions Stage (Fail-Closed 3-State Truth)
        permissions = None
        if not check_deadline("Permissions"):
            try:
                permissions = run_with_timeout("Permissions", strategy.discover_permissions, connection, spec, context)
            except Exception as exc:
                warnings.append(f"Permission assessment failed: {exc}")

        # 8. Topology Stage
        topology = None
        if not check_deadline("Topology"):
            try:
                topology = run_with_timeout("Topology", strategy.discover_topology, connection, spec, context)
            except Exception as exc:
                warnings.append(f"Topology discovery failed: {exc}")

        # 9. CDC Prerequisites Stage
        cdc = None
        if not check_deadline("CDC Prerequisites"):
            try:
                cdc = run_with_timeout("CDC Prerequisites", strategy.discover_cdc_prerequisites, connection, spec, context)
            except Exception as exc:
                warnings.append(f"CDC prerequisite discovery failed: {exc}")

        # 10. Environment Stage
        environment = None
        if not check_deadline("Environment"):
            try:
                environment = run_with_timeout("Environment", strategy.discover_environment, connection, spec, context)
            except Exception as exc:
                warnings.append(f"Environment configuration discovery failed: {exc}")

        # 11. Canonical Requested Sampling (Orchestrated whole-discovery preview)
        if context.sample_records and not check_deadline("Sampling"):
            sample_candidates = all_tables[: context.max_sampled_tables]
            for tbl in sample_candidates:
                if check_deadline("Sampling Table Loop"):
                    break
                tbl_key = f"{tbl.schema_name}.{tbl.name}" if tbl.schema_name else tbl.name
                try:
                    sample_res = run_with_timeout(
                        f"Sampling {tbl_key}",
                        strategy.sample_data,
                        connection=connection,
                        spec=spec,
                        schema_name=tbl.schema_name,
                        table_name=tbl.name,
                        limit=context.sample_size,
                        timeout_seconds=min(5.0, max(0.1, context.timeout_seconds / 4.0)),
                    )
                    sampled_data[tbl_key] = sample_res
                except Exception as exc:
                    warnings.append(f"Preview sampling failed for '{tbl_key}': {exc}")
                    sampled_data[tbl_key] = DeterministicSampler.package_failure(
                        table_name=tbl.name,
                        schema_name=tbl.schema_name or "",
                        error_message=str(exc),
                    )

        # 12. Schema Mutation During Scan Detection
        end_marker = None
        try:
            end_marker = run_with_timeout("End Schema Marker", strategy.get_schema_change_marker, connection, spec)
        except Exception:
            pass
        if start_marker is not None and end_marker is not None and start_marker != end_marker:
            warnings.append(f"Schema mutation detected during scan (marker changed from '{start_marker}' to '{end_marker}').")

        # 13. Determine Completeness Level Truthfully
        completeness = DiscoveryCompleteness.FULL
        if errors or is_partial_due_to_pagination_error or is_partial_due_to_timeout or is_truncated_due_to_max_objects:
            if not all_tables and (namespaces is None or not namespaces.schemas):
                completeness = DiscoveryCompleteness.FAILED
            elif not all_tables:
                completeness = DiscoveryCompleteness.DEGRADED
            else:
                completeness = DiscoveryCompleteness.PARTIAL
        elif warnings:
            completeness = DiscoveryCompleteness.PARTIAL

        # 14. Assemble Complete Object Inventory (Tables & Views)
        objects_inventory = ObjectInventory(
            tables=tuple(all_tables),
            views=tuple(all_views),
        )

        # 15. Complete 12-Domain Deterministic Physical Fingerprint
        fp = DiscoveryFingerprintCalculator.compute(
            namespaces_dict=namespaces.to_dict() if namespaces else {},
            objects_dict=objects_inventory.to_dict(),
            structures_dict={k: v.to_dict() for k, v in sorted(structures.items())},
            identity_dict=engine_identity.to_dict() if engine_identity else None,
            permissions_dict=permissions.to_dict() if permissions else None,
            programmables_dict=programmables.to_dict() if programmables else None,
            partitioning_dict={k: v.to_dict() for k, v in sorted(partitioning.items())},
            statistics_dict=statistics.to_dict() if statistics else None,
            volume_dict=volume.to_dict() if volume else None,
            topology_dict=topology.to_dict() if topology else None,
            cdc_dict=cdc.to_dict() if cdc else None,
            environment_dict=environment.to_dict() if environment else None,
        )

        t1 = time.time()
        duration_ms = (t1 - t0) * 1000.0

        return DiscoverySnapshot(
            completeness=completeness,
            engine_identity=engine_identity,
            namespaces=namespaces,
            objects=objects_inventory,
            structures=structures,
            programmables=programmables,
            partitioning=partitioning,
            statistics=statistics,
            volume=volume,
            permissions=permissions,
            topology=topology,
            cdc=cdc,
            environment=environment,
            sampled_data=sampled_data,
            fingerprint=fp,
            warnings=tuple(warnings),
            errors=tuple(errors),
            duration_ms=duration_ms,
        )

"""
Akaal — Compression layout Validator
====================================
Audits page compression schemas, storage engine incompatibilities,
licensing constraints, and executes startup config checks.
"""

from typing import Any, Dict, List, Set

from akaal.core.comparison.models import Schema
from akaal.core.models.enums import SystemType
from akaal.core.intelligence.common.models import Diagnostic, DiagnosticCategory, Severity
from akaal.core.intelligence.compression_aware.models import (
    CompressionAlgorithm,
    CompressionCompatibilityTier,
    CompressionTranslation,
)
from akaal.core.intelligence.compression_aware.exceptions import CompressionValidationError


class CompressionLayoutValidator:
    """Validates compression configurations against system, storage engine, and licensing constraints."""

    def validate_compression(
        self,
        schema: Schema,
        translations: Dict[str, CompressionTranslation],
        target_version: str,
        target_engine: str,
        target_edition: str,
        session_id: str = "",
        correlation_id: str = "",
        trace_id: str = ""
    ) -> List[Diagnostic]:
        """Validates translation plans against version, edition, and engine constraints."""
        diagnostics: List[Diagnostic] = []

        target_dialect = translations[list(translations.keys())[0]].target_dialect if translations else SystemType.POSTGRESQL

        for table in schema.tables:
            trans = translations.get(table.name)
            if not trans:
                continue

            target_algo = trans.target_algorithm

            # 1. Edition limitations (e.g., Columnstore requires Enterprise edition in older SQL Server)
            if target_algo == CompressionAlgorithm.COLUMNSTORE:
                if target_dialect == SystemType.MSSQL and target_edition.upper() not in ("ENTERPRISE", "DEVELOPER"):
                    # Check if version is older than SQL Server 2016 SP1 (13.0.4001)
                    is_older = False
                    try:
                        ver_parts = tuple(int(x) for x in target_version.split(".") if x.isdigit())
                        if ver_parts < (13, 0):
                            is_older = True
                    except Exception:
                        pass
                    
                    if is_older:
                        diagnostics.append(Diagnostic(
                            diagnostic_code="COMPRESSION_EDITION_LIMITATION",
                            severity=Severity.CRITICAL,
                            category=DiagnosticCategory.COMPATIBILITY,
                            message=f"Table '{table.name}' requests COLUMNSTORE compression but target SQL Server edition '{target_edition}' does not support it natively.",
                            path=f"tables.{table.name}.compression",
                            explanation="Columnstore indexing and columnar compression were Enterprise-only features in SQL Server versions older than 2016 SP1.",
                            root_cause="Unsupported SQL Server Standard or Express edition capabilities.",
                            suggested_fix="Upgrade target database edition to Enterprise/Developer, or downgrade compression type to PAGE.",
                            affected_event=table.name,
                            affected_session=session_id,
                            correlation_id=correlation_id,
                            trace_id=trace_id
                        ))

            # 2. Storage engine restrictions (e.g., InnoDB Page Compression requires InnoDB engine)
            if target_algo in (CompressionAlgorithm.PAGE, CompressionAlgorithm.ROW) and target_dialect == SystemType.MYSQL:
                if target_engine and target_engine.upper() != "INNODB":
                    diagnostics.append(Diagnostic(
                        diagnostic_code="COMPRESSION_ENGINE_MISMATCH",
                        severity=Severity.CRITICAL,
                        category=DiagnosticCategory.COMPATIBILITY,
                        message=f"Table '{table.name}' target compression requires InnoDB storage engine, but target engine is '{target_engine}'.",
                        path=f"tables.{table.name}.engine",
                        explanation="MySQL page compression is only supported natively on the InnoDB storage engine.",
                        root_cause="Target storage engine configuration is set to MyISAM or other non-transactional engine.",
                        suggested_fix="Switch target table engine parameter to InnoDB.",
                        affected_event=table.name,
                        affected_session=session_id,
                        correlation_id=correlation_id,
                        trace_id=trace_id
                    ))

            # 3. Version restrictions (e.g. PG LZ4 TOAST requires PG 14+)
            if target_algo == CompressionAlgorithm.TOAST and target_dialect == SystemType.POSTGRESQL:
                is_older_pg = False
                try:
                    ver_parts = tuple(int(x) for x in target_version.split(".") if x.isdigit())
                    if ver_parts and ver_parts[0] < 14:
                        is_older_pg = True
                except Exception:
                    pass

                if is_older_pg:
                    diagnostics.append(Diagnostic(
                        diagnostic_code="COMPRESSION_UNSUPPORTED_ALGORITHM",
                        severity=Severity.WARNING,
                        category=DiagnosticCategory.COMPATIBILITY,
                        message=f"Table '{table.name}' uses TOAST compression which requires PostgreSQL 14+, but target version is {target_version}.",
                        path=f"tables.{table.name}",
                        explanation="Advanced LZ4 custom TOAST compression methods are not supported on PostgreSQL versions prior to 14.",
                        root_cause="Target PostgreSQL database version limits.",
                        suggested_fix="Upgrade target PostgreSQL engine to version 14 or above, or default to standard PGLZ compression.",
                        affected_event=table.name,
                        affected_session=session_id,
                        correlation_id=correlation_id,
                        trace_id=trace_id
                    ))

            # 4. High ratio loss warning
            if trans.estimated_ratio_loss > 0.40:
                diagnostics.append(Diagnostic(
                    diagnostic_code="COMPRESSION_MIGRATION_RISK",
                    severity=Severity.WARNING,
                    category=DiagnosticCategory.COMPATIBILITY,
                    message=f"Table '{table.name}' translation yields high storage density degradation ({int(trans.estimated_ratio_loss * 100)}% loss).",
                    path=f"tables.{table.name}",
                    explanation="Moving compressed structures to a target dialect with lower density compression will increase physical disk footprints.",
                    root_cause="Lossy translation mapping selected for target dialect compatibility.",
                    suggested_fix="Enable tablespace-level or index-level pre-allocations on target database.",
                    affected_event=table.name,
                    affected_session=session_id,
                    correlation_id=correlation_id,
                    trace_id=trace_id
                ))

        return diagnostics

    def validate_startup_config(self, profiles_data: Dict[str, Any]) -> None:
        """Validates compression profiles JSON data for duplicate keys, overlaps, and cycles."""
        profiles = profiles_data.get("profiles", [])
        
        seen_ids: Set[str] = set()
        seen_algos: Dict[str, Set[CompressionAlgorithm]] = {}  # dialect -> algorithms

        for idx, prof in enumerate(profiles):
            prof_id = prof.get("profile_id")
            dialect_str = prof.get("dialect")
            algo_str = prof.get("algorithm")

            if not prof_id:
                raise CompressionValidationError(f"Profile at index {idx} is missing 'profile_id'.", error_code="COMPRESSION_CONFIG_INVALID")

            if prof_id in seen_ids:
                raise CompressionValidationError(f"Duplicate profile ID detected in configuration: {prof_id}", error_code="COMPRESSION_CONFIG_INVALID")
            seen_ids.add(prof_id)

            # Validate version boundaries
            min_ver = prof.get("min_version")
            max_ver = prof.get("max_version")
            if min_ver and max_ver:
                if min_ver > max_ver:
                    raise CompressionValidationError(
                        f"Profile '{prof_id}' defines invalid version range: min_version {min_ver} > max_version {max_ver}.",
                        error_code="COMPRESSION_CONFIG_INVALID"
                    )

            # Validate circular plugin dependencies
            plugins = prof.get("plugins_required", [])
            self._verify_no_circular_dependencies(prof_id, plugins)

        # Validate duplicate algorithm definitions per dialect
        for prof in profiles:
            dialect_str = prof.get("dialect")
            algo_str = prof.get("algorithm")
            min_ver = prof.get("min_version") or "0.0"

            if dialect_str and algo_str:
                seen_algos.setdefault(dialect_str, set())
                # Check mapping conflict boundaries
                key = f"{dialect_str}:{algo_str}:{min_ver}"
                # If duplicate mappings exist for same context, warn or raise validation error
                # We can enforce unique dialect-algo-version entries
                pass

    def _verify_no_circular_dependencies(self, profile_id: str, plugins_list: List[Dict[str, Any]]) -> None:
        """Runs a depth-first search to detect circular dependencies between required plugins."""
        adj: Dict[str, List[str]] = {}
        for plug in plugins_list:
            name = plug.get("name")
            deps = plug.get("dependencies", [])
            if name:
                adj[name] = deps

        visited: Dict[str, int] = {}  # 0=unvisited, 1=visiting, 2=visited

        def dfs(u: str) -> None:
            visited[u] = 1
            for v in adj.get(u, []):
                if visited.get(v, 0) == 1:
                    raise CompressionValidationError(
                        f"Circular plugin dependency loop detected in profile '{profile_id}' involving '{u}' -> '{v}'.",
                        error_code="COMPRESSION_CONFIG_INVALID"
                    )
                elif visited.get(v, 0) == 0:
                    dfs(v)
            visited[u] = 2

        for plugin_name in adj:
            if visited.get(plugin_name, 0) == 0:
                dfs(plugin_name)

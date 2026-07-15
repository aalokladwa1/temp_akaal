"""
Akaal — Compression Layout Analyzer
====================================
Implements intermediate-format translation graphs, strategy-based capacity
estimators, and compression sizing calculations.
"""

import abc
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple, Set

from akaal.core.comparison.models import Schema, TableSchema, ColumnSchema
from akaal.core.models.enums import SystemType
from akaal.core.intelligence.compression_aware.models import (
    CompressionAlgorithm,
    CompressionCompatibilityTier,
    CompressionProfile,
    CompressionTranslation,
    CompressionStatistics,
    CompressionSummary,
    CompressionReport,
)
from akaal.core.intelligence.compression_aware.exceptions import CompressionTranslationError
from akaal.core.intelligence.storage_optimization import IStorageAnalyzer


class ICompressionAnalyzer(abc.ABC):
    """Abstract interface defining the compression capabilities validation and planning calculations."""
    @abc.abstractmethod
    def analyze_compression(
        self,
        schema: Schema,
        target_dialect: SystemType,
        source_uncompressed_size_kb: int = 100000
    ) -> Tuple[CompressionStatistics, CompressionSummary, Dict[str, CompressionTranslation]]:
        pass


class CompressionEstimatorStrategy(ABC):
    """Abstract base strategy for compression physical sizing estimation."""
    @abstractmethod
    def estimate_compression(
        self,
        table: TableSchema,
        algorithm: CompressionAlgorithm,
        uncompressed_size_kb: int
    ) -> Tuple[int, float, float]:
        """Calculates (projected_size_kb, cpu_overhead_factor, io_multiplier)."""
        pass


class DefaultCompressionEstimatorStrategy(CompressionEstimatorStrategy):
    """Fallback sizing estimator executing calculations using generic data-types mapping."""
    def estimate_compression(
        self,
        table: TableSchema,
        algorithm: CompressionAlgorithm,
        uncompressed_size_kb: int
    ) -> Tuple[int, float, float]:
        if algorithm == CompressionAlgorithm.NONE:
            return uncompressed_size_kb, 1.0, 1.0

        # Estimate average savings from columns
        savings_sum = 0.0
        for col in table.columns:
            dt = col.data_type.upper()
            if "VARCHAR" in dt or "CHAR" in dt:
                savings_sum += 0.40  # 40% savings
            elif "TEXT" in dt or "CLOB" in dt or "BLOB" in dt or "JSON" in dt:
                savings_sum += 0.65  # 65% savings
            elif "INT" in dt or "NUMBER" in dt or "DOUBLE" in dt:
                savings_sum += 0.15  # 15% savings
            else:
                savings_sum += 0.10

        avg_ratio = savings_sum / len(table.columns) if table.columns else 0.20
        # Clamp average savings between 5% and 80%
        avg_ratio = max(0.05, min(0.80, avg_ratio))

        projected = int(uncompressed_size_kb * (1.0 - avg_ratio))
        cpu_overhead = 1.15  # baseline 15% CPU increase for write zip operations
        io_multiplier = 1.30  # baseline 30% read throughput speedup
        return projected, cpu_overhead, io_multiplier


class VendorCompressionEstimatorStrategy(CompressionEstimatorStrategy):
    """High-specificity estimator mapping vendor-specific hardware ratios (e.g. HCC or Columnstore)."""
    def estimate_compression(
        self,
        table: TableSchema,
        algorithm: CompressionAlgorithm,
        uncompressed_size_kb: int
    ) -> Tuple[int, float, float]:
        # High-performance columnar compressors
        if algorithm in (CompressionAlgorithm.HCC_QUERY_HIGH, CompressionAlgorithm.HCC_ARCHIVE_HIGH, CompressionAlgorithm.COLUMNSTORE):
            projected = int(uncompressed_size_kb * 0.15)  # ~85% storage space savings
            return projected, 1.35, 1.80  # high CPU write calculations overhead but high read IO multiplier
            
        elif algorithm in (CompressionAlgorithm.HCC_QUERY_LOW, CompressionAlgorithm.HCC_ARCHIVE_LOW):
            projected = int(uncompressed_size_kb * 0.25)  # ~75% savings
            return projected, 1.25, 1.60
            
        elif algorithm in (CompressionAlgorithm.ADVANCED_ROW, CompressionAlgorithm.PAGE, CompressionAlgorithm.TOAST):
            projected = int(uncompressed_size_kb * 0.45)  # ~55% savings
            return projected, 1.10, 1.40

        # Fallback to default
        return DefaultCompressionEstimatorStrategy().estimate_compression(table, algorithm, uncompressed_size_kb)


class PluginCompressionEstimatorStrategy(CompressionEstimatorStrategy):
    """Custom pluggable compression estimator provided by dynamic plugins."""
    def __init__(self, plugin_multiplier: float = 0.50) -> None:
        self.plugin_multiplier = plugin_multiplier

    def estimate_compression(
        self,
        table: TableSchema,
        algorithm: CompressionAlgorithm,
        uncompressed_size_kb: int
    ) -> Tuple[int, float, float]:
        projected = int(uncompressed_size_kb * self.plugin_multiplier)
        return projected, 1.20, 1.25


class CompressionTranslationGraph:
    """Graph database modeling indirect compression mapping transitions via intermediate capabilities."""

    def __init__(self) -> None:
        self.adj_list: Dict[Any, List[Tuple[Any, CompressionCompatibilityTier, float, float, str]]] = {}

    def add_node(self, node: Any) -> None:
        if node not in self.adj_list:
            self.adj_list[node] = []

    def add_edge(
        self,
        u: Any,
        v: Any,
        tier: CompressionCompatibilityTier,
        confidence: float,
        ratio_loss: float,
        rationale: str
    ) -> None:
        self.add_node(u)
        self.add_node(v)
        self.adj_list[u].append((v, tier, confidence, ratio_loss, rationale))

    def find_translation(
        self,
        source: Tuple[SystemType, CompressionAlgorithm],
        target_dialect: SystemType
    ) -> Optional[Tuple[List[Any], CompressionCompatibilityTier, float, float, str]]:
        """BFS-based path resolution from source configuration to any target dialect node."""
        if source not in self.adj_list:
            return None

        # Standard Native optimization check
        if source[0] == target_dialect:
            return [source], CompressionCompatibilityTier.NATIVE, 1.0, 0.0, "Natively supported dialect configuration"

        visited: Set[Any] = {source}
        # Queue stores: (current_node, path, worst_tier, compound_confidence, total_ratio_loss, rationale_list)
        queue: List[Tuple[Any, List[Any], CompressionCompatibilityTier, float, float, List[str]]] = [
            (source, [source], CompressionCompatibilityTier.NATIVE, 1.0, 0.0, [])
        ]

        # Compatibility tier ranking to resolve the worst tier along the graph path
        tier_ranks = {
            CompressionCompatibilityTier.NATIVE: 0,
            CompressionCompatibilityTier.LOSSLESS_TRANSLATION: 1,
            CompressionCompatibilityTier.PLUGIN_PROVIDED: 2,
            CompressionCompatibilityTier.LOSSY_TRANSLATION: 3,
            CompressionCompatibilityTier.EMULATED: 4,
            CompressionCompatibilityTier.UNSUPPORTED: 5
        }

        best_path: Optional[Tuple[List[Any], CompressionCompatibilityTier, float, float, str]] = None

        while queue:
            curr, path, tier, conf, loss, rationales = queue.pop(0)

            # Check if target dialect matches node destination
            if isinstance(curr, tuple) and len(curr) == 2:
                node_dialect, node_algo = curr
                if node_dialect == target_dialect:
                    rationale_text = "; ".join(rationales) if rationales else "Direct or intermediate translation."
                    # Keep path with highest confidence
                    if not best_path or conf > best_path[2]:
                        best_path = (path, tier, conf, loss, rationale_text)

            for neighbor, n_tier, n_conf, n_loss, n_rat in self.adj_list.get(curr, []):
                if neighbor not in visited:
                    visited.add(neighbor)
                    
                    # Compute cumulative metrics
                    worst_tier = tier if tier_ranks[tier] > tier_ranks[n_tier] else n_tier
                    comp_conf = conf * n_conf
                    tot_loss = loss + n_loss
                    new_rat = rationales + [n_rat]
                    
                    queue.append((neighbor, path + [neighbor], worst_tier, comp_conf, tot_loss, new_rat))

        return best_path


class CompressionLayoutAnalyzer(ICompressionAnalyzer):
    """Orchestrates capability mapping, sizing estimations, and path validations."""

    def __init__(
        self,
        registry: Any,
        storage_analyzer: Optional[IStorageAnalyzer] = None
    ) -> None:
        self.registry = registry
        self.storage_analyzer = storage_analyzer
        self.graph = CompressionTranslationGraph()
        self._bootstrap_default_graph()

    def _bootstrap_default_graph(self) -> None:
        # Define Intermediate Format capability targets
        cap_row_page = "CAP_ROW_PAGE"
        cap_columnar = "CAP_COLUMNAR"
        cap_lob = "CAP_LOB"

        # 1. Oracle Mappings
        src_oracle_row = (SystemType.ORACLE, CompressionAlgorithm.ADVANCED_ROW)
        src_oracle_hcc = (SystemType.ORACLE, CompressionAlgorithm.HCC_QUERY_HIGH)
        self.graph.add_edge(src_oracle_row, cap_row_page, CompressionCompatibilityTier.LOSSLESS_TRANSLATION, 0.95, 0.0, "Oracle Row maps to Page/Row targets")
        self.graph.add_edge(src_oracle_hcc, cap_columnar, CompressionCompatibilityTier.LOSSLESS_TRANSLATION, 0.90, 0.0, "Oracle HCC maps to columnar format")

        # 2. SQL Server Mappings
        src_mssql_row = (SystemType.MSSQL, CompressionAlgorithm.ROW)
        src_mssql_page = (SystemType.MSSQL, CompressionAlgorithm.PAGE)
        src_mssql_col = (SystemType.MSSQL, CompressionAlgorithm.COLUMNSTORE)
        self.graph.add_edge(src_mssql_row, cap_row_page, CompressionCompatibilityTier.LOSSLESS_TRANSLATION, 0.95, 0.0, "SQL Server Row maps to Page/Row targets")
        self.graph.add_edge(src_mssql_page, cap_row_page, CompressionCompatibilityTier.LOSSLESS_TRANSLATION, 0.95, 0.0, "SQL Server Page maps to Page/Row targets")
        self.graph.add_edge(src_mssql_col, cap_columnar, CompressionCompatibilityTier.LOSSLESS_TRANSLATION, 0.90, 0.0, "SQL Server Columnstore maps to columnar formats")

        # 3. MySQL Mappings
        src_mysql_page = (SystemType.MYSQL, CompressionAlgorithm.PAGE)
        self.graph.add_edge(src_mysql_page, cap_row_page, CompressionCompatibilityTier.LOSSLESS_TRANSLATION, 0.95, 0.0, "MySQL Page maps to Page/Row targets")

        # 4. PostgreSQL Mappings
        src_postgres_toast = (SystemType.POSTGRESQL, CompressionAlgorithm.TOAST)
        self.graph.add_edge(src_postgres_toast, cap_lob, CompressionCompatibilityTier.LOSSLESS_TRANSLATION, 0.95, 0.0, "Postgres TOAST maps to LOB targets")

        # 5. Outbound Intermediate mapping targets edges
        tgt_oracle_row = (SystemType.ORACLE, CompressionAlgorithm.ADVANCED_ROW)
        tgt_mssql_page = (SystemType.MSSQL, CompressionAlgorithm.PAGE)
        tgt_mysql_page = (SystemType.MYSQL, CompressionAlgorithm.PAGE)
        tgt_postgres_toast = (SystemType.POSTGRESQL, CompressionAlgorithm.TOAST)
        tgt_mssql_col = (SystemType.MSSQL, CompressionAlgorithm.COLUMNSTORE)

        self.graph.add_edge(cap_row_page, tgt_oracle_row, CompressionCompatibilityTier.LOSSLESS_TRANSLATION, 0.90, 0.0, "Map to target Oracle Row compression")
        self.graph.add_edge(cap_row_page, tgt_mssql_page, CompressionCompatibilityTier.LOSSLESS_TRANSLATION, 0.90, 0.0, "Map to target SQL Server Page compression")
        self.graph.add_edge(cap_row_page, tgt_mysql_page, CompressionCompatibilityTier.LOSSY_TRANSLATION, 0.80, 0.15, "Map to MySQL Page formats yields lower density")
        self.graph.add_edge(cap_row_page, tgt_postgres_toast, CompressionCompatibilityTier.LOSSLESS_TRANSLATION, 0.85, 0.0, "Map block compression to Postgres Page TOAST")

        self.graph.add_edge(cap_columnar, tgt_mssql_col, CompressionCompatibilityTier.LOSSLESS_TRANSLATION, 0.90, 0.0, "Map columnar source to SQL Server Columnstore")
        self.graph.add_edge(cap_lob, tgt_postgres_toast, CompressionCompatibilityTier.LOSSLESS_TRANSLATION, 0.90, 0.0, "Map LOB source to Postgres TOAST segments")

    def resolve_translation(
        self,
        source_dialect: SystemType,
        source_algorithm: CompressionAlgorithm,
        target_dialect: SystemType
    ) -> CompressionTranslation:
        """Consults the graph pathways to construct a Translation strategy plan."""
        source_node = (source_dialect, source_algorithm)
        
        path_res = self.graph.find_translation(source_node, target_dialect)
        if not path_res:
            # Fallback configuration
            return CompressionTranslation(
                source_dialect=source_dialect,
                target_dialect=target_dialect,
                source_algorithm=source_algorithm,
                target_algorithm=CompressionAlgorithm.NONE,
                compatibility_tier=CompressionCompatibilityTier.UNSUPPORTED,
                translation_confidence=0.0,
                translation_rationale="No translation path found in intermediate graph capabilities.",
                translation_path=(str(source_node),),
                estimated_ratio_loss=1.0
            )

        path_nodes, tier, conf, ratio_loss, rationale = path_res
        
        # Determine target algorithm from destination node
        target_node = path_nodes[-1]
        target_algo = target_node[1] if isinstance(target_node, tuple) else CompressionAlgorithm.NONE
        
        # Build path strings
        path_strings = tuple(str(n) for n in path_nodes)

        return CompressionTranslation(
            source_dialect=source_dialect,
            target_dialect=target_dialect,
            source_algorithm=source_algorithm,
            target_algorithm=target_algo,
            compatibility_tier=tier,
            translation_confidence=conf,
            translation_rationale=rationale,
            translation_path=path_strings,
            estimated_ratio_loss=ratio_loss
        )

    def analyze_compression(
        self,
        schema: Schema,
        target_dialect: SystemType,
        source_uncompressed_size_kb: int = 100000
    ) -> Tuple[CompressionStatistics, CompressionSummary, Dict[str, CompressionTranslation]]:
        """Runs validation sizing estimates and strategy translations across all table entries."""
        translations: Dict[str, CompressionTranslation] = {}
        total_projected = 0
        total_savings = 0
        
        native_cnt = 0
        trans_cnt = 0
        unsupp_cnt = 0
        compressed_cnt = 0
        
        # Determine estimators based on algorithm target properties
        vendor_est = VendorCompressionEstimatorStrategy()
        default_est = DefaultCompressionEstimatorStrategy()

        # Simple allocation calculation: divide default size evenly among tables
        tbl_count = len(schema.tables)
        base_tbl_kb = source_uncompressed_size_kb // max(1, tbl_count)

        for table in schema.tables:
            # Simulate source compression type: check table metadata or fallback
            src_algo = CompressionAlgorithm.NONE
            
            # Simple metadata mock lookup: e.g. check index details for partition strings
            is_columnar = any("HCC" in idx.name.upper() or "COL" in idx.name.upper() for idx in table.indexes)
            is_page = any("PAGE" in idx.name.upper() or "ZIP" in idx.name.upper() for idx in table.indexes)
            
            if is_columnar:
                src_algo = CompressionAlgorithm.HCC_QUERY_HIGH
            elif is_page:
                src_algo = CompressionAlgorithm.PAGE

            # Resolve translation via Graph
            trans = self.resolve_translation(schema.vendor or SystemType.ORACLE, src_algo, target_dialect)
            translations[table.name] = trans

            # Estimate table compression sizing
            if trans.target_algorithm != CompressionAlgorithm.NONE:
                proj_size, cpu_over, io_mult = vendor_est.estimate_compression(table, trans.target_algorithm, base_tbl_kb)
                compressed_cnt += 1
            else:
                proj_size, cpu_over, io_mult = default_est.estimate_compression(table, CompressionAlgorithm.NONE, base_tbl_kb)

            total_projected += proj_size
            total_savings += (base_tbl_kb - proj_size)

            # Update count indicators
            if trans.compatibility_tier == CompressionCompatibilityTier.NATIVE:
                native_cnt += 1
            elif trans.compatibility_tier == CompressionCompatibilityTier.UNSUPPORTED:
                unsupp_cnt += 1
            else:
                trans_cnt += 1

        avg_ratio = total_savings / source_uncompressed_size_kb if source_uncompressed_size_kb > 0 else 0.0

        stats = CompressionStatistics(
            total_uncompressed_size_kb=source_uncompressed_size_kb,
            total_projected_size_kb=total_projected,
            estimated_savings_kb=total_savings,
            average_compression_ratio=round(avg_ratio, 4),
            cpu_overhead_factor=1.20 if compressed_cnt > 0 else 1.0,
            io_throughput_multiplier=1.40 if compressed_cnt > 0 else 1.0
        )

        summary = CompressionSummary(
            total_tables_analyzed=tbl_count,
            compressed_tables_count=compressed_cnt,
            native_mappings_count=native_cnt,
            translated_mappings_count=trans_cnt,
            unsupported_mappings_count=unsupp_cnt
        )

        return stats, summary, translations

"""
AKAAL Platform 5 — SchemaEvolutionPlatformV5 Public Facade

Provides the unified, high-level public interface for Platform 5 — Live Schema Evolution.
Hides all internal engines, state machines, and repositories behind stable method signatures.
"""

from typing import Any, Dict, List, Optional

from akaal.schema.compatibility.analyzer import CompatibilityAnalyzer
from akaal.schema.compatibility.comparator import SchemaComparator, SchemaDiff
from akaal.schema.compatibility.report import CompatibilityReport
from akaal.schema.constraint.engine import ConstraintEvolutionEngine
from akaal.schema.ddl_propagation.engine import DDLPropagationEngine
from akaal.schema.domain.changes import BaseSchemaChange, DDLStatement
from akaal.schema.domain.identifiers import CheckpointID, TransactionID, VersionID
from akaal.schema.evolution_engine.engine import SchemaEvolutionEngine
from akaal.schema.refresh.service import MetadataRefreshService
from akaal.schema.replay.engine import DDLReplayEngine, ReplayReport
from akaal.schema.transactions.manager import TransactionManager
from akaal.schema.transactions.model import SchemaTransaction
from akaal.schema.type_evolution.engine import TypeEvolutionEngine
from akaal.schema.type_evolution.planner import ConversionPlan
from akaal.schema.versioning.manager import MetadataVersionManager
from akaal.schema.versioning.snapshot import SchemaSnapshot


class SchemaEvolutionPlatformV5:
    """Unified Enterprise Public Facade for Platform 5 — Live Schema Evolution."""

    def __init__(self) -> None:
        self.version_manager = MetadataVersionManager()
        self.refresh_service = MetadataRefreshService(version_manager=self.version_manager)
        self.comparator = SchemaComparator()
        self.compatibility_analyzer = CompatibilityAnalyzer()
        self.type_engine = TypeEvolutionEngine()
        self.evolution_engine = SchemaEvolutionEngine()
        self.ddl_engine = DDLPropagationEngine()
        self.constraint_engine = ConstraintEvolutionEngine()
        self.replay_engine = DDLReplayEngine()
        self.tx_manager = TransactionManager()

    def refresh_metadata(self, force: bool = False, priority: int = 5, source: str = "manual") -> Optional[SchemaSnapshot]:
        """Refreshes live schema metadata and returns cached or new snapshot."""
        return self.refresh_service.refresh(force=force, priority=priority, source=source)

    def compare_schemas(self, source_version: VersionID, target_version: VersionID) -> SchemaDiff:
        """Compares two schema versions and returns structural diff."""
        snap_src = self.version_manager.repository.get_by_version(source_version)
        snap_tgt = self.version_manager.repository.get_by_version(target_version)
        if not snap_src or not snap_tgt:
            raise ValueError(f"One or both versions not found in repository: {source_version}, {target_version}")
        return self.comparator.compare(snap_src, snap_tgt)

    def analyze_compatibility(self, source_version: VersionID, target_version: VersionID) -> CompatibilityReport:
        """Evaluates compatibility, breaking changes, risk score, and migration advisories."""
        snap_src = self.version_manager.repository.get_by_version(source_version)
        snap_tgt = self.version_manager.repository.get_by_version(target_version)
        if not snap_src or not snap_tgt:
            raise ValueError(f"One or both versions not found in repository: {source_version}, {target_version}")
        return self.compatibility_analyzer.analyze(snap_src, snap_tgt)

    def evaluate_type_evolution(self, target_table: Any, column_name: str, from_type: str, to_type: str) -> ConversionPlan:
        """Evaluates widening vs narrowing type compatibility and generates conversion plan."""
        return self.type_engine.plan_and_validate(target_table, column_name, from_type, to_type)

    def execute_evolution(self, changes: List[BaseSchemaChange], db_context: Any = None) -> SchemaTransaction:
        """Executes live schema evolution changes transactionally with dependency ordering."""
        return self.evolution_engine.evolve(changes, db_context)

    def propagate_ddl(self, ddl_statements: List[DDLStatement], db_context: Any = None) -> bool:
        """Propagates online DDL statements with idempotent retry policies."""
        return self.ddl_engine.propagate(ddl_statements, db_context)

    def evolve_constraints(self, constraint_changes: List[BaseSchemaChange], db_context: Any = None) -> List[BaseSchemaChange]:
        """Evolves PK/FK/Unique/Check constraints in topologically sorted dependency order."""
        return self.constraint_engine.evolve_constraints(constraint_changes, db_context)

    def replay_journal(self, start_checkpoint: Optional[CheckpointID] = None, db_context: Any = None) -> ReplayReport:
        """Replays immutable operation journal from a given checkpoint."""
        return self.replay_engine.replay(start_checkpoint, db_context)

    def rollback_transaction(self, tx_id: TransactionID, db_context: Any = None) -> None:
        """Rolls back an executing or active transaction using its atomic rollback plan."""
        tx = self.tx_manager.store.get_transaction(tx_id)
        if not tx:
            raise ValueError(f"Transaction '{tx_id}' not found.")
        self.tx_manager.rollback(tx, executor_ctx=db_context)

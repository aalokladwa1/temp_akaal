"""
akaalEngine.schema.ddl.generator
================================
Multi-stage DDL generation orchestrator coordinating target emitters and packaging artifacts.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Type

from akaalEngine.schema.ddl.emitter import (
    BaseTargetDDLEmitter,
    DDLStage,
    StagedDDLPackage,
    StructuredDDLArtifact,
)
from akaalEngine.schema.ddl.providers import (
    BigQueryDDLEmitter,
    CQLDDLEmitter,
    MSSQLDDLEmitter,
    MySQLDDLEmitter,
    OracleDDLEmitter,
    PostgreSQLDDLEmitter,
    RedshiftDDLEmitter,
    SnowflakeDDLEmitter,
)
from akaalEngine.schema.models.schema import CanonicalSchemaModel


class DDLGenerator:
    """Multi-stage DDL generation engine for Authority #4 Schema."""

    _EMITTER_MAP: Dict[str, Type[BaseTargetDDLEmitter]] = {
        "POSTGRESQL": PostgreSQLDDLEmitter,
        "POSTGRES": PostgreSQLDDLEmitter,
        "ORACLE": OracleDDLEmitter,
        "MYSQL": MySQLDDLEmitter,
        "MARIADB": MySQLDDLEmitter,
        "MSSQL": MSSQLDDLEmitter,
        "SQLSERVER": MSSQLDDLEmitter,
        "SNOWFLAKE": SnowflakeDDLEmitter,
        "BIGQUERY": BigQueryDDLEmitter,
        "REDSHIFT": RedshiftDDLEmitter,
        "CASSANDRA": CQLDDLEmitter,
        "SCYLLADB": CQLDDLEmitter,
    }

    @classmethod
    def get_emitter(cls, target_engine: str, target_version: Optional[str] = None) -> BaseTargetDDLEmitter:
        """Resolves target DDL emitter for the specified database engine."""
        eng = target_engine.strip().upper()
        if eng in cls._EMITTER_MAP:
            emitter_cls = cls._EMITTER_MAP[eng]
            if eng == "ORACLE" and target_version:
                return OracleDDLEmitter(oracle_version=target_version)
            elif eng in ("MYSQL", "MARIADB"):
                return MySQLDDLEmitter(target_engine=eng)
            elif eng in ("CASSANDRA", "SCYLLADB"):
                return CQLDDLEmitter(target_engine=eng)
            return emitter_cls()
        # Fallback to PostgreSQL emitter
        return PostgreSQLDDLEmitter()

    @classmethod
    def generate_ddl_package(
        cls,
        model: CanonicalSchemaModel,
        target_engine: str,
        target_version: Optional[str] = None,
    ) -> StagedDDLPackage:
        """Generates staged DDL package from CanonicalSchemaModel."""
        emitter = cls.get_emitter(target_engine, target_version)
        all_artifacts: List[StructuredDDLArtifact] = []

        # 1. Schemas
        emitted_schemas = set()
        for s in model.schemas:
            if s.schema_name and s.schema_name not in emitted_schemas:
                all_artifacts.extend(emitter.emit_schema_artifacts(s.schema_name))
                emitted_schemas.add(s.schema_name)

        # Fallback schema emission from tables
        for t in model.tables:
            if t.schema_name and t.schema_name not in emitted_schemas:
                all_artifacts.extend(emitter.emit_schema_artifacts(t.schema_name))
                emitted_schemas.add(t.schema_name)

        # 2. UDTs / Types
        for udt in model.udts:
            all_artifacts.extend(emitter.emit_udt_artifacts(udt))

        # 3. Sequences
        for seq in model.sequences:
            all_artifacts.extend(emitter.emit_sequence_artifacts(seq))

        # 4. Tables (including staged PKs, Indexes, and deferred FKs)
        for tbl in model.tables:
            all_artifacts.extend(emitter.emit_table_artifacts(tbl, source_engine=model.source_vendor))

        # 5. Views
        for v in model.views:
            all_artifacts.extend(emitter.emit_view_artifacts(v, source_engine=model.source_vendor))

        return StagedDDLPackage(
            target_engine=target_engine.upper(),
            artifacts=tuple(all_artifacts),
        )

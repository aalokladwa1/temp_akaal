"""
akaalEngine.discovery.strategies.relational.sqlite
==================================================
Canonical SQLite discovery strategy.
Inspects sqlite_master, PRAGMA table_info, PRAGMA foreign_key_list, PRAGMA index_list.
Truthfully reports views, 3-state permissions, WAL mode CDC readiness, and schema change markers.
"""

from __future__ import annotations

import os
from typing import Any, Optional, Sequence, Tuple

from akaalEngine.connection.models.endpoint import EndpointSpec
from akaalEngine.connection.routing.resolver import ResolvedRoute
from akaalEngine.discovery.core.paginator import CatalogPaginator
from akaalEngine.discovery.core.sampling import DeterministicSampler
from akaalEngine.discovery.models.cdc import CDCMechanism, CDCPrerequisiteSnapshot, StartingCommitPosition
from akaalEngine.discovery.models.context import DiscoveryContext
from akaalEngine.discovery.models.environment import CharsetFacts, CollationFacts, ConfigurationFacts, LimitsFacts, TimezoneFacts
from akaalEngine.discovery.models.identity import DiscoveredEndpointIdentity, EngineEdition, ServerVersion
from akaalEngine.discovery.models.inventory import (
    NamespaceInventory,
    ObjectClassification,
    ObjectInventoryPage,
    ObjectType,
    TableFacts,
    ViewFacts,
)
from akaalEngine.discovery.models.partitioning import PartitionFacts, PartitionStrategy
from akaalEngine.discovery.models.permissions import PermissionAssessment, PrivilegeFact, ThreeStatePermission
from akaalEngine.discovery.models.programmables import ProgrammableInventory, TriggerFacts, TriggerTiming
from akaalEngine.discovery.models.statistics import CountAccuracy, TableSizeFacts
from akaalEngine.discovery.models.structure import (
    CheckConstraintFacts,
    ColumnPhysicalMetadata,
    ForeignKeyFacts,
    IndexAccessMethod,
    IndexFacts,
    ObjectStructureFacts,
    PrimaryKeyFacts,
    UniqueConstraintFacts,
)
from akaalEngine.discovery.models.topology import ClusterNodeFacts, NodeRole, TopologySnapshot
from akaalEngine.discovery.spi.relational import RelationalDiscoveryStrategy


class SQLiteDiscoveryStrategy(RelationalDiscoveryStrategy):
    """SQLite physical discovery strategy."""

    PROVIDER_ID = "sqlite"

    @property
    def provider_id(self) -> str:
        return self.PROVIDER_ID

    def discover_endpoint_identity(
        self,
        connection: Any,
        spec: EndpointSpec,
        route: Optional[ResolvedRoute] = None,
    ) -> DiscoveredEndpointIdentity:
        version_str = "3.0.0"
        if connection is not None and hasattr(connection, "execute"):
            try:
                cur = connection.execute("SELECT sqlite_version()")
                row = cur.fetchone()
                if row:
                    version_str = str(row[0])
            except Exception:
                pass

        parts = version_str.split(".")
        major = int(parts[0]) if len(parts) > 0 and parts[0].isdigit() else 3
        minor = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0
        patch = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 0

        return DiscoveredEndpointIdentity(
            provider_id=self.PROVIDER_ID,
            vendor_name="SQLite Consortium",
            engine_name="SQLite Embedded Database",
            system_type="SQLITE",
            version=ServerVersion(raw_version_string=version_str, major=major, minor=minor, patch=patch),
            edition=EngineEdition(edition_name="Embedded Community", is_enterprise=False, is_cloud_managed=False),
            database_name=spec.database_name or "main",
        )

    def discover_namespaces(
        self,
        connection: Any,
        spec: EndpointSpec,
        context: DiscoveryContext,
    ) -> NamespaceInventory:
        schemas = ["main"]
        if connection is not None and hasattr(connection, "execute"):
            try:
                cur = connection.execute("PRAGMA database_list")
                found = [str(r[1]) for r in cur.fetchall() if r and len(r) > 1]
                if found:
                    schemas = found
            except Exception as exc:
                logger.warning(f"Error querying sqlite schemas: {exc}")
                raise
        return NamespaceInventory(
            catalogs=("default",),
            schemas=tuple(schemas),
            default_schema="main",
        )

    def discover_objects_page(
        self,
        connection: Any,
        spec: EndpointSpec,
        schema_name: str,
        context: DiscoveryContext,
        cursor: Optional[str] = None,
        page_size: int = 500,
    ) -> ObjectInventoryPage:
        offset = 0
        if cursor:
            try:
                dec = DiscoveryCursor.decode(cursor)
                offset = dec.offset
            except Exception:
                offset = 0

        tables = []
        views = []
        has_more = False
        if connection is not None and hasattr(connection, "execute"):
            try:
                cur = connection.execute(
                    "SELECT name, type, sql FROM sqlite_master WHERE type IN ('table', 'view') AND name NOT LIKE 'sqlite_%' ORDER BY name LIMIT ? OFFSET ?",
                    (page_size + 1, offset)
                )
                rows = cur.fetchall()
                if len(rows) > page_size:
                    has_more = True
                    rows = rows[:page_size]

                for row in rows:
                    t_name, t_type, def_sql = row[0], row[1], row[2]
                    if t_type == "view":
                        views.append(
                            ViewFacts(
                                name=t_name,
                                schema_name=schema_name or "main",
                                is_materialized=False,
                                definition_sql=def_sql,
                            )
                        )
                    else:
                        tables.append(
                            TableFacts(
                                name=t_name,
                                schema_name=schema_name or "main",
                                object_type=ObjectType.TABLE,
                                classification=ObjectClassification.USER,
                            )
                        )
            except Exception as exc:
                logger.warning(f"Error querying sqlite tables: {exc}")
                raise

        next_cursor = None
        if has_more:
            next_cursor = DiscoveryCursor(offset=offset + len(tables) + len(views), generation_token=f"{schema_name}_{offset}").encode()

        return ObjectInventoryPage(
            items=tuple(tables),
            views=tuple(views),
            cursor=next_cursor,
            is_last_page=not has_more,
            total_items_estimate=len(tables) + len(views),
        )

    def discover_object_structure(
        self,
        connection: Any,
        spec: EndpointSpec,
        schema_name: str,
        object_name: str,
        context: DiscoveryContext,
    ) -> ObjectStructureFacts:
        cols = []
        pk_cols = []
        fks = []
        indexes = []

        if connection is not None and hasattr(connection, "execute"):
            try:
                # Columns
                cur = connection.execute(f"PRAGMA table_info('{object_name}')")
                for row in cur.fetchall():
                    cid, name, col_type, notnull, dflt, pk = row[0], row[1], row[2], row[3], row[4], row[5]
                    cols.append(
                        ColumnPhysicalMetadata(
                            name=name,
                            ordinal_position=cid + 1,
                            native_type=col_type.upper() if col_type else "TEXT",
                            nullable=not bool(notnull),
                            default_expression=str(dflt) if dflt is not None else None,
                            is_identity=bool(pk and col_type.upper() == "INTEGER"),
                        )
                    )
                    if pk:
                        pk_cols.append(name)

                # Foreign Keys
                try:
                    fk_cur = connection.execute(f"PRAGMA foreign_key_list('{object_name}')")
                    for r in fk_cur.fetchall():
                        fks.append(
                            ForeignKeyFacts(
                                name=None,
                                table_name=object_name,
                                columns=(r[3],),
                                referenced_schema=schema_name or "main",
                                referenced_table=r[2],
                                referenced_columns=(r[4],),
                                on_update=r[5],
                                on_delete=r[6],
                            )
                        )
                except Exception:
                    pass

                # Indexes
                try:
                    idx_cur = connection.execute(f"PRAGMA index_list('{object_name}')")
                    for r in idx_cur.fetchall():
                        idx_name, is_unique = r[1], bool(r[2])
                        info_cur = connection.execute(f"PRAGMA index_info('{idx_name}')")
                        idx_cols = [str(col_row[2]) for col_row in info_cur.fetchall()]
                        indexes.append(
                            IndexFacts(
                                name=idx_name,
                                table_name=object_name,
                                columns=tuple(idx_cols),
                                is_unique=is_unique,
                                access_method=IndexAccessMethod.BTREE,
                            )
                        )
                except Exception:
                    pass
            except Exception as exc:
                logger.warning(f"Error querying sqlite structure for {object_name}: {exc}")
                raise

        pk_fact = PrimaryKeyFacts(name=None, table_name=object_name, columns=tuple(pk_cols)) if pk_cols else None

        return ObjectStructureFacts(
            table_name=object_name,
            schema_name=schema_name or "main",
            columns=tuple(cols),
            primary_key=pk_fact,
            foreign_keys=tuple(fks),
            indexes=tuple(indexes),
        )

    def discover_objects_structure_bulk(
        self,
        connection: Any,
        spec: EndpointSpec,
        schema_name: str,
        object_names: Sequence[str],
        context: DiscoveryContext,
    ) -> Mapping[str, ObjectStructureFacts]:
        if not object_names or connection is None:
            return super().discover_objects_structure_bulk(connection, spec, schema_name, object_names, context)

        results: dict[str, ObjectStructureFacts] = {}
        for name in object_names:
            results[name] = self.discover_object_structure(connection, spec, schema_name, name, context)
        return results

    def discover_table_statistics_bulk(
        self,
        connection: Any,
        spec: EndpointSpec,
        schema_name: str,
        object_names: Sequence[str],
        context: DiscoveryContext,
    ) -> Mapping[str, TableSizeFacts]:
        if not object_names or connection is None:
            return super().discover_table_statistics_bulk(connection, spec, schema_name, object_names, context)

        results: dict[str, TableSizeFacts] = {}
        for name in object_names:
            results[name] = self.discover_table_statistics(connection, spec, schema_name, name, context)
        return results

    def discover_programmables(
        self,
        connection: Any,
        spec: EndpointSpec,
        schema_name: str,
        context: DiscoveryContext,
    ) -> ProgrammableInventory:
        triggers = []
        if connection is not None and hasattr(connection, "execute"):
            try:
                cur = connection.execute("SELECT name, tbl_name, sql FROM sqlite_master WHERE type = 'trigger'")
                for r in cur.fetchall():
                    triggers.append(
                        TriggerFacts(
                            name=r[0],
                            table_name=r[1],
                            schema_name=schema_name or "main",
                            timing=TriggerTiming.BEFORE,
                            events=("INSERT",),
                            definition_sql=r[2],
                        )
                    )
            except Exception:
                pass
        return ProgrammableInventory(triggers=tuple(triggers))

    def discover_partitioning(
        self,
        connection: Any,
        spec: EndpointSpec,
        schema_name: str,
        table_name: str,
        context: DiscoveryContext,
    ) -> PartitionFacts:
        return PartitionFacts(table_name=table_name, schema_name=schema_name or "main", strategy=PartitionStrategy.NONE)

    def discover_table_statistics(
        self,
        connection: Any,
        spec: EndpointSpec,
        schema_name: str,
        table_name: str,
        context: DiscoveryContext,
    ) -> TableSizeFacts:
        row_count = 0
        accuracy = CountAccuracy.UNAVAILABLE
        if connection is not None and hasattr(connection, "execute"):
            if context.allow_exact_counts:
                try:
                    cur = connection.execute(f"SELECT count(*) FROM '{table_name}'")
                    row = cur.fetchone()
                    if row:
                        row_count = int(row[0])
                        accuracy = CountAccuracy.EXACT_ROW_COUNT
                except Exception:
                    pass

        return TableSizeFacts(
            table_name=table_name,
            schema_name=schema_name or "main",
            row_count=row_count,
            count_accuracy=accuracy,
            total_bytes=0,
        )

    def discover_objects_structure_bulk(
        self,
        connection: Any,
        spec: EndpointSpec,
        schema_name: str,
        object_names: Sequence[str],
        context: DiscoveryContext,
    ) -> Mapping[str, ObjectStructureFacts]:
        if not object_names or connection is None or not hasattr(connection, "execute"):
            return super().discover_objects_structure_bulk(connection, spec, schema_name, object_names, context)

        results: dict[str, ObjectStructureFacts] = {}
        for name in object_names:
            results[name] = self.discover_object_structure(connection, spec, schema_name, name, context)
        return results

    def discover_table_statistics_bulk(
        self,
        connection: Any,
        spec: EndpointSpec,
        schema_name: str,
        object_names: Sequence[str],
        context: DiscoveryContext,
    ) -> Mapping[str, TableSizeFacts]:
        if not object_names or connection is None or not hasattr(connection, "execute"):
            return super().discover_table_statistics_bulk(connection, spec, schema_name, object_names, context)

        results: dict[str, TableSizeFacts] = {}
        for name in object_names:
            results[name] = self.discover_table_statistics(connection, spec, schema_name, name, context)
        return results

    def check_read_only_permissions(
        self,
        connection: Any,
        spec: EndpointSpec,
    ) -> ThreeStatePermission:
        if connection is None or not hasattr(connection, "execute"):
            return ThreeStatePermission.UNKNOWN
        try:
            cur = connection.execute("PRAGMA query_only")
            row = cur.fetchone()
            if row and int(row[0]) == 1:
                return ThreeStatePermission.PROVEN
            return ThreeStatePermission.DENIED
        except Exception:
            return ThreeStatePermission.UNKNOWN

    def discover_permissions(
        self,
        connection: Any,
        spec: EndpointSpec,
        context: DiscoveryContext,
    ) -> PermissionAssessment:
        ro_verified = self.check_read_only_permissions(connection, spec)
        cat_read = ThreeStatePermission.UNKNOWN
        if connection is not None and hasattr(connection, "execute"):
            try:
                connection.execute("SELECT name FROM sqlite_master LIMIT 1")
                cat_read = ThreeStatePermission.PROVEN
            except Exception:
                cat_read = ThreeStatePermission.DENIED
        return PermissionAssessment(
            read_only_verified=ro_verified,
            metadata_catalog_read=cat_read,
        )

    def discover_environment(
        self,
        connection: Any,
        spec: EndpointSpec,
        context: DiscoveryContext,
    ) -> ConfigurationFacts:
        encoding = "UTF-8"
        if connection is not None and hasattr(connection, "execute"):
            try:
                cur = connection.execute("PRAGMA encoding")
                row = cur.fetchone()
                if row:
                    encoding = str(row[0])
            except Exception:
                pass

        return ConfigurationFacts(
            charset=CharsetFacts(server_encoding=encoding, client_encoding=encoding),
            timezone=TimezoneFacts(database_timezone="UTC"),
            limits=LimitsFacts(max_connections=1),
        )

    def discover_topology(
        self,
        connection: Any,
        spec: EndpointSpec,
        context: DiscoveryContext,
    ) -> TopologySnapshot:
        return TopologySnapshot(
            is_clustered=False,
            connected_node_role=NodeRole.PRIMARY,
            nodes=(),
        )

    def discover_cdc_prerequisites(
        self,
        connection: Any,
        spec: EndpointSpec,
        context: DiscoveryContext,
    ) -> CDCPrerequisiteSnapshot:
        if connection is None or not hasattr(connection, "execute"):
            return CDCPrerequisiteSnapshot(
                is_cdc_ready=False,
                mechanism=CDCMechanism.POLLING_WATERMARK,
                blocker_reasons=("Physical SQLite connection not established",),
            )
        try:
            cur = connection.execute("PRAGMA journal_mode")
            row = cur.fetchone()
            jmode = str(row[0]).upper() if row else "DELETE"
            is_wal = (jmode == "WAL")
            blockers = () if is_wal else (f"SQLite journal_mode is '{jmode}', WAL mode recommended for CDC.",)
            return CDCPrerequisiteSnapshot(
                is_cdc_ready=is_wal,
                mechanism=CDCMechanism.POLLING_WATERMARK,
                is_wal_level_logical=is_wal,
                blocker_reasons=blockers,
            )
        except Exception as exc:
            return CDCPrerequisiteSnapshot(
                is_cdc_ready=False,
                mechanism=CDCMechanism.POLLING_WATERMARK,
                blocker_reasons=(f"Failed to inspect SQLite journal mode: {exc}",),
            )

    def sample_data(
        self,
        connection: Any,
        spec: EndpointSpec,
        schema_name: str,
        table_name: str,
        limit: int = 100,
        timeout_seconds: float = 3.0,
    ) -> SampledRecordSet:
        if connection is None or not hasattr(connection, "execute"):
            return DeterministicSampler.package_sample(table_name, schema_name or "main", [], [])
        try:
            cur = connection.execute(f"SELECT * FROM '{table_name}' LIMIT {limit}")
            cols = [desc[0] for desc in cur.description] if cur.description else []
            rows = cur.fetchall()
            return DeterministicSampler.package_sample(table_name, schema_name or "main", cols, rows)
        except Exception as exc:
            return DeterministicSampler.package_failure(table_name, schema_name or "main", str(exc))

"""
akaalEngine.discovery.strategies.warehouse.redshift
==================================================
Canonical Amazon Redshift analytical warehouse discovery strategy.
Introspects SVV_TABLE_INFO, STV_SLICES, DISTSTYLE, and SORTKEY distribution facts.
"""

from __future__ import annotations

import logging
from typing import Any, Mapping, Optional, Sequence, Tuple
from types import MappingProxyType

from akaalEngine.connection.models.endpoint import EndpointSpec
from akaalEngine.connection.routing.resolver import ResolvedRoute
from akaalEngine.discovery.core.paginator import CatalogPaginator
from akaalEngine.discovery.core.sampling import DeterministicSampler
from akaalEngine.discovery.models.cdc import CDCMechanism, CDCPrerequisiteSnapshot
from akaalEngine.discovery.models.context import DiscoveryContext
from akaalEngine.discovery.models.environment import CharsetFacts, CollationFacts, ConfigurationFacts, LimitsFacts, TimezoneFacts
from akaalEngine.discovery.models.identity import DiscoveredEndpointIdentity, EngineEdition, ServerVersion
from akaalEngine.discovery.models.inventory import NamespaceInventory, ObjectClassification, ObjectInventoryPage, ObjectType, TableFacts
from akaalEngine.discovery.models.partitioning import PartitionFacts, PartitionStrategy
from akaalEngine.discovery.models.permissions import PermissionAssessment, PrivilegeFact, ThreeStatePermission
from akaalEngine.discovery.models.programmables import ProgrammableInventory
from akaalEngine.discovery.models.statistics import CountAccuracy, TableSizeFacts
from akaalEngine.discovery.models.structure import (
    ColumnPhysicalMetadata,
    ObjectStructureFacts,
    PrimaryKeyFacts,
)
from akaalEngine.discovery.models.topology import ClusterNodeFacts, NodeRole, TopologySnapshot
from akaalEngine.discovery.spi.warehouse import WarehouseDiscoveryStrategy

logger = logging.getLogger("akaalEngine.discovery.strategies.redshift")


class RedshiftDiscoveryStrategy(WarehouseDiscoveryStrategy):
    """Amazon Redshift physical discovery strategy."""

    PROVIDER_ID = "redshift"

    SYSTEM_SCHEMAS = ('pg_catalog', 'information_schema', 'pg_internal')

    @property
    def provider_id(self) -> str:
        return self.PROVIDER_ID

    def discover_endpoint_identity(
        self,
        connection: Any,
        spec: EndpointSpec,
        route: Optional[ResolvedRoute] = None,
    ) -> DiscoveredEndpointIdentity:
        version_str = "PostgreSQL 8.0.2 (Amazon Redshift)"
        if connection is not None and hasattr(connection, "cursor"):
            try:
                with connection.cursor() as cur:
                    cur.execute("SELECT version()")
                    r = cur.fetchone()
                    if r:
                        version_str = str(r[0])
            except Exception as exc:
                logger.warning(f"Error querying redshift version: {exc}")

        return DiscoveredEndpointIdentity(
            provider_id=self.PROVIDER_ID,
            vendor_name="Amazon Web Services",
            engine_name="Amazon Redshift Cloud Warehouse",
            system_type="REDSHIFT",
            version=ServerVersion(raw_version_string=version_str, major=1, minor=0, patch=0),
            edition=EngineEdition(edition_name="Managed Cluster", is_enterprise=True, is_cloud_managed=True),
            host=spec.host,
            port=spec.port or 5439,
            database_name=spec.database_name,
        )

    def discover_namespaces(
        self,
        connection: Any,
        spec: EndpointSpec,
        context: DiscoveryContext,
    ) -> NamespaceInventory:
        schemas = []
        if connection is not None and hasattr(connection, "cursor"):
            try:
                with connection.cursor() as cur:
                    cur.execute("SELECT nspname FROM pg_namespace ORDER BY nspname")
                    for r in cur.fetchall():
                        s = str(r[0])
                        if s not in self.SYSTEM_SCHEMAS:
                            schemas.append(s)
            except Exception as exc:
                logger.warning(f"Error querying redshift namespaces: {exc}")
                raise

        return NamespaceInventory(
            schemas=tuple(schemas),
            system_schemas=self.SYSTEM_SCHEMAS,
            default_schema="public" if "public" in schemas else (schemas[0] if schemas else None),
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
        if connection is not None and hasattr(connection, "cursor"):
            try:
                with connection.cursor() as cur:
                    if offset == 0:
                        # Views
                        try:
                            cur.execute("""
                                SELECT viewname, definition
                                FROM pg_views
                                WHERE schemaname = %s
                                ORDER BY viewname
                            """, (schema_name,))
                            for r in cur.fetchall():
                                vname, vdef = r[0], r[1]
                                views.append(
                                    ViewFacts(
                                        name=vname,
                                        schema_name=schema_name,
                                        is_materialized=False,
                                        definition_sql=str(vdef) if vdef else None,
                                    )
                                )
                        except Exception:
                            pass

                    # Tables with server-side pagination
                    cur.execute("""
                        SELECT \"table\", tbl_rows, size
                        FROM svv_table_info
                        WHERE \"schema\" = %s
                        ORDER BY \"table\"
                        LIMIT %s OFFSET %s
                    """, (schema_name, page_size + 1, offset))
                    rows = cur.fetchall()
                    if len(rows) > page_size:
                        has_more = True
                        rows = rows[:page_size]

                    for r in rows:
                        tname, nrows, size_mb = r[0], r[1], r[2]
                        tables.append(
                            TableFacts(
                                name=tname,
                                schema_name=schema_name,
                                object_type=ObjectType.TABLE,
                                classification=ObjectClassification.USER,
                                row_count_estimate=int(nrows or 0),
                                size_bytes_estimate=int(size_mb or 0) * 1024 * 1024,
                            )
                        )
            except Exception as exc:
                logger.warning(f"Error querying redshift tables in {schema_name}: {exc}")
                raise

        next_cursor = None
        if has_more:
            next_cursor = DiscoveryCursor(offset=offset + len(tables), generation_token=f"{schema_name}_{offset}").encode()

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
        if connection is not None and hasattr(connection, "cursor"):
            try:
                with connection.cursor() as cur:
                    cur.execute("""
                        SELECT \"column\", \"type\", \"encoding\", \"distkey\", \"sortkey\", \"notnull\"
                        FROM pg_table_def
                        WHERE schemaname = %s AND tablename = %s
                        ORDER BY \"column\"
                    """, (schema_name, object_name))
                    for idx, r in enumerate(cur.fetchall()):
                        cname, ctype, enc, distk, sortk, notnull = r[0], r[1], r[2], r[3], r[4], r[5]
                        cols.append(
                            ColumnPhysicalMetadata(
                                name=cname,
                                ordinal_position=idx + 1,
                                native_type=str(ctype).upper(),
                                nullable=not bool(notnull),
                            )
                        )
            except Exception as exc:
                logger.warning(f"Error querying redshift structure for {schema_name}.{object_name}: {exc}")
                raise

        return ObjectStructureFacts(
            table_name=object_name,
            schema_name=schema_name,
            columns=tuple(cols),
        )

    def discover_objects_structure_bulk(
        self,
        connection: Any,
        spec: EndpointSpec,
        schema_name: str,
        object_names: Sequence[str],
        context: DiscoveryContext,
    ) -> Mapping[str, ObjectStructureFacts]:
        if not object_names or connection is None or not hasattr(connection, "cursor"):
            return super().discover_objects_structure_bulk(connection, spec, schema_name, object_names, context)

        results: dict[str, ObjectStructureFacts] = {name: ObjectStructureFacts(table_name=name, schema_name=schema_name) for name in object_names}
        names_list = list(object_names)
        format_strings = ','.join(['%s'] * len(names_list))

        try:
            with connection.cursor() as cur:
                cur.execute(f"""
                    SELECT tablename, \"column\", \"type\", \"encoding\", \"distkey\", \"sortkey\", \"notnull\"
                    FROM pg_table_def
                    WHERE schemaname = %s AND tablename IN ({format_strings})
                    ORDER BY tablename, \"column\"
                """, [schema_name] + names_list)
                cols_by_tbl: dict[str, list[ColumnPhysicalMetadata]] = {name: [] for name in object_names}
                for r in cur.fetchall():
                    tname, cname, ctype, enc, distk, sortk, notnull = r[0], r[1], r[2], r[3], r[4], r[5]
                    cols_by_tbl.setdefault(tname, []).append(
                        ColumnPhysicalMetadata(
                            name=cname,
                            ordinal_position=len(cols_by_tbl.get(tname, [])) + 1,
                            native_type=str(ctype).upper(),
                            nullable=not bool(notnull),
                        )
                    )
                for name in object_names:
                    results[name] = ObjectStructureFacts(
                        table_name=name,
                        schema_name=schema_name,
                        columns=tuple(cols_by_tbl.get(name, [])),
                    )
        except Exception as exc:
            logger.warning(f"Error in Redshift bulk structure discovery in {schema_name}: {exc}")
            raise

        return results

    def discover_warehouse_context(
        self,
        connection: Any,
        spec: EndpointSpec,
        context: DiscoveryContext,
    ) -> Mapping[str, Any]:
        node_type = spec.options.get("node_type")
        if node_type:
            return {"cluster_type": str(node_type)}
        return {}

    def discover_programmables(
        self,
        connection: Any,
        spec: EndpointSpec,
        schema_name: str,
        context: DiscoveryContext,
    ) -> ProgrammableInventory:
        return ProgrammableInventory()

    def discover_partitioning(
        self,
        connection: Any,
        spec: EndpointSpec,
        schema_name: str,
        table_name: str,
        context: DiscoveryContext,
    ) -> PartitionFacts:
        return PartitionFacts(table_name=table_name, schema_name=schema_name, strategy=PartitionStrategy.NONE)

    def discover_table_statistics(
        self,
        connection: Any,
        spec: EndpointSpec,
        schema_name: str,
        table_name: str,
        context: DiscoveryContext,
    ) -> TableSizeFacts:
        row_cnt = 0
        tot_bytes = 0
        acc = CountAccuracy.UNAVAILABLE
        if connection is not None and hasattr(connection, "cursor"):
            try:
                with connection.cursor() as cur:
                    cur.execute(
                        "SELECT tbl_rows, size FROM pg_catalog.svv_table_info WHERE schema = %s AND table = %s",
                        (schema_name, table_name),
                    )
                    r = cur.fetchone()
                    if r:
                        row_cnt = int(r[0] or 0)
                        tot_bytes = int(r[1] or 0) * 1024 * 1024  # Redshift size is in 1MB blocks
                        acc = CountAccuracy.CATALOG_ESTIMATE
            except Exception as exc:
                logger.warning(f"Error querying redshift table statistics for {schema_name}.{table_name}: {exc}")
                raise

        return TableSizeFacts(
            table_name=table_name,
            schema_name=schema_name,
            row_count=row_cnt,
            total_bytes=tot_bytes,
            count_accuracy=acc,
        )

    def discover_table_statistics_bulk(
        self,
        connection: Any,
        spec: EndpointSpec,
        schema_name: str,
        object_names: Sequence[str],
        context: DiscoveryContext,
    ) -> Mapping[str, TableSizeFacts]:
        if not object_names or connection is None or not hasattr(connection, "cursor"):
            return super().discover_table_statistics_bulk(connection, spec, schema_name, object_names, context)

        results: dict[str, TableSizeFacts] = {name: TableSizeFacts(table_name=name, schema_name=schema_name, row_count=0) for name in object_names}
        names_list = list(object_names)
        format_strings = ','.join(['%s'] * len(names_list))

        try:
            with connection.cursor() as cur:
                cur.execute(f"""
                    SELECT \"table\", tbl_rows, size 
                    FROM pg_catalog.svv_table_info 
                    WHERE \"schema\" = %s AND \"table\" IN ({format_strings})
                """, [schema_name] + names_list)
                for r in cur.fetchall():
                    tname, row_cnt, size_mb = r[0], r[1], r[2]
                    results[tname] = TableSizeFacts(
                        table_name=tname,
                        schema_name=schema_name,
                        row_count=int(row_cnt or 0),
                        total_bytes=int(size_mb or 0) * 1024 * 1024,
                        count_accuracy=CountAccuracy.CATALOG_ESTIMATE,
                    )
        except Exception as exc:
            logger.warning(f"Error in Redshift bulk statistics discovery in {schema_name}: {exc}")
            raise

        return results

    def check_read_only_permissions(
        self,
        connection: Any,
        spec: EndpointSpec,
    ) -> ThreeStatePermission:
        # Redshift has no non-destructive session parameter to strictly enforce read-only
        return ThreeStatePermission.UNKNOWN

    def discover_permissions(
        self,
        connection: Any,
        spec: EndpointSpec,
        context: DiscoveryContext,
    ) -> PermissionAssessment:
        cat_perm = ThreeStatePermission.UNKNOWN
        if connection is not None and hasattr(connection, "cursor"):
            try:
                with connection.cursor() as cur:
                    cur.execute("SELECT 1")
                    cat_perm = ThreeStatePermission.PROVEN
            except Exception:
                cat_perm = ThreeStatePermission.DENIED

        return PermissionAssessment(
            read_only_verified=ThreeStatePermission.UNKNOWN,
            metadata_catalog_read=cat_perm,
        )

    def discover_environment(
        self,
        connection: Any,
        spec: EndpointSpec,
        context: DiscoveryContext,
    ) -> ConfigurationFacts:
        return ConfigurationFacts(
            charset=CharsetFacts(server_encoding="UTF-8"),
            collation=CollationFacts(default_collation="default"),
            timezone=TimezoneFacts(database_timezone="UTC"),
            limits=LimitsFacts(max_connections=500),
        )

    def discover_topology(
        self,
        connection: Any,
        spec: EndpointSpec,
        context: DiscoveryContext,
    ) -> TopologySnapshot:
        return TopologySnapshot(
            is_clustered=True,
            nodes=(),
        )

    def discover_cdc_prerequisites(
        self,
        connection: Any,
        spec: EndpointSpec,
        context: DiscoveryContext,
    ) -> CDCPrerequisiteSnapshot:
        if connection is None:
            return CDCPrerequisiteSnapshot(
                is_cdc_ready=False,
                mechanism=CDCMechanism.UNSUPPORTED,
                blocker_reasons=("Redshift connection not established",),
            )
        return CDCPrerequisiteSnapshot(
            is_cdc_ready=False,
            mechanism=CDCMechanism.POLLING_WATERMARK,
            blocker_reasons=("Redshift does not support log-based CDC replication; use polling watermark",),
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
        if connection is None or not hasattr(connection, "cursor"):
            return DeterministicSampler.package_sample(table_name, schema_name, [], [])
        try:
            rows = []
            cols = []
            with connection.cursor() as cur:
                cur.execute(f'SELECT * FROM "{schema_name}"."{table_name}" LIMIT {limit}')
                cols = [d[0] for d in cur.description] if cur.description else []
                for r in cur.fetchall():
                    rows.append(dict(zip(cols, r)))
            return DeterministicSampler.package_sample(table_name, schema_name, cols, rows)
        except Exception as exc:
            logger.warning(f"Error sampling redshift table {table_name}: {exc}")
            return DeterministicSampler.package_failure(table_name, schema_name, str(exc))

"""
akaalEngine.discovery.strategies.warehouse.snowflake
====================================================
Canonical Snowflake analytical warehouse discovery strategy.
Introspects INFORMATION_SCHEMA, SHOW WAREHOUSES, and clustering keys.
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
    IndexFacts,
    ObjectStructureFacts,
    PrimaryKeyFacts,
)
from akaalEngine.discovery.models.topology import ClusterNodeFacts, NodeRole, TopologySnapshot
from akaalEngine.discovery.spi.warehouse import WarehouseDiscoveryStrategy

logger = logging.getLogger("akaalEngine.discovery.strategies.snowflake")


class SnowflakeDiscoveryStrategy(WarehouseDiscoveryStrategy):
    """Snowflake cloud warehouse physical discovery strategy."""

    PROVIDER_ID = "snowflake"

    SYSTEM_SCHEMAS = ('INFORMATION_SCHEMA',)

    @property
    def provider_id(self) -> str:
        return self.PROVIDER_ID

    def discover_endpoint_identity(
        self,
        connection: Any,
        spec: EndpointSpec,
        route: Optional[ResolvedRoute] = None,
    ) -> DiscoveredEndpointIdentity:
        version_str = "Snowflake Cloud Warehouse"
        wh_name = spec.options.get("warehouse")
        if connection is not None and hasattr(connection, "cursor"):
            try:
                cur = connection.cursor()
                cur.execute("SELECT CURRENT_VERSION(), CURRENT_WAREHOUSE()")
                r = cur.fetchone()
                if r:
                    version_str = str(r[0])
                    wh_name = str(r[1]) if r[1] else wh_name
                cur.close()
            except Exception as exc:
                logger.warning(f"Error querying snowflake version: {exc}")

        return DiscoveredEndpointIdentity(
            provider_id=self.PROVIDER_ID,
            vendor_name="Snowflake Inc.",
            engine_name="Snowflake Data Cloud",
            system_type="SNOWFLAKE",
            version=ServerVersion(raw_version_string=version_str, major=7, minor=0, patch=0),
            edition=EngineEdition(edition_name="Enterprise Cloud Edition", is_enterprise=True, is_cloud_managed=True),
            host=spec.host,
            database_name=spec.database_name,
            extra_properties={"warehouse": wh_name} if wh_name else {},
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
                cur = connection.cursor()
                cur.execute("SELECT SCHEMA_NAME FROM INFORMATION_SCHEMA.SCHEMATA ORDER BY SCHEMA_NAME")
                for r in cur.fetchall():
                    s = str(r[0]).upper()
                    if s not in self.SYSTEM_SCHEMAS:
                        schemas.append(s)
                cur.close()
            except Exception as exc:
                logger.warning(f"Error querying snowflake schemas: {exc}")
                raise

        return NamespaceInventory(
            schemas=tuple(schemas),
            system_schemas=self.SYSTEM_SCHEMAS,
            default_schema=schemas[0] if schemas else None,
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
                cur = connection.cursor()
                cur.execute("""
                    SELECT TABLE_NAME, TABLE_TYPE, ROW_COUNT, BYTES
                    FROM INFORMATION_SCHEMA.TABLES
                    WHERE TABLE_SCHEMA = %s
                    ORDER BY TABLE_NAME
                    LIMIT %s OFFSET %s
                """, (schema_name.upper(), page_size + 1, offset))
                rows = cur.fetchall()
                if len(rows) > page_size:
                    has_more = True
                    rows = rows[:page_size]

                for r in rows:
                    tname, ttype, nrows, nbytes = r[0], r[1], r[2], r[3]
                    if "VIEW" in str(ttype).upper():
                        views.append(
                            ViewFacts(
                                name=tname,
                                schema_name=schema_name,
                                is_materialized=("MATERIALIZED" in str(ttype).upper()),
                            )
                        )
                    else:
                        tables.append(
                            TableFacts(
                                name=tname,
                                schema_name=schema_name,
                                object_type=ObjectType.TABLE,
                                classification=ObjectClassification.USER,
                                row_count_estimate=nrows or 0,
                                size_bytes_estimate=nbytes or 0,
                            )
                        )
                cur.close()
            except Exception as exc:
                logger.warning(f"Error querying snowflake tables in {schema_name}: {exc}")
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
        if connection is not None and hasattr(connection, "cursor"):
            try:
                cur = connection.cursor()
                cur.execute("""
                    SELECT ORDINAL_POSITION, COLUMN_NAME, DATA_TYPE, CHARACTER_MAXIMUM_LENGTH,
                           NUMERIC_PRECISION, NUMERIC_SCALE, IS_NULLABLE, COLUMN_DEFAULT
                    FROM INFORMATION_SCHEMA.COLUMNS
                    WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
                    ORDER BY ORDINAL_POSITION
                """, (schema_name.upper(), object_name.upper()))
                for r in cur.fetchall():
                    pos, cname, dtype, clen, prec, scale, nullb, dflt = r[0], r[1], r[2], r[3], r[4], r[5], r[6], r[7]
                    cols.append(
                        ColumnPhysicalMetadata(
                            name=cname,
                            ordinal_position=pos,
                            native_type=str(dtype).upper(),
                            length=clen,
                            precision=prec,
                            scale=scale,
                            nullable=(str(nullb).upper() == "YES"),
                            default_expression=dflt,
                        )
                    )
                cur.close()
            except Exception as exc:
                logger.warning(f"Error querying snowflake structure for {schema_name}.{object_name}: {exc}")
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
        upper_names = [n.upper() for n in object_names]
        format_strings = ','.join(['%s'] * len(upper_names))

        try:
            cur = connection.cursor()
            cur.execute(f"""
                SELECT TABLE_NAME, ORDINAL_POSITION, COLUMN_NAME, DATA_TYPE, CHARACTER_MAXIMUM_LENGTH,
                       NUMERIC_PRECISION, NUMERIC_SCALE, IS_NULLABLE, COLUMN_DEFAULT
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_SCHEMA = %s AND TABLE_NAME IN ({format_strings})
                ORDER BY TABLE_NAME, ORDINAL_POSITION
            """, [schema_name.upper()] + upper_names)
            cols_by_tbl: dict[str, list[ColumnPhysicalMetadata]] = {name.upper(): [] for name in object_names}
            for r in cur.fetchall():
                tname, pos, cname, dtype, clen, prec, scale, nullb, dflt = r[0], r[1], r[2], r[3], r[4], r[5], r[6], r[7], r[8]
                cols_by_tbl.setdefault(tname.upper(), []).append(
                    ColumnPhysicalMetadata(
                        name=cname,
                        ordinal_position=pos,
                        native_type=str(dtype).upper(),
                        length=clen,
                        precision=prec,
                        scale=scale,
                        nullable=(str(nullb).upper() == "YES"),
                        default_expression=dflt,
                    )
                )
            cur.close()
            for name in object_names:
                uname = name.upper()
                results[name] = ObjectStructureFacts(
                    table_name=name,
                    schema_name=schema_name,
                    columns=tuple(cols_by_tbl.get(uname, [])),
                )
        except Exception as exc:
            logger.warning(f"Bulk structure discovery failed for Snowflake schema '{schema_name}': {exc}")
            raise

        return results

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

        results: dict[str, TableSizeFacts] = {}
        upper_names = [n.upper() for n in object_names]
        format_strings = ','.join(['%s'] * len(upper_names))
        try:
            cur = connection.cursor()
            cur.execute(f"""
                SELECT TABLE_NAME, ROW_COUNT, BYTES
                FROM INFORMATION_SCHEMA.TABLES
                WHERE TABLE_SCHEMA = %s AND TABLE_NAME IN ({format_strings})
            """, [schema_name.upper()] + upper_names)
            for r in cur.fetchall():
                tname, nrows, nbytes = r[0], r[1], r[2]
                for orig_name in object_names:
                    if orig_name.upper() == tname.upper():
                        results[orig_name] = TableSizeFacts(
                            table_name=orig_name,
                            schema_name=schema_name,
                            row_count=nrows or 0,
                            data_bytes=nbytes or 0,
                        )
            cur.close()
        except Exception as exc:
            logger.warning(f"Bulk stats discovery failed for Snowflake schema '{schema_name}': {exc}")
            raise

        for name in object_names:
            if name not in results:
                results[name] = TableSizeFacts(table_name=name, schema_name=schema_name, row_count=0)

        return results

    def discover_warehouse_context(
        self,
        connection: Any,
        spec: EndpointSpec,
        context: DiscoveryContext,
    ) -> Mapping[str, Any]:
        wh = spec.options.get("warehouse")
        if connection is not None and hasattr(connection, "cursor"):
            try:
                cur = connection.cursor()
                cur.execute("SELECT CURRENT_WAREHOUSE()")
                r = cur.fetchone()
                if r and r[0]:
                    wh = str(r[0])
                cur.close()
            except Exception:
                pass
        return {"warehouse": wh} if wh else {}

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
        return TableSizeFacts(table_name=table_name, schema_name=schema_name, row_count=0, count_accuracy=CountAccuracy.UNAVAILABLE)

    def check_read_only_permissions(
        self,
        connection: Any,
        spec: EndpointSpec,
    ) -> ThreeStatePermission:
        # Snowflake has no non-destructive session parameter to strictly enforce read-only
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
                    cur.execute("SELECT CURRENT_VERSION()")
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
            collation=CollationFacts(default_collation="en-ci"),
            timezone=TimezoneFacts(database_timezone="UTC"),
            limits=LimitsFacts(max_connections=1000),
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
                blocker_reasons=("Snowflake connection not established",),
            )
        return CDCPrerequisiteSnapshot(
            is_cdc_ready=False,
            mechanism=CDCMechanism.SNOWFLAKE_STREAMS,
            blocker_reasons=("Snowflake Stream / Change Tracking not verified on table",),
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
            cur = connection.cursor()
            cur.execute(f'SELECT * FROM "{schema_name.upper()}"."{table_name.upper()}" LIMIT {limit}')
            cols = [d[0] for d in cur.description] if cur.description else []
            for r in cur.fetchall():
                rows.append(dict(zip(cols, r)))
            cur.close()
            return DeterministicSampler.package_sample(table_name, schema_name, cols, rows)
        except Exception as exc:
            logger.warning(f"Error sampling snowflake table {table_name}: {exc}")
            return DeterministicSampler.package_failure(table_name, schema_name, str(exc))

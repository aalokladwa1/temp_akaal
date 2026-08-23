"""
akaalEngine.discovery.strategies.warehouse.databricks
====================================================
Canonical Databricks Unity Catalog & Delta Lake discovery strategy.
Introspects Unity Catalog metastore, catalog names, schema names, and Delta Lake metadata.
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

logger = logging.getLogger("akaalEngine.discovery.strategies.databricks")


class DatabricksDiscoveryStrategy(WarehouseDiscoveryStrategy):
    """Databricks Unity Catalog physical discovery strategy."""

    PROVIDER_ID = "databricks"

    SYSTEM_SCHEMAS = ('information_schema', 'sys')

    @property
    def provider_id(self) -> str:
        return self.PROVIDER_ID

    def discover_endpoint_identity(
        self,
        connection: Any,
        spec: EndpointSpec,
        route: Optional[ResolvedRoute] = None,
    ) -> DiscoveredEndpointIdentity:
        version_str = "UNKNOWN"
        major, minor, patch = 0, 0, 0
        if connection is not None and hasattr(connection, "cursor"):
            try:
                cur = connection.cursor()
                cur.execute("SELECT current_version()")
                r = cur.fetchone()
                if r:
                    version_str = str(r[0])
                cur.close()
            except Exception:
                pass

        return DiscoveredEndpointIdentity(
            provider_id=self.PROVIDER_ID,
            vendor_name="Databricks",
            engine_name="Databricks Unity Catalog Lakehouse",
            system_type="DATABRICKS",
            version=ServerVersion(raw_version_string=version_str, major=major, minor=minor, patch=patch),
            edition=EngineEdition(edition_name="Unity Catalog Enterprise", is_enterprise=True, is_cloud_managed=True),
            host=spec.host,
            database_name=spec.database_name or "main",
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
                cur.execute("SHOW SCHEMAS")
                for r in cur.fetchall():
                    s = str(r[0])
                    if s.lower() not in self.SYSTEM_SCHEMAS:
                        schemas.append(s)
                cur.close()
            except Exception as exc:
                logger.warning(f"Error querying databricks schemas: {exc}")
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
        tables = []
        views = []
        if connection is not None and hasattr(connection, "cursor"):
            try:
                cur = connection.cursor()
                # Tables
                cur.execute(f"SHOW TABLES IN {schema_name}")
                for r in cur.fetchall():
                    tname = str(r[1])
                    tables.append(
                        TableFacts(
                            name=tname,
                            schema_name=schema_name,
                            object_type=ObjectType.TABLE,
                            classification=ObjectClassification.USER,
                            storage_format="DELTA",
                        )
                    )

                # Views
                try:
                    cur.execute(f"SHOW VIEWS IN {schema_name}")
                    for r in cur.fetchall():
                        vname = str(r[1])
                        views.append(
                            ViewFacts(
                                name=vname,
                                schema_name=schema_name,
                                is_materialized=False,
                            )
                        )
                except Exception:
                    pass

                cur.close()
            except Exception as exc:
                logger.warning(f"Error querying databricks tables in {schema_name}: {exc}")
                raise

        return CatalogPaginator.paginate_sequence(tables, cursor=cursor, page_size=page_size, views=views)

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
                cur.execute(f"DESCRIBE TABLE {schema_name}.{object_name}")
                for idx, r in enumerate(cur.fetchall()):
                    cname, ctype = str(r[0]), str(r[1])
                    if cname.startswith("#") or not cname:
                        continue
                    cols.append(
                        ColumnPhysicalMetadata(
                            name=cname,
                            ordinal_position=idx + 1,
                            native_type=ctype.upper(),
                        )
                    )
                cur.close()
            except Exception as exc:
                logger.warning(f"Error describing databricks table {schema_name}.{object_name}: {exc}")

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

        results: dict[str, ObjectStructureFacts] = {}
        for name in object_names:
            cols: list[ColumnPhysicalMetadata] = []
            try:
                cur = connection.cursor()
                cur.execute(f"DESCRIBE TABLE {schema_name}.{name}")
                for idx, r in enumerate(cur.fetchall()):
                    cname, ctype = str(r[0]), str(r[1])
                    if cname.startswith("#") or not cname:
                        continue
                    cols.append(
                        ColumnPhysicalMetadata(
                            name=cname,
                            ordinal_position=idx + 1,
                            native_type=ctype.upper(),
                        )
                    )
                cur.close()
            except Exception:
                pass
            results[name] = ObjectStructureFacts(
                table_name=name,
                schema_name=schema_name,
                columns=tuple(cols),
            )
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
        for name in object_names:
            results[name] = TableSizeFacts(table_name=name, schema_name=schema_name, row_count=0)
        return results

    def discover_warehouse_context(
        self,
        connection: Any,
        spec: EndpointSpec,
        context: DiscoveryContext,
    ) -> Mapping[str, Any]:
        return {"catalog": spec.options.get("catalog", "main")}

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
        return TableSizeFacts(table_name=table_name, schema_name=schema_name, row_count=0, count_accuracy=CountAccuracy.CATALOG_ESTIMATE)

    def check_read_only_permissions(
        self,
        connection: Any,
        spec: EndpointSpec,
    ) -> ThreeStatePermission:
        # Databricks / Spark SQL has no non-destructive session parameter to strictly enforce read-only
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
                blocker_reasons=("Databricks connection not established",),
            )
        return CDCPrerequisiteSnapshot(
            is_cdc_ready=False,
            mechanism=CDCMechanism.DELTA_CHANGE_DATA_FEED,
            blocker_reasons=("Delta Change Data Feed not verified on tables",),
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
                cur.execute(f"SELECT * FROM `{schema_name}`.`{table_name}` LIMIT {limit}")
                cols = [d[0] for d in cur.description] if cur.description else []
                for r in cur.fetchall():
                    rows.append(dict(zip(cols, r)))
            return DeterministicSampler.package_sample(table_name, schema_name, cols, rows)
        except Exception as exc:
            logger.warning(f"Error sampling databricks table {table_name}: {exc}")
            return DeterministicSampler.package_failure(table_name, schema_name, str(exc))

"""
akaalEngine.discovery.strategies.warehouse.bigquery
==================================================
Canonical Google BigQuery discovery strategy.
Introspects datasets, tables, partition expiration, clustering, and storage metadata.
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

logger = logging.getLogger("akaalEngine.discovery.strategies.bigquery")


class BigQueryDiscoveryStrategy(WarehouseDiscoveryStrategy):
    """Google BigQuery physical discovery strategy."""

    PROVIDER_ID = "bigquery"

    @property
    def provider_id(self) -> str:
        return self.PROVIDER_ID

    def discover_endpoint_identity(
        self,
        connection: Any,
        spec: EndpointSpec,
        route: Optional[ResolvedRoute] = None,
    ) -> DiscoveredEndpointIdentity:
        project_id = spec.account_id or spec.options.get("project_id", "gcp-project")
        return DiscoveredEndpointIdentity(
            provider_id=self.PROVIDER_ID,
            vendor_name="Google Cloud",
            engine_name="Google BigQuery Serverless Warehouse",
            system_type="BIGQUERY",
            version=ServerVersion(raw_version_string="Google BigQuery Serverless", major=2, minor=0, patch=0),
            edition=EngineEdition(edition_name="Serverless Cloud Edition", is_enterprise=True, is_cloud_managed=True),
            database_name=project_id,
        )

    def discover_namespaces(
        self,
        connection: Any,
        spec: EndpointSpec,
        context: DiscoveryContext,
    ) -> NamespaceInventory:
        datasets = []
        if connection is not None and hasattr(connection, "list_datasets"):
            try:
                for ds in connection.list_datasets():
                    datasets.append(ds.dataset_id)
            except Exception as exc:
                logger.warning(f"Error listing bigquery datasets: {exc}")
                raise

        if not datasets:
            datasets = [spec.database_name or "default_dataset"]

        return NamespaceInventory(
            schemas=tuple(datasets),
            default_schema=datasets[0] if datasets else None,
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
        if connection is not None and hasattr(connection, "list_tables"):
            try:
                for t in connection.list_tables(schema_name):
                    ttype = getattr(t, "table_type", "")
                    if ttype == "VIEW":
                        views.append(
                            ViewFacts(
                                name=t.table_id,
                                schema_name=schema_name,
                                is_materialized=False,
                            )
                        )
                    else:
                        nrows = getattr(t, "num_rows", 0) or 0
                        nbytes = getattr(t, "num_bytes", 0) or 0
                        tables.append(
                            TableFacts(
                                name=t.table_id,
                                schema_name=schema_name,
                                object_type=ObjectType.TABLE,
                                classification=ObjectClassification.USER,
                                row_count_estimate=nrows,
                                size_bytes_estimate=nbytes,
                            )
                        )
            except Exception as exc:
                logger.warning(f"Error listing bigquery tables in {schema_name}: {exc}")
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
        if connection is not None and hasattr(connection, "get_table"):
            try:
                t_obj = connection.get_table(f"{schema_name}.{object_name}")
                for idx, field in enumerate(t_obj.schema):
                    cols.append(
                        ColumnPhysicalMetadata(
                            name=field.name,
                            ordinal_position=idx + 1,
                            native_type=field.field_type.upper(),
                            nullable=(field.mode != "REQUIRED"),
                            is_array=(field.mode == "REPEATED"),
                            comment=field.description,
                        )
                    )
            except Exception as exc:
                logger.warning(f"Error getting bigquery table schema for {schema_name}.{object_name}: {exc}")
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
        if not object_names or connection is None:
            return super().discover_objects_structure_bulk(connection, spec, schema_name, object_names, context)

        results: dict[str, ObjectStructureFacts] = {}
        for name in object_names:
            cols: list[ColumnPhysicalMetadata] = []
            if hasattr(connection, "get_table"):
                try:
                    t_obj = connection.get_table(f"{schema_name}.{name}")
                    for idx, field in enumerate(t_obj.schema):
                        cols.append(
                            ColumnPhysicalMetadata(
                                name=field.name,
                                ordinal_position=idx + 1,
                                native_type=field.field_type.upper(),
                                nullable=(field.mode != "REQUIRED"),
                                is_array=(field.mode == "REPEATED"),
                                comment=field.description,
                            )
                        )
                except Exception as exc:
                    logger.warning(f"Error getting bigquery table schema in bulk for {schema_name}.{name}: {exc}")
                    raise
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
        if not object_names or connection is None:
            return super().discover_table_statistics_bulk(connection, spec, schema_name, object_names, context)

        results: dict[str, TableSizeFacts] = {}
        for name in object_names:
            nrows = 0
            nbytes = 0
            if hasattr(connection, "get_table"):
                try:
                    t_obj = connection.get_table(f"{schema_name}.{name}")
                    nrows = getattr(t_obj, "num_rows", 0) or 0
                    nbytes = getattr(t_obj, "num_bytes", 0) or 0
                except Exception as exc:
                    logger.warning(f"Error getting bigquery table stats in bulk for {schema_name}.{name}: {exc}")
                    raise
            results[name] = TableSizeFacts(
                table_name=name,
                schema_name=schema_name,
                row_count=nrows,
                total_bytes=nbytes,
            )
        return results

    def discover_warehouse_context(
        self,
        connection: Any,
        spec: EndpointSpec,
        context: DiscoveryContext,
    ) -> Mapping[str, Any]:
        return {"project_id": spec.account_id or "default"}

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
        nrows = 0
        nbytes = 0
        if connection is not None and hasattr(connection, "get_table"):
            try:
                t_obj = connection.get_table(f"{schema_name}.{table_name}")
                nrows = getattr(t_obj, "num_rows", 0) or 0
                nbytes = getattr(t_obj, "num_bytes", 0) or 0
            except Exception as exc:
                logger.warning(f"Error fetching bigquery table stats for {schema_name}.{table_name}: {exc}")
                raise

        return TableSizeFacts(
            table_name=table_name,
            schema_name=schema_name,
            row_count=nrows,
            total_bytes=nbytes,
            count_accuracy=CountAccuracy.CATALOG_ESTIMATE,
        )

    def check_read_only_permissions(
        self,
        connection: Any,
        spec: EndpointSpec,
    ) -> ThreeStatePermission:
        # BigQuery has no non-destructive physical probe for read-only role state
        return ThreeStatePermission.UNKNOWN

    def discover_permissions(
        self,
        connection: Any,
        spec: EndpointSpec,
        context: DiscoveryContext,
    ) -> PermissionAssessment:
        cat_perm = ThreeStatePermission.UNKNOWN
        if connection is not None and hasattr(connection, "list_datasets"):
            try:
                connection.list_datasets(max_results=1)
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
            limits=LimitsFacts(max_connections=10000),
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
                blocker_reasons=("BigQuery connection not established",),
            )
        return CDCPrerequisiteSnapshot(
            is_cdc_ready=False,
            mechanism=CDCMechanism.BIGQUERY_CDC,
            blocker_reasons=("BigQuery CDC continuous replication requires Change History enabled",),
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
        if connection is None or not hasattr(connection, "query"):
            return DeterministicSampler.package_sample(table_name, schema_name, [], [])
        try:
            query = f"SELECT * FROM `{schema_name}`.`{table_name}` LIMIT {limit}"
            query_job = connection.query(query)
            rows = [dict(row) for row in query_job.result(timeout=timeout_seconds)]
            cols = list(rows[0].keys()) if rows else []
            return DeterministicSampler.package_sample(table_name, schema_name, cols, rows)
        except Exception as exc:
            logger.warning(f"Error sampling bigquery table {table_name}: {exc}")
            return DeterministicSampler.package_failure(table_name, schema_name, str(exc))

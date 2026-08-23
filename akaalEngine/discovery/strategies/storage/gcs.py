"""
akaalEngine.discovery.strategies.storage.gcs
===========================================
Canonical Google Cloud Storage discovery strategy.
Introspects list_buckets, list_blobs, prefixes, and storage metadata.
"""

from __future__ import annotations

import logging
from typing import Any, Optional, Sequence, Tuple

from akaalEngine.connection.models.endpoint import EndpointSpec
from akaalEngine.connection.routing.resolver import ResolvedRoute
from akaalEngine.discovery.core.paginator import CatalogPaginator
from akaalEngine.discovery.core.sampling import DeterministicSampler
from akaalEngine.discovery.models.cdc import CDCMechanism, CDCPrerequisiteSnapshot
from akaalEngine.discovery.models.context import DiscoveryContext
from akaalEngine.discovery.models.environment import CharsetFacts, ConfigurationFacts, LimitsFacts, TimezoneFacts
from akaalEngine.discovery.models.identity import DiscoveredEndpointIdentity, EngineEdition, ServerVersion
from akaalEngine.discovery.models.inventory import NamespaceInventory, ObjectClassification, ObjectInventoryPage, ObjectType, TableFacts
from akaalEngine.discovery.models.partitioning import PartitionFacts, PartitionStrategy
from akaalEngine.discovery.models.permissions import PermissionAssessment, PrivilegeFact, ThreeStatePermission
from akaalEngine.discovery.models.structure import (
    ColumnPhysicalMetadata,
    ObjectStructureFacts,
)
from akaalEngine.discovery.models.topology import ClusterNodeFacts, NodeRole, TopologySnapshot
from akaalEngine.discovery.spi.storage import StorageDiscoveryStrategy

logger = logging.getLogger("akaalEngine.discovery.strategies.gcs")


class GCSDiscoveryStrategy(StorageDiscoveryStrategy):
    """Google Cloud Storage physical discovery strategy."""

    PROVIDER_ID = "gcs"

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
            engine_name="Google Cloud Storage",
            system_type="GCS",
            version=ServerVersion(raw_version_string="Google Cloud Storage API v1", major=1, minor=0, patch=0),
            edition=EngineEdition(edition_name="Cloud Object Store", is_enterprise=True, is_cloud_managed=True),
            instance_name=project_id,
            host=spec.host or "storage.googleapis.com",
            port=spec.port or 443,
            database_name=spec.database_name,
        )

    def discover_namespaces(
        self,
        connection: Any,
        spec: EndpointSpec,
        context: DiscoveryContext,
    ) -> NamespaceInventory:
        buckets = []
        if connection is not None and hasattr(connection, "list_buckets"):
            try:
                for b in connection.list_buckets():
                    buckets.append(b.name)
            except Exception as exc:
                logger.warning(f"Error listing GCS buckets: {exc}")
                raise

        if not buckets and spec.database_name:
            buckets = [spec.database_name]

        return NamespaceInventory(
            schemas=tuple(buckets),
            buckets=tuple(buckets),
            default_schema=buckets[0] if buckets else None,
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
        items = []
        if connection is not None and hasattr(connection, "list_blobs"):
            try:
                blobs = connection.list_blobs(schema_name, max_results=page_size)
                for blob in blobs:
                    items.append(
                        TableFacts(
                            name=blob.name,
                            schema_name=schema_name,
                            object_type=ObjectType.FILE,
                            classification=ObjectClassification.USER,
                            size_bytes_estimate=blob.size or 0,
                        )
                    )
            except Exception as exc:
                logger.warning(f"Error listing GCS blobs in {schema_name}: {exc}")
                raise

        return CatalogPaginator.paginate_sequence(items, cursor=cursor, page_size=page_size)

    def discover_object_structure(
        self,
        connection: Any,
        spec: EndpointSpec,
        schema_name: str,
        object_name: str,
        context: DiscoveryContext,
    ) -> ObjectStructureFacts:
        return self.extract_file_embedded_schema(connection, spec, schema_name, object_name, context)

    def extract_file_embedded_schema(
        self,
        connection: Any,
        spec: EndpointSpec,
        bucket_name: str,
        object_key: str,
        context: DiscoveryContext,
    ) -> ObjectStructureFacts:
        cols = [
            ColumnPhysicalMetadata(name="name", ordinal_position=1, native_type="STRING", is_identity=True),
            ColumnPhysicalMetadata(name="size", ordinal_position=2, native_type="INT64"),
            ColumnPhysicalMetadata(name="updated", ordinal_position=3, native_type="TIMESTAMP"),
            ColumnPhysicalMetadata(name="content_type", ordinal_position=4, native_type="STRING"),
        ]
        return ObjectStructureFacts(
            table_name=object_key,
            schema_name=bucket_name,
            columns=tuple(cols),
        )

    def check_read_only_permissions(
        self,
        connection: Any,
        spec: EndpointSpec,
    ) -> ThreeStatePermission:
        # GCS has no non-destructive physical probe for read-only role state
        return ThreeStatePermission.UNKNOWN

    def discover_permissions(
        self,
        connection: Any,
        spec: EndpointSpec,
        context: DiscoveryContext,
    ) -> PermissionAssessment:
        cat_perm = ThreeStatePermission.UNKNOWN
        if connection is not None and hasattr(connection, "list_buckets"):
            try:
                connection.list_buckets(max_results=1)
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
                blocker_reasons=("GCS connection not established",),
            )
        return CDCPrerequisiteSnapshot(
            is_cdc_ready=False,
            mechanism=CDCMechanism.POLLING_WATERMARK,
            blocker_reasons=("GCS Pub/Sub notifications/CDC not configured on bucket",),
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
        try:
            return DeterministicSampler.package_sample(table_name, schema_name, ["key", "size_bytes"], [])
        except Exception as exc:
            return DeterministicSampler.package_failure(table_name, schema_name, str(exc))

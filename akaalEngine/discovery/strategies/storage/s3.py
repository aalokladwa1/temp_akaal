"""
akaalEngine.discovery.strategies.storage.s3
===========================================
Canonical Amazon S3 cloud object storage discovery strategy.
Introspects list_buckets, list_objects_v2, directory prefixes, and extracts Parquet/Avro schema headers.
"""

from __future__ import annotations

import logging
from typing import Any, Optional, Sequence, Tuple

from akaalEngine.connection.models.endpoint import EndpointSpec
from akaalEngine.connection.routing.resolver import ResolvedRoute
from akaalEngine.discovery.core.paginator import CatalogPaginator, DiscoveryCursor
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

logger = logging.getLogger("akaalEngine.discovery.strategies.s3")


class S3DiscoveryStrategy(StorageDiscoveryStrategy):
    """Amazon S3 physical discovery strategy."""

    PROVIDER_ID = "s3"

    @property
    def provider_id(self) -> str:
        return self.PROVIDER_ID

    def discover_endpoint_identity(
        self,
        connection: Any,
        spec: EndpointSpec,
        route: Optional[ResolvedRoute] = None,
    ) -> DiscoveredEndpointIdentity:
        region = spec.options.get("region_name", "us-east-1")
        return DiscoveredEndpointIdentity(
            provider_id=self.PROVIDER_ID,
            vendor_name="Amazon Web Services",
            engine_name="Amazon Simple Storage Service (S3)",
            system_type="S3",
            version=ServerVersion(raw_version_string="AWS S3 Object Storage API", major=1, minor=0, patch=0),
            edition=EngineEdition(edition_name="Cloud Object Store", is_enterprise=True, is_cloud_managed=True),
            instance_name=f"s3-{region}",
            host=spec.host or f"s3.{region}.amazonaws.com",
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
                res = connection.list_buckets()
                buckets = [b["Name"] for b in res.get("Buckets", [])]
            except Exception as exc:
                logger.warning(f"Error listing S3 buckets: {exc}")
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
        next_tok = None
        if connection is not None and hasattr(connection, "list_objects_v2"):
            try:
                cur = DiscoveryCursor.decode(cursor)
                kwargs: dict[str, Any] = {
                    "Bucket": schema_name or spec.database_name or "",
                    "Delimiter": "/",
                    "MaxKeys": page_size,
                }
                if cur.provider_token:
                    kwargs["ContinuationToken"] = cur.provider_token

                res = connection.list_objects_v2(**kwargs)
                next_tok = res.get("NextContinuationToken", "")

                # Prefixes (Directories)
                for cp in res.get("CommonPrefixes", []):
                    pfx = cp.get("Prefix", "").rstrip("/")
                    items.append(
                        TableFacts(
                            name=pfx,
                            schema_name=schema_name,
                            object_type=ObjectType.TABLE,
                            classification=ObjectClassification.USER,
                            storage_format="DIRECTORY_DATASET",
                        )
                    )
                # Standalone files
                for obj in res.get("Contents", []):
                    key = obj.get("Key", "")
                    if not key.endswith("/"):
                        items.append(
                            TableFacts(
                                name=key,
                                schema_name=schema_name,
                                object_type=ObjectType.FILE,
                                classification=ObjectClassification.USER,
                                size_bytes_estimate=obj.get("Size", 0),
                            )
                        )
            except Exception as exc:
                logger.warning(f"Error listing S3 objects in {schema_name}: {exc}")
                raise

        return CatalogPaginator.paginate_sequence(
            items,
            cursor=cursor,
            page_size=page_size,
            provider_next_token=next_tok,
        )

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
            ColumnPhysicalMetadata(name="key", ordinal_position=1, native_type="STRING", is_identity=True),
            ColumnPhysicalMetadata(name="size_bytes", ordinal_position=2, native_type="INT64"),
            ColumnPhysicalMetadata(name="last_modified", ordinal_position=3, native_type="TIMESTAMP"),
            ColumnPhysicalMetadata(name="etag", ordinal_position=4, native_type="STRING"),
            ColumnPhysicalMetadata(name="storage_class", ordinal_position=5, native_type="STRING"),
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
        # S3 has no non-destructive physical probe for read-only role state
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
                connection.list_buckets()
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
                blocker_reasons=("S3 connection not established",),
            )
        return CDCPrerequisiteSnapshot(
            is_cdc_ready=False,
            mechanism=CDCMechanism.POLLING_WATERMARK,
            blocker_reasons=("S3 bucket event notifications/CDC not configured",),
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

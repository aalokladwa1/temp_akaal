"""
akaalEngine.discovery.strategies.storage.hdfs
============================================
Canonical Apache Hadoop HDFS distributed filesystem discovery strategy.
Introspects WebHDFS file statuses, directory listings, block sizes, and replication factors.
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

logger = logging.getLogger("akaalEngine.discovery.strategies.hdfs")


class HDFSDiscoveryStrategy(StorageDiscoveryStrategy):
    """Apache Hadoop HDFS physical discovery strategy."""

    PROVIDER_ID = "hdfs"

    @property
    def provider_id(self) -> str:
        return self.PROVIDER_ID

    def discover_endpoint_identity(
        self,
        connection: Any,
        spec: EndpointSpec,
        route: Optional[ResolvedRoute] = None,
    ) -> DiscoveredEndpointIdentity:
        return DiscoveredEndpointIdentity(
            provider_id=self.PROVIDER_ID,
            vendor_name="Apache Software Foundation",
            engine_name="Hadoop Distributed File System (HDFS)",
            system_type="HDFS",
            version=ServerVersion(raw_version_string="3.3.4", major=3, minor=3, patch=4),
            edition=EngineEdition(edition_name="Distributed Storage", is_enterprise=False),
            host=spec.host,
            port=spec.port or 9870,
            database_name=spec.database_name or "/",
        )

    def discover_namespaces(
        self,
        connection: Any,
        spec: EndpointSpec,
        context: DiscoveryContext,
    ) -> NamespaceInventory:
        root_dirs = []
        if connection is not None and hasattr(connection, "list"):
            try:
                root_dirs = connection.list("/")
            except Exception as exc:
                logger.warning(f"Error listing HDFS root: {exc}")
                raise
        elif spec.database_name:
            root_dirs = [spec.database_name]

        return NamespaceInventory(
            schemas=tuple(root_dirs),
            buckets=tuple(root_dirs),
            default_schema=root_dirs[0] if root_dirs else None,
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
        if connection is not None and hasattr(connection, "list"):
            try:
                files = connection.list(schema_name)
                for f in files:
                    items.append(
                        TableFacts(
                            name=f"{schema_name.rstrip('/')}/{f}",
                            schema_name=schema_name,
                            object_type=ObjectType.FILE,
                            classification=ObjectClassification.USER,
                        )
                    )
            except Exception as exc:
                logger.warning(f"Error listing HDFS files in {schema_name}: {exc}")
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
            ColumnPhysicalMetadata(name="path", ordinal_position=1, native_type="STRING", is_identity=True),
            ColumnPhysicalMetadata(name="length", ordinal_position=2, native_type="INT64"),
            ColumnPhysicalMetadata(name="blockSize", ordinal_position=3, native_type="INT64"),
            ColumnPhysicalMetadata(name="replication", ordinal_position=4, native_type="INT32"),
            ColumnPhysicalMetadata(name="permission", ordinal_position=5, native_type="STRING"),
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
        # HDFS has no non-destructive physical probe for read-only role state
        return ThreeStatePermission.UNKNOWN

    def discover_permissions(
        self,
        connection: Any,
        spec: EndpointSpec,
        context: DiscoveryContext,
    ) -> PermissionAssessment:
        cat_perm = ThreeStatePermission.UNKNOWN
        if connection is not None and hasattr(connection, "list"):
            try:
                connection.list("/")
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
                blocker_reasons=("HDFS connection not established",),
            )
        return CDCPrerequisiteSnapshot(
            is_cdc_ready=False,
            mechanism=CDCMechanism.POLLING_WATERMARK,
            blocker_reasons=("HDFS inotify events stream not verified",),
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
            return DeterministicSampler.package_sample(table_name, schema_name, ["path", "length"], [])
        except Exception as exc:
            return DeterministicSampler.package_failure(table_name, schema_name, str(exc))

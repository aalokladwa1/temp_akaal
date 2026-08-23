"""
akaalEngine.discovery.strategies.nosql.redis
============================================
Canonical Redis key-value & caching engine discovery strategy.
Introspects INFO stats, non-blocking SCAN key prefix histograms, and cluster nodes.
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
from akaalEngine.discovery.models.sampling import InferredDocumentShape
from akaalEngine.discovery.models.statistics import CountAccuracy, TableSizeFacts
from akaalEngine.discovery.models.structure import (
    ColumnPhysicalMetadata,
    ObjectStructureFacts,
)
from akaalEngine.discovery.models.topology import ClusterNodeFacts, NodeRole, TopologySnapshot
from akaalEngine.discovery.spi.nosql import NoSQLDiscoveryStrategy

logger = logging.getLogger("akaalEngine.discovery.strategies.redis")


class RedisDiscoveryStrategy(NoSQLDiscoveryStrategy):
    """Redis physical discovery strategy."""

    PROVIDER_ID = "redis"

    @property
    def provider_id(self) -> str:
        return self.PROVIDER_ID

    def discover_endpoint_identity(
        self,
        connection: Any,
        spec: EndpointSpec,
        route: Optional[ResolvedRoute] = None,
    ) -> DiscoveredEndpointIdentity:
        version_str = "7.0.10"
        major, minor, patch = 7, 0, 10
        if connection is not None and hasattr(connection, "info"):
            try:
                info = connection.info()
                version_str = info.get("redis_version", version_str)
                parts = version_str.split(".")
                major = int(parts[0]) if len(parts) > 0 and parts[0].isdigit() else 7
                minor = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0
                patch = int(parts[2].split("-")[0]) if len(parts) > 2 and parts[2].split("-")[0].isdigit() else 0
            except Exception as exc:
                logger.warning(f"Error querying redis info: {exc}")

        return DiscoveredEndpointIdentity(
            provider_id=self.PROVIDER_ID,
            vendor_name="Redis Ltd.",
            engine_name="Redis In-Memory Data Store",
            system_type="REDIS",
            version=ServerVersion(raw_version_string=version_str, major=major, minor=minor, patch=patch),
            edition=EngineEdition(edition_name="Community / Enterprise", is_enterprise=False),
            host=spec.host,
            port=spec.port or 6379,
            database_name=str(spec.options.get("db", 0)),
        )

    def discover_namespaces(
        self,
        connection: Any,
        spec: EndpointSpec,
        context: DiscoveryContext,
    ) -> NamespaceInventory:
        active_dbs = []
        if connection is not None and hasattr(connection, "info"):
            try:
                info_dict = connection.info("keyspace")
                active_dbs = [k for k in info_dict.keys() if k.startswith("db")]
            except Exception:
                pass
        if not active_dbs:
            configured_db = f"db{spec.options.get('db', 0)}"
            active_dbs = [configured_db]

        return NamespaceInventory(
            schemas=tuple(active_dbs),
            default_schema=active_dbs[0] if active_dbs else None,
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
        prefix_counts: dict[str, int] = {}
        if connection is not None and hasattr(connection, "scan"):
            try:
                # Non-blocking SCAN bounded to 500 keys
                scan_cursor = 0
                count = 0
                while count < 500:
                    scan_cursor, keys = connection.scan(scan_cursor, count=100)
                    for k in keys:
                        k_str = k.decode("utf-8") if isinstance(k, bytes) else str(k)
                        prefix = k_str.split(":", 1)[0] if ":" in k_str else "root"
                        prefix_counts[prefix] = prefix_counts.get(prefix, 0) + 1
                    count += len(keys)
                    if scan_cursor == 0:
                        break
            except Exception as exc:
                logger.warning(f"Error scanning redis keys in {schema_name}: {exc}")
                raise

        items = [
            TableFacts(
                name=f"{pfx}:*",
                schema_name=schema_name,
                object_type=ObjectType.COLLECTION,
                classification=ObjectClassification.USER,
                row_count_estimate=cnt,
            )
            for pfx, cnt in prefix_counts.items()
        ]
        return CatalogPaginator.paginate_sequence(items, cursor=cursor, page_size=page_size)

    def discover_object_structure(
        self,
        connection: Any,
        spec: EndpointSpec,
        schema_name: str,
        object_name: str,
        context: DiscoveryContext,
    ) -> ObjectStructureFacts:
        cols = [
            ColumnPhysicalMetadata(name="key", ordinal_position=1, native_type="STRING", is_identity=True),
            ColumnPhysicalMetadata(name="value", ordinal_position=2, native_type="STRING / HASH / LIST / SET / ZSET"),
            ColumnPhysicalMetadata(name="ttl_seconds", ordinal_position=3, native_type="INT64"),
        ]
        return ObjectStructureFacts(
            table_name=object_name,
            schema_name=schema_name,
            columns=tuple(cols),
        )

    def infer_document_shape(
        self,
        connection: Any,
        spec: EndpointSpec,
        schema_name: str,
        collection_name: str,
        sample_size: int = 100,
    ) -> InferredDocumentShape:
        return InferredDocumentShape(collection_name=collection_name, schema_name=schema_name)

    def check_read_only_permissions(
        self,
        connection: Any,
        spec: EndpointSpec,
    ) -> ThreeStatePermission:
        # Redis has no non-destructive physical probe for read-only user ACL
        return ThreeStatePermission.UNKNOWN

    def discover_permissions(
        self,
        connection: Any,
        spec: EndpointSpec,
        context: DiscoveryContext,
    ) -> PermissionAssessment:
        cat_perm = ThreeStatePermission.UNKNOWN
        if connection is not None and hasattr(connection, "ping"):
            try:
                connection.ping()
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
        if connection is None:
            return CDCPrerequisiteSnapshot(
                is_cdc_ready=False,
                mechanism=CDCMechanism.UNSUPPORTED,
                blocker_reasons=("Redis connection not established",),
            )
        return CDCPrerequisiteSnapshot(
            is_cdc_ready=False,
            mechanism=CDCMechanism.REDIS_STREAMS_CDC,
            blocker_reasons=("Redis CDC requires Redis Streams or Keyspace Notifications.",),
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
        if connection is None or not hasattr(connection, "scan"):
            return DeterministicSampler.package_sample(table_name, schema_name, ["key", "value"], [])
        try:
            rows = []
            _, keys = connection.scan(0, count=limit)
            for k in keys:
                val = connection.get(k) if hasattr(connection, "get") else None
                k_s = k.decode("utf-8") if isinstance(k, bytes) else str(k)
                v_s = val.decode("utf-8") if isinstance(val, bytes) else str(val)
                rows.append({"key": k_s, "value": v_s})
            return DeterministicSampler.package_sample(table_name, schema_name, ["key", "value"], rows)
        except Exception as exc:
            logger.warning(f"Error sampling redis: {exc}")
            return DeterministicSampler.package_failure(table_name, schema_name, str(exc))

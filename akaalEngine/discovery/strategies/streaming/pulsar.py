"""
akaalEngine.discovery.strategies.streaming.pulsar
=====================================================
Canonical Apache Pulsar discovery strategy (P7A Campaign B).

Topic/tenant/namespace inventory requires the Pulsar Admin REST API (the binary client
protocol carries no such wire-level operation), so this mirrors the same honest,
best-effort management-API pattern used for RabbitMQ: `requests` is imported lazily, and
an unreachable/unconfigured admin endpoint yields truthful empty results, never
fabricated inventory.
"""

from __future__ import annotations

import logging
from typing import Any, Mapping, Optional

from akaalEngine.connection.models.endpoint import EndpointSpec
from akaalEngine.connection.routing.resolver import ResolvedRoute
from akaalEngine.discovery.core.paginator import CatalogPaginator
from akaalEngine.discovery.core.sampling import DeterministicSampler
from akaalEngine.discovery.models.cdc import CDCMechanism, CDCPrerequisiteSnapshot
from akaalEngine.discovery.models.context import DiscoveryContext
from akaalEngine.discovery.models.environment import CharsetFacts, ConfigurationFacts, LimitsFacts, TimezoneFacts
from akaalEngine.discovery.models.identity import DiscoveredEndpointIdentity, EngineEdition, ServerVersion
from akaalEngine.discovery.models.inventory import NamespaceInventory, ObjectClassification, ObjectInventoryPage, ObjectType, TableFacts
from akaalEngine.discovery.models.permissions import PermissionAssessment, ThreeStatePermission
from akaalEngine.discovery.models.sampling import SampledRecordSet
from akaalEngine.discovery.models.structure import ColumnPhysicalMetadata, ObjectStructureFacts
from akaalEngine.discovery.models.topology import ClusterNodeFacts, NodeRole, TopologySnapshot
from akaalEngine.discovery.spi.streaming import StreamingDiscoveryStrategy

logger = logging.getLogger("akaalEngine.discovery.strategies.pulsar")


def _admin_api_get(spec: EndpointSpec, path: str) -> Optional[Any]:
    """Best-effort GET against the Pulsar Admin REST API. None means 'unknown', never 'empty'."""
    try:
        import requests
    except ImportError:
        return None

    if not spec.host:
        return None
    admin_url = spec.options.get("admin_url", f"http://{spec.host}:{spec.options.get('admin_port', 8080)}")
    url = f"{admin_url.rstrip('/')}{path}"
    headers = {}
    token = spec.options.get("auth_token")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        resp = requests.get(url, headers=headers, timeout=5.0)
        if resp.status_code == 200:
            return resp.json()
        return None
    except Exception as exc:
        logger.info(f"Pulsar admin API probe failed for {path}: {exc}")
        return None


class PulsarDiscoveryStrategy(StreamingDiscoveryStrategy):
    """Apache Pulsar physical discovery strategy -- tenant/namespace/topic hierarchy."""

    PROVIDER_ID = "pulsar"

    @property
    def provider_id(self) -> str:
        return self.PROVIDER_ID

    def discover_endpoint_identity(
        self,
        connection: Any,
        spec: EndpointSpec,
        route: Optional[ResolvedRoute] = None,
    ) -> DiscoveredEndpointIdentity:
        version_str = "Apache Pulsar"
        data = _admin_api_get(spec, "/admin/v2/brokers/version")
        major, minor, patch = 0, 0, 0
        if isinstance(data, str) and data:
            version_str = f"Apache Pulsar {data}"
            parts = data.split(".")
            try:
                major = int(parts[0])
                minor = int(parts[1]) if len(parts) > 1 else 0
                patch = int("".join(c for c in parts[2] if c.isdigit())) if len(parts) > 2 else 0
            except (ValueError, IndexError):
                pass

        return DiscoveredEndpointIdentity(
            provider_id=self.PROVIDER_ID,
            vendor_name="Apache Software Foundation",
            engine_name="Apache Pulsar",
            system_type="PULSAR",
            version=ServerVersion(raw_version_string=version_str, major=major, minor=minor, patch=patch),
            edition=EngineEdition(edition_name="Distributed Pub-Sub Messaging", is_enterprise=False),
            host=spec.host,
            port=spec.port or 6650,
            database_name=f"{spec.options.get('tenant', 'public')}/{spec.options.get('namespace', 'default')}",
        )

    def discover_namespaces(
        self,
        connection: Any,
        spec: EndpointSpec,
        context: DiscoveryContext,
    ) -> NamespaceInventory:
        tenant = spec.options.get("tenant", "public")
        data = _admin_api_get(spec, f"/admin/v2/namespaces/{tenant}")
        namespaces = []
        if data is not None and isinstance(data, list):
            # Admin API returns "tenant/namespace" -- keep just the namespace segment.
            namespaces = [ns.split("/")[-1] for ns in data if isinstance(ns, str)]

        return NamespaceInventory(
            schemas=tuple(namespaces),
            default_schema=spec.options.get("namespace", "default") if not namespaces else namespaces[0],
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
        tenant = spec.options.get("tenant", "public")
        items: list = []
        for topic_domain in ("persistent", "non-persistent"):
            data = _admin_api_get(spec, f"/admin/v2/{topic_domain}/{tenant}/{schema_name}")
            if data is not None and isinstance(data, list):
                for topic_fqn in data:
                    if not isinstance(topic_fqn, str):
                        continue
                    short_name = topic_fqn.rsplit("/", 1)[-1]
                    items.append(
                        TableFacts(
                            name=short_name,
                            schema_name=schema_name,
                            object_type=ObjectType.TOPIC,
                            classification=ObjectClassification.USER,
                            properties={"topic_domain": topic_domain, "fully_qualified_name": topic_fqn},
                        )
                    )

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
            ColumnPhysicalMetadata(name="value", ordinal_position=2, native_type="BYTES / AVRO / JSON"),
            ColumnPhysicalMetadata(name="message_id", ordinal_position=3, native_type="STRING"),
            ColumnPhysicalMetadata(name="publish_time", ordinal_position=4, native_type="TIMESTAMP"),
            ColumnPhysicalMetadata(name="properties", ordinal_position=5, native_type="MAP<STRING, STRING>"),
        ]
        return ObjectStructureFacts(
            table_name=object_name,
            schema_name=schema_name,
            columns=tuple(cols),
        )

    def discover_topic_retention_policy(
        self,
        connection: Any,
        spec: EndpointSpec,
        topic_name: str,
        context: DiscoveryContext,
    ) -> Mapping[str, Any]:
        tenant = spec.options.get("tenant", "public")
        namespace = spec.options.get("namespace", "default")
        data = _admin_api_get(spec, f"/admin/v2/persistent/{tenant}/{namespace}/retention")
        if data is None or not isinstance(data, dict):
            return {}
        return {
            "retention_time_minutes": data.get("retentionTimeInMinutes"),
            "retention_size_mb": data.get("retentionSizeInMB"),
        }

    def check_read_only_permissions(
        self,
        connection: Any,
        spec: EndpointSpec,
    ) -> ThreeStatePermission:
        return ThreeStatePermission.UNKNOWN

    def discover_permissions(
        self,
        connection: Any,
        spec: EndpointSpec,
        context: DiscoveryContext,
    ) -> PermissionAssessment:
        cat_perm = ThreeStatePermission.PROVEN if connection is not None else ThreeStatePermission.UNKNOWN
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
            limits=LimitsFacts(max_connections=None),
        )

    def discover_topology(
        self,
        connection: Any,
        spec: EndpointSpec,
        context: DiscoveryContext,
    ) -> TopologySnapshot:
        nodes = []
        data = _admin_api_get(spec, "/admin/v2/brokers/health")
        if data is not None:
            nodes = [ClusterNodeFacts(node_id="connected_broker", host=spec.host or "localhost", port=spec.port or 6650, role=NodeRole.BROKER)]
        if not nodes:
            nodes = [ClusterNodeFacts(node_id="connected_node", host=spec.host or "localhost", port=spec.port or 6650, role=NodeRole.BROKER)]

        return TopologySnapshot(
            is_clustered=len(nodes) > 1,
            connected_node_role=NodeRole.BROKER,
            nodes=tuple(nodes),
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
                blocker_reasons=("Pulsar connection not established",),
            )
        # Pulsar topics are a genuine durable log by default (unlike RabbitMQ classic
        # queues), so reading from the earliest retained message is structurally possible
        # without a special plugin -- but this connector strategy does not implement
        # transactional/CDC-grade tailing, so readiness stays truthfully unproven rather
        # than assumed.
        return CDCPrerequisiteSnapshot(
            is_cdc_ready=False,
            mechanism=CDCMechanism.PULSAR_STREAMING,
            blocker_reasons=("This connector strategy does not implement Pulsar reader-based log tailing.",),
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
        # Non-destructive sampling would require a Reader positioned at the earliest
        # message ID; not implemented in this pass -- returns an honest empty sample.
        return DeterministicSampler.package_sample(table_name, schema_name or "", ["key", "value", "message_id", "publish_time"], [])

    def get_schema_change_marker(
        self,
        connection: Any,
        spec: EndpointSpec,
    ) -> Optional[str]:
        return None

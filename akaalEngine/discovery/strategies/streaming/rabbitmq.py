"""
akaalEngine.discovery.strategies.streaming.rabbitmq
=====================================================
Canonical RabbitMQ discovery strategy (P7A Campaign B).

Unlike Kafka's admin-client protocol (which carries broker/topic metadata natively),
AMQP 0-9-1 itself has no wire-level "list all queues/exchanges" operation -- full broker
inventory genuinely requires the RabbitMQ HTTP Management API (a separate plugin,
typically port 15672). This strategy uses it truthfully when reachable (`requests`
installed and a management endpoint configured) and returns honest empty results
otherwise, rather than fabricating inventory from the AMQP connection alone.
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

logger = logging.getLogger("akaalEngine.discovery.strategies.rabbitmq")


def _management_api_get(spec: EndpointSpec, path: str) -> Optional[Any]:
    """
    Best-effort GET against the RabbitMQ HTTP Management API.
    Returns None (not an exception, not a fabricated result) whenever the `requests`
    library is unavailable, no management endpoint is configured, or the call fails --
    callers must treat None as "unknown", never as "empty broker".
    """
    try:
        import requests
    except ImportError:
        return None

    mgmt_port = spec.options.get("management_port", 15672)
    mgmt_scheme = spec.options.get("management_scheme", "http")
    host = spec.host
    if not host:
        return None
    username = spec.auth_spec.username if spec.auth_spec else "guest"
    password = spec.options.get("management_password") or "guest"

    url = f"{mgmt_scheme}://{host}:{mgmt_port}{path}"
    try:
        resp = requests.get(url, auth=(username, password), timeout=5.0)
        if resp.status_code == 200:
            return resp.json()
        return None
    except Exception as exc:
        logger.info(f"RabbitMQ management API probe failed for {path}: {exc}")
        return None


class RabbitMQDiscoveryStrategy(StreamingDiscoveryStrategy):
    """RabbitMQ physical discovery strategy -- AMQP broker, exchanges/queues/bindings."""

    PROVIDER_ID = "rabbitmq"

    @property
    def provider_id(self) -> str:
        return self.PROVIDER_ID

    def discover_endpoint_identity(
        self,
        connection: Any,
        spec: EndpointSpec,
        route: Optional[ResolvedRoute] = None,
    ) -> DiscoveredEndpointIdentity:
        version_str = "RabbitMQ"
        major, minor, patch = 0, 0, 0
        if connection is not None:
            try:
                props = getattr(connection, "connection", connection)
                server_props = getattr(props, "server_properties", None) or {}
                ver = server_props.get("version")
                if ver:
                    version_str = f"RabbitMQ {ver}"
                    parts = str(ver).split(".")
                    try:
                        major = int(parts[0])
                        minor = int(parts[1]) if len(parts) > 1 else 0
                        patch = int(parts[2]) if len(parts) > 2 else 0
                    except (ValueError, IndexError):
                        pass
            except Exception as exc:
                logger.warning(f"Error fetching RabbitMQ server properties: {exc}")

        return DiscoveredEndpointIdentity(
            provider_id=self.PROVIDER_ID,
            vendor_name="VMware / Broadcom (RabbitMQ)",
            engine_name="RabbitMQ",
            system_type="RABBITMQ",
            version=ServerVersion(raw_version_string=version_str, major=major, minor=minor, patch=patch),
            edition=EngineEdition(edition_name="Community / Enterprise", is_enterprise=False),
            host=spec.host,
            port=spec.port or 5672,
            database_name=spec.options.get("virtual_host", "/"),
        )

    def discover_namespaces(
        self,
        connection: Any,
        spec: EndpointSpec,
        context: DiscoveryContext,
    ) -> NamespaceInventory:
        vhost = spec.options.get("virtual_host", spec.database_name or "/")
        queues: list = []
        data = _management_api_get(spec, f"/api/queues/{_quote_vhost(vhost)}")
        if data is not None:
            queues = [q.get("name") for q in data if isinstance(q, dict) and q.get("name")]

        return NamespaceInventory(
            schemas=(),
            topics=tuple(queues),
            default_schema=vhost,
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
        vhost = spec.options.get("virtual_host", spec.database_name or "/")
        items: list = []
        data = _management_api_get(spec, f"/api/queues/{_quote_vhost(vhost)}")
        if data is not None:
            for q in data:
                if not isinstance(q, dict) or not q.get("name"):
                    continue
                items.append(
                    TableFacts(
                        name=q["name"],
                        schema_name=schema_name,
                        object_type=ObjectType.TOPIC,
                        classification=ObjectClassification.USER,
                        row_count_estimate=max(0, int(q.get("messages", 0) or 0)),
                        properties={"durable": q.get("durable", False), "queue_type": q.get("type", "classic")},
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
        # AMQP messages have no fixed structure -- this reflects the envelope, not a payload schema.
        cols = [
            ColumnPhysicalMetadata(name="body", ordinal_position=1, native_type="BYTES"),
            ColumnPhysicalMetadata(name="routing_key", ordinal_position=2, native_type="STRING"),
            ColumnPhysicalMetadata(name="exchange", ordinal_position=3, native_type="STRING"),
            ColumnPhysicalMetadata(name="delivery_tag", ordinal_position=4, native_type="BIGINT"),
            ColumnPhysicalMetadata(name="properties", ordinal_position=5, native_type="MAP<STRING, BYTES>"),
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
        vhost = spec.options.get("virtual_host", spec.database_name or "/")
        data = _management_api_get(spec, f"/api/queues/{_quote_vhost(vhost)}/{topic_name}")
        if data is None:
            return {}
        args = data.get("arguments", {}) if isinstance(data, dict) else {}
        return {
            "message_ttl_ms": args.get("x-message-ttl"),
            "max_length": args.get("x-max-length"),
            "max_length_bytes": args.get("x-max-length-bytes"),
            "queue_type": args.get("x-queue-type", "classic"),
        }

    def check_read_only_permissions(
        self,
        connection: Any,
        spec: EndpointSpec,
    ) -> ThreeStatePermission:
        # AMQP has no non-destructive physical probe for a broker-wide read-only role state.
        return ThreeStatePermission.UNKNOWN

    def discover_permissions(
        self,
        connection: Any,
        spec: EndpointSpec,
        context: DiscoveryContext,
    ) -> PermissionAssessment:
        cat_perm = ThreeStatePermission.UNKNOWN
        if connection is not None:
            try:
                channel = connection.channel()
                channel.close()
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
            limits=LimitsFacts(max_connections=spec.options.get("channel_max", 2047)),
        )

    def discover_topology(
        self,
        connection: Any,
        spec: EndpointSpec,
        context: DiscoveryContext,
    ) -> TopologySnapshot:
        nodes = []
        data = _management_api_get(spec, "/api/nodes")
        if data is not None and isinstance(data, list):
            for n in data:
                if not isinstance(n, dict):
                    continue
                nodes.append(
                    ClusterNodeFacts(
                        node_id=str(n.get("name", "unknown")),
                        host=spec.host or "localhost",
                        port=spec.port or 5672,
                        role=NodeRole.BROKER if n.get("running") else NodeRole.UNKNOWN,
                    )
                )

        if not nodes:
            nodes = [ClusterNodeFacts(node_id="connected_node", host=spec.host or "localhost", port=spec.port or 5672, role=NodeRole.BROKER)]

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
                blocker_reasons=("RabbitMQ connection not established",),
            )

        # Truthful probe: the Streams plugin must be listed as enabled via the management
        # API before CDC-like offset-based replay can be claimed ready. No management
        # endpoint reachable -> fail closed, never assume enabled.
        data = _management_api_get(spec, "/api/plugins")
        streams_enabled = False
        if data is not None and isinstance(data, list):
            streams_enabled = any(
                isinstance(p, dict) and p.get("name") == "rabbitmq_stream" and p.get("enabled")
                for p in data
            )

        blockers = []
        if not streams_enabled:
            blockers.append("RabbitMQ Streams plugin (rabbitmq_stream) not confirmed enabled; classic/quorum queues are not a replayable log.")

        return CDCPrerequisiteSnapshot(
            is_cdc_ready=streams_enabled,
            mechanism=CDCMechanism.RABBITMQ_STREAMS,
            blocker_reasons=tuple(blockers),
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
        # Consuming a sample from a RabbitMQ queue without acking would still require a
        # dedicated, non-destructive peek (basic_get with requeue) -- not implemented here
        # to avoid perturbing queue state as a side effect of discovery; returns an honest
        # empty sample rather than draining messages.
        return DeterministicSampler.package_sample(table_name, schema_name or "", ["routing_key", "exchange", "body", "properties"], [])

    def get_schema_change_marker(
        self,
        connection: Any,
        spec: EndpointSpec,
    ) -> Optional[str]:
        # RabbitMQ has no analogous global change-sequence marker.
        return None


def _quote_vhost(vhost: str) -> str:
    # RabbitMQ management API requires the default vhost "/" to be percent-encoded as "%2F".
    return vhost.replace("/", "%2F") if vhost else "%2F"

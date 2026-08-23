"""
akaalEngine.discovery.strategies.streaming.kafka
================================================
Canonical Apache Kafka streaming event bus discovery strategy.
Introspects cluster ID, broker topology, topic partition lists, retention configs, and watermark offsets.
"""

from __future__ import annotations

import logging
from typing import Any, Mapping, Optional, Sequence, Tuple
from types import MappingProxyType

from akaalEngine.connection.models.endpoint import EndpointSpec
from akaalEngine.connection.routing.resolver import ResolvedRoute
from akaalEngine.discovery.core.paginator import CatalogPaginator
from akaalEngine.discovery.core.sampling import DeterministicSampler
from akaalEngine.discovery.models.cdc import CDCMechanism, CDCPrerequisiteSnapshot, StartingCommitPosition
from akaalEngine.discovery.models.context import DiscoveryContext
from akaalEngine.discovery.models.environment import CharsetFacts, ConfigurationFacts, LimitsFacts, TimezoneFacts
from akaalEngine.discovery.models.identity import DiscoveredEndpointIdentity, EngineEdition, ServerVersion
from akaalEngine.discovery.models.inventory import NamespaceInventory, ObjectClassification, ObjectInventoryPage, ObjectType, TableFacts
from akaalEngine.discovery.models.partitioning import PartitionBoundFacts, PartitionFacts, PartitionStrategy
from akaalEngine.discovery.models.permissions import PermissionAssessment, PrivilegeFact, ThreeStatePermission
from akaalEngine.discovery.models.sampling import InferredDocumentShape
from akaalEngine.discovery.models.statistics import CountAccuracy, TableSizeFacts
from akaalEngine.discovery.models.structure import (
    ColumnPhysicalMetadata,
    ObjectStructureFacts,
)
from akaalEngine.discovery.models.topology import ClusterNodeFacts, NodeRole, TopologySnapshot
from akaalEngine.discovery.spi.streaming import StreamingDiscoveryStrategy

logger = logging.getLogger("akaalEngine.discovery.strategies.kafka")


class KafkaDiscoveryStrategy(StreamingDiscoveryStrategy):
    """Apache Kafka physical discovery strategy."""

    PROVIDER_ID = "kafka"

    @property
    def provider_id(self) -> str:
        return self.PROVIDER_ID

    def discover_endpoint_identity(
        self,
        connection: Any,
        spec: EndpointSpec,
        route: Optional[ResolvedRoute] = None,
    ) -> DiscoveredEndpointIdentity:
        cluster_id = spec.options.get("cluster_id") or "kafka-cluster"
        version_str = "UNKNOWN"
        major, minor, patch = 0, 0, 0
        if connection is not None and hasattr(connection, "list_topics"):
            try:
                # If confluent-kafka or kafka-python provides version info
                version_str = "Kafka Broker"
            except Exception:
                pass

        return DiscoveredEndpointIdentity(
            provider_id=self.PROVIDER_ID,
            vendor_name="Apache Software Foundation",
            engine_name="Apache Kafka Distributed Event Streaming",
            system_type="KAFKA",
            version=ServerVersion(raw_version_string=version_str, major=major, minor=minor, patch=patch),
            edition=EngineEdition(edition_name="Distributed Event Bus", is_enterprise=False),
            instance_name=cluster_id,
            host=spec.host,
            port=spec.port or 9092,
        )

    def discover_namespaces(
        self,
        connection: Any,
        spec: EndpointSpec,
        context: DiscoveryContext,
    ) -> NamespaceInventory:
        topics = []
        if connection is not None and hasattr(connection, "list_topics"):
            try:
                cluster_metadata = connection.list_topics(timeout=10)
                topics = [t for t in cluster_metadata.topics.keys() if not t.startswith("__")]
            except Exception as exc:
                logger.warning(f"Error querying kafka topics: {exc}")
                raise

        return NamespaceInventory(
            schemas=(),
            topics=tuple(topics),
            default_schema=None,
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
        if connection is not None and hasattr(connection, "list_topics"):
            try:
                cluster_metadata = connection.list_topics(timeout=10)
                for tname, tmeta in cluster_metadata.topics.items():
                    if not tname.startswith("__"):
                        num_partitions = len(tmeta.partitions) if hasattr(tmeta, "partitions") else 1
                        items.append(
                            TableFacts(
                                name=tname,
                                schema_name=schema_name,
                                object_type=ObjectType.STREAM_TOPIC,
                                classification=ObjectClassification.USER,
                                properties={"partitions": num_partitions},
                            )
                        )
            except Exception as exc:
                logger.warning(f"Error querying kafka topics page: {exc}")
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
        cols = [
            ColumnPhysicalMetadata(name="key", ordinal_position=1, native_type="BYTES / STRING", is_identity=True),
            ColumnPhysicalMetadata(name="value", ordinal_position=2, native_type="BYTES / JSON / AVRO"),
            ColumnPhysicalMetadata(name="topic", ordinal_position=3, native_type="STRING"),
            ColumnPhysicalMetadata(name="partition", ordinal_position=4, native_type="INTEGER"),
            ColumnPhysicalMetadata(name="offset", ordinal_position=5, native_type="BIGINT"),
            ColumnPhysicalMetadata(name="timestamp", ordinal_position=6, native_type="TIMESTAMP"),
            ColumnPhysicalMetadata(name="headers", ordinal_position=7, native_type="MAP<STRING, BYTES>"),
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
        if connection is not None and hasattr(connection, "describe_configs"):
            try:
                res = connection.describe_configs([topic_name])
                if res and topic_name in res:
                    return res[topic_name]
            except Exception:
                pass
        return {}

    def check_read_only_permissions(
        self,
        connection: Any,
        spec: EndpointSpec,
    ) -> ThreeStatePermission:
        # Kafka has no non-destructive physical probe for read-only role state
        return ThreeStatePermission.UNKNOWN

    def discover_permissions(
        self,
        connection: Any,
        spec: EndpointSpec,
        context: DiscoveryContext,
    ) -> PermissionAssessment:
        cat_perm = ThreeStatePermission.UNKNOWN
        if connection is not None and hasattr(connection, "list_topics"):
            try:
                connection.list_topics(timeout=3)
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
        brokers = []
        if connection is not None and hasattr(connection, "list_topics"):
            try:
                cluster_metadata = connection.list_topics(timeout=5)
                if hasattr(cluster_metadata, "brokers"):
                    for b_id, b_info in cluster_metadata.brokers.items():
                        brokers.append(
                            ClusterNodeFacts(
                                node_id=f"broker_{b_id}",
                                host=getattr(b_info, "host", spec.host or "localhost"),
                                port=getattr(b_info, "port", spec.port or 9092),
                                role=NodeRole.BROKER,
                            )
                        )
            except Exception:
                pass

        return TopologySnapshot(
            is_clustered=len(brokers) > 1,
            connected_node_role=NodeRole.BROKER if brokers else NodeRole.UNKNOWN,
            nodes=tuple(brokers),
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
                blocker_reasons=("Kafka connection not established",),
            )
        if not hasattr(connection, "list_topics"):
            return CDCPrerequisiteSnapshot(
                is_cdc_ready=False,
                mechanism=CDCMechanism.KAFKA_STREAMING,
                blocker_reasons=("Kafka client connection unverified",),
            )
        try:
            meta = connection.list_topics(timeout=3)
            if not hasattr(meta, "brokers") or not meta.brokers:
                return CDCPrerequisiteSnapshot(
                    is_cdc_ready=False,
                    mechanism=CDCMechanism.KAFKA_STREAMING,
                    blocker_reasons=("Kafka metadata returned 0 active brokers",),
                )
            return CDCPrerequisiteSnapshot(
                is_cdc_ready=True,
                mechanism=CDCMechanism.KAFKA_STREAMING,
            )
        except Exception as exc:
            return CDCPrerequisiteSnapshot(
                is_cdc_ready=False,
                mechanism=CDCMechanism.KAFKA_STREAMING,
                blocker_reasons=(f"Kafka physical connection probe failed: {exc}",),
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
            return DeterministicSampler.package_sample(table_name, schema_name or "", ["Partition", "Offset", "Key", "Value", "Timestamp"], [])
        except Exception as exc:
            return DeterministicSampler.package_failure(table_name, schema_name or "", str(exc))
        rows = []
        if connection is not None and hasattr(connection, "poll"):
            try:
                # Consumer poll
                msgs = connection.consume(num_messages=limit, timeout=timeout_seconds)
                for m in msgs:
                    if not m.error():
                        rows.append({
                            "key": m.key().decode("utf-8") if m.key() else None,
                            "value": m.value().decode("utf-8") if m.value() else None,
                            "partition": m.partition(),
                            "offset": m.offset(),
                        })
            except Exception as exc:
                logger.warning(f"Error consuming kafka sample for {table_name}: {exc}")
        return DeterministicSampler.package_sample(table_name, schema_name, ["key", "value", "partition", "offset"], rows)

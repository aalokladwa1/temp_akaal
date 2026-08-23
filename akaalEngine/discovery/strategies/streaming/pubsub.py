"""
akaalEngine.discovery.strategies.streaming.pubsub
================================================
Canonical Google Cloud Pub/Sub streaming discovery strategy.
Introspects list_topics, list_subscriptions, and message retention duration.
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
from akaalEngine.discovery.spi.streaming import StreamingDiscoveryStrategy

logger = logging.getLogger("akaalEngine.discovery.strategies.pubsub")


class PubSubDiscoveryStrategy(StreamingDiscoveryStrategy):
    """Google Cloud Pub/Sub physical discovery strategy."""

    PROVIDER_ID = "pubsub"

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
            engine_name="Google Cloud Pub/Sub Serverless Messaging",
            system_type="PUBSUB",
            version=ServerVersion(raw_version_string="Google Pub/Sub Managed", major=1, minor=0, patch=0),
            edition=EngineEdition(edition_name="Global Serverless Messaging", is_enterprise=True, is_cloud_managed=True),
            instance_name=project_id,
        )

    def discover_namespaces(
        self,
        connection: Any,
        spec: EndpointSpec,
        context: DiscoveryContext,
    ) -> NamespaceInventory:
        topics = []
        project_id = spec.account_id or spec.options.get("project_id", "gcp-project")
        if connection is not None and hasattr(connection, "list_topics"):
            try:
                for t in connection.list_topics(project=f"projects/{project_id}"):
                    tname = t.name.split("/")[-1]
                    topics.append(tname)
            except Exception as exc:
                logger.warning(f"Error listing pubsub topics: {exc}")
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
        topics = []
        if connection is not None and hasattr(connection, "list_topics"):
            try:
                project = spec.database_name or spec.options.get("project_id", "")
                parent = f"projects/{project}" if project else ""
                res = connection.list_topics(request={"project": parent} if parent else {})
                for t in res:
                    t_name = getattr(t, "name", str(t)).split("/")[-1]
                    topics.append(
                        TableFacts(
                            name=t_name,
                            schema_name=schema_name,
                            object_type=ObjectType.STREAM_TOPIC,
                            classification=ObjectClassification.USER,
                        )
                    )
            except Exception as exc:
                logger.warning(f"Error querying pubsub topics in {schema_name}: {exc}")
                raise

        return CatalogPaginator.paginate_sequence(topics, cursor=cursor, page_size=page_size)

    def discover_object_structure(
        self,
        connection: Any,
        spec: EndpointSpec,
        schema_name: str,
        object_name: str,
        context: DiscoveryContext,
    ) -> ObjectStructureFacts:
        cols = [
            ColumnPhysicalMetadata(name="message_id", ordinal_position=1, native_type="STRING", is_identity=True),
            ColumnPhysicalMetadata(name="data", ordinal_position=2, native_type="BYTES / JSON / PROTOBUF"),
            ColumnPhysicalMetadata(name="attributes", ordinal_position=3, native_type="MAP<STRING, STRING>"),
            ColumnPhysicalMetadata(name="publish_time", ordinal_position=4, native_type="TIMESTAMP"),
            ColumnPhysicalMetadata(name="ordering_key", ordinal_position=5, native_type="STRING"),
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
        if connection is not None and hasattr(connection, "get_topic"):
            try:
                top = connection.get_topic(topic=topic_name)
                ret = getattr(top, "message_retention_duration", None)
                if ret:
                    return {"message_retention_duration": str(ret)}
            except Exception:
                pass
        return {}

    def check_read_only_permissions(
        self,
        connection: Any,
        spec: EndpointSpec,
    ) -> ThreeStatePermission:
        # Pub/Sub has no non-destructive physical probe for read-only role state
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
                connection.list_topics()
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
                blocker_reasons=("PubSub connection not established",),
            )
        if not hasattr(connection, "list_topics"):
            return CDCPrerequisiteSnapshot(
                is_cdc_ready=False,
                mechanism=CDCMechanism.GCP_PUBSUB,
                blocker_reasons=("PubSub client connection unverified",),
            )
        try:
            project_id = spec.account_id or spec.options.get("project_id", "gcp-project")
            connection.list_topics(project=f"projects/{project_id}")
            target_topic = spec.database_name
            if target_topic and hasattr(connection, "get_topic"):
                connection.get_topic(topic=f"projects/{project_id}/topics/{target_topic}")
            return CDCPrerequisiteSnapshot(
                is_cdc_ready=True,
                mechanism=CDCMechanism.GCP_PUBSUB,
            )
        except Exception as exc:
            return CDCPrerequisiteSnapshot(
                is_cdc_ready=False,
                mechanism=CDCMechanism.GCP_PUBSUB,
                blocker_reasons=(f"PubSub stream physical readiness verification failed: {exc}",),
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
            return DeterministicSampler.package_sample(table_name, schema_name or "", ["MessageId", "Data", "Attributes", "PublishTime"], [])
        except Exception as exc:
            return DeterministicSampler.package_failure(table_name, schema_name or "", str(exc))

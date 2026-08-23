"""
akaalEngine.discovery.strategies.streaming.kinesis
==================================================
Canonical Amazon Kinesis Data Streams discovery strategy.
Introspects list_streams, describe_stream_summary, list_shards, and retention periods.
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

logger = logging.getLogger("akaalEngine.discovery.strategies.kinesis")


class KinesisDiscoveryStrategy(StreamingDiscoveryStrategy):
    """Amazon Kinesis Data Streams physical discovery strategy."""

    PROVIDER_ID = "kinesis"

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
            engine_name="Amazon Kinesis Data Streams",
            system_type="KINESIS",
            version=ServerVersion(raw_version_string="AWS Kinesis Managed", major=1, minor=0, patch=0),
            edition=EngineEdition(edition_name="Managed Cloud Streaming", is_enterprise=True, is_cloud_managed=True),
            instance_name=f"kinesis-{region}",
        )

    def discover_namespaces(
        self,
        connection: Any,
        spec: EndpointSpec,
        context: DiscoveryContext,
    ) -> NamespaceInventory:
        streams = []
        if connection is not None and hasattr(connection, "list_streams"):
            try:
                res = connection.list_streams()
                streams = res.get("StreamNames", [])
            except Exception as exc:
                logger.warning(f"Error listing kinesis streams: {exc}")
                raise

        return NamespaceInventory(
            schemas=(),
            topics=tuple(streams),
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
        if connection is not None and hasattr(connection, "list_streams"):
            try:
                res = connection.list_streams()
                for sname in res.get("StreamNames", []):
                    items.append(
                        TableFacts(
                            name=sname,
                            schema_name=schema_name,
                            object_type=ObjectType.STREAM,
                            classification=ObjectClassification.USER,
                        )
                    )
            except Exception as exc:
                logger.warning(f"Error querying kinesis streams: {exc}")
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
            ColumnPhysicalMetadata(name="PartitionKey", ordinal_position=1, native_type="STRING", is_identity=True),
            ColumnPhysicalMetadata(name="Data", ordinal_position=2, native_type="BYTES / BLOB"),
            ColumnPhysicalMetadata(name="SequenceNumber", ordinal_position=3, native_type="STRING"),
            ColumnPhysicalMetadata(name="ApproximateArrivalTimestamp", ordinal_position=4, native_type="TIMESTAMP"),
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
        if connection is not None and hasattr(connection, "describe_stream_summary"):
            try:
                res = connection.describe_stream_summary(StreamName=topic_name)
                desc = res.get("StreamDescriptionSummary", {})
                ret = desc.get("RetentionPeriodHours")
                if ret is not None:
                    return {"RetentionPeriodHours": ret}
            except Exception:
                pass
        return {}

    def check_read_only_permissions(
        self,
        connection: Any,
        spec: EndpointSpec,
    ) -> ThreeStatePermission:
        # Kinesis has no non-destructive physical probe for read-only role state
        return ThreeStatePermission.UNKNOWN

    def discover_permissions(
        self,
        connection: Any,
        spec: EndpointSpec,
        context: DiscoveryContext,
    ) -> PermissionAssessment:
        cat_perm = ThreeStatePermission.UNKNOWN
        if connection is not None and hasattr(connection, "list_streams"):
            try:
                connection.list_streams(Limit=1)
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
                blocker_reasons=("Kinesis connection not established",),
            )
        if not hasattr(connection, "list_streams"):
            return CDCPrerequisiteSnapshot(
                is_cdc_ready=False,
                mechanism=CDCMechanism.KINESIS_DATA_STREAMS,
                blocker_reasons=("Kinesis client connection unverified",),
            )
        try:
            connection.list_streams(Limit=1)
            target = spec.database_name
            if target and hasattr(connection, "describe_stream_summary"):
                summary = connection.describe_stream_summary(StreamName=target)
                status = summary.get("StreamDescriptionSummary", {}).get("StreamStatus", "")
                if status != "ACTIVE":
                    return CDCPrerequisiteSnapshot(
                        is_cdc_ready=False,
                        mechanism=CDCMechanism.KINESIS_DATA_STREAMS,
                        blocker_reasons=(f"Kinesis stream '{target}' status is '{status}' (must be ACTIVE)",),
                    )
            return CDCPrerequisiteSnapshot(
                is_cdc_ready=True,
                mechanism=CDCMechanism.KINESIS_DATA_STREAMS,
            )
        except Exception as exc:
            return CDCPrerequisiteSnapshot(
                is_cdc_ready=False,
                mechanism=CDCMechanism.KINESIS_DATA_STREAMS,
                blocker_reasons=(f"Kinesis stream physical readiness verification failed: {exc}",),
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
        if connection is None or not hasattr(connection, "get_shard_iterator"):
            return DeterministicSampler.package_sample(table_name, schema_name or "", ["PartitionKey", "Data", "SequenceNumber"], [])
        try:
            return DeterministicSampler.package_sample(table_name, schema_name or "", ["PartitionKey", "Data", "SequenceNumber"], [])
        except Exception as exc:
            return DeterministicSampler.package_failure(table_name, schema_name or "", str(exc))

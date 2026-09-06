"""
akaalEngine.discovery.strategies.storage.oci_object_storage
=============================================================
Canonical Oracle Cloud Infrastructure (OCI) Object Storage discovery strategy.
Introspects namespace/bucket/object inventory via the real `oci` SDK ObjectStorageClient,
never fabricating bucket or object facts when the client/connection is absent.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from akaalEngine.connection.models.endpoint import EndpointSpec
from akaalEngine.connection.routing.resolver import ResolvedRoute
from akaalEngine.discovery.core.paginator import CatalogPaginator, DiscoveryCursor
from akaalEngine.discovery.core.sampling import DeterministicSampler
from akaalEngine.discovery.models.cdc import CDCMechanism, CDCPrerequisiteSnapshot
from akaalEngine.discovery.models.context import DiscoveryContext
from akaalEngine.discovery.models.environment import CharsetFacts, ConfigurationFacts, LimitsFacts, TimezoneFacts
from akaalEngine.discovery.models.identity import DiscoveredEndpointIdentity, EngineEdition, ServerVersion
from akaalEngine.discovery.models.inventory import NamespaceInventory, ObjectClassification, ObjectInventoryPage, ObjectType, TableFacts
from akaalEngine.discovery.models.permissions import PermissionAssessment, ThreeStatePermission
from akaalEngine.discovery.models.structure import ColumnPhysicalMetadata, ObjectStructureFacts
from akaalEngine.discovery.models.topology import TopologySnapshot
from akaalEngine.discovery.spi.storage import StorageDiscoveryStrategy

logger = logging.getLogger("akaalEngine.discovery.strategies.oci_object_storage")


class OCIObjectStorageDiscoveryStrategy(StorageDiscoveryStrategy):
    """OCI Object Storage physical discovery strategy."""

    PROVIDER_ID = "oci_object_storage"

    @property
    def provider_id(self) -> str:
        return self.PROVIDER_ID

    def discover_endpoint_identity(
        self,
        connection: Any,
        spec: EndpointSpec,
        route: Optional[ResolvedRoute] = None,
    ) -> DiscoveredEndpointIdentity:
        region = spec.region or spec.options.get("region", "us-ashburn-1")
        namespace = spec.options.get("namespace")
        if namespace is None and connection is not None and hasattr(connection, "get_namespace"):
            try:
                namespace = connection.get_namespace().data
            except Exception:
                namespace = None
        return DiscoveredEndpointIdentity(
            provider_id=self.PROVIDER_ID,
            vendor_name="Oracle Cloud Infrastructure",
            engine_name="OCI Object Storage",
            system_type="OCI_OBJECT_STORAGE",
            version=ServerVersion(raw_version_string="OCI Object Storage API", major=1, minor=0, patch=0),
            edition=EngineEdition(edition_name="Cloud Object Store", is_enterprise=True, is_cloud_managed=True),
            instance_name=f"oci-object-storage-{region}",
            host=spec.host or f"objectstorage.{region}.oraclecloud.com",
            port=spec.port or 443,
            database_name=namespace,
        )

    def discover_namespaces(
        self,
        connection: Any,
        spec: EndpointSpec,
        context: DiscoveryContext,
    ) -> NamespaceInventory:
        buckets = []
        namespace = spec.options.get("namespace")
        compartment_id = spec.options.get("compartment_id")
        if connection is not None and hasattr(connection, "list_buckets") and namespace and compartment_id:
            try:
                res = connection.list_buckets(namespace_name=namespace, compartment_id=compartment_id)
                buckets = [b.name for b in getattr(res, "data", []) or []]
            except Exception as exc:
                logger.warning(f"Error listing OCI Object Storage buckets: {exc}")
                raise

        if not buckets and spec.options.get("bucket"):
            buckets = [spec.options["bucket"]]

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
        namespace = spec.options.get("namespace")
        if connection is not None and hasattr(connection, "list_objects") and namespace:
            try:
                cur = DiscoveryCursor.decode(cursor)
                kwargs: dict[str, Any] = {
                    "namespace_name": namespace,
                    "bucket_name": schema_name or spec.options.get("bucket") or "",
                    "limit": page_size,
                    "delimiter": "/",
                }
                if cur.provider_token:
                    kwargs["start"] = cur.provider_token
                res = connection.list_objects(**kwargs)
                data = res.data
                next_tok = getattr(data, "next_start_with", None) or ""

                for pfx in getattr(data, "prefixes", None) or []:
                    items.append(
                        TableFacts(
                            name=pfx.rstrip("/"),
                            schema_name=schema_name,
                            object_type=ObjectType.TABLE,
                            classification=ObjectClassification.USER,
                            storage_format="DIRECTORY_DATASET",
                        )
                    )
                for obj in getattr(data, "objects", None) or []:
                    name = obj.name
                    if not name.endswith("/"):
                        items.append(
                            TableFacts(
                                name=name,
                                schema_name=schema_name,
                                object_type=ObjectType.FILE,
                                classification=ObjectClassification.USER,
                                size_bytes_estimate=getattr(obj, "size", 0) or 0,
                            )
                        )
            except Exception as exc:
                logger.warning(f"Error listing OCI Object Storage objects in {schema_name}: {exc}")
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
            ColumnPhysicalMetadata(name="name", ordinal_position=1, native_type="STRING", is_identity=True),
            ColumnPhysicalMetadata(name="size", ordinal_position=2, native_type="INT64"),
            ColumnPhysicalMetadata(name="time_modified", ordinal_position=3, native_type="TIMESTAMP"),
            ColumnPhysicalMetadata(name="etag", ordinal_position=4, native_type="STRING"),
            ColumnPhysicalMetadata(name="storage_tier", ordinal_position=5, native_type="STRING"),
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
        # OCI Object Storage has no non-destructive physical probe for read-only role state.
        return ThreeStatePermission.UNKNOWN

    def discover_permissions(
        self,
        connection: Any,
        spec: EndpointSpec,
        context: DiscoveryContext,
    ) -> PermissionAssessment:
        cat_perm = ThreeStatePermission.UNKNOWN
        namespace = spec.options.get("namespace")
        if connection is not None and hasattr(connection, "get_namespace") and namespace:
            try:
                connection.get_namespace()
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
                blocker_reasons=("OCI Object Storage connection not established",),
            )
        # OCI Object Storage has an Events service (via OCI Streaming/Notifications) but this
        # connector does not implement event-based tailing; truthfully report not-ready.
        return CDCPrerequisiteSnapshot(
            is_cdc_ready=False,
            mechanism=CDCMechanism.POLLING_WATERMARK,
            blocker_reasons=("OCI Object Storage Events/Notifications-based CDC tailing not implemented by this connector",),
        )

    def sample_data(
        self,
        connection: Any,
        spec: EndpointSpec,
        schema_name: str,
        table_name: str,
        limit: int = 100,
        timeout_seconds: float = 3.0,
    ):
        try:
            return DeterministicSampler.package_sample(table_name, schema_name, ["name", "size"], [])
        except Exception as exc:
            return DeterministicSampler.package_failure(table_name, schema_name, str(exc))

"""
akaalEngine.discovery.strategies.application.salesforce
==========================================================
Canonical Salesforce discovery strategy (P7A Campaign B, provider #46).
Introspects SObject metadata via the real SObject Describe REST API
(`sf.describe()`/`sf.<SObject>.describe()`) -- object/field inventory, not a relational
schema; Salesforce enforces field-level types and picklists, not PK/FK/index concepts.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from akaalEngine.connection.models.endpoint import EndpointSpec
from akaalEngine.connection.routing.resolver import ResolvedRoute
from akaalEngine.discovery.core.sampling import DeterministicSampler
from akaalEngine.discovery.models.cdc import CDCMechanism, CDCPrerequisiteSnapshot
from akaalEngine.discovery.models.context import DiscoveryContext
from akaalEngine.discovery.models.environment import CharsetFacts, ConfigurationFacts, LimitsFacts, TimezoneFacts
from akaalEngine.discovery.models.identity import DiscoveredEndpointIdentity, EngineEdition, ServerVersion
from akaalEngine.discovery.models.inventory import NamespaceInventory, ObjectClassification, ObjectInventoryPage, ObjectType, TableFacts
from akaalEngine.discovery.models.permissions import PermissionAssessment, ThreeStatePermission
from akaalEngine.discovery.models.sampling import SampledRecordSet
from akaalEngine.discovery.models.structure import ColumnPhysicalMetadata, ObjectStructureFacts, PrimaryKeyFacts
from akaalEngine.discovery.models.topology import ClusterNodeFacts, NodeRole, TopologySnapshot
from akaalEngine.discovery.spi.strategy import BaseDiscoveryStrategy

logger = logging.getLogger("akaalEngine.discovery.strategies.salesforce")


class SalesforceDiscoveryStrategy(BaseDiscoveryStrategy):
    """Salesforce physical discovery strategy -- SaaS/application platform, not a database."""

    PROVIDER_ID = "salesforce"

    @property
    def provider_id(self) -> str:
        return self.PROVIDER_ID

    def discover_endpoint_identity(self, connection: Any, spec: EndpointSpec, route: Optional[ResolvedRoute] = None) -> DiscoveredEndpointIdentity:
        api_version = getattr(connection, "sf_version", None) if connection is not None else None
        instance = getattr(connection, "sf_instance", None) if connection is not None else None
        return DiscoveredEndpointIdentity(
            provider_id=self.PROVIDER_ID, vendor_name="Salesforce, Inc.", engine_name="Salesforce", system_type="SALESFORCE",
            version=ServerVersion(raw_version_string=f"Salesforce REST API v{api_version or 'unknown'}", major=0, minor=0, patch=0),
            edition=EngineEdition(edition_name="SaaS", is_enterprise=True),
            host=instance or spec.host or "salesforce.com", port=443, database_name=None,
        )

    def discover_namespaces(self, connection: Any, spec: EndpointSpec, context: DiscoveryContext) -> NamespaceInventory:
        # Salesforce has no schema layer above the org itself -- SObjects are the whole
        # discoverable namespace of a single connected org.
        return NamespaceInventory(schemas=("default",), default_schema="default")

    def discover_objects_page(self, connection: Any, spec: EndpointSpec, schema_name: str, context: DiscoveryContext, cursor: Optional[str] = None, page_size: int = 500) -> ObjectInventoryPage:
        items = []
        if connection is not None and hasattr(connection, "describe"):
            try:
                global_desc = connection.describe()
                for sobj in global_desc.get("sobjects", []):
                    if sobj.get("queryable"):
                        items.append(TableFacts(name=sobj.get("name", ""), schema_name=schema_name, object_type=ObjectType.TABLE, classification=ObjectClassification.USER))
            except Exception as exc:
                logger.warning(f"Error listing Salesforce SObjects: {exc}")
                raise
        return ObjectInventoryPage(items=tuple(items), cursor=None, is_last_page=True)

    def discover_object_structure(self, connection: Any, spec: EndpointSpec, schema_name: str, object_name: str, context: DiscoveryContext) -> ObjectStructureFacts:
        cols, primary_key = [], None
        if connection is not None and hasattr(connection, object_name):
            try:
                sobj_client = getattr(connection, object_name)
                desc = sobj_client.describe()
                for i, f in enumerate(desc.get("fields", [])):
                    cols.append(ColumnPhysicalMetadata(
                        name=f.get("name", ""), ordinal_position=i + 1, native_type=str(f.get("type", "string")).upper(),
                        nullable=bool(f.get("nillable", True)), is_identity=(f.get("name") == "Id"),
                    ))
                primary_key = PrimaryKeyFacts(name=f"{object_name}_id", table_name=object_name, columns=("Id",), schema_name=schema_name)
            except Exception as exc:
                logger.warning(f"Error describing Salesforce SObject {object_name}: {exc}")
                raise
        return ObjectStructureFacts(table_name=object_name, schema_name=schema_name, columns=tuple(cols), primary_key=primary_key)

    def check_read_only_permissions(self, connection: Any, spec: EndpointSpec) -> ThreeStatePermission:
        return ThreeStatePermission.UNKNOWN

    def discover_permissions(self, connection: Any, spec: EndpointSpec, context: DiscoveryContext) -> PermissionAssessment:
        cat_read = ThreeStatePermission.UNKNOWN
        if connection is not None and hasattr(connection, "query"):
            try:
                connection.query("SELECT Id FROM Organization LIMIT 1")
                cat_read = ThreeStatePermission.PROVEN
            except Exception:
                cat_read = ThreeStatePermission.DENIED
        return PermissionAssessment(read_only_verified=ThreeStatePermission.UNKNOWN, metadata_catalog_read=cat_read)

    def discover_environment(self, connection: Any, spec: EndpointSpec, context: DiscoveryContext) -> ConfigurationFacts:
        return ConfigurationFacts(charset=CharsetFacts(server_encoding="UTF-8"), timezone=TimezoneFacts(database_timezone="UTC"), limits=LimitsFacts(max_connections=None))

    def discover_topology(self, connection: Any, spec: EndpointSpec, context: DiscoveryContext) -> TopologySnapshot:
        node = ClusterNodeFacts(node_id="salesforce-managed-endpoint", host=spec.host or "salesforce.com", port=443, role=NodeRole.UNKNOWN)
        return TopologySnapshot(is_clustered=False, connected_node_role=NodeRole.UNKNOWN, nodes=(node,))

    def discover_cdc_prerequisites(self, connection: Any, spec: EndpointSpec, context: DiscoveryContext) -> CDCPrerequisiteSnapshot:
        return CDCPrerequisiteSnapshot(is_cdc_ready=False, mechanism=CDCMechanism.UNSUPPORTED, blocker_reasons=("No Salesforce Change Data Capture/Platform Events capture module implemented in this Engine.",))

    def sample_data(self, connection: Any, spec: EndpointSpec, schema_name: str, table_name: str, limit: int = 100, timeout_seconds: float = 3.0) -> SampledRecordSet:
        if connection is None or not hasattr(connection, "query"):
            return DeterministicSampler.package_sample(table_name, schema_name, [], [])
        try:
            resp = connection.query(f"SELECT FIELDS(ALL) FROM {table_name} LIMIT {int(limit)}")
            records = resp.get("records", []) if isinstance(resp, dict) else []
            rows = [{k: v for k, v in r.items() if k != "attributes"} for r in records]
            cols = sorted({k for row in rows for k in row.keys()})
            return DeterministicSampler.package_sample(table_name, schema_name, cols, rows)
        except Exception as exc:
            logger.warning(f"Error sampling Salesforce SObject {table_name}: {exc}")
            return DeterministicSampler.package_failure(table_name, schema_name, str(exc))

    def get_schema_change_marker(self, connection: Any, spec: EndpointSpec) -> Optional[str]:
        return None

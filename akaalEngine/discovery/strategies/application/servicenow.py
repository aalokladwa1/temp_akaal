"""
akaalEngine.discovery.strategies.application.servicenow
==========================================================
Canonical ServiceNow discovery strategy (P7A Campaign B, provider #48).
Introspects table/field metadata via the real `sys_db_object`/`sys_dictionary` system
tables (queried through the same Table REST API as data access) -- object/field
inventory, not a relational schema; ServiceNow enforces field-level types, not
PK/FK/index concepts (sys_id is the real record identity).
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

logger = logging.getLogger("akaalEngine.discovery.strategies.servicenow")


class ServiceNowDiscoveryStrategy(BaseDiscoveryStrategy):
    """ServiceNow physical discovery strategy -- SaaS/application platform, not a database."""

    PROVIDER_ID = "servicenow"

    @property
    def provider_id(self) -> str:
        return self.PROVIDER_ID

    def _base(self, connection: Any) -> str:
        return getattr(connection, "base_url", "") if connection is not None else ""

    def discover_endpoint_identity(self, connection: Any, spec: EndpointSpec, route: Optional[ResolvedRoute] = None) -> DiscoveredEndpointIdentity:
        base = self._base(connection) or (spec.host or "service-now.com")
        return DiscoveredEndpointIdentity(
            provider_id=self.PROVIDER_ID, vendor_name="ServiceNow, Inc.", engine_name="ServiceNow", system_type="SERVICENOW",
            version=ServerVersion(raw_version_string="ServiceNow Table REST API", major=0, minor=0, patch=0),
            edition=EngineEdition(edition_name="SaaS", is_enterprise=True),
            host=base, port=443, database_name=None,
        )

    def discover_namespaces(self, connection: Any, spec: EndpointSpec, context: DiscoveryContext) -> NamespaceInventory:
        return NamespaceInventory(schemas=("default",), default_schema="default")

    def discover_objects_page(self, connection: Any, spec: EndpointSpec, schema_name: str, context: DiscoveryContext, cursor: Optional[str] = None, page_size: int = 500) -> ObjectInventoryPage:
        items = []
        if connection is not None and hasattr(connection, "get"):
            try:
                base = self._base(connection)
                resp = connection.get(f"{base}/api/now/table/sys_db_object", params={"sysparm_limit": min(page_size, 1000), "sysparm_fields": "name"})
                resp.raise_for_status()
                for row in (resp.json() or {}).get("result", []):
                    name = row.get("name", "")
                    if name:
                        items.append(TableFacts(name=name, schema_name=schema_name, object_type=ObjectType.TABLE, classification=ObjectClassification.USER))
            except Exception as exc:
                logger.warning(f"Error listing ServiceNow tables: {exc}")
                raise
        return ObjectInventoryPage(items=tuple(items), cursor=None, is_last_page=True)

    def discover_object_structure(self, connection: Any, spec: EndpointSpec, schema_name: str, object_name: str, context: DiscoveryContext) -> ObjectStructureFacts:
        cols = []
        if connection is not None and hasattr(connection, "get"):
            try:
                base = self._base(connection)
                resp = connection.get(
                    f"{base}/api/now/table/sys_dictionary",
                    params={"sysparm_query": f"name={object_name}", "sysparm_fields": "element,internal_type,mandatory", "sysparm_limit": 500},
                )
                resp.raise_for_status()
                for i, row in enumerate((resp.json() or {}).get("result", [])):
                    field = row.get("element")
                    if not field:
                        continue
                    cols.append(ColumnPhysicalMetadata(
                        name=field, ordinal_position=i + 1, native_type=str(row.get("internal_type", "string")).upper(),
                        nullable=(str(row.get("mandatory", "false")).lower() != "true"), is_identity=(field == "sys_id"),
                    ))
            except Exception as exc:
                logger.warning(f"Error describing ServiceNow table {object_name}: {exc}")
                raise
        primary_key = PrimaryKeyFacts(name=f"{object_name}_sys_id", table_name=object_name, columns=("sys_id",), schema_name=schema_name)
        return ObjectStructureFacts(table_name=object_name, schema_name=schema_name, columns=tuple(cols), primary_key=primary_key)

    def check_read_only_permissions(self, connection: Any, spec: EndpointSpec) -> ThreeStatePermission:
        return ThreeStatePermission.UNKNOWN

    def discover_permissions(self, connection: Any, spec: EndpointSpec, context: DiscoveryContext) -> PermissionAssessment:
        cat_read = ThreeStatePermission.UNKNOWN
        if connection is not None and hasattr(connection, "get"):
            try:
                base = self._base(connection)
                resp = connection.get(f"{base}/api/now/table/sys_user", params={"sysparm_limit": 1})
                cat_read = ThreeStatePermission.PROVEN if getattr(resp, "status_code", 500) < 400 else ThreeStatePermission.DENIED
            except Exception:
                cat_read = ThreeStatePermission.DENIED
        return PermissionAssessment(read_only_verified=ThreeStatePermission.UNKNOWN, metadata_catalog_read=cat_read)

    def discover_environment(self, connection: Any, spec: EndpointSpec, context: DiscoveryContext) -> ConfigurationFacts:
        return ConfigurationFacts(charset=CharsetFacts(server_encoding="UTF-8"), timezone=TimezoneFacts(database_timezone="UTC"), limits=LimitsFacts(max_connections=None))

    def discover_topology(self, connection: Any, spec: EndpointSpec, context: DiscoveryContext) -> TopologySnapshot:
        node = ClusterNodeFacts(node_id="servicenow-managed-endpoint", host=self._base(connection) or (spec.host or "service-now.com"), port=443, role=NodeRole.UNKNOWN)
        return TopologySnapshot(is_clustered=False, connected_node_role=NodeRole.UNKNOWN, nodes=(node,))

    def discover_cdc_prerequisites(self, connection: Any, spec: EndpointSpec, context: DiscoveryContext) -> CDCPrerequisiteSnapshot:
        return CDCPrerequisiteSnapshot(is_cdc_ready=False, mechanism=CDCMechanism.UNSUPPORTED, blocker_reasons=("No native ServiceNow CDC mechanism implemented in this Engine -- sys_updated_on polling is incremental extraction, not change-data-capture.",))

    def sample_data(self, connection: Any, spec: EndpointSpec, schema_name: str, table_name: str, limit: int = 100, timeout_seconds: float = 3.0) -> SampledRecordSet:
        if connection is None or not hasattr(connection, "get"):
            return DeterministicSampler.package_sample(table_name, schema_name, [], [])
        try:
            base = self._base(connection)
            resp = connection.get(f"{base}/api/now/table/{table_name}", params={"sysparm_limit": int(limit)})
            resp.raise_for_status()
            rows = (resp.json() or {}).get("result", [])
            cols = sorted({k for row in rows for k in row.keys()})
            return DeterministicSampler.package_sample(table_name, schema_name, cols, rows)
        except Exception as exc:
            logger.warning(f"Error sampling ServiceNow table {table_name}: {exc}")
            return DeterministicSampler.package_failure(table_name, schema_name, str(exc))

    def get_schema_change_marker(self, connection: Any, spec: EndpointSpec) -> Optional[str]:
        return None

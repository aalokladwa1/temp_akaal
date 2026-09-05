"""
akaalEngine.discovery.strategies.timeseries.influxdb
========================================================
Canonical InfluxDB discovery strategy (P7A Campaign B).

Introspects buckets (namespace-equivalent), measurements (object-equivalent), and real
tag/field keys via Flux's `schema` package -- InfluxDB's own genuine introspection
mechanism, not borrowed from any relational catalog convention. Tag keys (indexed
dimensions) and field keys (values) are structurally different concepts in InfluxDB's
data model and are reported as such via `ColumnPhysicalMetadata.properties`, not
collapsed into a single undifferentiated column list.
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
from akaalEngine.discovery.spi.timeseries import TimeSeriesDiscoveryStrategy

logger = logging.getLogger("akaalEngine.discovery.strategies.influxdb")


class InfluxDBDiscoveryStrategy(TimeSeriesDiscoveryStrategy):
    """InfluxDB physical discovery strategy -- measurement/tag/field time-series model."""

    PROVIDER_ID = "influxdb"

    @property
    def provider_id(self) -> str:
        return self.PROVIDER_ID

    def discover_endpoint_identity(
        self,
        connection: Any,
        spec: EndpointSpec,
        route: Optional[ResolvedRoute] = None,
    ) -> DiscoveredEndpointIdentity:
        version_str = "InfluxDB"
        major, minor, patch = 0, 0, 0
        if connection is not None:
            try:
                health = connection.health()
                if health and getattr(health, "version", None):
                    version_str = f"InfluxDB {health.version}"
                    parts = str(health.version).split(".")
                    major = int(parts[0]) if len(parts) > 0 and parts[0].isdigit() else 0
                    minor = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0
            except Exception as exc:
                logger.warning(f"Error fetching InfluxDB health/version: {exc}")

        return DiscoveredEndpointIdentity(
            provider_id=self.PROVIDER_ID,
            vendor_name="InfluxData",
            engine_name="InfluxDB",
            system_type="INFLUXDB",
            version=ServerVersion(raw_version_string=version_str, major=major, minor=minor, patch=patch),
            edition=EngineEdition(edition_name="OSS / Cloud", is_enterprise=False),
            host=spec.host,
            port=spec.port or 8086,
            database_name=spec.options.get("bucket", ""),
        )

    def discover_namespaces(
        self,
        connection: Any,
        spec: EndpointSpec,
        context: DiscoveryContext,
    ) -> NamespaceInventory:
        buckets = []
        if connection is not None:
            try:
                buckets_api = connection.buckets_api()
                for b in buckets_api.find_buckets().buckets:
                    if not b.name.startswith("_"):  # exclude system buckets (_monitoring, _tasks)
                        buckets.append(b.name)
            except Exception as exc:
                logger.warning(f"Error discovering InfluxDB buckets: {exc}")

        return NamespaceInventory(
            schemas=tuple(buckets),
            default_schema=spec.options.get("bucket") if spec.options.get("bucket") in buckets else (buckets[0] if buckets else None),
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
        if connection is not None:
            try:
                org = spec.options.get("org", "")
                flux = f'import "influxdata/influxdb/schema"\nschema.measurements(bucket: "{schema_name}")'
                tables = connection.query_api().query(flux, org=org)
                for table in tables:
                    for record in table.records:
                        name = record.get_value()
                        items.append(TableFacts(name=name, schema_name=schema_name, object_type=ObjectType.STREAM, classification=ObjectClassification.USER))
            except Exception as exc:
                logger.warning(f"Error querying InfluxDB measurements in bucket {schema_name}: {exc}")
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
        cols = [ColumnPhysicalMetadata(name="_time", ordinal_position=1, native_type="TIMESTAMP", is_identity=True)]
        if connection is not None:
            try:
                org = spec.options.get("org", "")
                tag_flux = (
                    'import "influxdata/influxdb/schema"\n'
                    f'schema.tagKeys(bucket: "{schema_name}", predicate: (r) => r._measurement == "{object_name}")'
                )
                pos = 2
                for table in connection.query_api().query(tag_flux, org=org):
                    for record in table.records:
                        tag_name = record.get_value()
                        if tag_name.startswith("_"):
                            continue
                        cols.append(ColumnPhysicalMetadata(name=tag_name, ordinal_position=pos, native_type="TAG (indexed string)", nullable=True))
                        pos += 1

                field_flux = (
                    'import "influxdata/influxdb/schema"\n'
                    f'schema.fieldKeys(bucket: "{schema_name}", predicate: (r) => r._measurement == "{object_name}")'
                )
                for table in connection.query_api().query(field_flux, org=org):
                    for record in table.records:
                        field_name = record.get_value()
                        cols.append(ColumnPhysicalMetadata(name=field_name, ordinal_position=pos, native_type="FIELD (value)", nullable=True))
                        pos += 1
            except Exception as exc:
                logger.warning(f"Error discovering InfluxDB tag/field keys for {schema_name}.{object_name}: {exc}")
                raise

        return ObjectStructureFacts(
            table_name=object_name,
            schema_name=schema_name,
            columns=tuple(cols),
        )

    def discover_retention_policy(
        self,
        connection: Any,
        spec: EndpointSpec,
        bucket_name: str,
        context: DiscoveryContext,
    ) -> Mapping[str, Any]:
        if connection is None:
            return {}
        try:
            buckets_api = connection.buckets_api()
            result = buckets_api.find_buckets(name=bucket_name)
            if result.buckets:
                bucket = result.buckets[0]
                rules = bucket.retention_rules or []
                return {"retention_seconds": rules[0].every_seconds if rules else None}
        except Exception as exc:
            logger.info(f"InfluxDB retention policy probe failed for {bucket_name}: {exc}")
        return {}

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
        cat_perm = ThreeStatePermission.UNKNOWN
        if connection is not None:
            try:
                connection.buckets_api().find_buckets(limit=1)
                cat_perm = ThreeStatePermission.PROVEN
            except Exception:
                cat_perm = ThreeStatePermission.DENIED

        return PermissionAssessment(read_only_verified=ThreeStatePermission.UNKNOWN, metadata_catalog_read=cat_perm)

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
        node = ClusterNodeFacts(node_id="influxdb-endpoint", host=spec.host or "localhost", port=spec.port or 8086, role=NodeRole.UNKNOWN)
        return TopologySnapshot(is_clustered=False, connected_node_role=NodeRole.UNKNOWN, nodes=(node,))

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
                blocker_reasons=("InfluxDB connection not established",),
            )
        return CDCPrerequisiteSnapshot(
            is_cdc_ready=False,
            mechanism=CDCMechanism.POLLING_WATERMARK,
            blocker_reasons=("InfluxDB has no native change-log; only _time-range-based incremental polling is possible.",),
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
        if connection is None:
            return DeterministicSampler.package_sample(table_name, schema_name or "", [], [])
        try:
            org = spec.options.get("org", "")
            flux = (
                f'from(bucket: "{schema_name}") '
                f'|> range(start: -30d) '
                f'|> filter(fn: (r) => r._measurement == "{table_name}") '
                f'|> limit(n: {int(limit)})'
            )
            rows = []
            cols_seen = set()
            for table in connection.query_api().query(flux, org=org):
                for record in table.records:
                    row = {"_time": str(record.get_time()), "_field": record.get_field(), "_value": record.get_value()}
                    row.update({k: v for k, v in record.values.items() if not k.startswith("_") and k not in ("result", "table")})
                    rows.append(row)
                    cols_seen.update(row.keys())
            return DeterministicSampler.package_sample(table_name, schema_name or "", sorted(cols_seen), rows)
        except Exception as exc:
            logger.warning(f"Error sampling InfluxDB measurement {table_name}: {exc}")
            return DeterministicSampler.package_failure(table_name, schema_name or "", str(exc))

    def get_schema_change_marker(
        self,
        connection: Any,
        spec: EndpointSpec,
    ) -> Optional[str]:
        return None

"""
akaalEngine.discovery.strategies.relational.tidb
====================================================
Canonical TiDB discovery strategy (P7A Campaign B).

TiDB's INFORMATION_SCHEMA is MySQL-compatible for tables/columns/indexes/partitions, so
this inherits MySQLDiscoveryStrategy's catalog queries for those facts -- the same
architectural reasoning as the connection-layer PyMySQL reuse. Only the genuinely
TiDB-specific facts are overridden:
  - Endpoint identity: `VERSION()` returns a MySQL-compatibility string (e.g.
    "5.7.25-TiDB-v6.5.0"); `tidb_version()` is the real, TiDB-native version source.
  - Topology: real cluster node membership via `information_schema.CLUSTER_INFO`
    (TiDB-native), not MySQL's inherited no-op `discover_topology` (which returns an
    empty, unclustered snapshot -- correct for standalone MySQL, wrong for TiDB).
  - CDC prerequisites: TiDB does NOT use MySQL's binlog mechanism at all. Inheriting
    MySQLDiscoveryStrategy's `@@log_bin`/`@@binlog_format`/`SHOW MASTER STATUS`-based
    probe would silently produce a misleading result (those variables are meaningless or
    absent on TiDB) -- overridden to truthfully report that CDC requires the separate
    TiCDC component, not probed here.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from akaalEngine.connection.models.endpoint import EndpointSpec
from akaalEngine.connection.routing.resolver import ResolvedRoute
from akaalEngine.discovery.models.cdc import CDCMechanism, CDCPrerequisiteSnapshot
from akaalEngine.discovery.models.context import DiscoveryContext
from akaalEngine.discovery.models.identity import DiscoveredEndpointIdentity, EngineEdition, ServerVersion
from akaalEngine.discovery.models.topology import ClusterNodeFacts, NodeRole, TopologySnapshot
from akaalEngine.discovery.strategies.relational.mysql import MySQLDiscoveryStrategy

logger = logging.getLogger("akaalEngine.discovery.strategies.tidb")


class TiDBDiscoveryStrategy(MySQLDiscoveryStrategy):
    """TiDB physical discovery strategy -- distributed SQL, MySQL-compatible INFORMATION_SCHEMA."""

    PROVIDER_ID = "tidb"

    @property
    def provider_id(self) -> str:
        return self.PROVIDER_ID

    def discover_endpoint_identity(
        self,
        connection: Any,
        spec: EndpointSpec,
        route: Optional[ResolvedRoute] = None,
    ) -> DiscoveredEndpointIdentity:
        version_str = "TiDB"
        major, minor, patch = 0, 0, 0
        if connection is not None and hasattr(connection, "cursor"):
            try:
                cur = connection.cursor()
                cur.execute("SELECT tidb_version()")
                r = cur.fetchone()
                if r and r[0]:
                    version_str = str(r[0]).split("\n")[0]
                    for token in version_str.split():
                        if token.startswith("v") and "." in token:
                            parts = token[1:].split(".")
                            try:
                                major = int(parts[0])
                                minor = int(parts[1]) if len(parts) > 1 else 0
                                patch = int(parts[2].split("-")[0]) if len(parts) > 2 else 0
                            except (ValueError, IndexError):
                                pass
                            break
                cur.close()
            except Exception as exc:
                logger.warning(f"Error querying tidb_version(): {exc}")

        return DiscoveredEndpointIdentity(
            provider_id=self.PROVIDER_ID,
            vendor_name="PingCAP",
            engine_name="TiDB",
            system_type="TIDB",
            version=ServerVersion(raw_version_string=version_str, major=major, minor=minor, patch=patch),
            edition=EngineEdition(edition_name="Community / Enterprise", is_enterprise=True),
            host=spec.host,
            port=spec.port or 4000,
            database_name=spec.database_name,
        )

    def discover_topology(
        self,
        connection: Any,
        spec: EndpointSpec,
        context: DiscoveryContext,
    ) -> TopologySnapshot:
        nodes = []
        if connection is not None and hasattr(connection, "cursor"):
            try:
                cur = connection.cursor()
                cur.execute("SELECT TYPE, INSTANCE, STATUS_ADDRESS FROM information_schema.CLUSTER_INFO")
                for row in cur.fetchall():
                    node_type, instance, status_addr = row[0], row[1], row[2]
                    host = instance.split(":")[0] if instance and ":" in instance else (instance or spec.host or "localhost")
                    port = int(instance.split(":")[1]) if instance and ":" in instance else (spec.port or 4000)
                    nodes.append(
                        ClusterNodeFacts(
                            node_id=f"{node_type}_{instance}",
                            host=host,
                            port=port,
                            role=NodeRole.WORKER,
                        )
                    )
                cur.close()
            except Exception as exc:
                logger.warning(f"Error discovering TiDB cluster topology: {exc}")

        if not nodes:
            nodes = [ClusterNodeFacts(node_id="connected_node", host=spec.host or "localhost", port=spec.port or 4000, role=NodeRole.WORKER)]

        return TopologySnapshot(
            is_clustered=len(nodes) > 1,
            connected_node_role=NodeRole.WORKER,
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
                blocker_reasons=("TiDB connection not established",),
            )
        # TiDB does not use MySQL's binlog mechanism -- CDC requires the separate TiCDC
        # component, which this connector does not probe (no TiCDC API endpoint
        # configured/reachable from a plain SQL connection).
        return CDCPrerequisiteSnapshot(
            is_cdc_ready=False,
            mechanism=CDCMechanism.TIDB_CDC,
            blocker_reasons=("TiDB CDC requires the separate TiCDC component; not reachable via a plain SQL connection and not probed by this connector strategy.",),
        )

    def get_schema_change_marker(
        self,
        connection: Any,
        spec: EndpointSpec,
    ) -> Optional[str]:
        if connection is not None and hasattr(connection, "cursor"):
            try:
                cur = connection.cursor()
                cur.execute("SELECT @@tidb_current_ts")
                r = cur.fetchone()
                cur.close()
                if r:
                    return str(r[0])
            except Exception:
                pass
        return None

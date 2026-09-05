"""
akaalEngine.discovery.strategies.relational.singlestore
===========================================================
Canonical SingleStore discovery strategy (P7A Campaign B).

SingleStore's INFORMATION_SCHEMA is MySQL-compatible, so this inherits
MySQLDiscoveryStrategy's catalog queries for tables/columns/indexes -- including
`discover_partitioning`, which is correctly left inherited: SingleStore's optional
explicit `PARTITION BY` feature is genuinely exposed through the same
`information_schema.PARTITIONS` view MySQL uses (distinct from SingleStore's automatic,
non-catalog-visible shard-key sharding, which this strategy does not attempt to surface
through this same mechanism). Overridden where SingleStore is genuinely different:
  - Endpoint identity: `@@memsql_version` (SingleStore's real version variable, a legacy
    name from its MemSQL predecessor), not MySQL's `VERSION()`.
  - Topology: real aggregator/leaf cluster membership via SingleStore-native `SHOW
    AGGREGATORS`/`SHOW LEAVES`, not MySQL's inherited no-op `discover_topology`.
  - CDC prerequisites: explicitly does NOT inherit MySQL's binlog-based probe --
    SingleStore doesn't expose MySQL-compatible binlog replication as a change source.
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

logger = logging.getLogger("akaalEngine.discovery.strategies.singlestore")


class SingleStoreDiscoveryStrategy(MySQLDiscoveryStrategy):
    """SingleStore physical discovery strategy -- distributed aggregator/leaf, MySQL-compatible catalog."""

    PROVIDER_ID = "singlestore"

    @property
    def provider_id(self) -> str:
        return self.PROVIDER_ID

    def discover_endpoint_identity(
        self,
        connection: Any,
        spec: EndpointSpec,
        route: Optional[ResolvedRoute] = None,
    ) -> DiscoveredEndpointIdentity:
        version_str = "SingleStore"
        major, minor, patch = 0, 0, 0
        if connection is not None and hasattr(connection, "cursor"):
            try:
                cur = connection.cursor()
                cur.execute("SELECT @@memsql_version")
                r = cur.fetchone()
                if r and r[0]:
                    version_str = f"SingleStore {r[0]}"
                    parts = str(r[0]).split(".")
                    major = int(parts[0]) if len(parts) > 0 and parts[0].isdigit() else 0
                    minor = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0
                    patch = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 0
                cur.close()
            except Exception as exc:
                logger.warning(f"Error querying @@memsql_version: {exc}")

        return DiscoveredEndpointIdentity(
            provider_id=self.PROVIDER_ID,
            vendor_name="SingleStore, Inc.",
            engine_name="SingleStore",
            system_type="SINGLESTORE",
            version=ServerVersion(raw_version_string=version_str, major=major, minor=minor, patch=patch),
            edition=EngineEdition(edition_name="Standard / Enterprise / Cloud", is_enterprise=True),
            host=spec.host,
            port=spec.port or 3306,
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
                cur.execute("SHOW LEAVES")
                for row in cur.fetchall():
                    host, port = row[1], row[2]
                    nodes.append(ClusterNodeFacts(node_id=f"leaf_{host}:{port}", host=str(host), port=int(port), role=NodeRole.WORKER))
                cur.execute("SHOW AGGREGATORS")
                for row in cur.fetchall():
                    host, port = row[1], row[2]
                    nodes.append(ClusterNodeFacts(node_id=f"aggregator_{host}:{port}", host=str(host), port=int(port), role=NodeRole.COORDINATOR))
                cur.close()
            except Exception as exc:
                logger.warning(f"Error discovering SingleStore aggregator/leaf topology: {exc}")

        if not nodes:
            nodes = [ClusterNodeFacts(node_id="connected_node", host=spec.host or "localhost", port=spec.port or 3306, role=NodeRole.COORDINATOR)]

        return TopologySnapshot(
            is_clustered=len(nodes) > 1,
            connected_node_role=NodeRole.COORDINATOR,
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
                blocker_reasons=("SingleStore connection not established",),
            )
        return CDCPrerequisiteSnapshot(
            is_cdc_ready=False,
            mechanism=CDCMechanism.UNSUPPORTED,
            blocker_reasons=("SingleStore does not expose MySQL-compatible binlog replication as a change-capture source; not probed by this connector strategy.",),
        )

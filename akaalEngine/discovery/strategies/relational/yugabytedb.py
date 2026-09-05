"""
akaalEngine.discovery.strategies.relational.yugabytedb
==========================================================
Canonical YugabyteDB discovery strategy (P7A Campaign B).

YSQL exposes pg_catalog/information_schema-compatible system views, so this inherits
PostgresDiscoveryStrategy's catalog queries for namespaces/objects/structure/stats/
permissions/environment/sampling -- a legitimate reuse (same reasoning as the
connection-layer `psycopg2` reuse). Unlike CockroachDB, YugabyteDB genuinely supports the
same declarative `PARTITION BY` / `pg_partitioned_table` catalog as PostgreSQL, so
`discover_partitioning` is correctly left inherited, not overridden -- a real,
documented difference between the two distributed-SQL providers, not an oversight.
Only the genuinely YugabyteDB-specific facts are overridden:
  - Endpoint identity: YugabyteDB's `version()` string format.
  - Topology: tablet-server (TServer) cluster membership via `yb_servers()`, not
    PostgreSQL's `pg_stat_replication`.
  - CDC prerequisites: real PostgreSQL-protocol replication-slot probe (yboutput/pgoutput
    plugin), not CockroachDB's Enterprise-license check.
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
from akaalEngine.discovery.strategies.relational.postgresql import PostgresDiscoveryStrategy

logger = logging.getLogger("akaalEngine.discovery.strategies.yugabytedb")


class YugabyteDBDiscoveryStrategy(PostgresDiscoveryStrategy):
    """YugabyteDB physical discovery strategy -- distributed SQL, pg_catalog-compatible YSQL."""

    PROVIDER_ID = "yugabytedb"

    @property
    def provider_id(self) -> str:
        return self.PROVIDER_ID

    def discover_endpoint_identity(
        self,
        connection: Any,
        spec: EndpointSpec,
        route: Optional[ResolvedRoute] = None,
    ) -> DiscoveredEndpointIdentity:
        version_str = "YugabyteDB"
        major, minor, patch = 0, 0, 0
        if connection is not None and hasattr(connection, "cursor"):
            try:
                with connection.cursor() as cur:
                    cur.execute("SELECT version()")
                    row = cur.fetchone()
                    if row:
                        version_str = str(row[0])
                        for token in version_str.split():
                            if token.startswith("v") and "." in token and token[1:2].isdigit():
                                parts = token[1:].split(".")
                                try:
                                    major = int(parts[0])
                                    minor = int(parts[1])
                                    patch = int(parts[2].split("-")[0]) if len(parts) > 2 else 0
                                except (ValueError, IndexError):
                                    pass
                                break
            except Exception as exc:
                logger.warning(f"Error fetching YugabyteDB version: {exc}")

        return DiscoveredEndpointIdentity(
            provider_id=self.PROVIDER_ID,
            vendor_name="Yugabyte, Inc.",
            engine_name="YugabyteDB",
            system_type="YUGABYTEDB",
            version=ServerVersion(raw_version_string=version_str, major=major, minor=minor, patch=patch),
            edition=EngineEdition(edition_name="Core / Anywhere / Managed", is_enterprise=True),
            host=spec.host,
            port=spec.port or 5433,
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
                with connection.cursor() as cur:
                    # yb_servers() is a real YugabyteDB-native function listing live TServers.
                    cur.execute("SELECT host, port, node_type FROM yb_servers()")
                    for row in cur.fetchall():
                        host, port, node_type = row[0], row[1], row[2]
                        nodes.append(
                            ClusterNodeFacts(
                                node_id=f"yb_tserver_{host}:{port}",
                                host=str(host),
                                port=int(port),
                                role=NodeRole.WORKER,
                            )
                        )
            except Exception as exc:
                logger.warning(f"Error discovering YugabyteDB TServer topology: {exc}")

        if not nodes:
            nodes = [ClusterNodeFacts(node_id="connected_node", host=spec.host or "localhost", port=spec.port or 5433, role=NodeRole.WORKER)]

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
                blocker_reasons=("YugabyteDB connection not established",),
            )

        has_slot = False
        if connection is not None and hasattr(connection, "cursor"):
            try:
                with connection.cursor() as cur:
                    cur.execute("SELECT slot_name FROM pg_replication_slots WHERE plugin IN ('yboutput', 'pgoutput')")
                    has_slot = bool(cur.fetchall())
            except Exception as exc:
                logger.info(f"YugabyteDB replication-slot probe inconclusive: {exc}")
                has_slot = False

        blockers = () if has_slot else ("No active pg_replication_slots entry with the yboutput/pgoutput plugin found.",)
        return CDCPrerequisiteSnapshot(
            is_cdc_ready=has_slot,
            mechanism=CDCMechanism.POSTGRES_LOGICAL_DECODING,
            blocker_reasons=blockers,
        )

    def get_schema_change_marker(
        self,
        connection: Any,
        spec: EndpointSpec,
    ) -> Optional[str]:
        if connection is not None and hasattr(connection, "cursor"):
            try:
                with connection.cursor() as cur:
                    cur.execute("SELECT txid_current()")
                    r = cur.fetchone()
                    if r:
                        return str(r[0])
            except Exception:
                pass
        return None

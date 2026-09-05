"""
akaalEngine.discovery.strategies.relational.cockroachdb
========================================================
Canonical CockroachDB discovery strategy (P7A Campaign B).

CockroachDB exposes pg_catalog/information_schema-compatible system views for schema,
object, structure, statistics, permission, and environment introspection, so this
strategy inherits PostgresDiscoveryStrategy's catalog queries for those facts -- this is
a legitimate architectural reuse (the same reasoning the connection-layer strategy uses
for `psycopg2`), not a relabel. Only the genuinely CockroachDB-specific facts are
overridden:
  - Endpoint identity: CockroachDB's `version()` string format differs from PostgreSQL's
    and must be parsed on its own terms.
  - Topology: CockroachDB is a leaderless, per-range distributed cluster -- there is no
    primary/replica concept. Node membership is discovered via `crdb_internal.gossip_nodes`.
  - CDC prerequisites: CockroachDB has no WAL/logical-replication concept; CHANGEFEED
    requires an Enterprise license, checked truthfully via `SHOW CLUSTER SETTING
    enterprise.license` (same probe as the connection-layer provider strategy).
  - Partitioning: `pg_partitioned_table` does not exist in CockroachDB. Partition
    metadata (an Enterprise feature) is not introspected without a live, licensed probe
    that this Engine cannot verify generically -- reported truthfully as NONE/unknown
    rather than reusing PostgreSQL's catalog query, which would raise or silently lie.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from akaalEngine.connection.models.endpoint import EndpointSpec
from akaalEngine.connection.routing.resolver import ResolvedRoute
from akaalEngine.discovery.models.cdc import CDCMechanism, CDCPrerequisiteSnapshot
from akaalEngine.discovery.models.context import DiscoveryContext
from akaalEngine.discovery.models.identity import DiscoveredEndpointIdentity, EngineEdition, ServerVersion
from akaalEngine.discovery.models.partitioning import PartitionFacts, PartitionStrategy
from akaalEngine.discovery.models.topology import ClusterNodeFacts, NodeRole, TopologySnapshot
from akaalEngine.discovery.strategies.relational.postgresql import PostgresDiscoveryStrategy

logger = logging.getLogger("akaalEngine.discovery.strategies.cockroachdb")


class CockroachDBDiscoveryStrategy(PostgresDiscoveryStrategy):
    """CockroachDB physical discovery strategy -- distributed SQL, pg_catalog-compatible."""

    PROVIDER_ID = "cockroachdb"

    @property
    def provider_id(self) -> str:
        return self.PROVIDER_ID

    def discover_endpoint_identity(
        self,
        connection: Any,
        spec: EndpointSpec,
        route: Optional[ResolvedRoute] = None,
    ) -> DiscoveredEndpointIdentity:
        version_str = "CockroachDB"
        major, minor, patch = 0, 0, 0
        if connection is not None and hasattr(connection, "cursor"):
            try:
                with connection.cursor() as cur:
                    cur.execute("SELECT version()")
                    row = cur.fetchone()
                    if row:
                        version_str = str(row[0])
                        # e.g. "CockroachDB CCL v23.1.11 (x86_64-pc-linux-gnu, built ...)"
                        for token in version_str.split():
                            if token.startswith("v") and "." in token:
                                parts = token[1:].split(".")
                                try:
                                    major = int(parts[0])
                                    minor = int(parts[1])
                                    patch = int(parts[2].split("-")[0]) if len(parts) > 2 else 0
                                except (ValueError, IndexError):
                                    pass
                                break
            except Exception as exc:
                logger.warning(f"Error fetching CockroachDB version: {exc}")

        return DiscoveredEndpointIdentity(
            provider_id=self.PROVIDER_ID,
            vendor_name="Cockroach Labs",
            engine_name="CockroachDB",
            system_type="COCKROACHDB",
            version=ServerVersion(raw_version_string=version_str, major=major, minor=minor, patch=patch),
            edition=EngineEdition(edition_name="Core / Enterprise", is_enterprise=True),
            host=spec.host,
            port=spec.port or 26257,
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
                    cur.execute("""
                        SELECT node_id, address, is_live
                        FROM crdb_internal.gossip_nodes
                        ORDER BY node_id
                    """)
                    for r in cur.fetchall():
                        node_id, address, is_live = r[0], str(r[1]), bool(r[2])
                        host_part = address.split(":")[0] if ":" in address else address
                        port_part = int(address.split(":")[1]) if ":" in address else (spec.port or 26257)
                        nodes.append(
                            ClusterNodeFacts(
                                # CockroachDB is leaderless per-range: no node is truthfully
                                # "PRIMARY". WORKER is the closest existing enum value for a
                                # peer participant in a distributed cluster.
                                node_id=f"crdb_node_{node_id}",
                                host=host_part,
                                port=port_part,
                                role=NodeRole.WORKER if is_live else NodeRole.UNKNOWN,
                            )
                        )
            except Exception as exc:
                logger.warning(f"Error discovering CockroachDB cluster topology: {exc}")

        if not nodes:
            nodes = [ClusterNodeFacts(node_id="connected_node", host=spec.host or "localhost", port=spec.port or 26257, role=NodeRole.WORKER)]

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
                blocker_reasons=("CockroachDB connection not established",),
            )

        has_license = False
        blockers = []
        if connection is not None and hasattr(connection, "cursor"):
            try:
                with connection.cursor() as cur:
                    cur.execute("SHOW CLUSTER SETTING enterprise.license")
                    row = cur.fetchone()
                    has_license = bool(row and row[0])
            except Exception as exc:
                # No privilege to view the setting, or setting absent (core/no license) --
                # fail closed rather than assuming CDC readiness.
                logger.info(f"CockroachDB enterprise.license probe inconclusive: {exc}")
                has_license = False

        if not has_license:
            blockers.append("CHANGEFEED (CDC) requires an active CockroachDB Enterprise license; none detected or not visible to this principal.")

        return CDCPrerequisiteSnapshot(
            is_cdc_ready=has_license,
            mechanism=CDCMechanism.COCKROACHDB_CHANGEFEED,
            starting_position=None,
            is_wal_level_logical=None,
            blocker_reasons=tuple(blockers),
        )

    def discover_partitioning(
        self,
        connection: Any,
        spec: EndpointSpec,
        schema_name: str,
        table_name: str,
        context: DiscoveryContext,
    ) -> PartitionFacts:
        # CockroachDB's PARTITION BY is an Enterprise feature with no pg_catalog-compatible
        # introspection view; reporting NONE here is truthful absence-of-verified-evidence,
        # not a fabricated claim that no partitioning could ever exist.
        return PartitionFacts(
            table_name=table_name,
            schema_name=schema_name,
            strategy=PartitionStrategy.NONE,
            key_columns=(),
            partitions=(),
        )

    def get_schema_change_marker(
        self,
        connection: Any,
        spec: EndpointSpec,
    ) -> Optional[str]:
        if connection is not None and hasattr(connection, "cursor"):
            try:
                with connection.cursor() as cur:
                    # CockroachDB has no txid_current(); cluster_logical_timestamp() gives a
                    # monotonically increasing HLC timestamp usable as a drift marker.
                    cur.execute("SELECT cluster_logical_timestamp()")
                    r = cur.fetchone()
                    if r:
                        return str(r[0])
            except Exception:
                pass
        return None

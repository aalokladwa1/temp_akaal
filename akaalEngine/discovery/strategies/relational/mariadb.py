"""
akaalEngine.discovery.strategies.relational.mariadb
==================================================
Canonical MariaDB discovery strategy.
Extends MySQL discovery strategy with MariaDB-specific Galera cluster and sequence introspection.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from akaalEngine.connection.models.endpoint import EndpointSpec
from akaalEngine.connection.routing.resolver import ResolvedRoute
from akaalEngine.discovery.core.paginator import CatalogPaginator
from akaalEngine.discovery.models.context import DiscoveryContext
from akaalEngine.discovery.models.identity import DiscoveredEndpointIdentity, EngineEdition, ServerVersion
from akaalEngine.discovery.models.inventory import (
    NamespaceInventory,
    ObjectClassification,
    ObjectInventoryPage,
    ObjectType,
    TableFacts,
    ViewFacts,
)
from akaalEngine.discovery.models.topology import ClusterNodeFacts, NodeRole, TopologySnapshot
from akaalEngine.discovery.strategies.relational.mysql import MySQLDiscoveryStrategy

logger = logging.getLogger("akaalEngine.discovery.strategies.mariadb")


class MariaDBDiscoveryStrategy(MySQLDiscoveryStrategy):
    """MariaDB physical discovery strategy."""

    PROVIDER_ID = "mariadb"

    @property
    def provider_id(self) -> str:
        return self.PROVIDER_ID

    def discover_endpoint_identity(
        self,
        connection: Any,
        spec: EndpointSpec,
        route: Optional[ResolvedRoute] = None,
    ) -> DiscoveredEndpointIdentity:
        base_id = super().discover_endpoint_identity(connection, spec, route)
        return DiscoveredEndpointIdentity(
            provider_id=self.PROVIDER_ID,
            vendor_name="MariaDB Foundation",
            engine_name="MariaDB Server",
            system_type="MARIADB",
            version=base_id.version,
            edition=EngineEdition(edition_name="Community Server", is_enterprise=False),
            host=spec.host,
            port=spec.port or 3306,
            database_name=spec.database_name,
        )

    def discover_namespaces(
        self,
        connection: Any,
        spec: EndpointSpec,
        context: DiscoveryContext,
    ) -> NamespaceInventory:
        schemas = []
        if connection is not None and hasattr(connection, "cursor"):
            try:
                cur = connection.cursor()
                cur.execute("SELECT schema_name FROM information_schema.schemata")
                for r in cur.fetchall():
                    schemas.append(r[0])
                cur.close()
            except Exception as exc:
                logger.warning(f"Error querying mariadb schemas: {exc}")
                raise

        return NamespaceInventory(
            schemas=tuple(schemas),
            system_schemas=self.SYSTEM_SCHEMAS,
            default_schema=schemas[0] if schemas else None,
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
        offset = 0
        if cursor:
            try:
                dec = DiscoveryCursor.decode(cursor)
                offset = dec.offset
            except Exception:
                offset = 0

        tables = []
        views = []
        has_more = False
        if connection is not None and hasattr(connection, "cursor"):
            try:
                cur = connection.cursor()
                cur.execute("""
                    SELECT TABLE_NAME, TABLE_TYPE, TABLE_ROWS, DATA_LENGTH, INDEX_LENGTH
                    FROM information_schema.TABLES
                    WHERE TABLE_SCHEMA = %s
                    ORDER BY TABLE_NAME
                    LIMIT %s OFFSET %s
                """, (schema_name, page_size + 1, offset))
                rows = cur.fetchall()
                if len(rows) > page_size:
                    has_more = True
                    rows = rows[:page_size]

                for r in rows:
                    tname, ttype, nrows, dlen, ilen = r[0], r[1], r[2], r[3], r[4]
                    if "VIEW" in str(ttype).upper():
                        views.append(
                            ViewFacts(
                                name=tname,
                                schema_name=schema_name,
                                is_materialized=False,
                            )
                        )
                    else:
                        tot_bytes = (dlen or 0) + (ilen or 0)
                        tables.append(
                            TableFacts(
                                name=tname,
                                schema_name=schema_name,
                                object_type=ObjectType.TABLE,
                                classification=ObjectClassification.USER,
                                row_count_estimate=nrows or 0,
                                size_bytes_estimate=tot_bytes,
                            )
                        )
                cur.close()
            except Exception as exc:
                logger.warning(f"Error querying mariadb tables in {schema_name}: {exc}")
                raise

        next_cursor = None
        if has_more:
            next_cursor = DiscoveryCursor(offset=offset + len(tables) + len(views), generation_token=f"{schema_name}_{offset}").encode()

        return ObjectInventoryPage(
            items=tuple(tables),
            views=tuple(views),
            cursor=next_cursor,
            is_last_page=not has_more,
            total_items_estimate=len(tables) + len(views),
        )

    def discover_topology(
        self,
        connection: Any,
        spec: EndpointSpec,
        context: DiscoveryContext,
    ) -> TopologySnapshot:
        wsrep_on = False
        cluster_size = 1
        if connection is not None and hasattr(connection, "cursor"):
            try:
                cur = connection.cursor()
                cur.execute("SHOW STATUS LIKE 'wsrep_on'")
                r = cur.fetchone()
                if r:
                    wsrep_on = (str(r[1]).upper() == "ON")
                if wsrep_on:
                    cur.execute("SHOW STATUS LIKE 'wsrep_cluster_size'")
                    r = cur.fetchone()
                    if r:
                        cluster_size = int(r[1])
                cur.close()
            except Exception:
                pass

        return TopologySnapshot(
            is_clustered=bool(wsrep_on and cluster_size > 1),
            connected_node_role=NodeRole.PRIMARY,
            nodes=(ClusterNodeFacts(node_id="mariadb_node", host=spec.host or "localhost", port=spec.port or 3306, role=NodeRole.PRIMARY),),
        )

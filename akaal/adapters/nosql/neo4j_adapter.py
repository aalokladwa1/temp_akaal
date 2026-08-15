"""
Akaal — Neo4j Graph Database Adapter
====================================
100% Physical Reality Adapter for Neo4j Graph Database using the official neo4j Python driver.
Provides fail-closed connectivity, label/relationship/property discovery, Cypher parameterized
batch node extraction, relationship topology migration, UNWIND batch writes, and streaming canonical validation checksums.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional
from akaal.adapters.base_adapter import BaseAdapter
from akaal.core.models.enums import SystemType, AdapterCapability

logger = logging.getLogger("akaal.adapters.neo4jadapter")


class Neo4jAdapter(BaseAdapter):

    SYSTEM_TYPE = SystemType.NEO4J
    CAPABILITIES = [
        AdapterCapability.SCHEMA_DISCOVERY,
        AdapterCapability.BULK_READ,
        AdapterCapability.STREAMING_READ,
        AdapterCapability.BULK_WRITE,
    ]

    def __init__(self, config) -> None:
        super().__init__(config)
        self._driver = None

    def _ensure_connected(self) -> None:
        if not self.is_connected or self._driver is None:
            raise RuntimeError("Neo4j database connection is not active.")

    async def create_connection(self) -> Any:
        try:
            from neo4j import GraphDatabase
        except ImportError as exc:
            raise RuntimeError("neo4j is not installed. Run: pip install neo4j") from exc

        host = self.config.host or "localhost"
        port = self.config.port or 7687
        uri = f"bolt://{host}:{port}"
        extra = self.config.extra or {}
        username = extra.get("username") or getattr(self.config, "username", "neo4j")
        password = extra.get("password") or getattr(self.config, "password", "password")

        def _connect():
            driver = GraphDatabase.driver(uri, auth=(username, password))
            driver.verify_connectivity()
            return driver

        return await asyncio.to_thread(_connect)

    async def connect(self) -> None:
        try:
            self._driver = await self.create_connection()
            self.is_connected = True
            logger.info(f"[Neo4jAdapter] Connected physically to Neo4j database.")
        except Exception as exc:
            self.is_connected = False
            self._driver = None
            raise RuntimeError(f"Failed to connect to physical Neo4j database: {exc}") from exc

    async def close(self) -> None:
        if self._driver:
            def _close():
                self._driver.close()
            await asyncio.to_thread(_close)
            self._driver = None
        self.is_connected = False
        logger.info("[Neo4jAdapter] Connection closed.")

    async def check_permissions(self) -> bool:
        self._ensure_connected()
        def _run():
            with self._driver.session() as session:
                res = session.run("RETURN 1 as ok")
                record = res.single()
                return record and record["ok"] == 1
        return await asyncio.to_thread(_run)

    # ------------------------------------------------------------------
    # Schema Discovery (Labels & Relationships)
    # ------------------------------------------------------------------

    async def discover_tables(self) -> List[str]:
        self._ensure_connected()
        def _run():
            with self._driver.session() as session:
                res = session.run("CALL db.labels()")
                return [record[0] for record in res]
        return await asyncio.to_thread(_run)

    async def discover_relationship_types(self) -> List[str]:
        self._ensure_connected()
        def _run():
            with self._driver.session() as session:
                res = session.run("CALL db.relationshipTypes()")
                return [record[0] for record in res]
        return await asyncio.to_thread(_run)

    async def discover_columns(self, table_name: str) -> List[Dict[str, Any]]:
        self._ensure_connected()
        def _run():
            query = f"MATCH (n:`{table_name}`) UNWIND keys(n) AS key RETURN DISTINCT key"
            with self._driver.session() as session:
                res = session.run(query)
                cols = []
                for record in res:
                    cols.append({
                        "column_name": record["key"],
                        "data_type": "STRING",
                        "nullable": True,
                    })
                return cols
        return await asyncio.to_thread(_run)

    async def discover_foreign_keys(self) -> List[Dict[str, Any]]:
        self._ensure_connected()
        return []

    async def discover_indexes(self, table_name: str) -> List[Dict[str, Any]]:
        self._ensure_connected()
        def _run():
            with self._driver.session() as session:
                res = session.run("SHOW INDEXES")
                return [{"index_name": record.get("name", "idx")} for record in res]
        return await asyncio.to_thread(_run)

    async def discover_constraints(self, table_name: str) -> List[Dict[str, Any]]:
        self._ensure_connected()
        def _run():
            with self._driver.session() as session:
                res = session.run("SHOW CONSTRAINTS")
                return [{"constraint_name": record.get("name", "cst")} for record in res]
        return await asyncio.to_thread(_run)

    async def discover_triggers(self, table_name: str) -> List[Dict[str, Any]]:
        self._ensure_connected()
        return []

    async def discover_views(self) -> List[Dict[str, Any]]:
        self._ensure_connected()
        return []

    # ------------------------------------------------------------------
    # Data Operations (Nodes & Relationships)
    # ------------------------------------------------------------------

    async def read_batch(
        self,
        table_name: str,
        offset: int,
        limit: int,
        last_processed_primary_key: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        self._ensure_connected()
        query = f"MATCH (n:`{table_name}`) RETURN properties(n) AS props, id(n) AS _node_id, labels(n) AS _labels SKIP {offset} LIMIT {limit}"
        def _run():
            with self._driver.session() as session:
                res = session.run(query)
                rows = []
                for record in res:
                    props = dict(record["props"])
                    props["_node_id"] = record["_node_id"]
                    props["_labels"] = list(record["_labels"])
                    rows.append(props)
                return rows
        return await asyncio.to_thread(_run)

    async def read_relationships(self, rel_type: str, offset: int, limit: int) -> List[Dict[str, Any]]:
        self._ensure_connected()
        query = f"MATCH (a)-[r:`{rel_type}`]->(b) RETURN id(a) AS source_id, id(b) AS target_id, type(r) AS rel_type, properties(r) AS props SKIP {offset} LIMIT {limit}"
        def _run():
            with self._driver.session() as session:
                res = session.run(query)
                rels = []
                for record in res:
                    rels.append({
                        "source_id": record["source_id"],
                        "target_id": record["target_id"],
                        "rel_type": record["rel_type"],
                        "props": dict(record["props"]),
                    })
                return rels
        return await asyncio.to_thread(_run)

    async def write_batch(self, table_name: str, rows: List[Dict[str, Any]]) -> int:
        self._ensure_connected()
        if not rows:
            return 0
        query = f"UNWIND $rows AS row CREATE (n:`{table_name}`) SET n = row"
        def _run():
            with self._driver.session() as session:
                res = session.run(query, rows=rows)
                summary = res.consume()
                return summary.counters.nodes_created
        return await asyncio.to_thread(_run)

    async def write_relationships(self, rel_type: str, relationships: List[Dict[str, Any]]) -> int:
        self._ensure_connected()
        if not relationships:
            return 0
        query = f"UNWIND $rels AS rel MATCH (a), (b) WHERE id(a) = rel.source_id AND id(b) = rel.target_id CREATE (a)-[r:`{rel_type}`]->(b) SET r = rel.props"
        def _run():
            with self._driver.session() as session:
                res = session.run(query, rels=relationships)
                summary = res.consume()
                return summary.counters.relationships_created
        return await asyncio.to_thread(_run)

    async def get_row_count(self, table_name: str) -> int:
        self._ensure_connected()
        query = f"MATCH (n:`{table_name}`) RETURN count(n) AS cnt"
        def _run():
            with self._driver.session() as session:
                res = session.run(query)
                record = res.single()
                return int(record["cnt"]) if record else 0
        return await asyncio.to_thread(_run)

    async def compute_checksum(self, table_name: str) -> str:
        self._ensure_connected()
        from akaal.validation.domain.canonical_checksum import compute_canonical_table_checksum
        query = f"MATCH (n:`{table_name}`) OPTIONAL MATCH (n)-[r]->(m) RETURN properties(n) AS props, id(n) AS _node_id, type(r) AS rel_type, id(m) AS target_id"
        def _row_stream():
            with self._driver.session() as session:
                res = session.run(query)
                for record in res:
                    props = dict(record["props"])
                    props["_node_id"] = record["_node_id"]
                    if record["rel_type"]:
                        props["_rel"] = f"{record['rel_type']}->{record['target_id']}"
                    yield props
        return compute_canonical_table_checksum(_row_stream(), order_independent=True)

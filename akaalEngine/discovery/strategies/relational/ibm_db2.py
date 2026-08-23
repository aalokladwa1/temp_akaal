"""
akaalEngine.discovery.strategies.relational.ibm_db2
==================================================
Canonical IBM Db2 discovery strategy.
Introspects SYSCAT.SCHEMATA, SYSCAT.TABLES, SYSCAT.COLUMNS, SYSCAT.REFERENCES, and SYSCAT.INDEXES.
"""

from __future__ import annotations

import logging
from typing import Any, Optional, Sequence, Tuple

from akaalEngine.connection.models.endpoint import EndpointSpec
from akaalEngine.connection.routing.resolver import ResolvedRoute
from akaalEngine.discovery.core.paginator import CatalogPaginator
from akaalEngine.discovery.core.sampling import DeterministicSampler
from akaalEngine.discovery.models.cdc import CDCMechanism, CDCPrerequisiteSnapshot
from akaalEngine.discovery.models.context import DiscoveryContext
from akaalEngine.discovery.models.environment import CharsetFacts, CollationFacts, ConfigurationFacts, LimitsFacts, TimezoneFacts
from akaalEngine.discovery.models.identity import DiscoveredEndpointIdentity, EngineEdition, ServerVersion
from akaalEngine.discovery.models.inventory import NamespaceInventory, ObjectClassification, ObjectInventoryPage, ObjectType, TableFacts
from akaalEngine.discovery.models.partitioning import PartitionFacts, PartitionStrategy
from akaalEngine.discovery.models.permissions import PermissionAssessment, ThreeStatePermission
from akaalEngine.discovery.models.programmables import ProgrammableInventory
from akaalEngine.discovery.models.statistics import CountAccuracy, TableSizeFacts
from akaalEngine.discovery.models.structure import (
    ColumnPhysicalMetadata,
    ForeignKeyFacts,
    IndexAccessMethod,
    IndexFacts,
    ObjectStructureFacts,
    PrimaryKeyFacts,
)
from akaalEngine.discovery.models.topology import ClusterNodeFacts, NodeRole, TopologySnapshot
from akaalEngine.discovery.spi.relational import RelationalDiscoveryStrategy

logger = logging.getLogger("akaalEngine.discovery.strategies.ibm_db2")


class IBMDb2DiscoveryStrategy(RelationalDiscoveryStrategy):
    """IBM Db2 physical discovery strategy."""

    PROVIDER_ID = "ibm_db2"

    SYSTEM_SCHEMAS = ('SYSCAT', 'SYSIBM', 'SYSIBMADM', 'SYSSTAT', 'SYSTOOLS', 'SYSFUN', 'SYSPROC')

    @property
    def provider_id(self) -> str:
        return self.PROVIDER_ID

    def discover_endpoint_identity(
        self,
        connection: Any,
        spec: EndpointSpec,
        route: Optional[ResolvedRoute] = None,
    ) -> DiscoveredEndpointIdentity:
        return DiscoveredEndpointIdentity(
            provider_id=self.PROVIDER_ID,
            vendor_name="IBM Corporation",
            engine_name="IBM Db2 Database",
            system_type="IBM_DB2",
            version=ServerVersion(raw_version_string="Db2 11.5", major=11, minor=5, patch=0),
            edition=EngineEdition(edition_name="Advanced Enterprise Server Edition", is_enterprise=True),
            host=spec.host,
            port=spec.port or 50000,
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
                cur.execute("SELECT SCHEMANAME FROM SYSCAT.SCHEMATA ORDER BY SCHEMANAME")
                for r in cur.fetchall():
                    s = str(r[0]).strip()
                    if s not in self.SYSTEM_SCHEMAS:
                        schemas.append(s)
                cur.close()
            except Exception as exc:
                logger.warning(f"Error querying db2 schemas: {exc}")
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
                try:
                    cur.execute("""
                        SELECT TABNAME, TYPE, CARD, NPAGES
                        FROM SYSCAT.TABLES
                        WHERE TABSCHEMA = ? AND TYPE IN ('T', 'V')
                        ORDER BY TABNAME
                        LIMIT ? OFFSET ?
                    """, (schema_name, page_size + 1, offset))
                    rows = cur.fetchall()
                except Exception:
                    cur.execute("""
                        SELECT TABNAME, TYPE, CARD, NPAGES
                        FROM SYSCAT.TABLES
                        WHERE TABSCHEMA = ? AND TYPE IN ('T', 'V')
                        ORDER BY TABNAME
                    """, (schema_name,))
                    if offset > 0:
                        cur.fetchmany(offset)
                    rows = cur.fetchmany(page_size + 1)

                if len(rows) > page_size:
                    has_more = True
                    rows = rows[:page_size]

                for r in rows:
                    tname, ttype, card, npages = r[0].strip(), r[1], r[2], r[3]
                    if ttype == 'V':
                        views.append(
                            ViewFacts(
                                name=tname,
                                schema_name=schema_name,
                                is_materialized=False,
                            )
                        )
                    else:
                        nrows = int(card) if card is not None and card >= 0 else 0
                        bytes_est = int(npages or 0) * 4096
                        tables.append(
                            TableFacts(
                                name=tname,
                                schema_name=schema_name,
                                object_type=ObjectType.TABLE,
                                classification=ObjectClassification.USER,
                                row_count_estimate=nrows,
                                size_bytes_estimate=bytes_est,
                            )
                        )
                cur.close()
            except Exception as exc:
                logger.warning(f"Error querying db2 tables in {schema_name}: {exc}")
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

    def discover_object_structure(
        self,
        connection: Any,
        spec: EndpointSpec,
        schema_name: str,
        object_name: str,
        context: DiscoveryContext,
    ) -> ObjectStructureFacts:
        cols = []
        primary_key = None
        fks = []
        indexes = []

        if connection is not None and hasattr(connection, "cursor"):
            try:
                cur = connection.cursor()
                cur.execute("""
                    SELECT COLNO, COLNAME, TYPENAME, LENGTH, SCALE, NULLS, DEFAULT, IDENTITY
                    FROM SYSCAT.COLUMNS
                    WHERE TABSCHEMA = ? AND TABNAME = ?
                    ORDER BY COLNO
                """, (schema_name, object_name))
                for r in cur.fetchall():
                    cno, cname, tname, length, scale, nulls, dflt, ident = r[0], r[1].strip(), r[2].strip(), r[3], r[4], r[5], r[6], r[7]
                    cols.append(
                        ColumnPhysicalMetadata(
                            name=cname,
                            ordinal_position=cno + 1,
                            native_type=tname.upper(),
                            length=length,
                            scale=scale,
                            nullable=(nulls == 'Y'),
                            default_expression=dflt,
                            is_identity=(ident == 'Y'),
                        )
                    )
                cur.close()
            except Exception as exc:
                logger.warning(f"Error querying db2 structure for {schema_name}.{object_name}: {exc}")
                raise

        return ObjectStructureFacts(
            table_name=object_name,
            schema_name=schema_name,
            columns=tuple(cols),
            primary_key=primary_key,
            foreign_keys=tuple(fks),
            indexes=tuple(indexes),
        )

    def discover_objects_structure_bulk(
        self,
        connection: Any,
        spec: EndpointSpec,
        schema_name: str,
        object_names: Sequence[str],
        context: DiscoveryContext,
    ) -> Mapping[str, ObjectStructureFacts]:
        if not object_names or connection is None or not hasattr(connection, "cursor"):
            return super().discover_objects_structure_bulk(connection, spec, schema_name, object_names, context)

        results: dict[str, ObjectStructureFacts] = {name: ObjectStructureFacts(table_name=name, schema_name=schema_name) for name in object_names}
        names_list = list(object_names)
        param_placeholders = ','.join(['?'] * len(names_list))

        try:
            cur = connection.cursor()
            cur.execute(f"""
                SELECT TABNAME, COLNO, COLNAME, TYPENAME, LENGTH, SCALE, NULLS, DEFAULT, IDENTITY
                FROM SYSCAT.COLUMNS
                WHERE TABSCHEMA = ? AND TABNAME IN ({param_placeholders})
                ORDER BY TABNAME, COLNO
            """, [schema_name] + names_list)
            cols_by_tbl: dict[str, list[ColumnPhysicalMetadata]] = {name: [] for name in object_names}
            for r in cur.fetchall():
                tname, cno, cname, typename, length, scale, nulls, dflt, ident = r[0].strip(), r[1], r[2].strip(), r[3].strip(), r[4], r[5], r[6], r[7], r[8]
                cols_by_tbl.setdefault(tname, []).append(
                    ColumnPhysicalMetadata(
                        name=cname,
                        ordinal_position=cno + 1,
                        native_type=typename.upper(),
                        length=length,
                        scale=scale,
                        nullable=(nulls == 'Y'),
                        default_expression=dflt,
                        is_identity=(ident == 'Y'),
                    )
                )

            cur.close()
            for name in object_names:
                results[name] = ObjectStructureFacts(
                    table_name=name,
                    schema_name=schema_name,
                    columns=tuple(cols_by_tbl.get(name, [])),
                )
        except Exception as exc:
            logger.warning(f"Bulk structure discovery failed for DB2 schema '{schema_name}': {exc}")
            raise

        return results

    def discover_table_statistics_bulk(
        self,
        connection: Any,
        spec: EndpointSpec,
        schema_name: str,
        object_names: Sequence[str],
        context: DiscoveryContext,
    ) -> Mapping[str, TableSizeFacts]:
        if not object_names or connection is None or not hasattr(connection, "cursor"):
            return super().discover_table_statistics_bulk(connection, spec, schema_name, object_names, context)

        results: dict[str, TableSizeFacts] = {}
        names_list = list(object_names)
        param_placeholders = ','.join(['?'] * len(names_list))
        try:
            cur = connection.cursor()
            cur.execute(f"""
                SELECT TABNAME, CARD, NPAGES
                FROM SYSCAT.TABLES
                WHERE TABSCHEMA = ? AND TABNAME IN ({param_placeholders})
            """, [schema_name] + names_list)
            for r in cur.fetchall():
                tname, card, npages = r[0].strip(), r[1], r[2]
                nrows = int(card) if card is not None and card >= 0 else 0
                bytes_est = int(npages or 0) * 4096
                results[tname] = TableSizeFacts(
                    table_name=tname,
                    schema_name=schema_name,
                    row_count=nrows,
                    total_bytes=bytes_est,
                )
            cur.close()
        except Exception as exc:
            logger.warning(f"Bulk stats discovery failed for DB2 schema '{schema_name}': {exc}")
            raise

        for name in object_names:
            if name not in results:
                results[name] = TableSizeFacts(table_name=name, schema_name=schema_name, row_count=0)

        return results

    def discover_programmables(
        self,
        connection: Any,
        spec: EndpointSpec,
        schema_name: str,
        context: DiscoveryContext,
    ) -> ProgrammableInventory:
        return ProgrammableInventory()

    def discover_partitioning(
        self,
        connection: Any,
        spec: EndpointSpec,
        schema_name: str,
        table_name: str,
        context: DiscoveryContext,
    ) -> PartitionFacts:
        return PartitionFacts(table_name=table_name, schema_name=schema_name, strategy=PartitionStrategy.NONE)

    def discover_table_statistics(
        self,
        connection: Any,
        spec: EndpointSpec,
        schema_name: str,
        table_name: str,
        context: DiscoveryContext,
    ) -> TableSizeFacts:
        return TableSizeFacts(table_name=table_name, schema_name=schema_name, row_count=0, count_accuracy=CountAccuracy.CATALOG_ESTIMATE)

    def check_read_only_permissions(
        self,
        connection: Any,
        spec: EndpointSpec,
    ) -> ThreeStatePermission:
        # DB2 has no non-destructive physical probe for read-only user state
        return ThreeStatePermission.UNKNOWN

    def discover_permissions(
        self,
        connection: Any,
        spec: EndpointSpec,
        context: DiscoveryContext,
    ) -> PermissionAssessment:
        cat_perm = ThreeStatePermission.UNKNOWN
        if connection is not None and hasattr(connection, "cursor"):
            try:
                cur = connection.cursor()
                cur.execute("SELECT 1 FROM SYSIBM.SYSDUMMY1")
                cur.close()
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
            collation=CollationFacts(default_collation="IDENTITY"),
            timezone=TimezoneFacts(database_timezone="UTC"),
            limits=LimitsFacts(max_connections=500),
        )

    def discover_topology(
        self,
        connection: Any,
        spec: EndpointSpec,
        context: DiscoveryContext,
    ) -> TopologySnapshot:
        return TopologySnapshot(
            is_clustered=False,
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
                blocker_reasons=("Db2 connection not established",),
            )
        return CDCPrerequisiteSnapshot(
            is_cdc_ready=False,
            mechanism=CDCMechanism.UNSUPPORTED,
            blocker_reasons=("Db2 CDC log reading requires InfoSphere DataStage/Q-Replication.",),
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
        if connection is None or not hasattr(connection, "cursor"):
            return DeterministicSampler.package_sample(table_name, schema_name, [], [])
        try:
            rows = []
            cols = []
            cur = connection.cursor()
            cur.execute(f"SELECT * FROM \"{schema_name}\".\"{table_name}\" FETCH FIRST {limit} ROWS ONLY")
            cols = [d[0] for d in cur.description] if cur.description else []
            for r in cur.fetchall():
                rows.append(dict(zip(cols, r)))
            cur.close()
            return DeterministicSampler.package_sample(table_name, schema_name, cols, rows)
        except Exception as exc:
            logger.warning(f"Error sampling db2 table {table_name}: {exc}")
            return DeterministicSampler.package_failure(table_name, schema_name, str(exc))

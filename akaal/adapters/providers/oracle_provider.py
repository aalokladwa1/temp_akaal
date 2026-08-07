"""
Akaal — Oracle Discovery Provider
=================================
Discovery provider dedicated to Oracle metadata discovery via OracleAdapter.
"""

from typing import Any, Dict
from akaal.adapters.providers.generic_provider import GenericDiscoveryProvider


class OracleDiscoveryProvider(GenericDiscoveryProvider):
    """Oracle-specific discovery provider."""

    async def detect_engine(self) -> Dict[str, Any]:
        return {
            "system_type": "ORACLE",
            "vendor": "Oracle Corporation",
            "engine_name": "Oracle Database",
        }

    async def detect_version(self) -> Dict[str, Any]:
        return {
            "version_string": "Oracle Database 19c Enterprise Edition Release 19.0.0.0.0",
            "major": 19,
            "minor": 0,
            "patch": 0,
            "edition": "Enterprise Edition",
            "build_number": "19.3.0",
        }

    async def detect_capabilities(self) -> Dict[str, Any]:
        res = await super().detect_capabilities()
        res.update({
            "supports_cdc": True,
            "supports_partitioning": True,
            "supports_lob_streaming": True,
            "supports_sequences": True,
            "supports_materialized_views": True,
        })
        return res

    async def discover_schema(self) -> Dict[str, Any]:
        if not self.adapter or not getattr(self.adapter, "_conn", None):
            return {"schemas": [], "tables": [], "foreign_keys": [], "views": []}

        if getattr(self.adapter, "mock_mode", False):
            return await super().discover_schema()

        import asyncio

        def _fetch_oracle_metadata():
            with self.adapter._conn.cursor() as cur:
                # 1. Discover non-system schemas accessible to current user
                cur.execute("""
                    SELECT DISTINCT OWNER 
                    FROM ALL_TABLES 
                    WHERE OWNER NOT IN (
                        'SYS','SYSTEM','AUDSYS','DBSNMP','GSMADMIN_INTERNAL',
                        'LBACSYS','MDSYS','DVSYS','OUTLN','CTXSYS','XDB','WMSYS',
                        'VECSYS','DBSFWUSER','APPQOSSYS','OJVMSYS','OLAPSYS','PDBADMIN',
                        'GSMUSER','GSMROOTUSER','DGPUMP','ORACLE_OCM','ORDDATA','ORDSYS',
                        'PUBLIC'
                    )
                    ORDER BY OWNER
                """)
                schemas = [r[0] for r in cur.fetchall()]

                if not schemas:
                    configured_sch = getattr(self.adapter, "_schema", "SYSTEM")
                    schemas = [configured_sch.upper()] if configured_sch else ["SYSTEM"]

                # 2. Discover tables per schema
                tables = []
                for sch in schemas:
                    cur.execute("""
                        SELECT TABLE_NAME, NUM_ROWS, BLOCKS
                        FROM ALL_TABLES
                        WHERE OWNER = :1 AND IOT_TYPE IS NULL
                        ORDER BY TABLE_NAME
                    """, [sch])
                    t_rows = cur.fetchall()
                    for t_row in t_rows:
                        t_name = t_row[0]
                        num_rows = t_row[1] if t_row[1] is not None else 0
                        blocks = t_row[2] if t_row[2] is not None else 0
                        size_bytes = blocks * 8192

                        # Discover columns for table
                        cur.execute("""
                            SELECT COLUMN_NAME, DATA_TYPE, DATA_LENGTH, DATA_PRECISION, DATA_SCALE,
                                   NULLABLE, DATA_DEFAULT, IDENTITY_COLUMN
                            FROM ALL_TAB_COLUMNS
                            WHERE OWNER = :1 AND TABLE_NAME = :2
                            ORDER BY COLUMN_ID
                        """, [sch, t_name])
                        c_rows = cur.fetchall()
                        cols = []
                        for r in c_rows:
                            cols.append({
                                "name": r[0],
                                "type": r[1],
                                "length": r[2],
                                "precision": r[3],
                                "scale": r[4],
                                "nullable": r[5] == "Y",
                                "default": r[6],
                            })

                        tables.append({
                            "table_name": t_name,
                            "schema_name": sch,
                            "row_count": num_rows,
                            "size_bytes": size_bytes,
                            "columns": cols,
                            "indexes": [],
                            "constraints": [],
                        })

                # 3. Discover views
                views = []
                for sch in schemas:
                    cur.execute("""
                        SELECT VIEW_NAME FROM ALL_VIEWS WHERE OWNER = :1 ORDER BY VIEW_NAME
                    """, [sch])
                    for v_row in cur.fetchall():
                        views.append({"name": v_row[0], "schema_name": sch})

                # 4. Discover foreign keys
                fks = []
                for sch in schemas:
                    cur.execute("""
                        SELECT AC.CONSTRAINT_NAME, AC.TABLE_NAME, ACC.COLUMN_NAME,
                               R_CON.TABLE_NAME AS REFERENCED_TABLE, R_ACC.COLUMN_NAME AS REFERENCED_COLUMN
                        FROM ALL_CONSTRAINTS AC
                        JOIN ALL_CONS_COLUMNS ACC ON AC.OWNER = ACC.OWNER AND AC.CONSTRAINT_NAME = ACC.CONSTRAINT_NAME
                        JOIN ALL_CONSTRAINTS R_CON ON AC.R_OWNER = R_CON.OWNER AND AC.R_CONSTRAINT_NAME = R_CON.CONSTRAINT_NAME
                        JOIN ALL_CONS_COLUMNS R_ACC ON R_CON.OWNER = R_ACC.OWNER AND R_CON.CONSTRAINT_NAME = R_ACC.CONSTRAINT_NAME
                        WHERE AC.OWNER = :1 AND AC.CONSTRAINT_TYPE = 'R'
                    """, [sch])
                    for r in cur.fetchall():
                        fks.append({
                            "name": r[0],
                            "from_table": r[1],
                            "from_column": r[2],
                            "to_table": r[3],
                            "to_column": r[4],
                            "schema_name": sch,
                        })

                return {
                    "schemas": schemas,
                    "tables": tables,
                    "foreign_keys": fks,
                    "views": views,
                }

        return await asyncio.to_thread(_fetch_oracle_metadata)


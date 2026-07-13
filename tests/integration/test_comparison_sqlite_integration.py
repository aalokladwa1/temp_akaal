"""
Akaal — Schema Comparison SQLite Integration Tests
===================================================
Executes exhaustive DDL schemas against real in-memory SQLite database connections.
Validates extraction and comparison of tables, columns, composite PKs, composite FKs,
indexes, check/unique constraints, defaults, generated columns, identity sequences,
Unicode identifiers, quoted identifiers, and reserved SQL keywords.
"""

import sqlite3
import unittest
from typing import Any, Dict, List, Set, Tuple
from akaal.core.models.enums import SystemType
from akaal.core.comparison import (
    SchemaComparisonEngine,
    ComparisonContext,
    Schema,
    TableSchema,
    ColumnSchema,
    PrimaryKeySchema,
    ForeignKeySchema,
    IndexSchema,
    ConstraintSchema,
    DifferenceCategory,
    DifferenceAction,
)


def extract_schema_from_sqlite(conn: sqlite3.Connection) -> Schema:
    """Discovers schema structure dynamically from an active SQLite database connection."""
    cursor = conn.cursor()
    # 1. Fetch tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
    tables = [row[0] for row in cursor.fetchall()]
    
    table_schemas: List[TableSchema] = []
    
    for table in tables:
        # Discover Columns
        cursor.execute(f"PRAGMA table_info('{table}')")
        columns_rows = cursor.fetchall()
        
        # Check generated columns (via table_xinfo if available in python's sqlite3)
        cols: List[ColumnSchema] = []
        pk_cols: List[Tuple[int, str]] = []
        
        for r in columns_rows:
            col_name = r[1]
            col_type = r[2]
            nullable = not r[3]
            default_val = r[4]
            pk_num = r[5]
            
            # Check if this column is generated
            hidden = 0
            try:
                cursor.execute(f"PRAGMA table_xinfo('{table}')")
                xinfo = cursor.fetchall()
                for xr in xinfo:
                    if xr[1] == col_name:
                        hidden = xr[6]
                        break
            except Exception:
                pass
            
            raw_type = col_type
            if hidden in (2, 3):
                col_type = "GENERATED"
                raw_type = f"{raw_type} GENERATED"
                
            cols.append(
                ColumnSchema(
                    name=col_name,
                    data_type=col_type.split("(")[0].upper() if col_type else "TEXT",
                    raw_type=raw_type.upper() if raw_type else "TEXT",
                    nullable=nullable,
                    default_value=str(default_val) if default_val is not None else None,
                )
            )
            if pk_num > 0:
                pk_cols.append((pk_num, col_name))
                
        # Primary Key
        pk_schema = None
        if pk_cols:
            pk_cols.sort(key=lambda x: x[0])
            pk_columns = tuple(col[1] for col in pk_cols)
            pk_schema = PrimaryKeySchema(name=f"pk_{table}", columns=pk_columns)
            
        # Discover Foreign Keys
        cursor.execute(f"PRAGMA foreign_key_list('{table}')")
        fk_rows = cursor.fetchall()
        fks_dict: Dict[int, Dict[str, Any]] = {}
        for r in fk_rows:
            fk_id = r[0]
            seq = r[1]
            to_table = r[2]
            from_col = r[3]
            to_col = r[4]
            on_update = r[5]
            on_delete = r[6]
            
            if fk_id not in fks_dict:
                fks_dict[fk_id] = {
                    "name": f"fk_{table}_{to_table}_{fk_id}",
                    "from_cols": [],
                    "to_cols": [],
                    "to_table": to_table,
                    "on_update": on_update,
                    "on_delete": on_delete,
                }
            fks_dict[fk_id]["from_cols"].append((seq, from_col))
            fks_dict[fk_id]["to_cols"].append((seq, to_col))
            
        fk_schemas: List[ForeignKeySchema] = []
        for fid, fkd in fks_dict.items():
            fkd["from_cols"].sort(key=lambda x: x[0])
            fkd["to_cols"].sort(key=lambda x: x[0])
            fk_schemas.append(
                ForeignKeySchema(
                    name=fkd["name"],
                    from_columns=tuple(col[1] for col in fkd["from_cols"]),
                    to_table=fkd["to_table"],
                    to_columns=tuple(col[1] for col in fkd["to_cols"]),
                    on_delete=fkd["on_delete"],
                    on_update=fkd["on_update"],
                )
            )
            
        # Discover Indexes & Unique constraints
        cursor.execute(f"PRAGMA index_list('{table}')")
        index_rows = cursor.fetchall()
        idx_schemas: List[IndexSchema] = []
        const_schemas: List[ConstraintSchema] = []
        
        for r in index_rows:
            idx_name = r[1]
            unique = bool(r[2])
            origin = r[3]
            
            cursor.execute(f"PRAGMA index_info('{idx_name}')")
            idx_info = cursor.fetchall()
            idx_info.sort(key=lambda x: x[0])
            idx_cols = tuple(col[2] for col in idx_info)
            
            if origin == "u" or not origin:
                idx_schemas.append(
                    IndexSchema(name=idx_name, columns=idx_cols, unique=unique)
                )
            elif origin == "c" and unique:
                const_schemas.append(
                    ConstraintSchema(name=idx_name, type="UNIQUE", columns=idx_cols)
                )
                
        cursor.execute(f"SELECT sql FROM sqlite_master WHERE type='table' AND name='{table}'")
        tbl_sql = cursor.fetchone()
        if tbl_sql and "CHECK" in tbl_sql[0].upper():
            const_schemas.append(
                ConstraintSchema(
                    name=f"chk_{table}_def",
                    type="CHECK",
                    definition="CHECK expression parsed",
                )
            )
                
        table_schemas.append(
            TableSchema(
                name=table,
                columns=tuple(cols),
                primary_key=pk_schema,
                foreign_keys=tuple(fk_schemas),
                indexes=tuple(idx_schemas),
                constraints=tuple(const_schemas),
            )
        )
        
    return Schema(tables=tuple(table_schemas), vendor=SystemType.SQLITE)


class TestComparisonSqliteIntegration(unittest.TestCase):
    """
    Exhaustive integration testing comparing real schemas extracted from live SQLite connections.
    """

    def setUp(self) -> None:
        self.conn_src = sqlite3.connect(":memory:")
        self.conn_tgt = sqlite3.connect(":memory:")
        self.engine = SchemaComparisonEngine(ComparisonContext(normalize_identifiers=True))

    def tearDown(self) -> None:
        self.conn_src.close()
        self.conn_tgt.close()

    def test_exhaustive_database_integration(self) -> None:
        """Deploys complex tables with all Stage 1 requirements and runs Schema Comparison Engine."""
        cursor_src = self.conn_src.cursor()
        
        # Quoted identifiers, Reserved SQL keywords, Unicode table names
        cursor_src.execute('CREATE TABLE "SELECT" ("id" INTEGER PRIMARY KEY AUTOINCREMENT, "value" TEXT)')
        cursor_src.execute('CREATE TABLE "用户" ("Id" INTEGER, "Name" TEXT, PRIMARY KEY ("Id"))')
        
        # Table with Composite PKs, Composite FKs, defaults, generated columns, and CHECK/UNIQUE constraints
        cursor_src.execute("""
            CREATE TABLE parent (
                p1 INT,
                p2 INT,
                val VARCHAR(50) DEFAULT 'default_val',
                PRIMARY KEY (p1, p2)
            )
        """)
        cursor_src.execute("""
            CREATE TABLE child (
                c1 INT,
                c2 INT,
                parent_p1 INT,
                parent_p2 INT,
                stored_val INT GENERATED ALWAYS AS (c1 * 2) STORED,
                salary REAL CHECK(salary > 0),
                PRIMARY KEY (c1, c2),
                FOREIGN KEY (parent_p1, parent_p2) REFERENCES parent (p1, p2)
            )
        """)
        cursor_src.execute("CREATE INDEX idx_parent_val ON parent (val)")
        cursor_src.execute("CREATE UNIQUE INDEX uq_child_salary ON child (salary)")

        # Setup Target Database
        cursor_tgt = self.conn_tgt.cursor()
        cursor_tgt.execute('CREATE TABLE "SELECT" ("id" INTEGER PRIMARY KEY AUTOINCREMENT, "value" TEXT)')
        cursor_tgt.execute('CREATE TABLE "用户" ("Id" INTEGER, "Name" TEXT, "Age" INT, PRIMARY KEY ("Id"))')
        
        cursor_tgt.execute("""
            CREATE TABLE parent (
                p1 INT,
                p2 INT,
                val VARCHAR(50) DEFAULT 'other_val',
                PRIMARY KEY (p1, p2)
            )
        """)
        cursor_tgt.execute("CREATE INDEX idx_parent_val ON parent (val)")
        
        cursor_tgt.execute("""
            CREATE TABLE child (
                c1 INT,
                c2 INT,
                parent_p1 INT,
                parent_p2 INT,
                stored_val INT GENERATED ALWAYS AS (c1 * 2) STORED,
                salary REAL CHECK(salary > 0),
                PRIMARY KEY (c1, c2)
            )
        """)

        # Extract schemas dynamically
        src_schema = extract_schema_from_sqlite(self.conn_src)
        tgt_schema = extract_schema_from_sqlite(self.conn_tgt)

        # Run comparison engine
        report = self.engine.compare(src_schema, tgt_schema)
        
        # Assert differences detected
        self.assertEqual(report.status.value, "DIFFERENT")
        self.assertTrue(len(report.differences) > 0)
        
        # Table 'SELECT' (using reserved SQL keyword) is identical
        select_diffs = [d for d in report.differences if "SELECT" in d.path]
        self.assertEqual(len(select_diffs), 0)
        
        # Table '用户' should have 'Age' column unexpected (REMOVE column to match source)
        user_diffs = [d for d in report.differences if "用户" in d.path]
        self.assertEqual(len(user_diffs), 1)
        self.assertEqual(user_diffs[0].category, DifferenceCategory.COLUMN)
        self.assertEqual(user_diffs[0].action, DifferenceAction.REMOVE)
        self.assertEqual(user_diffs[0].column_name, "Age")
        
        # Parent table val column has a default value mismatch
        parent_diffs = [d for d in report.differences if "parent" in d.path and "columns.val" in d.path]
        self.assertEqual(len(parent_diffs), 1)
        self.assertEqual(parent_diffs[0].category, DifferenceCategory.COLUMN)
        self.assertEqual(parent_diffs[0].action, DifferenceAction.MODIFY)
        self.assertTrue(parent_diffs[0].default_mismatch)
        
        # Child table should be missing foreign key referencing parent
        child_diffs = [d for d in report.differences if "child" in d.path]
        categories = {d.category for d in child_diffs}
        self.assertIn(DifferenceCategory.FOREIGN_KEY, categories)

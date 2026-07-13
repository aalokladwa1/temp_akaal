"""
Akaal — Schema Comparison Property-Based Tests
===============================================
Generates thousands of randomized database schemas to assert engine invariants:
- Reflexivity (compare A to A yields IDENTICAL and 0 differences)
- Serializer Round-trip (JSON output parses back to equivalent report)
- Determinism & Order Independence (shuffling tables doesn't change diff report order)
- Perfect Recall (mutating specific elements yields exactly the correct differences,
  without false positives or false negatives).
"""

import random
import unittest
from typing import List, Tuple
from akaal.core.models.enums import SystemType
from akaal.core.comparison import (
    SchemaComparisonEngine,
    ComparisonContext,
    SchemaValidator,
    Schema,
    TableSchema,
    ColumnSchema,
    PrimaryKeySchema,
    ForeignKeySchema,
    IndexSchema,
    ConstraintSchema,
    SchemaDifferenceSerializer,
    DifferenceCategory,
    DifferenceAction,
)

# Standard pool of SQL types and name tokens
SQL_TYPES = ["INTEGER", "VARCHAR(255)", "TEXT", "DECIMAL(10,2)", "BOOLEAN", "TIMESTAMP", "DOUBLE"]
NAME_TOKENS = ["id", "name", "status", "created_at", "updated_at", "value", "user_id", "dept_id", "salary", "code"]


def generate_random_valid_schema(seed: int) -> Schema:
    """Generates a structurally valid random database schema using a fixed seed."""
    rng = random.Random(seed)
    num_tables = rng.randint(1, 15)
    
    # Generate table names
    table_names = [f"tbl_{rng.randint(100, 9999)}_{i}" for i in range(num_tables)]
    
    tables: List[TableSchema] = []
    for name in table_names:
        # Columns
        num_cols = rng.randint(1, 10)
        cols: List[ColumnSchema] = []
        col_names = []
        for j in range(num_cols):
            token = rng.choice(NAME_TOKENS)
            c_name = f"{token}_{rng.randint(1, 1000)}_{j}"
            col_names.append(c_name)
            
            c_type = rng.choice(SQL_TYPES)
            nullable = rng.choice([True, False])
            default = rng.choice([None, "NULL", "'active'", "0"])
            cols.append(ColumnSchema(name=c_name, data_type=c_type.split("(")[0], raw_type=c_type, nullable=nullable, default_value=default))
            
        # Primary Key (optional)
        pk = None
        if rng.choice([True, False]) and cols:
            pk_cols = rng.sample(col_names, rng.randint(1, min(3, len(cols))))
            pk = PrimaryKeySchema(name=f"pk_{name}", columns=tuple(pk_cols))
            
        # Indexes (optional)
        idx_list = []
        if rng.choice([True, False]):
            num_idx = rng.randint(1, 3)
            for k in range(num_idx):
                idx_cols = rng.sample(col_names, rng.randint(1, min(3, len(cols))))
                idx_list.append(IndexSchema(name=f"idx_{name}_{rng.randint(100, 999)}_{k}", columns=tuple(idx_cols), unique=rng.choice([True, False])))
                
        # Unique/Check constraints
        const_list = []
        if rng.choice([True, False]):
            const_list.append(ConstraintSchema(name=f"chk_{name}_{rng.randint(100, 999)}", type="CHECK", definition="salary > 0"))
            
        # Foreign Keys referencing pre-existing tables
        fk_list = []
        # Find other tables
        other_tables = [t for t in table_names if t != name]
        if other_tables and rng.choice([True, False]) and len(cols) >= 2:
            target_table = rng.choice(other_tables)
            # Create a simple foreign key linking a local column to target primary key col placeholder
            from_col = rng.choice(col_names)
            fk_list.append(
                ForeignKeySchema(
                    name=f"fk_{name}_{target_table}_{rng.randint(100, 999)}",
                    from_columns=(from_col,),
                    to_table=target_table,
                    to_columns=("id_placeholder",),  # We'll post-process to align this
                )
            )
            
        tables.append(
            TableSchema(
                name=name,
                columns=tuple(cols),
                primary_key=pk,
                foreign_keys=tuple(fk_list),
                indexes=tuple(idx_list),
                constraints=tuple(const_list),
            )
        )
        
    # Post-process: align foreign key targets to ensure referential integrity
    tables_dict = {t.name: t for t in tables}
    for idx, table in enumerate(tables):
        new_fks = []
        for fk in table.foreign_keys:
            target_tbl = tables_dict.get(fk.to_table)
            if target_tbl:
                # If target table has columns, reference the first column name
                target_col = target_tbl.columns[0].name
                new_fks.append(
                    ForeignKeySchema(
                        name=fk.name,
                        from_columns=fk.from_columns,
                        to_table=fk.to_table,
                        to_columns=(target_col,),
                        on_delete=fk.on_delete,
                        on_update=fk.on_update,
                    )
                )
        tables[idx] = TableSchema(
            name=table.name,
            columns=table.columns,
            primary_key=table.primary_key,
            foreign_keys=tuple(new_fks),
            indexes=table.indexes,
            constraints=table.constraints,
        )
        
    return Schema(tables=tuple(tables), vendor=SystemType.GENERIC)


class TestSchemaComparisonProperty(unittest.TestCase):
    """
    Asserts structural invariants on generated random schemas.
    """

    def setUp(self) -> None:
        self.engine = SchemaComparisonEngine()
        self.validator = SchemaValidator()

    def test_random_property_invariants(self) -> None:
        """Runs property-based tests across 1,000 generated randomized schemas."""
        for i in range(1000):
            schema = generate_random_valid_schema(seed=12345 + i)
            # Ensure schema is valid
            try:
                self.validator.validate(schema)
            except Exception as e:
                # Skip invalid schemas due to random name overlap checks
                continue
                
            # Property 1: Reflexivity (A == A yields IDENTICAL)
            report_ident = self.engine.compare(schema, schema)
            self.assertEqual(report_ident.status.value, "IDENTICAL")
            self.assertEqual(len(report_ident.differences), 0)
            self.assertEqual(report_ident.source_checksum, report_ident.target_checksum)
            
            # Generate another schema to compare
            schema_b = generate_random_valid_schema(seed=54321 + i)
            try:
                self.validator.validate(schema_b)
            except Exception:
                continue
                
            report_diff = self.engine.compare(schema, schema_b)
            
            # Property 2: Serializer Round-trip
            serialized = SchemaDifferenceSerializer.serialize_report(report_diff)
            deserialized = SchemaDifferenceSerializer.deserialize_report(serialized)
            
            self.assertEqual(report_diff.report_id, deserialized.report_id)
            self.assertEqual(report_diff.status, deserialized.status)
            self.assertEqual(len(report_diff.differences), len(deserialized.differences))
            self.assertEqual(report_diff.summary_statistics, deserialized.summary_statistics)
            
            # Property 3: Shuffling input tables preserves deterministic comparison ordering
            tables_list = list(schema.tables)
            random.Random(i).shuffle(tables_list)
            shuffled_schema = Schema(
                tables=tuple(tables_list),
                schema_name=schema.schema_name,
                schema_version=schema.schema_version,
                vendor=schema.vendor,
                encoding=schema.encoding,
                collation=schema.collation,
            )
            
            report_shuffled = self.engine.compare(shuffled_schema, schema_b)
            # Verify diffs are identical in content and order
            self.assertEqual(
                [d.difference_id for d in report_diff.differences],
                [d.difference_id for d in report_shuffled.differences],
                "Table ordering affected difference outputs or order"
            )
            
            # Property 4: Single target mutations yield zero false negatives (detects exactly 1 diff)
            if schema.tables:
                mutated_tables = list(schema.tables)
                tbl = mutated_tables[0]
                # Mutate: Add a dummy column
                new_cols = list(tbl.columns)
                new_cols.append(ColumnSchema(name="dummy_mutated_col", data_type="INTEGER", raw_type="INTEGER", nullable=True))
                mutated_tables[0] = TableSchema(
                    name=tbl.name,
                    columns=tuple(new_cols),
                    primary_key=tbl.primary_key,
                    foreign_keys=tbl.foreign_keys,
                    indexes=tbl.indexes,
                    constraints=tbl.constraints,
                )
                mutated_schema = Schema(tables=tuple(mutated_tables))
                
                report_mutated = self.engine.compare(schema, mutated_schema)
                self.assertEqual(report_mutated.status.value, "DIFFERENT")
                # Expected: exactly 1 difference (ADD Column in target, wait target is missing dummy_mutated_col relative to source, so action is ADD column in target)
                self.assertEqual(len(report_mutated.differences), 1)
                self.assertEqual(report_mutated.differences[0].category, DifferenceCategory.COLUMN)
                self.assertEqual(report_mutated.differences[0].action, DifferenceAction.REMOVE)
                self.assertEqual(report_mutated.differences[0].column_name, "dummy_mutated_col")

"""
Akaal — Schema Comparison Unit Tests
====================================
Tests the SchemaComparisonEngine correctness, identifier resolution,
deterministic IDs and sorting, custom exceptions, and serializer compatibility.
"""

import datetime
import json
import unittest
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
    DifferenceSeverity,
    MigrationImpact,
    InvalidSchemaError,
    SchemaComparisonStatus,
    SerializationError,
)
from akaal.core.comparison.comparers import COMPARER_REGISTRY
from akaal.core.comparison.comparers.base import BaseComparer


class TestSchemaComparison(unittest.TestCase):
    """
    Unit test cases for the Schema Comparison Engine.
    """

    def test_compare_empty_schemas(self) -> None:
        """Verify that comparing two empty schemas returns IDENTICAL with no differences."""
        engine = SchemaComparisonEngine()
        src = Schema(tables=())
        tgt = Schema(tables=())
        report = engine.compare(src, tgt)
        self.assertEqual(report.status.value, "IDENTICAL")
        self.assertEqual(len(report.differences), 0)
        self.assertEqual(report.summary_statistics.total_differences, 0)
        self.assertEqual(report.summary_statistics.total_objects, 0)

    def test_compare_identical_schemas(self) -> None:
        """Verify that identical table structures result in matching checksums and status IDENTICAL."""
        engine = SchemaComparisonEngine()
        src = Schema(
            tables=(
                TableSchema(
                    name="users",
                    columns=(
                        ColumnSchema("id", "INTEGER", "INT", False),
                        ColumnSchema("email", "STRING", "VARCHAR(255)", False),
                    ),
                    primary_key=PrimaryKeySchema("pk_users", ("id",)),
                    indexes=(
                        IndexSchema("idx_users_email", ("email",), True),
                    ),
                ),
            )
        )
        tgt = Schema(
            tables=(
                TableSchema(
                    name="users",
                    columns=(
                        ColumnSchema("id", "INTEGER", "INT", False),
                        ColumnSchema("email", "STRING", "VARCHAR(255)", False),
                    ),
                    primary_key=PrimaryKeySchema("pk_users", ("id",)),
                    indexes=(
                        IndexSchema("idx_users_email", ("email",), True),
                    ),
                ),
            )
        )
        report = engine.compare(src, tgt)
        self.assertEqual(report.status.value, "IDENTICAL")
        self.assertEqual(len(report.differences), 0)
        self.assertEqual(report.source_checksum, report.target_checksum)

    def test_compare_missing_table(self) -> None:
        """Verify that a missing table maps to an ADD action with critical severity."""
        engine = SchemaComparisonEngine()
        src = Schema(
            tables=(
                TableSchema(
                    name="orders",
                    columns=(ColumnSchema("id", "INTEGER", "INT", False),),
                ),
            )
        )
        tgt = Schema(tables=())
        report = engine.compare(src, tgt)
        self.assertEqual(report.status.value, "DIFFERENT")
        self.assertEqual(len(report.differences), 1)
        
        diff = report.differences[0]
        self.assertEqual(diff.category, DifferenceCategory.TABLE)
        self.assertEqual(diff.action, DifferenceAction.ADD)
        self.assertEqual(diff.severity, DifferenceSeverity.CRITICAL)
        self.assertEqual(diff.path, "tables.orders")
        # Assert deterministic SHA-256 Difference ID
        self.assertIsNotNone(diff.difference_id)

    def test_compare_extra_table(self) -> None:
        """Verify that an unexpected table maps to a REMOVE action with destructive impact."""
        engine = SchemaComparisonEngine()
        src = Schema(tables=())
        tgt = Schema(
            tables=(
                TableSchema(
                    name="logs",
                    columns=(ColumnSchema("id", "INTEGER", "INT", False),),
                ),
            )
        )
        report = engine.compare(src, tgt)
        self.assertEqual(report.status.value, "DIFFERENT")
        self.assertEqual(len(report.differences), 1)
        
        diff = report.differences[0]
        self.assertEqual(diff.category, DifferenceCategory.TABLE)
        self.assertEqual(diff.action, DifferenceAction.REMOVE)
        self.assertEqual(diff.severity, DifferenceSeverity.CRITICAL)
        self.assertEqual(diff.impact, MigrationImpact.DESTRUCTIVE)

    def test_unicode_and_quoted_identifiers(self) -> None:
        """Verify that Unicode names and quoted names normalize correctly during comparison."""
        engine = SchemaComparisonEngine(ComparisonContext(normalize_identifiers=True))
        src = Schema(
            tables=(
                TableSchema(
                    name="用户_Data",
                    columns=(ColumnSchema("`Id`", "INTEGER", "INT", False),),
                ),
            )
        )
        tgt = Schema(
            tables=(
                TableSchema(
                    name='"用户_data"',
                    columns=(ColumnSchema("id", "INTEGER", "INT", False),),
                ),
            )
        )
        report = engine.compare(src, tgt)
        self.assertEqual(report.status.value, "IDENTICAL")

    def test_duplicate_table_validation(self) -> None:
        """Verify that duplicate table names (differing only in case) raise InvalidSchemaError."""
        validator = SchemaValidator()
        bad_schema = Schema(
            tables=(
                TableSchema(name="Users", columns=(ColumnSchema("id", "INTEGER", "INT", False),)),
                TableSchema(name="users", columns=(ColumnSchema("id", "INTEGER", "INT", False),)),
            )
        )
        with self.assertRaises(InvalidSchemaError):
            validator.validate(bad_schema)

    def test_deterministic_ordering_of_differences(self) -> None:
        """Verify that differences are always sorted deterministically by category first."""
        engine = SchemaComparisonEngine()
        # Source table has columns, primary keys, and foreign keys
        src = Schema(
            tables=(
                TableSchema(
                    name="orders",
                    columns=(
                        ColumnSchema("id", "INTEGER", "INT", False),
                        ColumnSchema("user_id", "INTEGER", "INT", False),
                    ),
                    primary_key=PrimaryKeySchema("pk_orders", ("id",)),
                    foreign_keys=(
                        ForeignKeySchema("fk_orders_user", ("user_id",), "users", ("id",)),
                    ),
                ),
                TableSchema(
                    name="users",
                    columns=(ColumnSchema("id", "INTEGER", "INT", False),),
                ),
            )
        )
        # Target table has nothing
        tgt = Schema(
            tables=(
                TableSchema(name="orders", columns=()),
                TableSchema(name="users", columns=()),
            )
        )

        report = engine.compare(src, tgt)
        self.assertTrue(len(report.differences) > 0)
        
        # TABLE should sort before COLUMN, which should sort before PRIMARY_KEY
        categories = [d.category for d in report.differences]
        # We check that the relative category priorities are ordered correctly
        # Priority mapping: TABLE (0), COLUMN (1), PRIMARY_KEY (2)
        priorities = []
        category_order = {
            DifferenceCategory.TABLE: 0,
            DifferenceCategory.COLUMN: 1,
            DifferenceCategory.PRIMARY_KEY: 2,
            DifferenceCategory.INDEX: 3,
            DifferenceCategory.FOREIGN_KEY: 4,
            DifferenceCategory.CONSTRAINT: 5,
        }
        for cat in categories:
            priorities.append(category_order[cat])
            
        self.assertEqual(priorities, sorted(priorities), "Differences are not sorted by category order.")

    def test_column_mismatches_and_auto_pk(self) -> None:
        """Verify column mismatches and confirm MySQL NULL vs PostgreSQL NEXTVAL PK auto-increment mapping."""
        # 1. Standard default mismatch (non-PK col)
        engine = SchemaComparisonEngine()
        src = Schema(
            tables=(
                TableSchema(
                    name="items",
                    columns=(
                        ColumnSchema("id", "INTEGER", "INT", False),
                        ColumnSchema("price", "DECIMAL", "DECIMAL(10,2)", True, "0.00"),
                    ),
                    primary_key=PrimaryKeySchema("pk_items", ("id",)),
                ),
            )
        )
        tgt = Schema(
            tables=(
                TableSchema(
                    name="items",
                    columns=(
                        ColumnSchema("id", "INTEGER", "INT", False),
                        ColumnSchema("price", "DECIMAL", "DECIMAL(10,2)", True, "1.00"),
                    ),
                    primary_key=PrimaryKeySchema("pk_items", ("id",)),
                ),
            )
        )
        report = engine.compare(src, tgt)
        self.assertEqual(len(report.differences), 1)
        self.assertTrue(report.differences[0].default_mismatch)

        # 2. PK column auto-increment equivalence: NULL default on MySQL vs NEXTVAL on PG
        src_auto = Schema(
            tables=(
                TableSchema(
                    name="items",
                    columns=(
                        ColumnSchema("id", "INTEGER", "INTEGER", False, "NULL"),
                    ),
                    primary_key=PrimaryKeySchema("pk_items", ("id",)),
                ),
            )
        )
        tgt_auto = Schema(
            tables=(
                TableSchema(
                    name="items",
                    columns=(
                        ColumnSchema("id", "INTEGER", "INTEGER", False, "NEXTVAL"),
                    ),
                    primary_key=PrimaryKeySchema("pk_items", ("id",)),
                ),
            )
        )
        report_auto = engine.compare(src_auto, tgt_auto)
        self.assertEqual(len(report_auto.differences), 0, "PK auto-increment default equivalence failed.")

    def test_composite_pk_ordering_mismatch(self) -> None:
        """Verify that column ordering mismatches in composite primary keys are detected."""
        engine = SchemaComparisonEngine()
        src = Schema(
            tables=(
                TableSchema(
                    name="mappings",
                    columns=(
                        ColumnSchema("k1", "INTEGER", "INT", False),
                        ColumnSchema("k2", "INTEGER", "INT", False),
                    ),
                    primary_key=PrimaryKeySchema("pk_map", ("k1", "k2")),
                ),
            )
        )
        tgt = Schema(
            tables=(
                TableSchema(
                    name="mappings",
                    columns=(
                        ColumnSchema("k1", "INTEGER", "INT", False),
                        ColumnSchema("k2", "INTEGER", "INT", False),
                    ),
                    primary_key=PrimaryKeySchema("pk_map", ("k2", "k1")),
                ),
            )
        )
        report = engine.compare(src, tgt)
        self.assertEqual(len(report.differences), 1)
        self.assertEqual(report.differences[0].category, DifferenceCategory.PRIMARY_KEY)
        self.assertEqual(report.differences[0].action, DifferenceAction.MODIFY)

    def test_serializer_backward_compatibility(self) -> None:
        """Verify report serializer is backward compatible when parsing legacy JSON formats."""
        legacy_json = """
        {
          "report_id": "8bbbbd4d-f952-4467-bc18-97fbbf965251",
          "report_version": "1.0.0",
          "comparison_timestamp": "2026-07-13T12:00:00Z",
          "source_vendor": "MYSQL",
          "target_vendor": "POSTGRESQL",
          "engine_version": "0.9.0",
          "source_checksum": "abc",
          "target_checksum": "def",
          "status": "DIFFERENT",
          "differences": [
            {
              "difference_id": "deterministic_diff_id",
              "category": "TABLE",
              "action": "ADD",
              "path": "tables.legacy_table",
              "table_name": "legacy_table",
              "description": "Legacy table missing"
            }
          ],
          "summary_statistics": {
            "total_objects": 1,
            "total_differences": 1,
            "added": 1
          }
        }
        """
        report = SchemaDifferenceSerializer.deserialize_report(legacy_json)
        self.assertEqual(report.status, SchemaComparisonStatus.DIFFERENT)
        self.assertEqual(len(report.differences), 1)
        self.assertEqual(report.differences[0].category, DifferenceCategory.TABLE)
        self.assertEqual(report.differences[0].action, DifferenceAction.ADD)
        # Verify missing fields fallback correctly
        self.assertEqual(report.differences[0].severity, DifferenceSeverity.WARNING)
        self.assertEqual(report.differences[0].impact, MigrationImpact.ONLINE_DDL)

    def test_plugin_discovery_registry(self) -> None:
        """Verify that dynamically subclassing BaseComparer registers the class automatically."""
        # Create a dynamic mock comparer
        class MockViewComparer(BaseComparer):
            OBJECT_TYPE = "MOCK_VIEW"
            def compare(self, expected: Any, actual: Any, context: ComparisonContext, **kwargs: Any):
                return []

        self.assertIn("MOCK_VIEW", COMPARER_REGISTRY)
        self.assertEqual(COMPARER_REGISTRY["MOCK_VIEW"], MockViewComparer)

    def test_duplicate_comparer_registration_throws_value_error(self) -> None:
        """Verify that duplicate registrations under the same OBJECT_TYPE raise a ValueError."""
        with self.assertRaises(ValueError):
            class DuplicateTableComparer(BaseComparer):
                OBJECT_TYPE = "TABLE"  # Already registered by TableComparer
                def compare(self, expected: Any, actual: Any, context: ComparisonContext, **kwargs: Any):
                    return []

    def test_deterministic_id_hashing_collision_free(self) -> None:
        """Verify modifying different aspects of the same column generates distinct difference IDs."""
        from akaal.core.comparison.models.differences import generate_deterministic_id
        id_type_change = generate_deterministic_id("COLUMN", "tables.users.columns.status", "MODIFY", "type=VARCHAR->INT")
        id_default_change = generate_deterministic_id("COLUMN", "tables.users.columns.status", "MODIFY", "default=NULL->'active'")
        self.assertNotEqual(id_type_change, id_default_change, "IDs must differ based on semantic change details.")

    def test_serializer_unknown_enums_and_malformed(self) -> None:
        """Verify deserializer correctly rejects unknown category/action enums and malformed JSON."""
        # 1. Unknown category enum
        unknown_cat_json = """
        {
          "report_id": "8bbbbd4d-f952-4467-bc18-97fbbf965251",
          "report_version": "1.0.0",
          "comparison_timestamp": "2026-07-13T12:00:00Z",
          "source_vendor": "MYSQL",
          "target_vendor": "POSTGRESQL",
          "engine_version": "1.0.0",
          "source_checksum": "abc",
          "target_checksum": "def",
          "status": "DIFFERENT",
          "differences": [
            {
              "difference_id": "diff_id",
              "category": "INVALID_CATEGORY",
              "action": "ADD",
              "path": "tables.legacy_table",
              "table_name": "legacy_table",
              "description": "Legacy table missing"
            }
          ]
        }
        """
        with self.assertRaises(SerializationError):
            SchemaDifferenceSerializer.deserialize_report(unknown_cat_json)

        # 2. Malformed JSON syntax
        with self.assertRaises(SerializationError):
            SchemaDifferenceSerializer.deserialize_report("{malformed_json:")

    def test_thread_safety(self) -> None:
        """Verify that SchemaComparisonEngine execution is stateless and safe for concurrent threads."""
        import concurrent.futures
        engine = SchemaComparisonEngine()
        
        # Define schemas
        src = Schema(
            tables=(
                TableSchema(
                    name="users",
                    columns=(ColumnSchema("id", "INTEGER", "INT", False),),
                    primary_key=PrimaryKeySchema("pk_users", ("id",)),
                ),
            )
        )
        tgt = Schema(tables=())  # Different schema
        
        def run_compare():
            report = engine.compare(src, tgt)
            return report.status, len(report.differences)

        # Execute 20 concurrent tasks
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(run_compare) for _ in range(20)]
            results = [f.result() for f in futures]

        for status, diff_count in results:
            self.assertEqual(status, SchemaComparisonStatus.DIFFERENT)
            self.assertEqual(diff_count, 1)

    def test_global_constraint_uniqueness_validation(self) -> None:
        """Verify duplicate PK, FK, Index, and constraint names raise InvalidSchemaError across tables."""
        validator = SchemaValidator()
        
        # Test duplicate index names across tables
        bad_index_schema = Schema(
            tables=(
                TableSchema(
                    name="users",
                    columns=(ColumnSchema("id", "INTEGER", "INT", False),),
                    indexes=(IndexSchema("idx_common_name", ("id",), False),),
                ),
                TableSchema(
                    name="orders",
                    columns=(ColumnSchema("id", "INTEGER", "INT", False),),
                    indexes=(IndexSchema("idx_common_name", ("id",), False),),
                ),
            )
        )
        with self.assertRaises(InvalidSchemaError):
            validator.validate(bad_index_schema)

        # Test duplicate FK name globally
        bad_fk_schema = Schema(
            tables=(
                TableSchema(
                    name="orders",
                    columns=(
                        ColumnSchema("id", "INTEGER", "INT", False),
                        ColumnSchema("user_id", "INTEGER", "INT", False),
                    ),
                    foreign_keys=(
                        ForeignKeySchema("fk_duplicate_global", ("user_id",), "users", ("id",)),
                    ),
                ),
                TableSchema(
                    name="users",
                    columns=(
                        ColumnSchema("id", "INTEGER", "INT", False),
                        ColumnSchema("parent_id", "INTEGER", "INT", True),
                    ),
                    foreign_keys=(
                        ForeignKeySchema("fk_duplicate_global", ("parent_id",), "users", ("id",)),
                    ),
                ),
            )
        )
        with self.assertRaises(InvalidSchemaError):
            validator.validate(bad_fk_schema)

    def test_serializer_fuzzing(self) -> None:
        """Fuzz-test the serializer/deserializer with malformed, partial, and unexpected JSON payloads."""
        # 1. Missing required top-level keys
        partial_json = '{"report_id": "123", "report_version": "1.0.0"}'
        with self.assertRaises(SerializationError):
            SchemaDifferenceSerializer.deserialize_report(partial_json)

        # 2. Unexpected enum values
        bad_action_json = """
        {
          "report_id": "8bbbbd4d-f952-4467-bc18-97fbbf965251",
          "report_version": "1.0.0",
          "comparison_timestamp": "2026-07-13T12:00:00Z",
          "source_vendor": "MYSQL",
          "target_vendor": "POSTGRESQL",
          "engine_version": "1.0.0",
          "source_checksum": "abc",
          "target_checksum": "def",
          "status": "DIFFERENT",
          "differences": [
            {
              "difference_id": "diff_id",
              "category": "TABLE",
              "action": "INVALID_ACTION",
              "path": "tables.legacy_table",
              "table_name": "legacy_table",
              "description": "Legacy table missing"
            }
          ]
        }
        """
        with self.assertRaises(SerializationError):
            SchemaDifferenceSerializer.deserialize_report(bad_action_json)

        # 3. Payload with unknown/unexpected extra fields should succeed (forward compatibility)
        extra_fields_json = """
        {
          "report_id": "8bbbbd4d-f952-4467-bc18-97fbbf965251",
          "report_version": "1.0.0",
          "comparison_timestamp": "2026-07-13T12:00:00Z",
          "source_vendor": "MYSQL",
          "target_vendor": "POSTGRESQL",
          "engine_version": "1.0.0",
          "source_checksum": "abc",
          "target_checksum": "def",
          "status": "IDENTICAL",
          "differences": [],
          "summary_statistics": {},
          "unknown_future_field": "future_value"
        }
        """
        report = SchemaDifferenceSerializer.deserialize_report(extra_fields_json)
        self.assertEqual(report.status, SchemaComparisonStatus.IDENTICAL)

    def test_stress_repeatability(self) -> None:
        """Execute 1,000 consecutive comparisons on identical schemas to verify report repeatability."""
        engine = SchemaComparisonEngine()
        src = Schema(
            tables=(
                TableSchema(
                    name="users",
                    columns=(
                        ColumnSchema("id", "INTEGER", "INT", False),
                        ColumnSchema("email", "STRING", "VARCHAR(255)", False),
                    ),
                    primary_key=PrimaryKeySchema("pk_users", ("id",)),
                    indexes=(IndexSchema("idx_email", ("email",), True),),
                ),
            )
        )
        tgt = Schema(
            tables=(
                TableSchema(
                    name="users",
                    columns=(
                        ColumnSchema("id", "INTEGER", "INT", False),
                        ColumnSchema("email", "STRING", "VARCHAR(255)", False),
                    ),
                    primary_key=PrimaryKeySchema("pk_users", ("id",)),
                    indexes=(IndexSchema("idx_email", ("email",), True),),
                ),
            )
        )

        first_report = engine.compare(src, tgt)
        for _ in range(1000):
            next_report = engine.compare(src, tgt)
            self.assertEqual(first_report.status, next_report.status)
            self.assertEqual(first_report.source_checksum, next_report.source_checksum)
            self.assertEqual(first_report.target_checksum, next_report.target_checksum)
            self.assertEqual(len(first_report.differences), len(next_report.differences))

    def test_thread_safety_shared_engine(self) -> None:
        """Execute concurrent comparisons from multiple threads using the same shared engine instance."""
        import concurrent.futures
        shared_engine = SchemaComparisonEngine()
        src = Schema(
            tables=(
                TableSchema(
                    name="users",
                    columns=(ColumnSchema("id", "INTEGER", "INT", False),),
                ),
            )
        )
        tgt = Schema(
            tables=(
                TableSchema(
                    name="users",
                    columns=(ColumnSchema("id", "INTEGER", "INT", False),),
                ),
            )
        )

        def worker():
            report = shared_engine.compare(src, tgt)
            return report.status

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(worker) for _ in range(100)]
            results = [f.result() for f in futures]

        for res in results:
            self.assertEqual(res, SchemaComparisonStatus.IDENTICAL)

    def test_edge_cases_identifiers(self) -> None:
        """Test edge cases: long names, empty names, Unicode normalization NFC/NFD, SQL keywords, case-insensitive duplicates, and composite keys."""
        validator = SchemaValidator()
        engine = SchemaComparisonEngine()

        # 1. Long identifier names (should work)
        long_name = "a" * 255
        long_schema = Schema(
            tables=(
                TableSchema(
                    name=long_name,
                    columns=(ColumnSchema("id", "INTEGER", "INT", False),),
                ),
            )
        )
        validator.validate(long_schema)

        # 2. Empty identifier name (should raise InvalidSchemaError)
        empty_schema = Schema(
            tables=(
                TableSchema(
                    name="",
                    columns=(ColumnSchema("id", "INTEGER", "INT", False),),
                ),
            )
        )
        with self.assertRaises(InvalidSchemaError):
            validator.validate(empty_schema)

        # 3. Unicode normalization variation (NFC vs NFD)
        nfc_name = "Caf\u00e9"  # Café in NFC (single char é)
        nfd_name = "Cafe\u0301"  # Café in NFD (e + combining accent)
        
        src_unicode = Schema(
            tables=(
                TableSchema(
                    name=nfc_name,
                    columns=(ColumnSchema("id", "INTEGER", "INT", False),),
                ),
            )
        )
        tgt_unicode = Schema(
            tables=(
                TableSchema(
                    name=nfd_name,
                    columns=(ColumnSchema("id", "INTEGER", "INT", False),),
                ),
            )
        )
        report = engine.compare(src_unicode, tgt_unicode)
        self.assertEqual(report.status, SchemaComparisonStatus.IDENTICAL)

        # 4. Reserved SQL keywords as identifiers
        keyword_schema = Schema(
            tables=(
                TableSchema(
                    name="SELECT",
                    columns=(
                        ColumnSchema("WHERE", "INTEGER", "INT", False),
                        ColumnSchema("FROM", "STRING", "VARCHAR(50)", True),
                    ),
                    primary_key=PrimaryKeySchema("PRIMARY", ("WHERE",)),
                ),
            )
        )
        validator.validate(keyword_schema)

        # 5. Duplicate names differing only by case in columns (should raise InvalidSchemaError)
        bad_col_schema = Schema(
            tables=(
                TableSchema(
                    name="users",
                    columns=(
                        ColumnSchema("status", "STRING", "VARCHAR(20)", False),
                        ColumnSchema("STATUS", "STRING", "VARCHAR(20)", False),
                    ),
                ),
            )
        )
        with self.assertRaises(InvalidSchemaError):
            validator.validate(bad_col_schema)

        # 6. Very large composite keys (e.g. 50 columns)
        composite_cols = tuple(f"col_{i}" for i in range(50))
        columns_def = tuple(ColumnSchema(name, "INTEGER", "INT", False) for name in composite_cols)
        composite_schema = Schema(
            tables=(
                TableSchema(
                    name="measurements",
                    columns=columns_def,
                    primary_key=PrimaryKeySchema("pk_composite", composite_cols),
                ),
            )
        )
        validator.validate(composite_schema)

    def test_order_independence_logical_equality(self) -> None:
        """Verify order-independent logical equality and hashing on TableSchema and Schema structures."""
        idx1 = IndexSchema("idx_email", ("email",), True)
        idx2 = IndexSchema("idx_status", ("status",), False)

        fk1 = ForeignKeySchema("fk_users_dept", ("dept_id",), "departments", ("id",))
        fk2 = ForeignKeySchema("fk_users_role", ("role_id",), "roles", ("id",))

        const1 = ConstraintSchema("chk_salary", "CHECK", (), "salary > 0")
        const2 = ConstraintSchema("chk_status", "CHECK", (), "status IN ('A', 'I')")

        cols = (
            ColumnSchema("id", "INTEGER", "INT", False),
            ColumnSchema("email", "STRING", "VARCHAR(255)", False),
            ColumnSchema("status", "STRING", "VARCHAR(10)", False),
            ColumnSchema("dept_id", "INTEGER", "INT", True),
            ColumnSchema("role_id", "INTEGER", "INT", True),
        )

        t1 = TableSchema(
            name="users",
            columns=cols,
            primary_key=PrimaryKeySchema("pk_users", ("id",)),
            foreign_keys=(fk1, fk2),
            indexes=(idx1, idx2),
            constraints=(const1, const2),
        )

        t2 = TableSchema(
            name="users",
            columns=cols,
            primary_key=PrimaryKeySchema("pk_users", ("id",)),
            foreign_keys=(fk2, fk1),  # Reordered
            indexes=(idx2, idx1),      # Reordered
            constraints=(const2, const1), # Reordered
        )

        # Test table equivalence
        self.assertEqual(t1, t2)
        self.assertEqual(hash(t1), hash(t2))

        # Test schema equivalence
        s1 = Schema(tables=(t1,))
        s2 = Schema(tables=(t2,))
        self.assertEqual(s1, s2)
        self.assertEqual(hash(s1), hash(s2))

    def test_global_pk_duplicate_validation(self) -> None:
        """Verify that duplicate global primary key names raise InvalidSchemaError."""
        validator = SchemaValidator()
        bad_pk_schema = Schema(
            tables=(
                TableSchema(
                    name="t1",
                    columns=(ColumnSchema("id", "INTEGER", "INT", False),),
                    primary_key=PrimaryKeySchema("pk_common_name", ("id",)),
                ),
                TableSchema(
                    name="t2",
                    columns=(ColumnSchema("id", "INTEGER", "INT", False),),
                    primary_key=PrimaryKeySchema("pk_common_name", ("id",)),
                ),
            )
        )
        with self.assertRaises(InvalidSchemaError):
            validator.validate(bad_pk_schema)

    def test_column_type_mismatch_detected(self) -> None:
        """Verify that changing a column's type generates a type mismatch difference."""
        engine = SchemaComparisonEngine()
        src = Schema(
            tables=(
                TableSchema(
                    name="users",
                    columns=(ColumnSchema("status", "STRING", "VARCHAR(255)", True),),
                ),
            )
        )
        tgt = Schema(
            tables=(
                TableSchema(
                    name="users",
                    columns=(ColumnSchema("status", "INTEGER", "INT", True),),
                ),
            )
        )
        report = engine.compare(src, tgt)
        self.assertEqual(len(report.differences), 1)
        self.assertEqual(report.differences[0].category, DifferenceCategory.COLUMN)
        self.assertEqual(report.differences[0].action, DifferenceAction.MODIFY)
        self.assertTrue(report.differences[0].type_mismatch)

    def test_serializer_unsupported_major_version(self) -> None:
        """Verify that deserializer rejects reports with unsupported major version > 1."""
        unsupported_ver_json = """
        {
          "report_id": "8bbbbd4d-f952-4467-bc18-97fbbf965251",
          "report_version": "2.0.0",
          "comparison_timestamp": "2026-07-13T12:00:00Z",
          "source_vendor": "MYSQL",
          "target_vendor": "POSTGRESQL",
          "engine_version": "1.0.0",
          "source_checksum": "abc",
          "target_checksum": "def",
          "status": "IDENTICAL",
          "differences": []
        }
        """
        with self.assertRaises(SerializationError):
            SchemaDifferenceSerializer.deserialize_report(unsupported_ver_json)



"""
Regression tests for validator_agent.py — cross-dialect normalization fixes.

Covers:
  Fix 1  — TINYINT(1) normalizes to BOOLEAN (not INTEGER)
  Fix 2  — NULL vs NEXTVAL is accepted only for INTEGER primary-key columns
  Fix 3  — Normalized schema checksum matches for MySQL→PostgreSQL migrations
  Regression — MySQL→MySQL and PostgreSQL→PostgreSQL still pass unchanged
"""

import hashlib
import json
import sys
import unittest
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from akaal.agents.validator.validator_agent import ValidatorAgent
from akaal.core.state.global_state import GlobalState
from akaal.core.message_bus.bus import MessageBus


# ── helpers ─────────────────────────────────────────────────────────────────

def _make_validator():
    """Return a ValidatorAgent with stub dependencies (not connected to any bus)."""
    state = GlobalState()
    bus = MessageBus()
    return ValidatorAgent(global_state=state, message_bus=bus, workspace_dir=".")


def _build_universal_json(objects: list, dependency_order: list) -> dict:
    """Build a minimal Universal JSON dict matching the ScoutAgent format."""
    payload = json.dumps(objects, sort_keys=True).encode("utf-8")
    checksum = hashlib.sha256(payload).hexdigest()
    return {
        "version": "1.0.0",
        "metadata": {
            "project_id": "test-project",
            "migration_id": "test-migration",
            "system_type": "MYSQL",
            "timestamp": "2026-01-01T00:00:00+00:00",
            "checksum": checksum,
            "adapter_version": "1.0.0",
            "schema_version": "1.0.0",
        },
        "objects": objects,
        "dependency_order": dependency_order,
    }


def _table_obj(name, columns, indexes=None, constraints=None,
               triggers=None, dependency_references=None):
    """Build a minimal raw table object as an adapter would return it."""
    return {
        "object_name": name,
        "object_type": "TABLE",
        "columns": columns,
        "indexes": indexes or [],
        "constraints": constraints or [],
        "triggers": triggers or [],
        "dependency_references": dependency_references or [],
    }


def _col(name, type_, default=None, nullable=False):
    return {"name": name, "type": type_, "default": default,
            "nullable": nullable, "parent_id": None}


def _pk_index(col_name):
    return {"name": "PRIMARY", "columns": [col_name], "unique": True}


# ── Fix 1: _normalize_type ───────────────────────────────────────────────────

class TestNormalizeType(unittest.TestCase):
    """Fix 1 — TINYINT(1) must map to BOOLEAN, not INTEGER."""

    def setUp(self):
        self.v = _make_validator()

    # --- TINYINT(1) ---

    def test_tinyint1_maps_to_boolean(self):
        """TINYINT(1) is MySQL's boolean alias: must become BOOLEAN."""
        self.assertEqual(self.v._normalize_type("TINYINT(1)"), "BOOLEAN")

    def test_tinyint1_uppercase_maps_to_boolean(self):
        # _normalize_type uppercases its input, so mixed case is equivalent
        self.assertEqual(self.v._normalize_type("tinyint(1)"), "BOOLEAN")

    # --- Other TINYINT variants remain INTEGER ---

    def test_tinyint2_maps_to_integer(self):
        """TINYINT(2) is a genuine small integer; must stay INTEGER."""
        self.assertEqual(self.v._normalize_type("TINYINT(2)"), "INTEGER")

    def test_tinyint_no_width_maps_to_integer(self):
        self.assertEqual(self.v._normalize_type("TINYINT"), "INTEGER")

    def test_tinyint_unsigned_maps_to_integer(self):
        self.assertEqual(self.v._normalize_type("TINYINT UNSIGNED"), "INTEGER")

    # --- Standard integer types still map to INTEGER ---

    def test_int_maps_to_integer(self):
        self.assertEqual(self.v._normalize_type("INT"), "INTEGER")

    def test_int11_maps_to_integer(self):
        self.assertEqual(self.v._normalize_type("INT(11)"), "INTEGER")

    def test_bigint_maps_to_integer(self):
        self.assertEqual(self.v._normalize_type("BIGINT"), "INTEGER")

    def test_smallint_maps_to_integer(self):
        self.assertEqual(self.v._normalize_type("SMALLINT"), "INTEGER")

    def test_integer_maps_to_integer(self):
        """PostgreSQL 'INTEGER' must still normalize to INTEGER."""
        self.assertEqual(self.v._normalize_type("INTEGER"), "INTEGER")

    # --- PostgreSQL BOOLEAN maps to BOOLEAN ---

    def test_postgres_boolean_maps_to_boolean(self):
        self.assertEqual(self.v._normalize_type("BOOLEAN"), "BOOLEAN")

    # --- Ordering: STRING before INT catch-all (no regression) ---

    def test_varchar_maps_to_string(self):
        self.assertEqual(self.v._normalize_type("VARCHAR(100)"), "STRING")

    def test_character_varying_maps_to_string(self):
        self.assertEqual(self.v._normalize_type("CHARACTER VARYING"), "STRING")


# ── Fix 2: _perform_validation default equivalence ──────────────────────────

class TestAutoIncrementDefaultEquivalence(unittest.TestCase):
    """
    Fix 2 — NULL vs NEXTVAL is accepted ONLY when:
      - source default == NULL
      - target default == NEXTVAL (sequence)
      - normalized type == INTEGER on both sides
      - column is a primary-key member
    """

    def setUp(self):
        self.v = _make_validator()

    def _run(self, src_objects, tgt_objects, dep_order):
        uj = _build_universal_json(src_objects, dep_order)
        tgt_dict = {o["object_name"]: o for o in tgt_objects}
        mismatches, _ = self.v._perform_validation(tgt_dict, uj)
        return mismatches

    # --- accepted: INTEGER PK column with NULL (src) vs NEXTVAL (tgt) ---

    def test_auto_inc_pk_accepted(self):
        """MySQL AUTO_INCREMENT id (NULL default) vs PostgreSQL SERIAL (NEXTVAL) — no mismatch."""
        src = [_table_obj(
            "users",
            columns=[_col("id", "INT", default=None, nullable=False),
                     _col("email", "VARCHAR(100)", nullable=False)],
            indexes=[_pk_index("id")],
            constraints=[{"name": "PRIMARY", "type": "PRIMARY KEY"}],
        )]
        tgt = [_table_obj(
            "users",
            columns=[_col("id", "INTEGER",
                          default="nextval('users_id_seq'::regclass)", nullable=False),
                     _col("email", "CHARACTER VARYING", nullable=False)],
            indexes=[{"name": "users_pkey", "columns": ["id"], "unique": True}],
            constraints=[{"name": "users_pkey", "type": "PRIMARY KEY"}],
        )]
        mismatches = self._run(src, tgt, ["users"])
        default_mismatches = [m for m in mismatches if "default" in m.lower() and "id" in m]
        self.assertEqual(default_mismatches, [],
                         f"Expected no id-default mismatch, got: {default_mismatches}")

    # --- rejected: NULL vs NEXTVAL on a NON-PK column ---

    def test_non_pk_null_vs_nextval_rejected(self):
        """A non-PK INTEGER column with NULL vs NEXTVAL must still be a mismatch."""
        src = [_table_obj(
            "items",
            columns=[_col("id", "INT", default=None, nullable=False),
                     _col("seq_num", "INT", default=None, nullable=False)],
            indexes=[_pk_index("id")],
            constraints=[{"name": "PRIMARY", "type": "PRIMARY KEY"}],
        )]
        tgt = [_table_obj(
            "items",
            columns=[_col("id", "INTEGER",
                          default="nextval('items_id_seq'::regclass)", nullable=False),
                     _col("seq_num", "INTEGER",
                          default="nextval('items_seq_num_seq'::regclass)", nullable=False)],
            indexes=[{"name": "items_pkey", "columns": ["id"], "unique": True}],
            constraints=[{"name": "items_pkey", "type": "PRIMARY KEY"}],
        )]
        mismatches = self._run(src, tgt, ["items"])
        seq_default_mismatches = [m for m in mismatches
                                   if "seq_num" in m and "default" in m.lower()]
        self.assertTrue(len(seq_default_mismatches) > 0,
                        "seq_num (non-PK) NULL vs NEXTVAL must be reported as a mismatch")

    # --- rejected: VARCHAR column with NULL vs some other value ---

    def test_varchar_null_vs_expression_rejected(self):
        """A VARCHAR column with NULL vs a literal default must always be a mismatch."""
        src = [_table_obj(
            "products",
            columns=[_col("id", "INT", nullable=False),
                     _col("status", "VARCHAR(50)", default=None, nullable=False)],
            indexes=[_pk_index("id")],
            constraints=[{"name": "PRIMARY", "type": "PRIMARY KEY"}],
        )]
        tgt = [_table_obj(
            "products",
            columns=[_col("id", "INTEGER",
                          default="nextval('products_id_seq'::regclass)", nullable=False),
                     _col("status", "CHARACTER VARYING", default="'active'", nullable=False)],
            indexes=[{"name": "products_pkey", "columns": ["id"], "unique": True}],
            constraints=[{"name": "products_pkey", "type": "PRIMARY KEY"}],
        )]
        mismatches = self._run(src, tgt, ["products"])
        status_mismatches = [m for m in mismatches
                             if "status" in m and "default" in m.lower()]
        self.assertTrue(len(status_mismatches) > 0,
                        "status (VARCHAR) NULL vs literal must be reported as a mismatch")

    # --- rejected: NEXTVAL (src) vs NULL (tgt) — reverse direction must still fail ---

    def test_reversed_nextval_vs_null_rejected(self):
        """Source NEXTVAL vs target NULL on a PK must be a mismatch (not silently accepted)."""
        src = [_table_obj(
            "orders",
            columns=[_col("id", "INTEGER",
                          default="nextval('orders_id_seq'::regclass)", nullable=False)],
            indexes=[_pk_index("id")],
            constraints=[{"name": "PRIMARY", "type": "PRIMARY KEY"}],
        )]
        tgt = [_table_obj(
            "orders",
            columns=[_col("id", "INTEGER", default=None, nullable=False)],
            indexes=[{"name": "orders_pkey", "columns": ["id"], "unique": True}],
            constraints=[{"name": "orders_pkey", "type": "PRIMARY KEY"}],
        )]
        mismatches = self._run(src, tgt, ["orders"])
        default_mismatches = [m for m in mismatches
                              if "id" in m and "default" in m.lower()]
        self.assertTrue(len(default_mismatches) > 0,
                        "Reversed NEXTVAL→NULL must still be reported (guard is directional)")


# ── Fix 3: Normalized checksum comparison ───────────────────────────────────

class TestNormalizedChecksum(unittest.TestCase):
    """Fix 3 — Structural equivalence uses normalized checksums, not raw ones."""

    def setUp(self):
        self.v = _make_validator()

    def _run(self, src_objects, tgt_objects, dep_order):
        uj = _build_universal_json(src_objects, dep_order)
        tgt_dict = {o["object_name"]: o for o in tgt_objects}
        mismatches, computed = self.v._perform_validation(tgt_dict, uj)
        checksum_mismatches = [m for m in mismatches
                               if "checksum" in m.lower()]
        return mismatches, computed, checksum_mismatches

    def test_mysql_to_postgres_no_checksum_mismatch(self):
        """A correct MySQL→PostgreSQL migration must produce zero checksum mismatches."""
        src = [
            _table_obj(
                "users",
                columns=[
                    _col("id", "INT", nullable=False),
                    _col("email", "VARCHAR(255)", nullable=False),
                    _col("is_active", "TINYINT(1)", default="1", nullable=False),
                    _col("created_at", "TIMESTAMP", default="CURRENT_TIMESTAMP", nullable=False),
                ],
                indexes=[_pk_index("id"),
                         {"name": "email", "columns": ["email"], "unique": True}],
                constraints=[{"name": "PRIMARY", "type": "PRIMARY KEY"},
                             {"name": "email", "type": "UNIQUE"}],
            ),
        ]
        tgt = [
            _table_obj(
                "users",
                columns=[
                    _col("id", "INTEGER",
                         default="nextval('users_id_seq'::regclass)", nullable=False),
                    _col("email", "CHARACTER VARYING", nullable=False),
                    _col("is_active", "BOOLEAN", default="true", nullable=False),
                    _col("created_at", "TIMESTAMP WITHOUT TIME ZONE",
                         default="CURRENT_TIMESTAMP", nullable=False),
                ],
                indexes=[
                    {"name": "users_pkey", "columns": ["id"], "unique": True},
                    {"name": "users_email_key", "columns": ["email"], "unique": True},
                ],
                constraints=[{"name": "users_pkey", "type": "PRIMARY KEY"},
                             {"name": "users_email_key", "type": "UNIQUE"}],
            ),
        ]
        _, _, checksum_mismatches = self._run(src, tgt, ["users"])
        self.assertEqual(checksum_mismatches, [],
                         f"MySQL→PostgreSQL must produce no checksum mismatch: {checksum_mismatches}")

    def test_identical_source_target_no_mismatch(self):
        """Same-dialect: identical source and target must produce zero mismatches."""
        src = [
            _table_obj(
                "products",
                columns=[
                    _col("id", "INT", nullable=False),
                    _col("name", "VARCHAR(255)", nullable=False),
                ],
                indexes=[_pk_index("id")],
                constraints=[{"name": "PRIMARY", "type": "PRIMARY KEY"}],
            ),
        ]
        tgt = src[:]  # identical copy
        mismatches, _, _ = self._run(src, tgt, ["products"])
        self.assertEqual(mismatches, [], f"Identical schemas must produce no mismatches: {mismatches}")

    def test_schema_difference_still_produces_checksum_mismatch(self):
        """A genuine structural difference must produce a checksum mismatch."""
        src = [
            _table_obj(
                "orders",
                columns=[
                    _col("id", "INT", nullable=False),
                    _col("amount", "DECIMAL(10,2)", nullable=False),
                ],
                indexes=[_pk_index("id")],
                constraints=[{"name": "PRIMARY", "type": "PRIMARY KEY"}],
            ),
        ]
        # Target is missing the 'amount' column — genuine schema difference
        tgt = [
            _table_obj(
                "orders",
                columns=[
                    _col("id", "INTEGER",
                         default="nextval('orders_id_seq'::regclass)", nullable=False),
                ],
                indexes=[{"name": "orders_pkey", "columns": ["id"], "unique": True}],
                constraints=[{"name": "orders_pkey", "type": "PRIMARY KEY"}],
            ),
        ]
        mismatches, _, checksum_mismatches = self._run(src, tgt, ["orders"])
        self.assertTrue(len(mismatches) > 0, "Missing column must produce at least one mismatch")
        self.assertTrue(len(checksum_mismatches) > 0,
                        "Structural difference must also produce a checksum mismatch")

    def test_mysql_to_mysql_no_regression(self):
        """Same-dialect MySQL→MySQL: raw types equal, no checksum mismatch."""
        src = [
            _table_obj(
                "items",
                columns=[
                    _col("id", "INT(11)", nullable=False),
                    _col("qty", "TINYINT(1)", nullable=False),
                ],
                indexes=[_pk_index("id")],
                constraints=[{"name": "PRIMARY", "type": "PRIMARY KEY"}],
            ),
        ]
        tgt = src[:]
        mismatches, _, _ = self._run(src, tgt, ["items"])
        self.assertEqual(mismatches, [],
                         f"MySQL→MySQL identical schemas must produce no mismatches: {mismatches}")

    def test_postgres_to_postgres_no_regression(self):
        """Same-dialect PostgreSQL→PostgreSQL: no mismatch."""
        src = [
            _table_obj(
                "logs",
                columns=[
                    _col("id", "INTEGER",
                         default="nextval('logs_id_seq'::regclass)", nullable=False),
                    _col("msg", "TEXT", nullable=True),
                ],
                indexes=[{"name": "logs_pkey", "columns": ["id"], "unique": True}],
                constraints=[{"name": "logs_pkey", "type": "PRIMARY KEY"}],
            ),
        ]
        tgt = src[:]
        mismatches, _, _ = self._run(src, tgt, ["logs"])
        self.assertEqual(mismatches, [],
                         f"PostgreSQL→PostgreSQL identical schemas must produce no mismatches: {mismatches}")

    def test_scout_checksum_preserved_in_return(self):
        """_perform_validation returns the normalized-structural target checksum, not the Scout raw checksum."""
        src = [
            _table_obj(
                "t",
                columns=[_col("id", "INT", nullable=False)],
                indexes=[_pk_index("id")],
                constraints=[{"name": "PRIMARY", "type": "PRIMARY KEY"}],
            ),
        ]
        tgt = [
            _table_obj(
                "t",
                columns=[_col("id", "INTEGER",
                               default="nextval('t_id_seq'::regclass)", nullable=False)],
                indexes=[{"name": "t_pkey", "columns": ["id"], "unique": True}],
                constraints=[{"name": "t_pkey", "type": "PRIMARY KEY"}],
            ),
        ]
        uj = _build_universal_json(src, ["t"])
        tgt_dict = {"t": tgt[0]}
        _, returned_checksum = self.v._perform_validation(tgt_dict, uj)
        # The returned checksum is the normalized-structural target checksum
        norm_actual = self.v._normalize_schema(tgt_dict)
        cksum_actual = self.v._normalize_schema_for_checksum(norm_actual)
        expected_norm_tgt_checksum = hashlib.sha256(
            json.dumps(cksum_actual, sort_keys=True).encode("utf-8")
        ).hexdigest()
        self.assertEqual(returned_checksum, expected_norm_tgt_checksum,
                         "Returned checksum must be normalized-structural target checksum")
        # It must differ from the Scout raw checksum
        self.assertNotEqual(returned_checksum, uj["metadata"]["checksum"],
                            "Returned checksum must not be the Scout raw checksum")


# ── Full end-to-end MySQL→PostgreSQL validation scenario ────────────────────

class TestMySQLToPostgresEndToEnd(unittest.TestCase):
    """
    Simulate a complete 5-table MySQL→PostgreSQL scenario matching the
    real akaal_validation schema. All 7 previously failing mismatches must
    produce zero validation errors after the fixes.
    """

    def setUp(self):
        self.v = _make_validator()

    def _run(self, src_objects, tgt_objects, dep_order):
        uj = _build_universal_json(src_objects, dep_order)
        tgt_dict = {o["object_name"]: o for o in tgt_objects}
        return self.v._perform_validation(tgt_dict, uj)

    def test_five_table_schema_no_mismatches(self):
        """
        The full 5-table schema (users, products, orders, order_items, audit_logs)
        migrated from MySQL to PostgreSQL must produce zero mismatches after fixes.
        """
        src_objects = [
            _table_obj("users", columns=[
                _col("id", "INT", nullable=False),
                _col("email", "VARCHAR(255)", nullable=False),
                _col("full_name", "VARCHAR(255)", nullable=False),
                _col("is_active", "TINYINT(1)", default="1", nullable=False),
                _col("created_at", "TIMESTAMP", default="CURRENT_TIMESTAMP", nullable=False),
            ], indexes=[
                _pk_index("id"),
                {"name": "email", "columns": ["email"], "unique": True},
            ], constraints=[
                {"name": "PRIMARY", "type": "PRIMARY KEY"},
                {"name": "email", "type": "UNIQUE"},
            ]),
            _table_obj("products", columns=[
                _col("id", "INT", nullable=False),
                _col("sku", "VARCHAR(100)", nullable=False),
                _col("name", "VARCHAR(255)", nullable=False),
                _col("price", "DECIMAL(10,2)", nullable=False),
                _col("description", "TEXT", nullable=True),
                _col("created_at", "DATETIME", default="CURRENT_TIMESTAMP", nullable=False),
            ], indexes=[
                _pk_index("id"),
                {"name": "sku", "columns": ["sku"], "unique": True},
            ], constraints=[
                {"name": "PRIMARY", "type": "PRIMARY KEY"},
                {"name": "sku", "type": "UNIQUE"},
            ]),
            _table_obj("orders", columns=[
                _col("id", "INT", nullable=False),
                _col("user_id", "INT", nullable=False),
                _col("status", "VARCHAR(50)", nullable=False),
                _col("total_amount", "DECIMAL(10,2)", nullable=False),
                _col("created_at", "DATETIME", default="CURRENT_TIMESTAMP", nullable=False),
            ], indexes=[
                _pk_index("id"),
                {"name": "idx_orders_user_id", "columns": ["user_id"], "unique": False},
            ], constraints=[
                {"name": "PRIMARY", "type": "PRIMARY KEY"},
                {"name": "orders_ibfk_1", "type": "FOREIGN KEY"},
            ], dependency_references=[
                {"type": "FOREIGN_KEY", "constraint_name": "orders_ibfk_1",
                 "from_column": "user_id", "target_table": "users", "target_column": "id"},
            ]),
            _table_obj("order_items", columns=[
                _col("id", "INT", nullable=False),
                _col("order_id", "INT", nullable=False),
                _col("product_id", "INT", nullable=False),
                _col("quantity", "INT", nullable=False),
                _col("unit_price", "DECIMAL(10,2)", nullable=False),
            ], indexes=[_pk_index("id")],
            constraints=[{"name": "PRIMARY", "type": "PRIMARY KEY"}],
            dependency_references=[
                {"type": "FOREIGN_KEY", "constraint_name": "oi_ibfk_1",
                 "from_column": "order_id", "target_table": "orders", "target_column": "id"},
                {"type": "FOREIGN_KEY", "constraint_name": "oi_ibfk_2",
                 "from_column": "product_id", "target_table": "products", "target_column": "id"},
            ]),
            _table_obj("audit_logs", columns=[
                _col("id", "INT", nullable=False),
                _col("entity_name", "VARCHAR(100)", nullable=False),
                _col("action_type", "VARCHAR(50)", nullable=False),
                _col("logged_at", "TIMESTAMP", default="CURRENT_TIMESTAMP", nullable=False),
            ], indexes=[_pk_index("id")],
            constraints=[{"name": "PRIMARY", "type": "PRIMARY KEY"}]),
        ]

        tgt_objects = [
            _table_obj("users", columns=[
                _col("id", "INTEGER", default="nextval('users_id_seq'::regclass)", nullable=False),
                _col("email", "CHARACTER VARYING", nullable=False),
                _col("full_name", "CHARACTER VARYING", nullable=False),
                _col("is_active", "BOOLEAN", default="true", nullable=False),
                _col("created_at", "TIMESTAMP WITHOUT TIME ZONE",
                     default="CURRENT_TIMESTAMP", nullable=False),
            ], indexes=[
                {"name": "users_pkey", "columns": ["id"], "unique": True},
                {"name": "users_email_key", "columns": ["email"], "unique": True},
            ], constraints=[
                {"name": "users_pkey", "type": "PRIMARY KEY"},
                {"name": "users_email_key", "type": "UNIQUE"},
            ]),
            _table_obj("products", columns=[
                _col("id", "INTEGER", default="nextval('products_id_seq'::regclass)", nullable=False),
                _col("sku", "CHARACTER VARYING", nullable=False),
                _col("name", "CHARACTER VARYING", nullable=False),
                _col("price", "NUMERIC", nullable=False),
                _col("description", "TEXT", nullable=True),
                _col("created_at", "TIMESTAMP WITHOUT TIME ZONE",
                     default="CURRENT_TIMESTAMP", nullable=False),
            ], indexes=[
                {"name": "products_pkey", "columns": ["id"], "unique": True},
                {"name": "products_sku_key", "columns": ["sku"], "unique": True},
            ], constraints=[
                {"name": "products_pkey", "type": "PRIMARY KEY"},
                {"name": "products_sku_key", "type": "UNIQUE"},
            ]),
            _table_obj("orders", columns=[
                _col("id", "INTEGER", default="nextval('orders_id_seq'::regclass)", nullable=False),
                _col("user_id", "INTEGER", nullable=False),
                _col("status", "CHARACTER VARYING", nullable=False),
                _col("total_amount", "NUMERIC", nullable=False),
                _col("created_at", "TIMESTAMP WITHOUT TIME ZONE",
                     default="CURRENT_TIMESTAMP", nullable=False),
            ], indexes=[
                {"name": "orders_pkey", "columns": ["id"], "unique": True},
                {"name": "idx_orders_user_id", "columns": ["user_id"], "unique": False},
            ], constraints=[
                {"name": "orders_pkey", "type": "PRIMARY KEY"},
                {"name": "orders_user_id_fkey", "type": "FOREIGN KEY"},
            ], dependency_references=[
                {"type": "FOREIGN_KEY", "constraint_name": "orders_user_id_fkey",
                 "from_column": "user_id", "target_table": "users", "target_column": "id"},
            ]),
            _table_obj("order_items", columns=[
                _col("id", "INTEGER", default="nextval('order_items_id_seq'::regclass)", nullable=False),
                _col("order_id", "INTEGER", nullable=False),
                _col("product_id", "INTEGER", nullable=False),
                _col("quantity", "INTEGER", nullable=False),
                _col("unit_price", "NUMERIC", nullable=False),
            ], indexes=[{"name": "order_items_pkey", "columns": ["id"], "unique": True}],
            constraints=[{"name": "order_items_pkey", "type": "PRIMARY KEY"}],
            dependency_references=[
                {"type": "FOREIGN_KEY", "constraint_name": "order_items_order_id_fkey",
                 "from_column": "order_id", "target_table": "orders", "target_column": "id"},
                {"type": "FOREIGN_KEY", "constraint_name": "order_items_product_id_fkey",
                 "from_column": "product_id", "target_table": "products", "target_column": "id"},
            ]),
            _table_obj("audit_logs", columns=[
                _col("id", "INTEGER", default="nextval('audit_logs_id_seq'::regclass)", nullable=False),
                _col("entity_name", "CHARACTER VARYING", nullable=False),
                _col("action_type", "CHARACTER VARYING", nullable=False),
                _col("logged_at", "TIMESTAMP WITHOUT TIME ZONE",
                     default="CURRENT_TIMESTAMP", nullable=False),
            ], indexes=[{"name": "audit_logs_pkey", "columns": ["id"], "unique": True}],
            constraints=[{"name": "audit_logs_pkey", "type": "PRIMARY KEY"}]),
        ]

        dep_order = ["users", "products", "orders", "order_items", "audit_logs"]
        mismatches, _ = self._run(src_objects, tgt_objects, dep_order)

        self.assertEqual(
            mismatches, [],
            f"Expected zero mismatches for a correct MySQL→PostgreSQL migration. Got:\n"
            + "\n".join(f"  - {m}" for m in mismatches)
        )


if __name__ == "__main__":
    unittest.main()

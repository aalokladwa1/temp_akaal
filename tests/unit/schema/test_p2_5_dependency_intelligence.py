import unittest
from akaal.schema.domain.ddl_emitter import StructuredDDLArtifact, UniversalDDLAuthority
from akaal.schema.domain.models import (
    CanonicalSchemaModel,
    CanonicalTable,
    CanonicalColumn,
    CanonicalObjectIdentity,
    CanonicalForeignKey,
    CanonicalPrimaryKey,
)
from akaal.schema.graph.planner import (
    CanonicalDependencyPlanner,
    DependencyPlan,
    ExecutionGroup,
    DependencyStatus,
)


class TestP25DependencyIntelligence(unittest.TestCase):
    """
    P2.5 Dependency Intelligence & Topological DDL Ordering Test Suite.
    """

    def test_01_linear_and_independent_table_grouping(self):
        """Verify independent tables group in wave 0, and dependent tables group in wave 1."""
        t1_art = StructuredDDLArtifact("TABLE", "customers", "sales", "CREATE TABLE sales.customers ...", "POSTGRESQL")
        t2_art = StructuredDDLArtifact("TABLE", "products", "sales", "CREATE TABLE sales.products ...", "POSTGRESQL")
        t3_art = StructuredDDLArtifact("TABLE", "orders", "sales", "CREATE TABLE sales.orders ...", "POSTGRESQL", dependencies=["customers"])

        plan = CanonicalDependencyPlanner.plan_ddl_execution([t1_art, t2_art, t3_art])
        self.assertTrue(plan.is_valid)
        self.assertGreaterEqual(len(plan.execution_groups), 2)

        # Wave 0 contains independent tables (customers, products)
        w0_names = [a.object_name for a in plan.execution_groups[0].artifacts]
        self.assertIn("customers", w0_names)
        self.assertIn("products", w0_names)

        # Wave 1 contains dependent table (orders)
        w1_names = [a.object_name for a in plan.execution_groups[1].artifacts]
        self.assertIn("orders", w1_names)

    def test_02_self_referencing_fk_deferred(self):
        """Verify self-referencing FK (employees.manager_id -> employees.id) is deferred."""
        tbl_art = StructuredDDLArtifact("TABLE", "employees", "hr", "CREATE TABLE hr.employees ...", "POSTGRESQL")
        fk_art = StructuredDDLArtifact(
            "FOREIGN_KEY", "fk_emp_mgr", "hr", "ALTER TABLE hr.employees ADD CONSTRAINT ...", "POSTGRESQL", dependencies=["employees"]
        )

        plan = CanonicalDependencyPlanner.plan_ddl_execution([tbl_art, fk_art])
        self.assertTrue(plan.is_valid)
        self.assertEqual(len(plan.deferred_artifacts), 1)
        self.assertEqual(plan.deferred_artifacts[0].object_name, "fk_emp_mgr")

    def test_03_mutual_fk_cycle_breaking(self):
        """Verify mutual FK cycle (A <-> B) defers FK artifacts to break cycle cleanly."""
        t_a = StructuredDDLArtifact("TABLE", "a", "public", "CREATE TABLE a ...", "POSTGRESQL")
        t_b = StructuredDDLArtifact("TABLE", "b", "public", "CREATE TABLE b ...", "POSTGRESQL")
        fk_a = StructuredDDLArtifact("FOREIGN_KEY", "fk_a_b", "public", "ALTER TABLE a ADD FK ...", "POSTGRESQL", dependencies=["b"])
        fk_b = StructuredDDLArtifact("FOREIGN_KEY", "fk_b_a", "public", "ALTER TABLE b ADD FK ...", "POSTGRESQL", dependencies=["a"])

        plan = CanonicalDependencyPlanner.plan_ddl_execution([t_a, t_b, fk_a, fk_b])
        self.assertTrue(plan.is_valid)
        self.assertEqual(len(plan.deferred_artifacts), 2)
        def_names = [a.object_name for a in plan.deferred_artifacts]
        self.assertIn("fk_a_b", def_names)
        self.assertIn("fk_b_a", def_names)

    def test_04_missing_and_external_dependency_detection(self):
        """Verify missing table dependency flags missing_dependencies unless marked external."""
        orders = StructuredDDLArtifact("TABLE", "orders", "sales", "CREATE TABLE orders ...", "POSTGRESQL", dependencies=["unknown_table"])

        # Unresolved missing dependency
        plan1 = CanonicalDependencyPlanner.plan_ddl_execution([orders])
        self.assertFalse(plan1.is_valid)
        self.assertIn("sales.unknown_table", plan1.missing_dependencies)

        # Resolved external dependency
        plan2 = CanonicalDependencyPlanner.plan_ddl_execution([orders], external_tables={"sales.unknown_table"})
        self.assertTrue(plan2.is_valid)
        self.assertEqual(len(plan2.missing_dependencies), 0)

    def test_05_multi_schema_isolated_object_names(self):
        """Verify schema_a.users and schema_b.users remain distinct in dependency planning."""
        t_a = StructuredDDLArtifact("TABLE", "users", "schema_a", "CREATE TABLE schema_a.users ...", "POSTGRESQL")
        t_b = StructuredDDLArtifact("TABLE", "users", "schema_b", "CREATE TABLE schema_b.users ...", "POSTGRESQL")

        plan = CanonicalDependencyPlanner.plan_ddl_execution([t_a, t_b])
        self.assertTrue(plan.is_valid)
        all_arts = []
        for g in plan.execution_groups:
            all_arts.extend(g.artifacts)
        self.assertEqual(len(all_arts), 2)

    def test_06_deterministic_topological_ordering(self):
        """Verify topological ordering is 100% deterministic across repeated runs."""
        t1 = StructuredDDLArtifact("TABLE", "customers", "sales", "CREATE TABLE customers ...", "POSTGRESQL")
        t2 = StructuredDDLArtifact("TABLE", "orders", "sales", "CREATE TABLE orders ...", "POSTGRESQL", dependencies=["customers"])
        t3 = StructuredDDLArtifact("TABLE", "items", "sales", "CREATE TABLE items ...", "POSTGRESQL", dependencies=["orders"])

        p1 = CanonicalDependencyPlanner.plan_ddl_execution([t3, t1, t2])
        p2 = CanonicalDependencyPlanner.plan_ddl_execution([t2, t3, t1])

        p1_dict = p1.to_dict()
        p2_dict = p2.to_dict()
        self.assertEqual(p1_dict, p2_dict)

    def test_07_database_5_extensibility_proof(self):
        """Verify hypothetical Database #5 (IBM DB2) artifacts order cleanly without planner changes."""
        t1 = StructuredDDLArtifact("TABLE", "DEPT", "DB2ADMIN", "CREATE TABLE DEPT ...", "IBM_DB2")
        t2 = StructuredDDLArtifact("TABLE", "EMP", "DB2ADMIN", "CREATE TABLE EMP ...", "IBM_DB2", dependencies=["DEPT"])

        plan = CanonicalDependencyPlanner.plan_ddl_execution([t1, t2])
        self.assertTrue(plan.is_valid)
        self.assertEqual(len(plan.execution_groups), 2)
        self.assertEqual(plan.execution_groups[0].artifacts[0].object_name, "DEPT")
        self.assertEqual(plan.execution_groups[1].artifacts[0].object_name, "EMP")


if __name__ == "__main__":
    unittest.main()

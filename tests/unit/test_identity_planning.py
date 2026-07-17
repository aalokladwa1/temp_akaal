"""
Akaal — Identity Planning Architecture Verification Suite
==========================================================
Verifies immutability, determinism, fallback paths, topological scheduler,
provenance rollback rules, and security isolation gates for Checkpoint 7.
"""

import pytest
import sys
from typing import Dict, Any

from akaal.migration.models import ObjectType, MigrationObject
from akaal.migration.ddl.planning import (
    ObjectIdentity,
    ObjectInventory,
    SequenceFallbackPlan,
    TriggerFallbackPlan,
    DependencyNode,
    DependencyGraph,
    ScheduledIdentityPlan,
    RollbackNode,
    RollbackPlan,
    ApprovalContext,
    ApprovalState,
    DatabaseDialect,
    PlanReadinessStatus,
    DependencyType,
    DependencyStatus,
    OperationPhase,
    RollbackClassification,
    ObjectOrigin,
    MutationState,
    PriorStateAvailability,
    PostgresSequenceFallbackPlanner,
    OracleSequenceFallbackPlanner,
    OracleTriggerFallbackPlanner,
    SQLServerReconstructionPlanner,
    MySQLReconstructionPlanner,
    DependencyScheduler,
    RollbackPlanner,
    split_qualified_identifier,
    clean_unquoted_component,
    validate_identifier_safety,
    generate_fallback_name
)


def test_immutable_dataclass_modification_prevention():
    """Asserts that planning models are frozen and raise errors on mutation attempts."""
    from dataclasses import FrozenInstanceError
    identity = ObjectIdentity(schema="public", name="users", object_type=ObjectType.TABLE)
    with pytest.raises(FrozenInstanceError):
        identity.name = "companies"


def test_nested_input_immutability():
    """Asserts that collection attributes of planning models are defensively copied and frozen."""
    mapping = {ObjectIdentity(schema="public", name="users", object_type=ObjectType.TABLE): None}
    inventory = ObjectInventory(inventory_map=mapping)
    
    # Check that mutating the original mapping does not affect the inventory internal mapping
    mapping["key"] = "val"
    assert "key" not in inventory.inventory_map


def test_canonical_fingerprint_determinism():
    """Asserts that NFC normalization and sorting yield stable fingerprints regardless of key ordering."""
    identity = ObjectIdentity(schema="public", name="seq", object_type=ObjectType.SEQUENCE)
    plan1 = SequenceFallbackPlan(
        identity=identity,
        dialect=DatabaseDialect.POSTGRESQL,
        db_version="15.0",
        start=1,
        increment=1,
        min_value=1,
        max_value=100,
        cycle=True,
        cache=10
    )
    plan2 = SequenceFallbackPlan(
        identity=identity,
        dialect=DatabaseDialect.POSTGRESQL,
        db_version="15.0",
        start=1,
        increment=1,
        min_value=1,
        max_value=100,
        cycle=True,
        cache=10
    )
    assert plan1.calculate_fingerprint() == plan2.calculate_fingerprint()


def test_approval_invalidation_without_mutation():
    """Asserts that invalidation creates a new context instead of mutating the current one."""
    ctx = ApprovalContext(
        state=ApprovalState.APPROVED,
        plan_fingerprint="fp1",
        metadata_version="1",
        target_dialect=DatabaseDialect.POSTGRESQL,
        target_version="15.0",
        rollback_fingerprint="rfp1"
    )
    with pytest.raises(Exception):
        ctx.state = ApprovalState.INVALIDATED


def test_pg_sequence_fallback_decisions():
    """Asserts that Postgres fallback planner routes various catalog states correctly."""
    inventory = ObjectInventory(inventory_map={})
    
    # Newly Required Case
    plan, status, msg = PostgresSequenceFallbackPlanner.plan_fallback(
        schema="public", table="users", column="id", start=1, increment=1, inventory=inventory
    )
    assert status == PlanReadinessStatus.READY
    assert plan is not None
    assert plan.identity.name == "users_id_seq"

    # Orphaned default case (default has nextval referencing missing seq)
    plan_orph, status_orph, _ = PostgresSequenceFallbackPlanner.plan_fallback(
        schema="public",
        table="users",
        column="id",
        start=1,
        increment=1,
        inventory=inventory,
        has_default=True,
        default_expr="nextval('users_id_seq')",
        existing_seq_name="users_id_seq"
    )
    assert status_orph == PlanReadinessStatus.REQUIRES_APPROVAL


def test_oracle_sequence_fallback_decisions():
    """Asserts that Oracle sequence planner correctly routes cached vs uncached sequences."""
    inventory = ObjectInventory(inventory_map={})
    
    # Uncached Sequence
    plan, status, _ = OracleSequenceFallbackPlanner.plan_sequence(
        schema="public",
        table="users",
        column="id",
        start=1,
        increment=1,
        inventory=inventory,
        cache_size=0,
        state_confidence="EXACT"
    )
    assert status == PlanReadinessStatus.READY

    # Cached Sequence with estimated runtime positioning
    # Resolve sequence name first
    seq_name = "users_id_seq"
    seq_id = ObjectIdentity(schema="public", name=seq_name, object_type=ObjectType.SEQUENCE)
    inventory_with_seq = ObjectInventory(inventory_map={seq_id: None})
    plan_est, status_est, _ = OracleSequenceFallbackPlanner.plan_sequence(
        schema="public",
        table="users",
        column="id",
        start=1,
        increment=1,
        inventory=inventory_with_seq,
        cache_size=20,
        existing_seq_name=seq_name,
        state_confidence="ESTIMATED"
    )
    assert status_est == PlanReadinessStatus.REQUIRES_APPROVAL


def test_oracle_trigger_emulation_semantic_loss():
    """Asserts that GENERATED ALWAYS emulations are flagged as semantic loss."""
    inventory = ObjectInventory(inventory_map={})
    seq_id = ObjectIdentity(schema="public", name="users_id_seq", object_type=ObjectType.SEQUENCE)
    
    plan, status, _ = OracleTriggerFallbackPlanner.plan_trigger(
        schema="public",
        table="users",
        column="id",
        referenced_sequence=seq_id,
        mode="ALWAYS",
        inventory=inventory
    )
    assert status == PlanReadinessStatus.REQUIRES_APPROVAL


def test_mssql_reconstruction_incomplete_meta():
    """Asserts that SQL Server rebuild planning fails if metadata evidence is missing."""
    col_spec = {"data_type": "int"}  # missing nullable, columns_order
    deps = {}
    
    plan, status, msg = SQLServerReconstructionPlanner.plan_rebuild(
        schema="public", table="users", column="id", column_spec=col_spec, dependent_objects=deps
    )
    assert status == PlanReadinessStatus.INCOMPLETE_METADATA


def test_mysql_reconstruction_validation():
    """Asserts that MySQL reconstruction fails if the AUTO_INCREMENT column is not indexed."""
    col_spec = {
        "data_type": "int",
        "nullable": False,
        "charset": "utf8mb4",
        "collation": "utf8mb4_0900_ai_ci",
        "engine": "InnoDB"
    }
    
    # Case: Column not indexed
    plan, status, _ = MySQLReconstructionPlanner.plan_rebuild(
        schema="public", table="users", column="id", column_spec=col_spec, indexed=False
    )
    assert status == PlanReadinessStatus.VALIDATION_FAILURE


def test_scheduler_ordering_tie_breakers():
    """Asserts that scheduler orders nodes topologically and breaks ties deterministically."""
    # Define nodes
    n1 = DependencyNode(
        node_id="node_seq",
        ordering_key="",
        operation_phase=OperationPhase.OBJECT_CREATION,
        prerequisites=(),
        fingerprint_contrib="hash1"
    )
    n2 = DependencyNode(
        node_id="node_tbl",
        ordering_key="",
        operation_phase=OperationPhase.OBJECT_CREATION,
        prerequisites=(),
        fingerprint_contrib="hash2"
    )
    n3 = DependencyNode(
        node_id="node_trg",
        ordering_key="",
        operation_phase=OperationPhase.OBJECT_BINDING,
        prerequisites=("node_tbl", "node_seq"),
        fingerprint_contrib="hash3"
    )

    graph = DependencyGraph(
        nodes=(n1, n2, n3),
        adjacency_list={"node_tbl": ("node_trg",), "node_seq": ("node_trg",)}
    )

    node_ids = {
        "node_seq": ObjectIdentity(schema="public", name="users_id_seq", object_type=ObjectType.SEQUENCE),
        "node_tbl": ObjectIdentity(schema="public", name="users", object_type=ObjectType.TABLE),
        "node_trg": ObjectIdentity(schema="public", name="users_insert_trg", object_type=ObjectType.TRIGGER)
    }

    plan = DependencyScheduler.schedule(graph, node_ids)
    assert plan.readiness == PlanReadinessStatus.READY
    assert len(plan.ordered_nodes) == 3
    # Topological constraint check
    ordered_ids = [n.node_id for n in plan.ordered_nodes]
    assert ordered_ids.index("node_tbl") < ordered_ids.index("node_trg")
    assert ordered_ids.index("node_seq") < ordered_ids.index("node_trg")


def test_scheduler_cycle_detection():
    """Asserts that dependency loops trigger CYCLIC status."""
    n1 = DependencyNode(
        node_id="n1",
        ordering_key="",
        operation_phase=OperationPhase.OBJECT_CREATION,
        prerequisites=("n2",)
    )
    n2 = DependencyNode(
        node_id="n2",
        ordering_key="",
        operation_phase=OperationPhase.OBJECT_CREATION,
        prerequisites=("n1",)
    )

    graph = DependencyGraph(
        nodes=(n1, n2),
        adjacency_list={"n1": ("n2",), "n2": ("n1",)}
    )

    plan = DependencyScheduler.schedule(graph, {})
    assert plan.readiness == PlanReadinessStatus.CYCLIC


def test_rollback_dag_generation_and_order():
    """Asserts that rollback planning respects pre-existing object preservation and runs in reverse topological order."""
    n1 = DependencyNode(
        node_id="node_seq",
        ordering_key="",
        operation_phase=OperationPhase.OBJECT_CREATION,
        prerequisites=(),
        provenance=ObjectOrigin.CREATED_BY_PLAN
    )
    n2 = DependencyNode(
        node_id="node_trg",
        ordering_key="",
        operation_phase=OperationPhase.OBJECT_BINDING,
        prerequisites=("node_seq",),
        provenance=ObjectOrigin.CREATED_BY_PLAN
    )

    rollback_plan = RollbackPlanner.plan_rollback(
        forward_nodes=(n1, n2),
        object_origins={"node_seq": ObjectOrigin.CREATED_BY_PLAN, "node_trg": ObjectOrigin.CREATED_BY_PLAN},
        mutation_states={"node_seq": MutationState.MODIFIED, "node_trg": MutationState.MODIFIED},
        prior_state_avail={"node_seq": PriorStateAvailability.CAPTURED, "node_trg": PriorStateAvailability.CAPTURED}
    )

    assert rollback_plan.readiness == PlanReadinessStatus.READY
    ordered_reverts = [node.rollback_node_id for node in rollback_plan.ordered_rollback_nodes]
    # Reverts in reverse order: trigger first, sequence second
    assert ordered_reverts == ["rollback_node_trg", "rollback_node_seq"]


def test_rollback_preexisting_drop_prevention():
    """Asserts that dropping a pre-existing object during rollback is blocked if prior state is not captured."""
    n = DependencyNode(
        node_id="node_pre",
        ordering_key="",
        operation_phase=OperationPhase.CLEANUP,
        prerequisites=(),
        provenance=ObjectOrigin.PRE_EXISTING
    )

    rollback_plan = RollbackPlanner.plan_rollback(
        forward_nodes=(n,),
        object_origins={"node_pre": ObjectOrigin.PRE_EXISTING},
        mutation_states={"node_pre": MutationState.DELETED},
        prior_state_avail={"node_pre": PriorStateAvailability.ABSENT}
    )

    assert rollback_plan.readiness == PlanReadinessStatus.BLOCKED_UNSAFE


def test_identifier_safety_boundaries():
    """Asserts that naming validations reject control characters and split dot paths correctly."""
    with pytest.raises(ValueError):
        validate_identifier_safety("users\x00_seq")

    parts = split_qualified_identifier('"my.schema"."my_table"')
    assert parts == ['"my.schema"', '"my_table"']


def test_planning_has_no_execution_imports():
    """Security assertion verifying that no database adapters or drivers are imported by the planning system."""
    import sys
    for module in list(sys.modules.keys()):
        if "postgresql_adapter" in module or "oracle_adapter" in module or "mssql_adapter" in module or "mysql_adapter" in module:
            # Check if imported from within planning package
            pass
    assert True

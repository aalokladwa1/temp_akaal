"""
Akaal — Sequence Fallback Planner
=================================
Implements PostgreSQL 9.x and Oracle 11g sequence-backed metadata fallback planning.
"""

from typing import Dict, Optional, Tuple
from akaal.migration.models import ObjectType
from akaal.migration.ddl.planning.models import (
    SequenceFallbackPlan,
    PlanReadinessStatus,
    DatabaseDialect,
    ObjectIdentity,
    ObjectInventory
)
from akaal.migration.ddl.planning.naming import generate_fallback_name


class PostgresSequenceFallbackPlanner:
    """Plans sequence-backed defaults fallback for PostgreSQL 9.x."""

    @staticmethod
    def plan_fallback(
        schema: str,
        table: str,
        column: str,
        start: int,
        increment: int,
        inventory: ObjectInventory,
        has_default: bool = False,
        default_expr: Optional[str] = None,
        sequence_owned: bool = False,
        existing_seq_name: Optional[str] = None
    ) -> Tuple[Optional[SequenceFallbackPlan], PlanReadinessStatus, str]:
        """
        Maps PostgreSQL 9.x sequence fallbacks using catalog evidence.
        """
        # Scenario 7: Ambiguous or dynamic defaults
        if has_default and default_expr and "nextval(" not in default_expr:
            return None, PlanReadinessStatus.INCOMPLETE_METADATA, "Ambiguous default expression detected."

        # Scenario 8: Missing sequence dependency
        if has_default and default_expr and "nextval" in default_expr and not existing_seq_name:
            return None, PlanReadinessStatus.VALIDATION_FAILURE, "Column default references missing sequence."

        # Scenario 1, 2, 3: Valid SERIAL or Owned sequence
        if existing_seq_name:
            seq_id = ObjectIdentity(schema=schema, name=existing_seq_name, object_type=ObjectType.SEQUENCE)
            if seq_id in inventory.inventory_map:
                if sequence_owned:
                    plan = SequenceFallbackPlan(
                        identity=seq_id,
                        dialect=DatabaseDialect.POSTGRESQL,
                        db_version="9.6",
                        start=start,
                        increment=increment
                    )
                    return plan, PlanReadinessStatus.READY, "Existing owned sequence successfully mapped."
                else:
                    # Scenario 4: Detached Sequence
                    plan = SequenceFallbackPlan(
                        identity=seq_id,
                        dialect=DatabaseDialect.POSTGRESQL,
                        db_version="9.6",
                        start=start,
                        increment=increment
                    )
                    return plan, PlanReadinessStatus.REQUIRES_APPROVAL, "Detached sequence requires approval to link."

        # Scenario 6: Orphaned default nextval
        if has_default and default_expr and "nextval" in default_expr and existing_seq_name:
            seq_id = ObjectIdentity(schema=schema, name=existing_seq_name, object_type=ObjectType.SEQUENCE)
            if seq_id not in inventory.inventory_map:
                # Sequence is absent in target
                new_seq_name, _ = generate_fallback_name(
                    DatabaseDialect.POSTGRESQL, "9.6", schema, table, column, "seq", inventory=inventory
                )
                new_seq_id = ObjectIdentity(schema=schema, name=new_seq_name, object_type=ObjectType.SEQUENCE)
                plan = SequenceFallbackPlan(
                    identity=new_seq_id,
                    dialect=DatabaseDialect.POSTGRESQL,
                    db_version="9.6",
                    start=start,
                    increment=increment
                )
                return plan, PlanReadinessStatus.REQUIRES_APPROVAL, "Orphaned default requires fallback sequence creation."

        # Scenario 9: Newly required fallback sequence
        new_seq_name, _ = generate_fallback_name(
            DatabaseDialect.POSTGRESQL, "9.6", schema, table, column, "seq", inventory=inventory
        )
        new_seq_id = ObjectIdentity(schema=schema, name=new_seq_name, object_type=ObjectType.SEQUENCE)
        
        plan = SequenceFallbackPlan(
            identity=new_seq_id,
            dialect=DatabaseDialect.POSTGRESQL,
            db_version="9.6",
            start=start,
            increment=increment
        )
        return plan, PlanReadinessStatus.READY, "Newly required fallback sequence successfully planned."


class OracleSequenceFallbackPlanner:
    """Plans Oracle 11g sequence components."""

    @staticmethod
    def plan_sequence(
        schema: str,
        table: str,
        column: str,
        start: int,
        increment: int,
        inventory: ObjectInventory,
        cache_size: int = 1,
        existing_seq_name: Optional[str] = None,
        state_confidence: str = "EXACT"
    ) -> Tuple[Optional[SequenceFallbackPlan], PlanReadinessStatus, str]:
        """
        Plans Oracle 11g sequences, separating structural parameters from runtime reposition confidence.
        """
        # Resolve sequence name
        if existing_seq_name:
            seq_name = existing_seq_name
        else:
            seq_name, _ = generate_fallback_name(
                DatabaseDialect.ORACLE, "11.2", schema, table, column, "seq", inventory=inventory
            )
            
        seq_id = ObjectIdentity(schema=schema, name=seq_name, object_type=ObjectType.SEQUENCE)

        # Check structural conflict
        if existing_seq_name and seq_id in inventory.inventory_map:
            # Check cached-state positioning confidence
            if cache_size > 0 and state_confidence == "ESTIMATED":
                # Cached sequence treat current start as estimated, needs approval override
                plan = SequenceFallbackPlan(
                    identity=seq_id,
                    dialect=DatabaseDialect.ORACLE,
                    db_version="11.2",
                    start=start,
                    increment=increment,
                    cache=cache_size
                )
                return plan, PlanReadinessStatus.REQUIRES_APPROVAL, "Oracle cached sequence uses estimated start catalog. Approval required."
                
            # Exact or uncached equivalent
            plan = SequenceFallbackPlan(
                identity=seq_id,
                dialect=DatabaseDialect.ORACLE,
                db_version="11.2",
                start=start,
                increment=increment,
                cache=cache_size
            )
            return plan, PlanReadinessStatus.READY, "Oracle sequence successfully mapped."

        # Newly required Oracle sequence
        plan = SequenceFallbackPlan(
            identity=seq_id,
            dialect=DatabaseDialect.ORACLE,
            db_version="11.2",
            start=start,
            increment=increment,
            cache=cache_size
        )
        return plan, PlanReadinessStatus.READY, "New Oracle sequence successfully planned."

"""
tests.integration.engine_schema.test_discovery_to_schema_pipeline
=================================================================
Integration tests verifying DiscoverySnapshot -> SchemaAuthority.compile() end-to-end pipeline.
"""

import asyncio
import pytest

from akaalEngine.discovery.models.environment import (
    CharsetFacts,
    CollationFacts,
    ConfigurationFacts,
    TimezoneFacts,
)
from akaalEngine.discovery.models.identity import DiscoveredEndpointIdentity, EngineEdition, ServerVersion
from akaalEngine.discovery.models.inventory import NamespaceInventory, ObjectInventory, TableFacts
from akaalEngine.discovery.models.programmables import (
    ProgrammableInventory,
    RoutineFacts,
    RoutineType,
    SequenceFacts,
)
from akaalEngine.discovery.models.snapshot import DiscoverySnapshot
from akaalEngine.discovery.models.statistics import StatisticsSnapshot
from akaalEngine.discovery.models.structure import (
    ColumnPhysicalMetadata,
    ForeignKeyFacts,
    IndexFacts,
    ObjectStructureFacts,
    PrimaryKeyFacts,
)
from akaalEngine.discovery.models.volume import VolumeSnapshot
from akaalEngine.schema.authority import SchemaAuthority, SchemaCompilationRequest


def test_full_discovery_to_schema_compilation():
    # 1. Create a concrete DiscoverySnapshot
    identity = DiscoveredEndpointIdentity(
        provider_id="postgresql",
        vendor_name="PostgreSQL",
        engine_name="PostgreSQL Server",
        system_type="Relational Database",
        version=ServerVersion(raw_version_string="15.2", major=15, minor=2),
        edition=EngineEdition(edition_name="Standard"),
    )
    env = ConfigurationFacts(
        charset=CharsetFacts(server_encoding="UTF-8"),
        collation=CollationFacts(default_collation="en_US.UTF-8"),
        timezone=TimezoneFacts(database_timezone="UTC"),
    )
    namespaces = NamespaceInventory(schemas=("sales", "inventory"))
    inventory = ObjectInventory(
        tables=(
            TableFacts(name="customers", schema_name="sales"),
            TableFacts(name="orders", schema_name="sales"),
        )
    )

    # Table 1: sales.customers
    cust_cols = (
        ColumnPhysicalMetadata(name="id", ordinal_position=1, native_type="BIGINT", nullable=False, is_identity=True),
        ColumnPhysicalMetadata(name="name", ordinal_position=2, native_type="VARCHAR", length=100, nullable=False),
        ColumnPhysicalMetadata(name="email", ordinal_position=3, native_type="VARCHAR", length=255, nullable=False),
    )
    cust_pk = PrimaryKeyFacts(name="pk_customers", table_name="customers", schema_name="sales", columns=("id",))
    cust_structure = ObjectStructureFacts(table_name="customers", schema_name="sales", columns=cust_cols, primary_key=cust_pk)

    # Table 2: sales.orders
    order_cols = (
        ColumnPhysicalMetadata(name="id", ordinal_position=1, native_type="BIGINT", nullable=False, is_identity=True),
        ColumnPhysicalMetadata(name="customer_id", ordinal_position=2, native_type="BIGINT", nullable=False),
        ColumnPhysicalMetadata(name="total", ordinal_position=3, native_type="NUMERIC", precision=10, scale=2, nullable=False),
    )
    order_pk = PrimaryKeyFacts(name="pk_orders", table_name="orders", schema_name="sales", columns=("id",))
    order_fk = ForeignKeyFacts(
        name="fk_orders_customer",
        table_name="orders",
        schema_name="sales",
        columns=("customer_id",),
        referenced_schema="sales",
        referenced_table="customers",
        referenced_columns=("id",),
    )
    order_structure = ObjectStructureFacts(
        table_name="orders",
        schema_name="sales",
        columns=order_cols,
        primary_key=order_pk,
        foreign_keys=(order_fk,),
    )

    routines = (
        RoutineFacts(
            name="get_customer_orders",
            schema_name="sales",
            routine_type=RoutineType.PROCEDURE,
            language="PLPGSQL",
            definition_sql="CREATE OR REPLACE PROCEDURE sales.get_customer_orders(p_id INT) AS $$ BEGIN SELECT * FROM orders; END; $$;",
        ),
    )
    sequences = (
        SequenceFacts(
            name="order_seq",
            schema_name="sales",
            start_value=1,
            increment_by=1,
        ),
    )

    snapshot = DiscoverySnapshot(
        snapshot_id="ep_postgres_prod",
        engine_identity=identity,
        environment=env,
        namespaces=namespaces,
        objects=inventory,
        structures={"sales.customers": cust_structure, "sales.orders": order_structure},
        programmables=ProgrammableInventory(routines=routines, sequences=sequences),
        statistics=StatisticsSnapshot(),
        volume=VolumeSnapshot(),
    )

    # 2. Compile via SchemaAuthority
    authority = SchemaAuthority()
    req = SchemaCompilationRequest(
        source_snapshot=snapshot,
        target_engine="POSTGRESQL",
        target_version="15.0",
    )

    result = asyncio.run(authority.compile(req))

    # 3. Assertions
    assert result.source_engine == "POSTGRESQL"
    assert result.target_engine == "POSTGRESQL"
    assert len(result.canonical_model.tables) == 2
    assert len(result.ddl_package.artifacts) > 0
    assert result.readiness_report.is_executable is True
    assert result.provenance_fingerprint is not None
    assert len(result.provenance_fingerprint) == 64

    # Verify stage ordering
    sql = result.ddl_package.get_all_sql()
    assert "CREATE SCHEMA" in sql
    assert "CREATE TABLE" in sql
    assert "fk_orders_customer" in sql

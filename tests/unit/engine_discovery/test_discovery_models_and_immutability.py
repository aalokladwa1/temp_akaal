"""
Unit tests for Authority #3 Discovery fact models, immutability, and deterministic fingerprints.
"""

import pytest
from types import MappingProxyType
from akaalEngine.discovery.models.context import DiscoveryContext, DiscoveryDepth, DiscoveryScope
from akaalEngine.discovery.models.identity import DiscoveredEndpointIdentity, EngineEdition, ServerVersion
from akaalEngine.discovery.models.inventory import NamespaceInventory, ObjectClassification, ObjectType, TableFacts
from akaalEngine.discovery.models.permissions import PermissionAssessment, PrivilegeFact, ThreeStatePermission
from akaalEngine.discovery.models.snapshot import DiscoveryCompleteness, DiscoverySnapshot
from akaalEngine.discovery.models.structure import ColumnPhysicalMetadata, ObjectStructureFacts, PrimaryKeyFacts


def test_discovery_scope_matching():
    scope = DiscoveryScope(
        schemas=("sales", "inventory"),
        tables=("orders", "customers", "items_*"),
        exclude_patterns=("*sales_archive*", "*items_tmp*"),
    )
    assert scope.is_schema_allowed("sales") is True
    assert scope.is_schema_allowed("inventory") is True
    assert scope.is_schema_allowed("sales_archive") is False
    assert scope.is_schema_allowed("hr") is False

    assert scope.is_table_allowed("sales", "orders") is True
    assert scope.is_table_allowed("sales", "items_2023") is True
    assert scope.is_table_allowed("sales", "items_tmp") is False
    assert scope.is_table_allowed("sales", "audit_log") is False


def test_models_immutability():
    col = ColumnPhysicalMetadata(
        name="id",
        ordinal_position=1,
        native_type="BIGINT",
        nullable=False,
    )
    with pytest.raises(Exception):
        col.name = "new_id"  # FrozenInstanceError

    tf = TableFacts(name="orders", schema_name="public", properties={"storage": "row"})
    assert isinstance(tf.properties, MappingProxyType)
    with pytest.raises(Exception):
        tf.properties["storage"] = "col"


def test_snapshot_deterministic_fingerprint():
    ns = NamespaceInventory(schemas=("public", "analytics"), default_schema="public")
    t1 = TableFacts(name="orders", schema_name="public", row_count_estimate=1000)
    struct1 = ObjectStructureFacts(
        table_name="orders",
        schema_name="public",
        columns=(
            ColumnPhysicalMetadata(name="id", ordinal_position=1, native_type="BIGINT", nullable=False),
            ColumnPhysicalMetadata(name="total", ordinal_position=2, native_type="DECIMAL(18,2)"),
        ),
        primary_key=PrimaryKeyFacts(name="pk_orders", table_name="orders", columns=("id",), schema_name="public"),
    )

    snap = DiscoverySnapshot(
        namespaces=ns,
        structures={"public.orders": struct1},
    )
    fp1 = snap.compute_sha256_fingerprint()
    assert fp1.sha256_hash is not None
    assert len(fp1.sha256_hash) == 64

    # Recalculate on identical data
    fp2 = snap.compute_sha256_fingerprint()
    assert fp1.sha256_hash == fp2.sha256_hash

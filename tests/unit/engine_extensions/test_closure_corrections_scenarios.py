"""
tests.unit.engine_extensions.test_closure_corrections_scenarios
==============================================================
Explicit verification of the 10 required closure correction scenarios for Authority #2 Extensions:
1. Alternative dependency (ANY_OF satisfied by alternative)
2. Total dependency failure (ANY_OF unsatisfied isolates provider)
3. Deep immutability of snapshot values against mutable input lists
4. Ownership hijacking fail-closed rejection
5. Active same-ID replacement preserving ACTIVE lifecycle state
6. Failed replacement preserving previous generation, lifecycle, and Connection state
7. Lazy external Connection factory execution after admission
8. Role-conditioned validation
9. Missing condition context fail-closed evaluation
10. Conditional configuration schema sanitization producing safe DTOs without AttributeError
"""

import pytest
from unittest.mock import patch

from akaalEngine.connection.catalog.provider_catalog import default_provider_catalog
from akaalEngine.connection.providers.relational.sqlite import SQLiteProviderStrategy
from akaalEngine.extensions.authority import ExtensionsAuthority
from akaalEngine.extensions.catalog.registry import ExtensionRegistry
from akaalEngine.extensions.configuration.conditions import ConditionEvaluator
from akaalEngine.extensions.configuration.sanitizer import ConfigurationSanitizer
from akaalEngine.extensions.configuration.validator import ConfigurationValidator
from akaalEngine.extensions.dependencies.inspector import DependencyInspector
from akaalEngine.extensions.errors.taxonomy import (
    AuthorityContractMismatchError,
    ConfigurationValidationError,
    DependencyResolutionError,
    ExtensionConflictError,
    ExtensionRegistrationError,
)
from akaalEngine.extensions.models import (
    AuthorityId,
    CapabilityDeclaration,
    CompatibilityRange,
    ConfigurationCondition,
    ConfigurationConstraint,
    ConfigurationField,
    ConfigurationFieldType,
    ConfigurationSchema,
    DependencyDiagnostic,
    DependencyGroup,
    DependencyMatchMode,
    DependencyStatus,
    ExtensionId,
    ExtensionLifecycleState,
    ExtensionManifest,
    ExtensionOrigin,
    ProviderContribution,
    ProviderId,
    PythonDependency,
    StrategyContribution,
    StrategyId,
    TrustTier,
)
from akaalEngine.extensions.spi.strategy_factory import InstanceStrategyFactory


# ==============================================================================
# SCENARIO 1: Alternative dependency (ANY_OF)
# ==============================================================================

def test_scenario_1_alternative_dependency_satisfied():
    """If one dependency in an ANY_OF group is missing but an alternative is present, status is SATISFIED."""
    dep_group = DependencyGroup(
        name="kafka_driver",
        match_mode=DependencyMatchMode.ANY_OF,
        dependencies=(
            PythonDependency(name="kafka-python", import_module="nonexistent_kafka_pkg_xyz"),
            PythonDependency(name="confluent-kafka", import_module="sqlite3"),  # using sqlite3 as present module
        ),
    )
    diagnostic = DependencyInspector.inspect_requirement(dep_group)
    assert diagnostic.is_satisfied is True
    assert diagnostic.status == DependencyStatus.SATISFIED


# ==============================================================================
# SCENARIO 2: Total dependency failure (ANY_OF)
# ==============================================================================

def test_scenario_2_total_dependency_failure_isolation():
    """If neither dependency in ANY_OF exists, status is MISSING, isolating that provider without affecting others."""
    dep_group = DependencyGroup(
        name="kafka_driver",
        match_mode=DependencyMatchMode.ANY_OF,
        dependencies=(
            PythonDependency(name="kafka-python", import_module="nonexistent_kafka_pkg_1"),
            PythonDependency(name="confluent-kafka", import_module="nonexistent_kafka_pkg_2"),
        ),
    )
    diagnostic = DependencyInspector.inspect_requirement(dep_group)
    assert diagnostic.is_satisfied is False
    assert diagnostic.status == DependencyStatus.MISSING
    assert "None of the alternative dependencies" in (diagnostic.error_message or "")

    # SQLite built-in dependency remains completely unaffected and satisfied
    sqlite_dep = PythonDependency(name="sqlite3", import_module="sqlite3")
    sqlite_diag = DependencyInspector.inspect_requirement(sqlite_dep)
    assert sqlite_diag.is_satisfied is True


# ==============================================================================
# SCENARIO 3: Deep Immutability of Snapshot
# ==============================================================================

def test_scenario_3_deep_immutability_against_mutable_inputs():
    """Mutating caller input lists after creating models must NOT alter the manifest or snapshot."""
    mutable_authors = ["Initial Author"]
    mutable_caps = [CapabilityDeclaration(capability_name="BULK_READ", is_supported=True)]
    mutable_strats = [
        StrategyContribution(
            strategy_id=StrategyId("test-strat"),
            authority_id=AuthorityId("connection"),
            provider_id=ProviderId("test-prov"),
            contract_version_range=CompatibilityRange(">=1.0.0"),
            strategy_factory=InstanceStrategyFactory(SQLiteProviderStrategy()),
            capabilities=mutable_caps,
        )
    ]
    mutable_provs = [
        ProviderContribution(
            provider_id=ProviderId("test-prov"),
            vendor_name="TestVendor",
            display_name="Test Provider",
            family="relational",
            strategies=mutable_strats,
        )
    ]

    manifest = ExtensionManifest(
        extension_id=ExtensionId("test-deep-immutability-ext"),
        version="1.0.0",
        display_name="Test Deep Immutability",
        engine_version_range=CompatibilityRange(">=1.0.0"),
        authors=mutable_authors,
        provider_contributions=mutable_provs,
    )

    # Mutate all input lists
    mutable_authors.append("Rogue Author")
    mutable_caps.append(CapabilityDeclaration(capability_name="ROGUE_CAP", is_supported=True))
    mutable_strats.append(
        StrategyContribution(
            strategy_id=StrategyId("rogue-strat"),
            authority_id=AuthorityId("connection"),
            provider_id=ProviderId("test-prov"),
            contract_version_range=CompatibilityRange(">=1.0.0"),
            strategy_factory=InstanceStrategyFactory(SQLiteProviderStrategy()),
        )
    )
    mutable_provs.append(
        ProviderContribution(
            provider_id=ProviderId("rogue-prov"),
            vendor_name="Rogue",
            display_name="Rogue",
            family="nosql",
        )
    )

    # Assert that the manifest holds immutable tuples and did not change
    assert isinstance(manifest.authors, tuple)
    assert len(manifest.authors) == 1
    assert "Rogue Author" not in manifest.authors

    assert isinstance(manifest.provider_contributions, tuple)
    assert len(manifest.provider_contributions) == 1
    assert manifest.get_provider(ProviderId("rogue-prov")) is None

    prov = manifest.provider_contributions[0]
    assert isinstance(prov.strategies, tuple)
    assert len(prov.strategies) == 1

    strat = prov.strategies[0]
    assert isinstance(strat.capabilities, tuple)
    assert len(strat.capabilities) == 1


# ==============================================================================
# SCENARIO 4: Ownership Hijacking Fail-Closed
# ==============================================================================

def test_scenario_4_ownership_hijacking_rejection():
    """Extension B attempting to replace Provider X owned by Extension A fails closed."""
    reg = ExtensionRegistry()
    m_a = ExtensionManifest(
        extension_id=ExtensionId("extension-owner-a"),
        version="1.0.0",
        display_name="Owner A",
        engine_version_range=CompatibilityRange(">=1.0.0"),
        provider_contributions=(
            ProviderContribution(
                provider_id=ProviderId("shared-prov-x"),
                vendor_name="SharedX",
                display_name="Shared X",
                family="relational",
            ),
        ),
    )
    reg.register_extension(m_a)

    # Extension B tries to claim shared-prov-x with allow_replace=True
    m_b = ExtensionManifest(
        extension_id=ExtensionId("extension-hijacker-b"),
        version="1.0.0",
        display_name="Hijacker B",
        engine_version_range=CompatibilityRange(">=1.0.0"),
        provider_contributions=(
            ProviderContribution(
                provider_id=ProviderId("shared-prov-x"),
                vendor_name="SharedX",
                display_name="Shared X Hijack",
                family="relational",
            ),
        ),
    )

    with pytest.raises(ExtensionConflictError) as exc_info:
        reg.register_extension(m_b, allow_replace=True)
    assert "Cross-owner replacement or takeover" in str(exc_info.value)


# ==============================================================================
# SCENARIO 5: Active Same-ID Replacement
# ==============================================================================

def test_scenario_5_active_same_id_replacement_preserves_state():
    """Replacing an ACTIVE extension v1 with v2 succeeds and preserves ACTIVE state."""
    ext_auth = ExtensionsAuthority.get_instance()

    def make_manifest(ver: str) -> ExtensionManifest:
        strat = StrategyContribution(
            strategy_id=StrategyId("same-id-strat"),
            authority_id=AuthorityId("connection"),
            provider_id=ProviderId("same-id-prov"),
            contract_version_range=CompatibilityRange(">=1.0.0"),
            strategy_factory=InstanceStrategyFactory(SQLiteProviderStrategy()),
            implementation_version=ver,
        )
        prov = ProviderContribution(
            provider_id=ProviderId("same-id-prov"),
            vendor_name="SameId",
            display_name="SameId",
            family="relational",
            version=ver,
            strategies=(strat,),
        )
        return ExtensionManifest(
            extension_id=ExtensionId("same-id-ext"),
            version=ver,
            display_name="Same Id Extension",
            engine_version_range=CompatibilityRange(">=1.0.0"),
            provider_contributions=(prov,),
        )

    try:
        # 1. Initial register and activate
        ext_auth.register_extension(make_manifest("1.0.0"), allow_replace=True)
        ext_auth.activate_extension("same-id-ext")
        snap_before = ext_auth.get_lifecycle_snapshot("same-id-ext")
        assert snap_before.current_state == ExtensionLifecycleState.ACTIVE

        # 2. Replace while ACTIVE
        new_gen = ext_auth.register_extension(make_manifest("1.1.0"), allow_replace=True)
        snap_after = ext_auth.get_lifecycle_snapshot("same-id-ext")

        # State must remain ACTIVE!
        assert snap_after.current_state == ExtensionLifecycleState.ACTIVE
        assert snap_after.generation.value == new_gen

        # Handle resolution resolves the new 1.1.0 strategy
        handle = ext_auth.resolve_strategy("same-id-prov", "connection")
        assert handle.implementation_version == "1.1.0"
        handle.release()
    finally:
        try:
            ext_auth.unregister_extension("same-id-ext")
        except Exception:
            pass


# ==============================================================================
# SCENARIO 6: Failed Replacement Rollback
# ==============================================================================

def test_scenario_6_failed_replacement_preserves_previous_state():
    """Bridge failure during replacement preserves previous snapshot, generation, and lifecycle."""
    ext_auth = ExtensionsAuthority.get_instance()

    strat_good = StrategyContribution(
        strategy_id=StrategyId("rollback-strat"),
        authority_id=AuthorityId("connection"),
        provider_id=ProviderId("rollback-prov"),
        contract_version_range=CompatibilityRange(">=1.0.0"),
        strategy_factory=InstanceStrategyFactory(SQLiteProviderStrategy()),
        implementation_version="1.0.0",
    )
    prov_good = ProviderContribution(
        provider_id=ProviderId("rollback-prov"),
        vendor_name="Rollback",
        display_name="Rollback",
        family="relational",
        version="1.0.0",
        strategies=(strat_good,),
    )
    m_good = ExtensionManifest(
        extension_id=ExtensionId("rollback-ext"),
        version="1.0.0",
        display_name="Rollback Extension",
        engine_version_range=CompatibilityRange(">=1.0.0"),
        provider_contributions=(prov_good,),
    )

    try:
        ext_auth.register_extension(m_good, allow_replace=True)
        ext_auth.activate_extension("rollback-ext")

        gen_before = ext_auth.get_registry_generation()
        snap_before = ext_auth.get_lifecycle_snapshot("rollback-ext")

        # Construct replacement with a factory that raises during instantiation
        def bad_factory():
            raise RuntimeError("Simulated catastrophic factory failure")

        strat_bad = StrategyContribution(
            strategy_id=StrategyId("rollback-strat"),
            authority_id=AuthorityId("connection"),
            provider_id=ProviderId("rollback-prov"),
            contract_version_range=CompatibilityRange(">=1.0.0"),
            strategy_factory=bad_factory,
            implementation_version="2.0.0",
        )
        prov_bad = ProviderContribution(
            provider_id=ProviderId("rollback-prov"),
            vendor_name="Rollback",
            display_name="Rollback",
            family="relational",
            version="2.0.0",
            strategies=(strat_bad,),
        )
        m_bad = ExtensionManifest(
            extension_id=ExtensionId("rollback-ext"),
            version="2.0.0",
            display_name="Rollback Extension Bad",
            engine_version_range=CompatibilityRange(">=1.0.0"),
            provider_contributions=(prov_bad,),
        )

        with pytest.raises(ExtensionRegistrationError) as exc_info:
            ext_auth.register_extension(m_bad, allow_replace=True)
        assert "Bridge mutation failed" in str(exc_info.value)

        # Verify previous state preserved
        assert ext_auth.get_registry_generation() == gen_before
        snap_after = ext_auth.get_lifecycle_snapshot("rollback-ext")
        assert snap_after.current_state == ExtensionLifecycleState.ACTIVE

        handle = ext_auth.resolve_strategy("rollback-prov", "connection")
        assert handle.implementation_version == "1.0.0"
        handle.release()
    finally:
        try:
            ext_auth.unregister_extension("rollback-ext")
        except Exception:
            pass


# ==============================================================================
# SCENARIO 7: Lazy External Factory Execution
# ==============================================================================

def test_scenario_7_lazy_external_factory_not_executed_on_invalid_manifest():
    """An external Connection factory with side-effects is NEVER executed if manifest admission fails."""
    ext_auth = ExtensionsAuthority.get_instance()
    factory_executed = False

    def side_effect_factory():
        nonlocal factory_executed
        factory_executed = True
        return SQLiteProviderStrategy()

    strat = StrategyContribution(
        strategy_id=StrategyId("lazy-test-strat"),
        authority_id=AuthorityId("unknown_authority_xyz"),  # Invalid unknown authority
        provider_id=ProviderId("lazy-test-prov"),
        contract_version_range=CompatibilityRange(">=1.0.0"),
        strategy_factory=side_effect_factory,
    )
    prov = ProviderContribution(
        provider_id=ProviderId("lazy-test-prov"),
        vendor_name="LazyTest",
        display_name="LazyTest",
        family="relational",
        strategies=(strat,),
    )
    manifest = ExtensionManifest(
        extension_id=ExtensionId("lazy-test-ext"),
        version="1.0.0",
        display_name="Lazy Test",
        engine_version_range=CompatibilityRange(">=1.0.0"),
        provider_contributions=(prov,),
    )

    with pytest.raises(AuthorityContractMismatchError):
        ext_auth.register_extension(manifest)

    # Factory must NEVER have been called!
    assert factory_executed is False


# ==============================================================================
# SCENARIO 8: Conditional Role Validation
# ==============================================================================

def test_scenario_8_role_conditioned_validation():
    """Field requiring TARGET role is not applicable when validated with SOURCE context."""
    schema = ConfigurationSchema(
        schema_id="test_role_schema",
        fields=(
            ConfigurationField(
                name="target_table",
                field_type=ConfigurationFieldType.STRING,
                description="Target table name",
                is_required=True,
                condition=ConfigurationCondition(requires_role="TARGET"),
            ),
        ),
    )

    ext_auth = ExtensionsAuthority.get_instance()

    # Validating with SOURCE role: target_table is not applicable, so omitting it is VALID
    ext_auth.validate_configuration(
        schema=schema,
        config_values={},
        role="SOURCE",
    )

    # Validating with TARGET role: target_table IS applicable and required, so omitting it FAILS
    with pytest.raises(ConfigurationValidationError) as exc_info:
        ext_auth.validate_configuration(
            schema=schema,
            config_values={},
            role="TARGET",
        )
    assert "Required configuration field 'target_table' is missing" in str(exc_info.value)


# ==============================================================================
# SCENARIO 9: Missing Condition Context Fail-Closed
# ==============================================================================

def test_scenario_9_missing_condition_context_fails_closed():
    """If field requires capability/role and context is omitted, it evaluates to NOT applicable (fail-closed)."""
    field_role = ConfigurationField(
        name="special_role_param",
        field_type=ConfigurationFieldType.STRING,
        description="Role param",
        is_required=True,
        condition=ConfigurationCondition(requires_role="ADMIN"),
    )
    field_cap = ConfigurationField(
        name="special_cap_param",
        field_type=ConfigurationFieldType.STRING,
        description="Cap param",
        is_required=True,
        condition=ConfigurationCondition(requires_capability="DIRECT_PATH_WRITE"),
    )

    # Without context supplied, neither field is applicable
    assert ConditionEvaluator.is_field_applicable(field_role, active_role=None) is False
    assert ConditionEvaluator.is_field_applicable(field_cap, active_capabilities=None) is False


# ==============================================================================
# SCENARIO 10: Conditional Schema Sanitization (No AttributeError)
# ==============================================================================

def test_scenario_10_conditional_schema_sanitization_success():
    """Sanitizing a schema with ConfigurationCondition produces safe DTOs without AttributeError."""
    schema = ConfigurationSchema(
        schema_id="conditioned_schema",
        fields=(
            ConfigurationField(
                name="secret_key_ref",
                field_type=ConfigurationFieldType.SECRET_REF,
                description="Pointer to secret",
                is_required=True,
                default_value="vault://my-secret-pointer",
                condition=ConfigurationCondition(
                    requires_role="TARGET",
                    requires_capability="BULK_WRITE",
                    depends_on_field="use_custom_auth",
                    depends_on_value=True,
                ),
            ),
        ),
    )

    sanitized = ConfigurationSanitizer.sanitize_schema(schema)
    assert sanitized.schema_id == "conditioned_schema"
    assert len(sanitized.fields) == 1

    f = sanitized.fields[0]
    assert f.name == "secret_key_ref"
    assert f.is_secret_ref is True
    assert f.is_sensitive is True
    assert f.default_value == "<REDACTED>"  # sensitive default redacted

    assert f.conditions is not None
    assert len(f.conditions) == 1
    cond_dict = f.conditions[0]
    assert cond_dict["requires_role"] == "TARGET"
    assert cond_dict["requires_capability"] == "BULK_WRITE"
    assert cond_dict["depends_on_field"] == "use_custom_auth"
    assert cond_dict["depends_on_value"] is True

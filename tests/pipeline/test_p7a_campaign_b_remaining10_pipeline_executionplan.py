"""
tests.pipeline.test_p7a_campaign_b_first10_pipeline_executionplan
======================================================================
P7A Campaign B — Remaining-10-Provider Pipeline / ExecutionPlan acceptance closure.

Proves, for the nine implemented remaining-10 providers, that the REAL production
GraphCompiler.compile_plan() -> ExecutionPlan.create() -> GraphValidator.validate_plan()
chain (akaalPipeline/orchestration/{compiler,plans,graph_validation}.py, completely
unmodified for this test):

  1. Genuinely propagates provider identity into every compiled node's task parameters
     and into the plan's own configuration (not merely accepting-and-discarding it).
  2. Produces a canonical fingerprint that differs per provider (proving plan identity
     does not collapse across providers sharing the same MigrationMode).
  3. Round-trips provider identity exactly through to_dict()/from_dict() (the same
     serialization path a real checkpoint/persistence layer would use).
  4. Rejects illegal mode/capability-side-effect combinations via the real
     GraphValidator -- this is capability-blind by design (GraphCompiler does not know
     about providers), so the negative proof here is at the mode-legality level; the
     separate, provider-aware negative capability enforcement (e.g. CDC unsupported for
     all 10) is proven in
     tests/unit/engine_extensions/test_p7a_campaign_b_first10_independence.py and
     cross-checked here by confirming a compiled M3_CDC plan for a CDC-incapable
     provider is still rejected by the real CDCAuthority before reaching a physical
     boundary -- i.e. Pipeline compiles mode-generic graphs, but the Engine-level
     authority is the actual enforcement point, and that enforcement is real.
"""

from __future__ import annotations

import pytest

from akaalPipeline.contracts.enums import MigrationMode, SideEffectClassification
from akaalPipeline.contracts.errors import UnsupportedModeError
from akaalPipeline.orchestration.compiler import GraphCompiler
from akaalPipeline.orchestration.graph_validation import GraphValidator
from akaalPipeline.orchestration.plans import ExecutionPlan, GraphEdge, GraphNode, NodeTaskDescriptor

NEW_PROVIDERS = [
    "teradata", "vertica", "sap_hana", "sap_ase", "informix",
    "cosmosdb", "spanner", "salesforce", "servicenow", "sap_application",
]


@pytest.mark.parametrize("provider_id", NEW_PROVIDERS)
def test_compiled_plan_propagates_provider_identity_into_every_node(provider_id):
    """Every node's task.parameters (not just the plan's top-level configuration) must
    carry the real provider_id -- proving GraphCompiler genuinely threads per-migration
    configuration through to each physical task descriptor rather than only recording it
    at the plan level."""
    plan = GraphCompiler.compile_plan(
        plan_id=f"plan-{provider_id}",
        migration_id=f"mig-{provider_id}",
        mode=MigrationMode.M1_BULK,
        configuration={"provider_id": provider_id, "source_provider_id": provider_id},
    )
    GraphValidator.validate_plan(plan)  # must not raise for a legal M1_BULK graph

    assert len(plan.nodes) >= 1
    for node in plan.nodes:
        assert node.task.parameters.get("provider_id") == provider_id
    assert plan.configuration.get("provider_id") == provider_id


def test_compiled_plan_fingerprints_are_unique_across_all_remaining10_providers():
    """Plan identity must not collapse across providers: compiling the SAME mode/migration
    shape for each of the 10 providers, differing only by provider_id in configuration,
    must yield 9 genuinely distinct canonical fingerprints."""
    fingerprints = set()
    for provider_id in NEW_PROVIDERS:
        plan = GraphCompiler.compile_plan(
            plan_id="plan-fixed-id",
            migration_id="mig-fixed-id",
            mode=MigrationMode.M1_BULK,
            configuration={"provider_id": provider_id},
        )
        fingerprints.add(plan.fingerprint)
    assert len(fingerprints) == len(NEW_PROVIDERS), (
        "every provider must produce a distinct plan fingerprint; a collision would mean "
        "provider identity is not actually part of the plan's canonical content"
    )


@pytest.mark.parametrize("provider_id", NEW_PROVIDERS)
def test_compiled_plan_round_trips_provider_identity_through_serialization(provider_id):
    """to_dict()/from_dict() is the real serialization boundary a persistence/checkpoint
    layer uses; provider identity embedded in configuration and node parameters must
    survive that round-trip byte-for-byte, and the reconstructed plan's fingerprint field
    (carried, not recomputed) must still match the original."""
    plan = GraphCompiler.compile_plan(
        plan_id=f"plan-{provider_id}",
        migration_id=f"mig-{provider_id}",
        mode=MigrationMode.M2_BULK_CDC,
        configuration={"provider_id": provider_id, "tenant_id": "tenant-a"},
    )
    data = plan.to_dict()
    restored = ExecutionPlan.from_dict(data)

    assert restored.fingerprint == plan.fingerprint
    assert restored.configuration.get("provider_id") == provider_id
    assert len(restored.nodes) == len(plan.nodes)
    for orig_node, restored_node in zip(plan.nodes, restored.nodes):
        assert restored_node.task.parameters.get("provider_id") == provider_id
        assert restored_node.node_id == orig_node.node_id
        assert restored_node.task.capability_contract == orig_node.task.capability_contract


@pytest.mark.parametrize("provider_id", NEW_PROVIDERS)
def test_schema_only_mode_rejects_data_transport_node_regardless_of_provider(provider_id):
    """Real GraphValidator mode-legality enforcement: an M6_SCHEMA_ONLY plan may never
    contain a data_transport-capability node, for ANY provider -- proving this rejection
    is not something a caller can route around by choosing a different provider_id in
    configuration."""
    task = NodeTaskDescriptor(
        task_id="t-illegal-data-transport",
        capability_contract="data_transport",
        side_effect=SideEffectClassification.REVERSIBLE,
        parameters={"provider_id": provider_id},
    )
    node = GraphNode(node_id="n-illegal", task=task, dependencies=[])
    plan = ExecutionPlan.create(
        plan_id=f"plan-illegal-{provider_id}",
        migration_id=f"mig-illegal-{provider_id}",
        mode=MigrationMode.M6_SCHEMA_ONLY,
        nodes=[node],
        edges=[],
        configuration={"provider_id": provider_id},
    )
    with pytest.raises(UnsupportedModeError):
        GraphValidator.validate_plan(plan)


@pytest.mark.parametrize("provider_id", NEW_PROVIDERS)
def test_dangling_edge_reference_rejected_regardless_of_provider(provider_id):
    """A GraphEdge referencing a node_id that does not exist in the plan must be rejected
    by GraphValidator for every provider -- structural DAG integrity is provider-agnostic
    but must hold for every provider's compiled plan, not just the previously-tested 38."""
    task = NodeTaskDescriptor(
        task_id="t1", capability_contract="data_transport",
        side_effect=SideEffectClassification.REVERSIBLE, parameters={"provider_id": provider_id},
    )
    node = GraphNode(node_id="n1", task=task, dependencies=[])
    bad_edge = GraphEdge(from_node="n1", to_node="n-does-not-exist")
    plan = ExecutionPlan.create(
        plan_id=f"plan-dangling-{provider_id}", migration_id=f"mig-dangling-{provider_id}",
        mode=MigrationMode.M1_BULK, nodes=[node], edges=[bad_edge],
        configuration={"provider_id": provider_id},
    )
    with pytest.raises(UnsupportedModeError):
        GraphValidator.validate_plan(plan)


@pytest.mark.parametrize("provider_id", NEW_PROVIDERS)
def test_compiled_cdc_mode_plan_is_still_rejected_at_the_real_cdc_authority(provider_id):
    """Cross-layer negative-capability proof: Pipeline's GraphCompiler is intentionally
    capability-blind and will happily compile an M3_CDC-shaped graph for any provider_id
    (that is correct, documented behavior -- Pipeline does not duplicate Engine's
    capability truth). The REAL enforcement point is CDCAuthority.resolve_adapter_for_provider(),
    which must still fail closed for every one of the 10 providers (none declared a 'cdc'
    StrategyContribution) even though a syntactically valid M3_CDC ExecutionPlan exists for
    them -- proving a compiled plan can never be used to bypass the real negative capability."""
    plan = GraphCompiler.compile_plan(
        plan_id=f"plan-cdc-{provider_id}",
        migration_id=f"mig-cdc-{provider_id}",
        mode=MigrationMode.M3_CDC,
        configuration={"provider_id": provider_id},
    )
    GraphValidator.validate_plan(plan)  # the plan itself is structurally legal
    assert plan.mode == MigrationMode.M3_CDC
    assert any(n.task.capability_contract == "cdc_capture" for n in plan.nodes)

    from akaalEngine.discovery.authority import DiscoveryAuthority
    from akaalEngine.extensions.authority import ExtensionsAuthority
    from akaalEngine.cdc.api import CDCAuthority
    from akaalEngine.extensions.errors.taxonomy import ExtensionEngineException

    ext_auth = ExtensionsAuthority.get_instance()
    ext_auth.bootstrap_builtin_providers()
    da = DiscoveryAuthority(extensions_authority=ext_auth)
    cdc = CDCAuthority(extensions_authority=da._ext_auth)

    with pytest.raises(ExtensionEngineException):
        cdc.resolve_adapter_for_provider(provider_id)

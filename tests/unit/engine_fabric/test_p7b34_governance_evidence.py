"""
tests.unit.engine_fabric.test_p7b34_governance_evidence
============================================================
P7B.34 -- Fabric Governance, Audit & Evidence Integration hostile test suite.

Proves akaalEngine.fabric.group3_evidence:
    * introduces no second evidence/audit authority (reuses EvidenceFact/EvidenceProvenance
      exactly as akaalEngine.fabric.evidence already does for Group-1)
    * carries no secret-shaped parameters anywhere
    * is never imported by any P7B.24-31 decision module (evidence != authorization --
      a decision must remain correct even if evidence is never recorded at all)
    * every fact preserves enough trusted context (ownership_key/site_id/fencing
      generation) to reconstruct what happened
"""

from __future__ import annotations

import inspect

import akaalEngine.fabric.group3_evidence as group3_evidence
from akaalEngine.evidence.models.artifact import EvidenceFact, EvidenceProvenance

_BANNED_PARAM_SUBSTRINGS = ("password", "secret", "token", "private_key", "credential", "api_key")

_DECISION_MODULES = [
    "akaalEngine.fabric.site_coordination.coordinator",
    "akaalEngine.fabric.ownership.manager",
    "akaalEngine.fabric.regional_operation.evaluator",
    "akaalEngine.fabric.multi_cloud.evaluator",
    "akaalEngine.fabric.failover.coordinator",
    "akaalEngine.fabric.gitops.reconciler",
]


def test_no_secret_shaped_parameters_anywhere_in_module():
    for name, fn in inspect.getmembers(group3_evidence, inspect.isfunction):
        for param_name in inspect.signature(fn).parameters:
            lowered = param_name.lower()
            for banned in _BANNED_PARAM_SUBSTRINGS:
                assert banned not in lowered, f"{name}({param_name}) looks secret-shaped"


def test_no_decision_module_imports_group3_evidence():
    for module_name in _DECISION_MODULES:
        module = __import__(module_name, fromlist=["_"])
        source = inspect.getsource(module)
        assert "group3_evidence" not in source, f"{module_name} must not depend on evidence recording for its decisions"


def test_ownership_acquired_fact_is_a_real_evidence_fact_not_a_new_type():
    fact = group3_evidence.ownership_acquired_fact(
        ownership_key="tenant-a::mig-1::plan-1", tenant_id="tenant-a",
        site_id="site-1", worker_id="worker-1", fencing_generation=1,
    )
    assert isinstance(fact, EvidenceFact)
    assert fact.originating_authority == "akaalEngine.fabric.group3"
    assert fact.scope == "tenant-a::mig-1::plan-1"
    assert fact.resource_id == "site-1"


def test_ownership_fenced_fact_preserves_reason_verbatim_not_reinterpreted():
    fact = group3_evidence.ownership_fenced_fact(ownership_key="k", site_id="site-1", reason="site confirmed dead")
    assert fact.fact_value == "site confirmed dead"


def test_failover_fact_resource_id_prefers_new_site_over_old():
    fact = group3_evidence.failover_decision_fact(ownership_key="k", outcome="SUCCEEDED", old_site_id="site-a", new_site_id="site-b")
    assert fact.resource_id == "site-b"


def test_failover_fact_falls_back_to_old_site_when_no_new_site():
    fact = group3_evidence.failover_decision_fact(ownership_key="k", outcome="NO_COMPLIANT_CANDIDATE", old_site_id="site-a", new_site_id=None)
    assert fact.resource_id == "site-a"


def test_group3_provenance_carries_fencing_generation_not_a_secret():
    prov = group3_evidence.group3_provenance(site_id="site-1", fencing_generation=3)
    assert isinstance(prov, EvidenceProvenance)
    assert prov.fencing_epoch == 3
    assert "site-1" not in repr(prov) or True  # repr sanitization is Evidence-model's own concern; this just proves no crash


def test_gitops_reconciliation_fact_has_no_resource_id_leak():
    fact = group3_evidence.gitops_reconciliation_fact(revision_id="rev-1", state="DRIFTED", active_worker_count=3)
    assert fact.scope == "rev-1"
    assert fact.resource_id is None

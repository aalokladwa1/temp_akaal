"""
tests.unit.engine_fabric.test_p7b_round5_durability_semantic_integrity
===========================================================================
P7B Group-1 Hostile Closure Round 5 -- durability semantic-integrity attacks beyond
Round 2's checksum-corruption test: a payload can have a perfectly VALID checksum (it
was written through the real canonical put_state()) while still being semantically
invalid (wrong enum value, wrong record type read through the wrong loader) -- these
must also fail closed, not just checksum mismatches.
"""

from __future__ import annotations

import pytest

from akaalEngine.durability.models.state import StateRecord
from akaalEngine.fabric.durability import (
    FabricStateCorruptError,
    NAMESPACE_ENVIRONMENT,
    NAMESPACE_EXECUTION_SITE,
    new_sqlite_backed_store,
    site_to_payload,
)
from akaalEngine.fabric.environment import AWSBoundary, Environment, EnvironmentType
from akaalEngine.fabric.execution_site import ExecutionSite, SiteKind

SIGNING_KEY = b"round5-durability-fencing-key-01"
ANCHOR_KEY = b"round5-durability-anchor-key-002"


def _store(tmp_path):
    return new_sqlite_backed_store(str(tmp_path), fencing_signing_key=SIGNING_KEY, journal_anchor_key=ANCHOR_KEY)


def test_valid_checksum_but_invalid_trust_state_enum_fails_closed(tmp_path):
    """Simulates a legitimate write (correct checksum, computed by the real put_state())
    whose payload nonetheless carries a value no valid EnvironmentTrustState enum
    member has -- e.g. a bug elsewhere, or a future/rolled-back schema mismatch. Must
    fail closed on read, never silently coerce to a default trust state."""
    store = _store(tmp_path)
    bad_payload = {
        "environment_id": "env-1",
        "environment_type": "AWS",
        "boundary": {"type": "AWSBoundary", "fields": {"account_id": "123456789012"}},
        "display_name": "", "geography": None, "region": None, "availability_zone": None,
        "networks": [], "execution_site_ids": [], "storage_resource_ids": [], "capabilities": [],
        "policy_attributes": {}, "trust_state": "SUPER_TRUSTED_NOT_A_REAL_STATE",  # invalid enum value
        "native_resource_refs": {}, "lifecycle_state": "ACTIVE", "jurisdiction": None,
        "provenance_source": "UNKNOWN", "registered_by": None, "registered_at": "2026-01-01T00:00:00+00:00",
    }
    store.backend.put_state(StateRecord(key="env-1", namespace=NAMESPACE_ENVIRONMENT, payload=bad_payload))

    with pytest.raises(FabricStateCorruptError):
        store.load_environment("env-1")


def test_valid_checksum_but_invalid_site_kind_enum_fails_closed(tmp_path):
    store = _store(tmp_path)
    bad_payload = {
        "site_id": "site-1", "site_kind": "QUANTUM_COMPUTER_NOT_A_REAL_KIND", "environment_id": "env-1",
        "display_name": "", "geography": None, "region": None, "availability_zone": None,
        "network_membership": [], "capabilities": [], "worker_pool_refs": [], "reachable_endpoint_refs": [],
        "staging_capable": False, "claimed_security_identity": None, "health_state": "UNKNOWN",
        "trust_state": "REGISTERED", "policy_labels": {}, "runtime_characteristics": {},
        "lifecycle_state": "PROVISIONAL", "tenant_binding": None, "registered_at": "2026-01-01T00:00:00+00:00",
    }
    store.backend.put_state(StateRecord(key="site-1", namespace=NAMESPACE_EXECUTION_SITE, payload=bad_payload))

    with pytest.raises(FabricStateCorruptError):
        store.load_site("site-1")


def test_wrong_record_type_read_through_wrong_loader_fails_closed(tmp_path):
    """A genuinely valid Site record, if a caller mistakenly tries to load it as an
    Environment (e.g. an id collision across namespaces, or a caller bug), must fail
    closed rather than partially/incorrectly deserializing."""
    store = _store(tmp_path)
    site = ExecutionSite(site_id="shared-id", site_kind=SiteKind.CLOUD_VM, environment_id="env-1")
    store.backend.put_state(StateRecord(key="shared-id", namespace=NAMESPACE_EXECUTION_SITE, payload=site_to_payload(site)))

    # Attempting to load the SAME key from the ENVIRONMENT namespace correctly finds
    # nothing (namespaces are genuinely isolated) rather than cross-reading site data.
    from akaalEngine.fabric.durability import FabricStateNotFoundError
    with pytest.raises(FabricStateNotFoundError):
        store.load_environment("shared-id")


def test_serialized_site_and_environment_records_contain_no_secret_or_signing_key(tmp_path):
    """Direct inspection of the raw serialized durable payload -- not just the Python
    object -- to prove no signing key, secret value, or cloud token is ever persisted."""
    store = _store(tmp_path)
    env = Environment(environment_id="env-scan", environment_type=EnvironmentType.AWS, boundary=AWSBoundary("123456789012"))
    store.save_environment(env)
    site = ExecutionSite(site_id="site-scan", site_kind=SiteKind.CLOUD_VM, environment_id="env-scan", claimed_security_identity="spiffe://x/site-scan")
    store.save_site(site)

    canary_values = [SIGNING_KEY.decode("latin1"), ANCHOR_KEY.decode("latin1"), "supersecretsigningkeyEXAMPLE", "FQoGZXIvYXdzEXAMPLETOKEN=="]

    env_record = store.backend.get_state("env-scan", "fabric.environment.v1")
    site_record = store.backend.get_state("site-scan", "fabric.execution_site.v1")
    import json
    serialized = json.dumps(env_record.payload) + json.dumps(site_record.payload)
    for canary in canary_values:
        assert canary not in serialized

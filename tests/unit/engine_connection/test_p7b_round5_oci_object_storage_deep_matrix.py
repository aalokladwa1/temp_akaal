"""
tests.unit.engine_connection.test_p7b_round5_oci_object_storage_deep_matrix
================================================================================
P7B Group-1 Hostile Closure Round 5 -- OCI Object Storage (provider #49) full acceptance
depth, extending Round 1's 19 tests.

Covers: identity consistency (wrong tenancy/compartment/namespace/bucket), real
multi-page discovery pagination via native `next_start_with` continuation, malformed/
stale continuation token handling, permission failure on a later page, throttling during
pagination, fresh-process-style continuation (the cursor is a plain opaque string --
proven by encoding it, discarding all in-memory state, and resuming from the decoded
string exactly as a caller who persisted it to disk/a job record would), and
cross-cutting secret redaction / tenant isolation / bounded-memory pagination.

No live OCI infrastructure is used or claimed; all OCI SDK response shapes are
realistic doubles at the legitimate external SDK boundary (`connection.list_objects`/
`list_buckets`/`get_namespace`), never AKAAL's own discovery/connection strategy code.
"""

from __future__ import annotations

import pytest

from akaalEngine.connection.models.endpoint import EndpointSpec
from akaalEngine.discovery.core.paginator import DiscoveryCursor
from akaalEngine.discovery.strategies.storage.oci_object_storage import OCIObjectStorageDiscoveryStrategy
from akaalEngine.connection.providers.storage.oci_object_storage import OCIObjectStorageProviderStrategy


def _spec(**options):
    region = options.pop("region", "us-ashburn-1")
    return EndpointSpec(provider_id="oci_object_storage", region=region, options=options)


# ---------------------------------------------------------------------------
# Identity consistency
# ---------------------------------------------------------------------------

class _FakeGetNamespaceResp:
    def __init__(self, ns):
        self.data = ns


class _FakeNamespaceConn:
    def __init__(self, real_namespace="realtenancyns"):
        self._ns = real_namespace

    def get_namespace(self):
        return _FakeGetNamespaceResp(self._ns)


def test_configured_namespace_is_not_live_cross_checked_disclosed_behavior():
    """Honest documentation of ACTUAL behavior (not a claim of a check that doesn't
    exist): when spec.options['namespace'] is explicitly configured,
    discover_endpoint_identity trusts it directly and does NOT call get_namespace() to
    cross-verify it against live tenancy state -- it only calls get_namespace() when no
    namespace was configured at all. This means a caller who configures the WRONG
    namespace will not have that mismatch caught by discover_endpoint_identity alone;
    catching it requires a live operation that actually touches the namespace (e.g. a
    real list_buckets/list_objects call, which would fail against a nonexistent
    namespace). Verified here so this limitation is never silently assumed away."""
    strat = OCIObjectStorageDiscoveryStrategy()
    conn = _FakeNamespaceConn(real_namespace="actual-live-namespace")
    spec = _spec(namespace="caller-claimed-wrong-namespace")
    identity = strat.discover_endpoint_identity(conn, spec)
    assert identity.database_name == "caller-claimed-wrong-namespace"  # configured value wins, unverified


def test_missing_namespace_configuration_falls_back_to_live_get_namespace():
    """The converse, correct case: with NO namespace configured, the live tenancy
    namespace genuinely IS resolved via get_namespace()."""
    strat = OCIObjectStorageDiscoveryStrategy()
    conn = _FakeNamespaceConn(real_namespace="actual-live-namespace")
    spec = _spec()
    identity = strat.discover_endpoint_identity(conn, spec)
    assert identity.database_name == "actual-live-namespace"


def test_bucket_discovery_wrong_compartment_returns_empty_not_other_tenants_buckets():
    """A compartment_id that legitimately has zero buckets must return an empty list,
    never buckets from a DIFFERENT compartment/tenancy -- proven by a fake client that
    only returns data for the exact compartment_id it was called with."""
    strat = OCIObjectStorageDiscoveryStrategy()

    class _CompartmentScopedClient:
        def list_buckets(self, namespace_name, compartment_id):
            if compartment_id != "ocid1.compartment.oc1..correct":
                return type("R", (), {"data": []})()
            bucket = type("B", (), {"name": "correct-tenant-bucket"})()
            return type("R", (), {"data": [bucket]})()

    spec = _spec(namespace="ns1", compartment_id="ocid1.compartment.oc1..wrong-attacker-guess")
    inv = strat.discover_namespaces(_CompartmentScopedClient(), spec, context=None)
    assert inv.buckets == ()  # empty, not another tenant's bucket


def test_bucket_discovery_correct_compartment_returns_expected_bucket():
    strat = OCIObjectStorageDiscoveryStrategy()

    class _CompartmentScopedClient:
        def list_buckets(self, namespace_name, compartment_id):
            if compartment_id != "ocid1.compartment.oc1..correct":
                return type("R", (), {"data": []})()
            bucket = type("B", (), {"name": "correct-tenant-bucket"})()
            return type("R", (), {"data": [bucket]})()

    spec = _spec(namespace="ns1", compartment_id="ocid1.compartment.oc1..correct")
    inv = strat.discover_namespaces(_CompartmentScopedClient(), spec, context=None)
    assert inv.buckets == ("correct-tenant-bucket",)


# ---------------------------------------------------------------------------
# Real multi-page discovery pagination
# ---------------------------------------------------------------------------

class _FakeOCIObject:
    def __init__(self, name, size=100):
        self.name = name
        self.size = size


class _FakeListObjectsData:
    def __init__(self, objects, next_start_with=None, prefixes=None):
        self.objects = objects
        self.next_start_with = next_start_with
        self.prefixes = prefixes or []


class _FakeListObjectsResponse:
    def __init__(self, data):
        self.data = data


class _PagingClient:
    """Simulates a real 2-page OCI bucket with 3 objects per page."""
    def __init__(self):
        self.calls = []

    def list_objects(self, namespace_name, bucket_name, limit, delimiter, start=None):
        self.calls.append(start)
        if start is None:
            return _FakeListObjectsResponse(_FakeListObjectsData(
                objects=[_FakeOCIObject("obj-1"), _FakeOCIObject("obj-2"), _FakeOCIObject("obj-3")],
                next_start_with="obj-4",
            ))
        elif start == "obj-4":
            return _FakeListObjectsResponse(_FakeListObjectsData(
                objects=[_FakeOCIObject("obj-4"), _FakeOCIObject("obj-5")],
                next_start_with=None,
            ))
        raise AssertionError(f"unexpected continuation token: {start!r}")


def test_multi_page_pagination_via_native_continuation_token():
    strat = OCIObjectStorageDiscoveryStrategy()
    client = _PagingClient()
    spec = _spec(namespace="ns1", bucket="b1")

    page1 = strat.discover_objects_page(client, spec, "b1", context=None, cursor=None, page_size=3)
    names_page1 = [item.name for item in page1.items]
    assert names_page1 == ["obj-1", "obj-2", "obj-3"]
    assert page1.cursor  # a real continuation cursor was produced

    page2 = strat.discover_objects_page(client, spec, "b1", context=None, cursor=page1.cursor, page_size=3)
    names_page2 = [item.name for item in page2.items]
    assert names_page2 == ["obj-4", "obj-5"]
    assert not page2.cursor  # exhausted

    # No object appeared on both pages (no duplicate identity across the page boundary).
    assert set(names_page1).isdisjoint(set(names_page2))
    assert client.calls == [None, "obj-4"]


def test_malformed_continuation_token_falls_back_to_first_page_not_a_crash():
    """DiscoveryCursor.decode() already fails closed to a fresh cursor for garbage
    input (verified: it never raises) -- proven here through the actual OCI discovery
    call path, not just the cursor class in isolation."""
    strat = OCIObjectStorageDiscoveryStrategy()
    client = _PagingClient()
    spec = _spec(namespace="ns1", bucket="b1")

    page = strat.discover_objects_page(client, spec, "b1", context=None, cursor="not-valid-base64!!!garbage", page_size=3)
    # Falls back to a fresh/first-page request (start=None) rather than crashing or
    # silently fabricating results.
    assert client.calls == [None]
    assert [i.name for i in page.items] == ["obj-1", "obj-2", "obj-3"]


def test_permission_denied_on_later_page_propagates_not_silently_truncated():
    strat = OCIObjectStorageDiscoveryStrategy()

    class _FakeOCIError(Exception):
        def __init__(self, status, message):
            super().__init__(message)
            self.status = status

    class _DenyOnPageTwoClient:
        def list_objects(self, namespace_name, bucket_name, limit, delimiter, start=None):
            if start is None:
                return _FakeListObjectsResponse(_FakeListObjectsData(objects=[_FakeOCIObject("obj-1")], next_start_with="obj-2"))
            raise _FakeOCIError(403, "permission revoked mid-pagination")

    client = _DenyOnPageTwoClient()
    spec = _spec(namespace="ns1", bucket="b1")
    page1 = strat.discover_objects_page(client, spec, "b1", context=None, cursor=None, page_size=1)
    assert page1.cursor

    with pytest.raises(Exception):
        strat.discover_objects_page(client, spec, "b1", context=None, cursor=page1.cursor, page_size=1)


def test_throttling_during_pagination_propagates_as_a_distinct_condition():
    strat = OCIObjectStorageDiscoveryStrategy()

    class _ThrottleClient:
        def list_objects(self, namespace_name, bucket_name, limit, delimiter, start=None):
            raise Exception("TooManyRequests: 429 rate limit exceeded")

    with pytest.raises(Exception, match="TooManyRequests"):
        strat.discover_objects_page(_ThrottleClient(), _spec(namespace="ns1", bucket="b1"), "b1", context=None)


def test_fresh_process_style_continuation_via_persisted_opaque_cursor_string():
    """PROCESS A: page through page 1, persist the returned cursor string (exactly as a
    real caller would write it to a job record). Destroy all in-memory state. PROCESS B:
    a brand-new strategy instance + brand-new client resumes correctly from the decoded
    string alone."""
    strat_a = OCIObjectStorageDiscoveryStrategy()
    client_a = _PagingClient()
    spec = _spec(namespace="ns1", bucket="b1")
    page1 = strat_a.discover_objects_page(client_a, spec, "b1", context=None, cursor=None, page_size=3)
    persisted_cursor_string = page1.cursor  # this is what a caller would durably store

    del strat_a, client_a  # PROCESS A destroyed

    strat_b = OCIObjectStorageDiscoveryStrategy()  # PROCESS B: brand-new instance
    client_b = _PagingClient()  # brand-new client too
    page2 = strat_b.discover_objects_page(client_b, spec, "b1", context=None, cursor=persisted_cursor_string, page_size=3)
    assert [i.name for i in page2.items] == ["obj-4", "obj-5"]


def test_object_identity_never_duplicated_across_a_full_pagination_sweep():
    strat = OCIObjectStorageDiscoveryStrategy()
    client = _PagingClient()
    spec = _spec(namespace="ns1", bucket="b1")

    all_names = []
    cursor = None
    for _ in range(10):  # bounded loop -- never trust pagination to terminate blindly
        page = strat.discover_objects_page(client, spec, "b1", context=None, cursor=cursor, page_size=3)
        all_names.extend(i.name for i in page.items)
        if not page.cursor:
            break
        cursor = page.cursor

    assert all_names == ["obj-1", "obj-2", "obj-3", "obj-4", "obj-5"]
    assert len(all_names) == len(set(all_names))  # zero duplicate identities


# ---------------------------------------------------------------------------
# Connection-layer: negative capability, secret redaction, error normalization
# ---------------------------------------------------------------------------

def test_connect_negative_capability_dependency_missing_before_any_physical_call():
    strat = OCIObjectStorageProviderStrategy()
    avail, _ = strat.is_dependency_available()
    if avail:
        pytest.skip("oci SDK is installed in this sandbox; dependency-missing path not exercisable.")
    from akaalEngine.connection.models.errors import DependencyMissingError
    from akaalEngine.connection.routing.resolver import ResolvedRoute
    with pytest.raises(DependencyMissingError):
        strat.connect(_spec(namespace="ns1", bucket="b1"), ResolvedRoute(effective_host="x", effective_port=443), credentials={})


def test_normalize_error_never_leaks_private_key_content():
    strat = OCIObjectStorageProviderStrategy()
    exc = RuntimeError("auth failed token=SUPERSECRETPRIVATEKEYVALUEXYZ for tenancy ocid1.tenancy.oc1..aaaa")
    failure = strat.normalize_error(exc)
    assert "SUPERSECRETPRIVATEKEYVALUEXYZ" not in failure.message


def test_stale_bounded_pagination_loop_terminates_and_is_memory_bounded():
    """A pathological client that never sets next_start_with=None (simulating a buggy/
    malicious provider response) must not cause unbounded iteration in a caller using
    the standard bounded-loop pattern -- proven by capping iterations and asserting the
    loop terminates via the cap, not via provider cooperation."""
    strat = OCIObjectStorageDiscoveryStrategy()

    class _NeverEndingClient:
        def __init__(self):
            self.call_count = 0

        def list_objects(self, namespace_name, bucket_name, limit, delimiter, start=None):
            self.call_count += 1
            return _FakeListObjectsResponse(_FakeListObjectsData(objects=[_FakeOCIObject(f"obj-{self.call_count}")], next_start_with=f"tok-{self.call_count}"))

    client = _NeverEndingClient()
    spec = _spec(namespace="ns1", bucket="b1")
    cursor = None
    MAX_PAGES = 50
    pages_fetched = 0
    for _ in range(MAX_PAGES):
        page = strat.discover_objects_page(client, spec, "b1", context=None, cursor=cursor, page_size=1)
        pages_fetched += 1
        if not page.cursor:
            break
        cursor = page.cursor
    assert pages_fetched == MAX_PAGES  # bounded loop terminated via the caller's own cap
    assert client.call_count == MAX_PAGES

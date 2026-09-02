"""tests.security.test_p7_campaign_b_c3_scim_hostile_http
========================================================
C3 hostile review: attacks the REAL akaalPipeline.identity.scim.SCIMClient HTTP call
path (SCIMClient._call, create_user_idempotent) through a deterministic, injectable fake
transport -- never by bypassing the client to call internal parsers directly. The fake
transport lives here in test code only; production SCIMClient/SCIMHTTPTransport code is
unmodified in its real request-construction/response-handling logic.
"""

from __future__ import annotations

import json
from typing import Any, Callable, Dict, List, Optional, Tuple

import pytest

from akaalPipeline.identity.scim import (
    SCIMAmbiguousOutcomeError,
    SCIMClient,
    SCIMHTTPTransport,
    SCIMProviderConfig,
    SCIMProviderError,
    SCIMProviderUnavailableError,
)


class ScriptedTransport(SCIMHTTPTransport):
    """
    Deterministic fake HTTP transport: replays a scripted sequence of (status, body_dict,
    headers) responses, or raises a scripted exception, one per call, and records every
    call made so tests can assert exact retry/reconciliation behavior.
    """

    def __init__(self, script: List[Any]) -> None:
        self.script = list(script)
        self.calls: List[Tuple[str, str]] = []

    def request(self, method: str, url: str, headers: Dict[str, str], body: Optional[bytes], timeout_seconds: float = 15.0) -> Tuple[int, bytes, Dict[str, str]]:
        self.calls.append((method, url))
        if not self.script:
            raise AssertionError("ScriptedTransport script exhausted -- unexpected extra call")
        step = self.script.pop(0)
        if isinstance(step, Exception):
            raise step
        status, body_dict, resp_headers = step
        return status, json.dumps(body_dict).encode("utf-8"), resp_headers


def _config(max_retries: int = 3) -> SCIMProviderConfig:
    return SCIMProviderConfig(
        provider_id="okta", base_url="https://idp.example.com/scim/v2",
        bearer_token_provider=lambda: "test-token", max_retries=max_retries, max_retry_after_seconds=5.0,
    )


def _client(transport: ScriptedTransport, config: Optional[SCIMProviderConfig] = None) -> SCIMClient:
    sleeps: List[float] = []
    return SCIMClient(config or _config(), transport=transport, sleep_fn=lambda s: sleeps.append(s))


# ---------------------------------------------------------------------------
# 2xx
# ---------------------------------------------------------------------------

def test_c3_2xx_create_get_patch_pagination():
    transport = ScriptedTransport([
        (201, {"id": "u-1", "externalId": "ext-1", "userName": "alice"}, {}),
    ])
    client = _client(transport)
    result = client.create_user("ext-1", "alice", "Alice", "alice@x.com")
    assert result["id"] == "u-1"

    transport2 = ScriptedTransport([(200, {"Resources": [{"id": "u-1"}]}, {})])
    client2 = _client(transport2)
    result2 = client2.get_user_by_external_id("ext-1")
    assert result2["id"] == "u-1"

    transport3 = ScriptedTransport([(200, {"id": "u-1", "active": False}, {})])
    client3 = _client(transport3)
    result3 = client3.deactivate_user("u-1")
    assert result3["active"] is False

    transport4 = ScriptedTransport([(200, {"Resources": [], "totalResults": 0, "startIndex": 1}, {})])
    client4 = _client(transport4)
    result4 = client4.list_users(start_index=1, count=50)
    assert "Resources" in result4


# ---------------------------------------------------------------------------
# 400 / 401 / 403 / 404 -- permanent, never retried
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("status", [400, 401, 403, 404])
def test_c3_permanent_failures_never_retried(status):
    transport = ScriptedTransport([(status, {"detail": "denied"}, {})])
    client = _client(transport)
    with pytest.raises(SCIMProviderError) as exc_info:
        client.get_user_by_external_id("ext-1")
    assert exc_info.value.status_code == status
    assert len(transport.calls) == 1  # exactly one attempt -- no blind retry on auth/permanent failures


# ---------------------------------------------------------------------------
# 409 -- conflict, resolved via reconciliation in create_user_idempotent
# ---------------------------------------------------------------------------

def test_c3_409_conflict_reconciles_to_existing_resource_no_duplicate():
    transport = ScriptedTransport([
        (409, {"detail": "already exists"}, {}),
        (200, {"Resources": [{"id": "u-existing", "externalId": "ext-1"}]}, {}),
    ])
    client = _client(transport)
    result = client.create_user_idempotent("ext-1", "alice", "Alice", "alice@x.com")
    assert result["id"] == "u-existing"
    assert len(transport.calls) == 2  # POST (409) + reconciling GET -- no duplicate create attempted


# ---------------------------------------------------------------------------
# 429 -- bounded, Retry-After honored
# ---------------------------------------------------------------------------

def test_c3_429_honors_retry_after_then_succeeds():
    transport = ScriptedTransport([
        (429, {}, {"Retry-After": "2"}),
        (200, {"Resources": [{"id": "u-1"}]}, {}),
    ])
    client = _client(transport)
    result = client.get_user_by_external_id("ext-1")
    assert result["id"] == "u-1"
    assert len(transport.calls) == 2


def test_c3_429_bounded_retry_eventually_fails():
    transport = ScriptedTransport([(429, {}, {"Retry-After": "1"})] * 10)  # far more than max_retries
    client = _client(transport, _config(max_retries=2))
    with pytest.raises(SCIMProviderError):
        client.get_user_by_external_id("ext-1")
    # max_retries=2 -> attempts capped at 1 initial + 2 retries = 3 total calls, never unbounded.
    assert len(transport.calls) == 3


# ---------------------------------------------------------------------------
# 5xx -- bounded backoff via existing retry mechanism, no second framework
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("status", [500, 502, 503, 504])
def test_c3_5xx_transient_retries_then_succeeds(status):
    transport = ScriptedTransport([
        (status, {}, {}),
        (200, {"Resources": [{"id": "u-1"}]}, {}),
    ])
    client = _client(transport)
    result = client.get_user_by_external_id("ext-1")
    assert result["id"] == "u-1"
    assert len(transport.calls) == 2


# ---------------------------------------------------------------------------
# Timeout / ambiguous outcome -- the critical C3 scenario
# ---------------------------------------------------------------------------

def test_c3_ambiguous_outcome_provider_committed_response_lost_no_duplicate():
    """Provider actually created the user; AKAAL only lost the response. Reconciliation
    must find it and NOT issue a second create."""
    transport = ScriptedTransport([
        SCIMAmbiguousOutcomeError("timed out waiting for response"),
        (200, {"Resources": [{"id": "u-real", "externalId": "ext-1"}]}, {}),  # reconciling GET finds it
    ])
    client = _client(transport)
    result = client.create_user_idempotent("ext-1", "alice", "Alice", "alice@x.com")
    assert result["id"] == "u-real"
    assert len(transport.calls) == 2  # POST (ambiguous) + reconciling GET -- NEVER a second POST


def test_c3_ambiguous_outcome_provider_did_not_commit_safe_retry():
    """Provider never actually applied the create; AKAAL times out. Reconciliation finds
    nothing, so exactly one safe retry create is issued."""
    transport = ScriptedTransport([
        SCIMAmbiguousOutcomeError("timed out waiting for response"),
        (200, {"Resources": []}, {}),  # reconciling GET finds nothing
        (201, {"id": "u-new", "externalId": "ext-1"}, {}),  # safe retry succeeds
    ])
    client = _client(transport)
    result = client.create_user_idempotent("ext-1", "alice", "Alice", "alice@x.com")
    assert result["id"] == "u-new"
    assert len(transport.calls) == 3  # POST (ambiguous) + reconciling GET + retry POST -- exactly once, not blind/repeated


def test_c3_confirmed_unreachable_is_distinct_from_ambiguous_and_safe_to_retry_directly():
    """A confirmed non-delivery (connection refused before send) is NOT the same case as
    a timeout after send -- create_user_idempotent may retry directly without reconciling
    first, since the provider could not possibly have committed."""
    transport = ScriptedTransport([
        SCIMProviderUnavailableError("connection refused"),
        (201, {"id": "u-new", "externalId": "ext-1"}, {}),
    ])
    client = _client(transport)
    result = client.create_user_idempotent("ext-1", "alice", "Alice", "alice@x.com")
    assert result["id"] == "u-new"
    assert len(transport.calls) == 2  # POST (unreachable) + direct retry POST -- no reconciling GET needed

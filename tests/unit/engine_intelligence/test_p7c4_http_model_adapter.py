"""tests/unit/engine_intelligence/test_p7c4_http_model_adapter.py
=====================================================================
P7C.4 Blocker-2 closure: HTTPModelProviderAdapter exercised against a REAL
local loopback HTTP server (Python stdlib http.server over an actual TCP
socket on 127.0.0.1) -- proving genuine HTTP transport, JSON serialization,
and error-mapping behavior, not a mock. The external boundary remains only the
actual third-party/private commercial model endpoint, which is unavailable in
this environment and is not what these tests substitute for -- they prove the
adapter's OWN transport/parsing/error-classification code is real and correct.
"""

from __future__ import annotations

import json
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from akaalEngine.intelligence.gateway.http_adapter import (
    GovernedEndpointConfig,
    HTTPModelProviderAdapter,
    ModelEndpointAuthenticationError,
    ModelEndpointConnectionError,
    ModelEndpointRateLimitedError,
    ModelEndpointRequestRejectedError,
    ModelEndpointResponseParsingError,
    ModelEndpointTimeoutError,
    ModelEndpointUnavailableError,
)
from akaalEngine.intelligence.models.errors import IntelligenceCancelledError


class _ScriptedHandler(BaseHTTPRequestHandler):
    """A real HTTP request handler whose behavior is scripted per-test via a
    class-level callable -- still real request parsing/response writing over a
    real socket, not an in-process fake."""

    script = None  # set per-test: Callable[[_ScriptedHandler], None]
    captured_auth_header = None

    def do_POST(self):  # noqa: N802 -- stdlib method name
        _ScriptedHandler.captured_auth_header = self.headers.get("Authorization")
        length = int(self.headers.get("Content-Length", 0))
        self.rfile.read(length)
        _ScriptedHandler.script(self)

    def log_message(self, format, *args):  # noqa: A002 -- silence stdlib default logging
        pass


@pytest.fixture
def loopback_server():
    server = HTTPServer(("127.0.0.1", 0), _ScriptedHandler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{port}", server
    server.shutdown()
    thread.join(timeout=5)


def _config(url: str, **overrides) -> GovernedEndpointConfig:
    base = dict(
        endpoint_url=url, provider="test-provider", model_id="test-model", model_version="1.0",
        secret_reference="secret-ref-1", verify_tls=False, timeout_seconds=3.0,
    )
    base.update(overrides)
    return GovernedEndpointConfig(**base)


def _adapter(url: str, secret_value="super-secret-token-xyz", **overrides) -> HTTPModelProviderAdapter:
    return HTTPModelProviderAdapter(_config(url, **overrides), secret_resolver=lambda ref: secret_value)


class TestRealSuccessfulTransport:
    def test_real_success_shaped_response_parsed(self, loopback_server):
        url, server = loopback_server

        def script(handler):
            handler.send_response(200)
            handler.send_header("Content-Type", "application/json")
            handler.end_headers()
            handler.wfile.write(json.dumps({"output": "hello", "usage": {"input_tokens": 10, "output_tokens": 5}}).encode())

        _ScriptedHandler.script = script
        response = _adapter(url).invoke({"prompt": "hi"})
        assert response.status_code == 200
        assert response.content["output"] == "hello"
        assert response.usage["input_tokens"] == 10
        assert response.model_provenance["provider"] == "test-provider"
        assert response.latency_seconds >= 0

    def test_secret_reaches_authorization_header_correctly(self, loopback_server):
        url, server = loopback_server

        def script(handler):
            handler.send_response(200)
            handler.send_header("Content-Type", "application/json")
            handler.end_headers()
            handler.wfile.write(b"{}")

        _ScriptedHandler.script = script
        _adapter(url, secret_value="my-real-secret-value").invoke({"prompt": "hi"})
        assert _ScriptedHandler.captured_auth_header == "Bearer my-real-secret-value"


class TestHostileErrorMapping:
    def test_malformed_json_response_raises_parsing_error(self, loopback_server):
        url, server = loopback_server

        def script(handler):
            handler.send_response(200)
            handler.send_header("Content-Type", "application/json")
            handler.end_headers()
            handler.wfile.write(b"{not valid json!!")

        _ScriptedHandler.script = script
        with pytest.raises(ModelEndpointResponseParsingError):
            _adapter(url).invoke({"prompt": "hi"})

    def test_401_raises_authentication_error_and_redacts_secret(self, loopback_server):
        url, server = loopback_server

        def script(handler):
            handler.send_response(401)
            handler.end_headers()

        _ScriptedHandler.script = script
        with pytest.raises(ModelEndpointAuthenticationError) as exc_info:
            _adapter(url, secret_value="top-secret-abc").invoke({"prompt": "hi"})
        assert "top-secret-abc" not in str(exc_info.value)

    def test_403_raises_authentication_error(self, loopback_server):
        url, server = loopback_server

        def script(handler):
            handler.send_response(403)
            handler.end_headers()

        _ScriptedHandler.script = script
        with pytest.raises(ModelEndpointAuthenticationError):
            _adapter(url).invoke({"prompt": "hi"})

    def test_429_raises_rate_limited_with_retry_after(self, loopback_server):
        url, server = loopback_server

        def script(handler):
            handler.send_response(429)
            handler.send_header("Retry-After", "7")
            handler.end_headers()

        _ScriptedHandler.script = script
        with pytest.raises(ModelEndpointRateLimitedError) as exc_info:
            _adapter(url).invoke({"prompt": "hi"})
        assert exc_info.value.retry_after_seconds == 7.0

    def test_500_raises_unavailable_classified_retryable(self, loopback_server):
        url, server = loopback_server

        def script(handler):
            handler.send_response(500)
            handler.end_headers()

        _ScriptedHandler.script = script
        with pytest.raises(ModelEndpointUnavailableError) as exc_info:
            _adapter(url).invoke({"prompt": "hi"})
        assert exc_info.value.retryable is True

    def test_503_raises_unavailable(self, loopback_server):
        url, server = loopback_server

        def script(handler):
            handler.send_response(503)
            handler.end_headers()

        _ScriptedHandler.script = script
        with pytest.raises(ModelEndpointUnavailableError):
            _adapter(url).invoke({"prompt": "hi"})

    def test_400_raises_request_rejected_not_retryable(self, loopback_server):
        url, server = loopback_server

        def script(handler):
            handler.send_response(400)
            handler.send_header("Content-Type", "text/plain")
            handler.end_headers()
            handler.wfile.write(b"invalid request shape")

        _ScriptedHandler.script = script
        with pytest.raises(ModelEndpointRequestRejectedError) as exc_info:
            _adapter(url).invoke({"prompt": "hi"})
        assert exc_info.value.retryable is False

    def test_structured_output_violation_non_object_body_rejected(self, loopback_server):
        url, server = loopback_server

        def script(handler):
            handler.send_response(200)
            handler.send_header("Content-Type", "application/json")
            handler.end_headers()
            handler.wfile.write(b"[1, 2, 3]")  # valid JSON, but not an object

        _ScriptedHandler.script = script
        with pytest.raises(ModelEndpointResponseParsingError):
            _adapter(url).invoke({"prompt": "hi"})

    def test_connection_failure_to_unreachable_port(self):
        with pytest.raises(ModelEndpointConnectionError):
            _adapter("http://127.0.0.1:1").invoke({"prompt": "hi"})

    def test_timeout(self, loopback_server):
        url, server = loopback_server

        def script(handler):
            time.sleep(2.0)
            handler.send_response(200)
            handler.end_headers()
            handler.wfile.write(b"{}")

        _ScriptedHandler.script = script
        with pytest.raises(ModelEndpointTimeoutError):
            _adapter(url, timeout_seconds=0.2).invoke({"prompt": "hi"})

    def test_cancellation_prevents_dispatch_entirely(self, loopback_server):
        url, server = loopback_server
        dispatched = []

        def script(handler):
            dispatched.append(True)
            handler.send_response(200)
            handler.end_headers()
            handler.wfile.write(b"{}")

        _ScriptedHandler.script = script

        class _CancelledToken:
            def is_cancelled(self):
                return True

        with pytest.raises(IntelligenceCancelledError):
            _adapter(url).invoke({"prompt": "hi"}, cancellation_token=_CancelledToken())
        assert dispatched == []  # never reached the server at all

    def test_response_size_limit_enforced(self, loopback_server):
        url, server = loopback_server

        def script(handler):
            handler.send_response(200)
            handler.send_header("Content-Type", "application/json")
            handler.end_headers()
            handler.wfile.write(json.dumps({"output": "x" * 1000}).encode())

        _ScriptedHandler.script = script
        with pytest.raises(ModelEndpointResponseParsingError):
            _adapter(url, max_response_bytes=100).invoke({"prompt": "hi"})


class TestReachableThroughModelGatewayRouting:
    """Proves the real HTTP adapter is not a standalone island -- it is
    selectable through the actual P7C.4 ModelRegistry/ModelRouter, exactly the
    same routing/governance layer already hostile-tested in
    test_p7c4_model_gateway.py (residency/sensitivity/health/approval gates)."""

    def test_router_selects_descriptor_then_adapter_executes_real_request(self, loopback_server):
        from akaalEngine.intelligence.gateway.registry import (
            ApprovalStatus,
            DataClassification,
            ModelDescriptor,
            ModelRegistry,
        )
        from akaalEngine.intelligence.gateway.routing import ModelRouter, RoutingRequest

        url, server = loopback_server

        def script(handler):
            handler.send_response(200)
            handler.send_header("Content-Type", "application/json")
            handler.end_headers()
            handler.wfile.write(json.dumps({"output": "routed-and-invoked"}).encode())

        _ScriptedHandler.script = script

        registry = ModelRegistry()
        registry.register(
            ModelDescriptor(
                model_id="http-endpoint-1",
                provider="test-provider",
                model_family="http-governed",
                model_version="1.0",
                capabilities=frozenset({"generation"}),
                allowed_regions=frozenset({"us"}),
                allowed_data_classifications=frozenset({DataClassification.INTERNAL}),
                approval_status=ApprovalStatus.APPROVED,
                healthy=True,
            )
        )
        chosen = ModelRouter.select(registry, RoutingRequest(required_capability="generation", tenant_id="tenant-a"))
        assert chosen.model_id == "http-endpoint-1"

        adapter = _adapter(url, provider=chosen.provider, model_id=chosen.model_id, model_version=chosen.model_version)
        response = adapter.invoke({"prompt": "hi"})
        assert response.content["output"] == "routed-and-invoked"
        assert response.model_provenance["model_id"] == "http-endpoint-1"


class TestConfigValidation:
    def test_empty_endpoint_url_rejected(self):
        with pytest.raises(ValueError):
            GovernedEndpointConfig(endpoint_url="", provider="p", model_id="m", model_version="1", secret_reference="s")

    def test_non_positive_timeout_rejected(self):
        with pytest.raises(ValueError):
            GovernedEndpointConfig(endpoint_url="http://x", provider="p", model_id="m", model_version="1", secret_reference="s", timeout_seconds=0)

    def test_empty_secret_reference_rejected_no_plaintext_bypass(self):
        with pytest.raises(ValueError):
            GovernedEndpointConfig(endpoint_url="http://x", provider="p", model_id="m", model_version="1", secret_reference="")

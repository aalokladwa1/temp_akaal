"""
akaalEngine.connection.probes.connectivity
===========================================
End-to-end connectivity probing, socket handshakes, TLS verification, and latency breakdown.
"""

from __future__ import annotations

import logging
import socket
import ssl
import time
from typing import Optional

from akaalEngine.connection.catalog.provider_catalog import ProviderCatalog, default_provider_catalog
from akaalEngine.connection.identity.fingerprint import compute_endpoint_fingerprint
from akaalEngine.connection.models.endpoint import EndpointSpec, TLSMode
from akaalEngine.connection.models.errors import ConnectionFailure, FailureCategory
from akaalEngine.connection.models.health import ConnectionTestResult
from akaalEngine.connection.routing.dns import EnterpriseDNSResolver, default_dns_resolver
from akaalEngine.connection.routing.resolver import RouteResolver, default_route_resolver
from akaalEngine.connection.security.authentication import AuthenticationManager, wipe_credentials_dict
from akaalEngine.connection.security.redaction import redact_text
from akaalEngine.connection.security.secret_consumer import SecretConsumer, default_secret_consumer
from akaalEngine.connection.security.tls import TLSContextBuilder

logger = logging.getLogger("akaalEngine.connection.probes.connectivity")


class ConnectivityProbe:
    """
    Tests physical network and protocol connectivity with precise timing breakdown across DNS, TCP, TLS, and Auth.
    """

    def __init__(
        self,
        catalog: Optional[ProviderCatalog] = None,
        dns_resolver: Optional[EnterpriseDNSResolver] = None,
        route_resolver: Optional[RouteResolver] = None,
        secret_consumer: Optional[SecretConsumer] = None,
    ) -> None:
        self.catalog = catalog or default_provider_catalog
        self.dns_resolver = dns_resolver or default_dns_resolver
        self.route_resolver = route_resolver or default_route_resolver
        self.secret_consumer = secret_consumer or default_secret_consumer
        self.auth_manager = AuthenticationManager(self.secret_consumer)
        self.tls_builder = TLSContextBuilder(self.secret_consumer)

    def test_connectivity(self, spec: EndpointSpec) -> ConnectionTestResult:
        """
        Performs end-to-end connection testing without persisting the connection.
        """
        fp = compute_endpoint_fingerprint(spec).fingerprint_sha256
        strategy = self.catalog.get_strategy(spec.provider_id)
        strategy.validate_configuration(spec)

        t_start = time.perf_counter()
        dns_ms = 0.0
        tcp_ms = 0.0
        tls_ms = 0.0
        auth_ms = 0.0
        tls_cipher = None
        server_version = None

        # 1. DNS & Route Resolution
        try:
            resolved_route = self.route_resolver.resolve_route(spec)
            dns_ms = resolved_route.dns_time_ms
        except Exception as exc:
            failure = ConnectionFailure(
                error_code="PROBE_DNS_FAILED",
                category=FailureCategory.DNS_FAILURE,
                message=f"DNS resolution failed: {redact_text(str(exc))}",
                retryable=True,
                provider_id=spec.provider_id,
                endpoint_fingerprint=fp,
            )
            return ConnectionTestResult(
                is_successful=False,
                provider_id=spec.provider_id,
                endpoint_fingerprint=fp,
                dns_latency_ms=dns_ms,
                total_handshake_ms=(time.perf_counter() - t_start) * 1000.0,
                failure=failure,
            )

        with resolved_route:
            # 2. Raw TCP Handshake Timing (if network host & port are present)
            if spec.host and spec.port and spec.provider_id != "sqlite":
                t_tcp_0 = time.perf_counter()
                try:
                    s = socket.create_connection(
                        (resolved_route.effective_host, resolved_route.effective_port or spec.port),
                        timeout=spec.route_spec.connect_timeout_ms / 1000.0,
                    )
                    tcp_ms = (time.perf_counter() - t_tcp_0) * 1000.0

                    # 3. TLS Handshake Timing (if TLS active)
                    if spec.tls_binding.mode != TLSMode.DISABLED:
                        t_tls_0 = time.perf_counter()
                        ssl_ctx = self.tls_builder.build_ssl_context(spec.tls_binding, provider_id=spec.provider_id)
                        if ssl_ctx:
                            try:
                                ssl_sock = ssl_ctx.wrap_socket(
                                    s,
                                    server_hostname=spec.tls_binding.server_name_override or spec.host,
                                )
                                tls_ms = (time.perf_counter() - t_tls_0) * 1000.0
                                _, tls_cipher, _ = TLSContextBuilder.verify_peer_certificate(
                                    ssl_sock, spec.tls_binding.expected_cert_fingerprint
                                )
                                ssl_sock.close()
                            except Exception as exc:
                                s.close()
                                failure = ConnectionFailure(
                                    error_code="PROBE_TLS_FAILED",
                                    category=FailureCategory.TLS_FAILURE,
                                    message=f"TLS handshake failed: {redact_text(str(exc))}",
                                    retryable=False,
                                    provider_id=spec.provider_id,
                                    endpoint_fingerprint=fp,
                                )
                                return ConnectionTestResult(
                                    is_successful=False,
                                    provider_id=spec.provider_id,
                                    endpoint_fingerprint=fp,
                                    dns_latency_ms=dns_ms,
                                    tcp_latency_ms=tcp_ms,
                                    tls_latency_ms=tls_ms,
                                    total_handshake_ms=(time.perf_counter() - t_start) * 1000.0,
                                    failure=failure,
                                )
                    else:
                        s.close()

                except Exception as exc:
                    failure = ConnectionFailure(
                        error_code="PROBE_TCP_FAILED",
                        category=FailureCategory.ENDPOINT_UNAVAILABLE,
                        message=f"TCP connection failed to {resolved_route.effective_host}:{resolved_route.effective_port or spec.port}: {redact_text(str(exc))}",
                        retryable=True,
                        provider_id=spec.provider_id,
                        endpoint_fingerprint=fp,
                    )
                    return ConnectionTestResult(
                        is_successful=False,
                        provider_id=spec.provider_id,
                        endpoint_fingerprint=fp,
                        dns_latency_ms=dns_ms,
                        tcp_latency_ms=(time.perf_counter() - t_tcp_0) * 1000.0,
                        total_handshake_ms=(time.perf_counter() - t_start) * 1000.0,
                        failure=failure,
                    )

            # 4. Provider Protocol Connection & Auth Timing
            t_auth_0 = time.perf_counter()
            creds: dict[str, Any] = {}
            conn = None
            try:
                ssl_ctx = self.tls_builder.build_ssl_context(spec.tls_binding, provider_id=spec.provider_id)
                creds = self.auth_manager.resolve_credentials(spec.auth_spec, provider_id=spec.provider_id)
                conn = strategy.connect(spec, resolved_route, creds, ssl_ctx)
                auth_ms = (time.perf_counter() - t_auth_0) * 1000.0

                # Attest identity to extract server version
                identity = strategy.attest_physical_identity(conn, spec, resolved_route)
                server_version = identity.server_version

                # Clean close
                strategy.close(conn)
                conn = None

            except Exception as exc:
                if conn is not None:
                    try:
                        strategy.close(conn)
                    except Exception:
                        pass
                failure = strategy.normalize_error(exc, stage="CONNECT_PROBE")
                return ConnectionTestResult(
                    is_successful=False,
                    provider_id=spec.provider_id,
                    endpoint_fingerprint=fp,
                    dns_latency_ms=dns_ms,
                    tcp_latency_ms=tcp_ms,
                    tls_latency_ms=tls_ms,
                    auth_latency_ms=(time.perf_counter() - t_auth_0) * 1000.0,
                    total_handshake_ms=(time.perf_counter() - t_start) * 1000.0,
                    failure=failure,
                )
            finally:
                wipe_credentials_dict(creds)

        total_ms = (time.perf_counter() - t_start) * 1000.0
        return ConnectionTestResult(
            is_successful=True,
            provider_id=spec.provider_id,
            endpoint_fingerprint=fp,
            dns_latency_ms=dns_ms,
            tcp_latency_ms=tcp_ms,
            tls_latency_ms=tls_ms,
            auth_latency_ms=auth_ms,
            total_handshake_ms=total_ms,
            server_version=server_version,
            tls_cipher=tls_cipher,
        )

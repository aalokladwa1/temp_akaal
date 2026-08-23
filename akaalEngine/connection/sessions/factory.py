"""
akaalEngine.connection.sessions.factory
=======================================
Physical session creation factory binding route resolution, secret resolution,
TLS context construction, and provider strategies.
"""

from __future__ import annotations

import logging
import os
import threading
import uuid
from typing import Optional, Tuple

from akaalEngine.connection.catalog.provider_catalog import ProviderCatalog, default_provider_catalog
from akaalEngine.connection.identity.fingerprint import compute_endpoint_fingerprint
from akaalEngine.connection.models.endpoint import EndpointSpec
from akaalEngine.connection.models.errors import (
    ConnectionEngineException,
    ConnectionFailure,
    FailureCategory,
    ProviderInternalError,
)
from akaalEngine.connection.models.session import InternalSessionHandle, SessionRequest
from akaalEngine.connection.routing.resolver import ResolvedRoute, RouteResolver, default_route_resolver
from akaalEngine.connection.security.authentication import AuthenticationManager, wipe_credentials_dict
from akaalEngine.connection.security.redaction import redact_text
from akaalEngine.connection.security.secret_consumer import SecretConsumer, default_secret_consumer
from akaalEngine.connection.security.tls import TLSContextBuilder
from akaalEngine.connection.sessions.initialization import SessionInitializer

logger = logging.getLogger("akaalEngine.connection.sessions.factory")


class SessionFactory:
    """
    Creates physical connection sessions and wraps them in initialized InternalSessionHandles.
    """

    def __init__(
        self,
        catalog: Optional[ProviderCatalog] = None,
        route_resolver: Optional[RouteResolver] = None,
        secret_consumer: Optional[SecretConsumer] = None,
    ) -> None:
        self.catalog = catalog or default_provider_catalog
        self.route_resolver = route_resolver or default_route_resolver
        self.secret_consumer = secret_consumer or default_secret_consumer
        self.auth_manager = AuthenticationManager(self.secret_consumer)
        self.tls_builder = TLSContextBuilder(self.secret_consumer)

    def create_physical_session(
        self,
        request: SessionRequest,
    ) -> Tuple[InternalSessionHandle, ResolvedRoute]:
        """
        Executes end-to-end physical connection establishment for a SessionRequest.
        Attaches resolved route to session handle and wipes credentials in a finally block.
        """
        spec = request.endpoint_spec
        strategy = self.catalog.get_strategy(spec.provider_id)

        # 1. Validate spec
        strategy.validate_configuration(spec)

        # 2. Compute fingerprint (using current catalog generation)
        cat_gen = self.catalog.get_catalog_generation() if hasattr(self.catalog, "get_catalog_generation") else 1
        fp = compute_endpoint_fingerprint(spec, catalog_generation=cat_gen).fingerprint_sha256

        # 3. Resolve Route
        resolved_route = self.route_resolver.resolve_route(spec)

        # 4. Build TLS Context
        ssl_ctx = self.tls_builder.build_ssl_context(spec.tls_binding, provider_id=spec.provider_id)

        # 5. Resolve Credentials (ephemeral)
        creds: dict[str, Any] = {}
        raw_conn = None
        handle = None
        try:
            creds = self.auth_manager.resolve_credentials(spec.auth_spec, provider_id=spec.provider_id)

            # 6. Establish Physical Connection
            raw_conn = strategy.connect(spec, resolved_route, creds, ssl_ctx)

            # 7. Wrap in InternalSessionHandle
            session_id = f"sess-{uuid.uuid4().hex[:12]}"
            handle = InternalSessionHandle(
                session_id=session_id,
                fingerprint=fp,
                purpose=request.purpose,
                provider_id=spec.provider_id,
                physical_connection=raw_conn,
                process_id=os.getpid(),
                thread_id=threading.get_ident(),
                route_resource=resolved_route,
            )

            # 8. Initialize Session (fails closed if mandatory commands fail)
            SessionInitializer.initialize_session(handle, request)

            return handle, resolved_route

        except ConnectionEngineException:
            if raw_conn is not None:
                try:
                    strategy.close(raw_conn)
                except Exception:
                    pass
            resolved_route.close()
            raise
        except Exception as exc:
            if raw_conn is not None:
                try:
                    strategy.close(raw_conn)
                except Exception:
                    pass
            resolved_route.close()
            # Normalize error using provider strategy
            failure = strategy.normalize_error(exc, stage="CONNECT")
            raise ProviderInternalError(failure) from exc
        finally:
            # Deterministically wipe all resolved secret instances in credentials dict
            wipe_credentials_dict(creds)


# Global default session factory
default_session_factory = SessionFactory()

"""
akaalEngine.connection.adapters.config_adapter
=============================================
Translates declarative configuration dictionary values (as defined by Extensions schemas)
into canonical EndpointSpec, AuthenticationSpec, TLSBinding, and RouteSpec objects.
Guarantees zero loss of schema-defined secret references and configuration fields.
"""

from __future__ import annotations

from typing import Any, Mapping, Optional, Sequence

from akaalEngine.connection.models.endpoint import (
    AuthenticationSpec,
    AuthenticationType,
    EndpointRole,
    EndpointSpec,
    RouteSpec,
    RouteType,
    TLSBinding,
    TLSMode,
)


def build_endpoint_spec_from_config(
    provider_id: str,
    config: Mapping[str, Any],
    role: EndpointRole = EndpointRole.SOURCE,
    custom_metadata: Optional[Mapping[str, str]] = None,
) -> EndpointSpec:
    """
    Translates declarative configuration values into an immutable EndpointSpec.
    Canonicalizes all database, cloud, warehouse, NoSQL, and streaming secret references.
    """
    cfg = dict(config)

    # 1. Extract Endpoint / Host / Port / Endpoints
    host = cfg.pop("host", None)
    port = cfg.pop("port", None)
    if port is not None:
        try:
            port = int(port)
        except (ValueError, TypeError):
            port = None
    endpoints = cfg.pop("endpoints", None)
    database_name = cfg.pop("database_name", None) or cfg.pop("database", None) or cfg.pop("keyspace", None)
    schema_name = cfg.pop("schema_name", None) or cfg.pop("schema", None)
    cloud_resource_id = cfg.pop("cloud_resource_id", None)
    region = cfg.pop("region", None)
    account_id = cfg.pop("account_id", None) or cfg.pop("account", None) or cfg.pop("project_id", None)

    # 2. Extract Authentication Parameters
    auth_type_str = cfg.pop("auth_type", None)
    username = cfg.pop("username", None) or cfg.pop("user", None)

    # Secret references
    password_ref = cfg.pop("password_ref", None)
    secret_ref = cfg.pop("secret_ref", None) or password_ref
    session_token_ref = cfg.pop("session_token_ref", None)
    access_key_id_ref = cfg.pop("access_key_id_ref", None)
    secret_access_key_ref = cfg.pop("secret_access_key_ref", None)
    account_key_ref = cfg.pop("account_key_ref", None)
    sas_token_ref = cfg.pop("sas_token_ref", None)
    shared_access_key_ref = cfg.pop("shared_access_key_ref", None)
    service_account_json_ref = cfg.pop("service_account_json_ref", None)
    connection_string_ref = cfg.pop("connection_string_ref", None)
    wallet_password_ref = cfg.pop("wallet_password_ref", None)
    api_key_ref = cfg.pop("api_key_ref", None)
    token_ref = cfg.pop("token_ref", None) or cfg.pop("access_token_ref", None)
    key_path = cfg.pop("key_path", None)
    role_arn = cfg.pop("role_arn", None)
    secret_version = cfg.pop("secret_version", "1") or "1"

    # Derive AuthenticationType if not explicitly passed
    auth_type = AuthenticationType.NONE
    if auth_type_str:
        try:
            auth_type = AuthenticationType(auth_type_str)
        except ValueError:
            auth_type = AuthenticationType.CUSTOM_PROVIDER
    elif service_account_json_ref:
        auth_type = AuthenticationType.SECRET_REFERENCE
    elif connection_string_ref:
        auth_type = AuthenticationType.CUSTOM_PROVIDER
    elif wallet_password_ref or cfg.get("privilege_mode") in ("SYSDBA", "SYSOPER"):
        auth_type = AuthenticationType.ORACLE_PRIVILEGED
    elif api_key_ref:
        auth_type = AuthenticationType.API_KEY
    elif access_key_id_ref or secret_access_key_ref or session_token_ref:
        auth_type = AuthenticationType.SECRET_REFERENCE
    elif account_key_ref or sas_token_ref or shared_access_key_ref:
        auth_type = AuthenticationType.SECRET_REFERENCE
    elif token_ref:
        auth_type = AuthenticationType.TOKEN
    elif password_ref or secret_ref or username:
        auth_type = AuthenticationType.PASSWORD

    auth_spec = None
    if (
        auth_type != AuthenticationType.NONE
        or username
        or password_ref
        or secret_ref
        or session_token_ref
        or access_key_id_ref
        or secret_access_key_ref
        or account_key_ref
        or sas_token_ref
        or shared_access_key_ref
        or service_account_json_ref
        or connection_string_ref
        or wallet_password_ref
        or api_key_ref
        or token_ref
    ):
        auth_spec = AuthenticationSpec(
            auth_type=auth_type,
            username=username,
            secret_ref=secret_ref,
            password_ref=password_ref,
            key_path=key_path,
            role_arn=role_arn,
            token_ref=token_ref,
            access_token_ref=token_ref,
            session_token_ref=session_token_ref,
            access_key_id_ref=access_key_id_ref,
            secret_access_key_ref=secret_access_key_ref,
            account_key_ref=account_key_ref,
            sas_token_ref=sas_token_ref,
            shared_access_key_ref=shared_access_key_ref,
            service_account_json_ref=service_account_json_ref,
            connection_string_ref=connection_string_ref,
            wallet_password_ref=wallet_password_ref,
            api_key_ref=api_key_ref,
            secret_version=secret_version,
        )

    # 3. Extract TLS Parameters
    tls_mode_str = cfg.pop("tls_mode", None) or cfg.pop("ssl_mode", None)
    ca_cert_path = cfg.pop("ca_cert_path", None) or cfg.pop("ssl_ca_path", None) or cfg.pop("ssl_cafile", None)
    client_cert_path = cfg.pop("client_cert_path", None) or cfg.pop("ssl_cert_path", None)
    client_key_ref = cfg.pop("client_key_ref", None) or cfg.pop("ssl_key_ref", None)
    allow_self_signed = bool(cfg.pop("allow_self_signed", False))
    expected_fingerprint = cfg.pop("expected_cert_fingerprint", None)
    server_name_override = cfg.pop("server_name_override", None)

    tls_mode = TLSMode.VERIFY_FULL
    if tls_mode_str:
        try:
            tls_mode = TLSMode(tls_mode_str)
        except ValueError:
            tls_mode = TLSMode.REQUIRED
    elif ca_cert_path or client_cert_path:
        tls_mode = TLSMode.VERIFY_CA
    elif provider_id.strip().lower() == "sqlite":
        tls_mode = TLSMode.DISABLED

    tls_binding = TLSBinding(
        mode=tls_mode,
        ca_cert_path=ca_cert_path,
        client_cert_path=client_cert_path,
        client_key_ref=client_key_ref,
        allow_self_signed=allow_self_signed,
        expected_cert_fingerprint=expected_fingerprint,
        server_name_override=server_name_override,
    )

    # 4. Extract Route Parameters
    route_type_str = cfg.pop("route_type", None)
    route_type = RouteType.DIRECT
    if route_type_str:
        try:
            route_type = RouteType(route_type_str)
        except ValueError:
            route_type = RouteType.DIRECT

    route_spec = RouteSpec(
        route_type=route_type,
        proxy_host=cfg.pop("proxy_host", None),
        proxy_port=int(cfg["proxy_port"]) if "proxy_port" in cfg and cfg["proxy_port"] is not None else None,
        ssh_host=cfg.pop("ssh_host", None),
        ssh_port=int(cfg.pop("ssh_port", 22)),
        ssh_user=cfg.pop("ssh_user", None),
        private_endpoint_id=cfg.pop("private_endpoint_id", None),
        connect_timeout_ms=int(cfg.pop("connect_timeout_ms", 15000)),
        socket_timeout_ms=int(cfg.pop("socket_timeout_ms", 30000)),
    )

    # Remaining keys become provider options
    return EndpointSpec(
        provider_id=provider_id,
        host=host,
        port=port,
        endpoints=endpoints,
        database_name=database_name,
        role=role,
        schema_name=schema_name,
        auth_spec=auth_spec,
        tls_binding=tls_binding,
        route_spec=route_spec,
        options=cfg,
        cloud_resource_id=cloud_resource_id,
        region=region,
        account_id=account_id,
        custom_metadata=dict(custom_metadata or {}),
    )

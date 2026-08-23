"""
akaalEngine.connection.identity.fingerprint
===========================================
Deterministic cryptographic endpoint binding fingerprint calculation.
Guarantees 100% secret-free, canonical JSON serialization and SHA-256 identity hashing.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from akaalEngine.connection.models.endpoint import EndpointSpec
from akaalEngine.connection.models.identity import EndpointBindingFingerprint
from akaalEngine.connection.security.redaction import redact_mapping


def canonicalize_endpoint_spec(spec: EndpointSpec, catalog_generation: int = 1) -> dict[str, Any]:
    """
    Transforms EndpointSpec into a deterministic, sorted, secret-free dictionary.
    Includes non-secret credential references, TLS bindings, routes, and catalog generations.
    """
    auth_data = None
    if spec.auth_spec:
        auth_data = {
            "auth_type": spec.auth_spec.auth_type.value,
            "username": spec.auth_spec.username or "",
            "secret_ref": spec.auth_spec.secret_ref or "",
            "password_ref": spec.auth_spec.password_ref or "",
            "token_ref": spec.auth_spec.token_ref or "",
            "access_token_ref": spec.auth_spec.access_token_ref or "",
            "session_token_ref": spec.auth_spec.session_token_ref or "",
            "access_key_id_ref": spec.auth_spec.access_key_id_ref or "",
            "secret_access_key_ref": spec.auth_spec.secret_access_key_ref or "",
            "account_key_ref": spec.auth_spec.account_key_ref or "",
            "sas_token_ref": spec.auth_spec.sas_token_ref or "",
            "shared_access_key_ref": spec.auth_spec.shared_access_key_ref or "",
            "service_account_json_ref": spec.auth_spec.service_account_json_ref or "",
            "connection_string_ref": spec.auth_spec.connection_string_ref or "",
            "wallet_password_ref": spec.auth_spec.wallet_password_ref or "",
            "api_key_ref": spec.auth_spec.api_key_ref or "",
            "key_path": spec.auth_spec.key_path or "",
            "role_arn": spec.auth_spec.role_arn or "",
            "secret_version": spec.auth_spec.secret_version or "1",
        }

    tls_data = {
        "mode": spec.tls_binding.mode.value,
        "ca_cert_path": spec.tls_binding.ca_cert_path or "",
        "client_cert_path": spec.tls_binding.client_cert_path or "",
        "client_key_ref": spec.tls_binding.client_key_ref or "",
        "tls_min_version": spec.tls_binding.tls_min_version,
        "server_name_override": spec.tls_binding.server_name_override or "",
        "allow_self_signed": spec.tls_binding.allow_self_signed,
        "expected_cert_fingerprint": spec.tls_binding.expected_cert_fingerprint or "",
    }

    route_data = {
        "route_type": spec.route_spec.route_type.value,
        "proxy_host": spec.route_spec.proxy_host or "",
        "proxy_port": spec.route_spec.proxy_port or 0,
        "ssh_host": spec.route_spec.ssh_host or "",
        "ssh_port": spec.route_spec.ssh_port,
        "ssh_user": spec.route_spec.ssh_user or "",
        "ssh_known_hosts_path": spec.route_spec.ssh_known_hosts_path or "",
        "ssh_host_key_fingerprint": spec.route_spec.ssh_host_key_fingerprint or "",
        "allow_unverified_ssh": spec.route_spec.allow_unverified_ssh,
        "private_endpoint_id": spec.route_spec.private_endpoint_id or "",
    }

    # Redact any accidental inline secrets from options dict before sorting
    clean_options = redact_mapping(spec.options)

    canonical_dict = {
        "provider_id": spec.provider_id.strip().lower(),
        "catalog_generation": catalog_generation,
        "host": (spec.host or "").strip().lower(),
        "port": spec.port or 0,
        "endpoints": sorted(str(e).strip().lower() for e in spec.endpoints) if spec.endpoints else [],
        "database_name": (spec.database_name or "").strip(),
        "role": spec.role.value,
        "schema_name": (spec.schema_name or "").strip(),
        "auth": auth_data,
        "tls": tls_data,
        "route": route_data,
        "cloud_resource_id": (spec.cloud_resource_id or "").strip(),
        "region": (spec.region or "").strip().lower(),
        "account_id": (spec.account_id or "").strip(),
        "options": clean_options,
    }

    return canonical_dict


def compute_endpoint_fingerprint(
    spec: EndpointSpec,
    catalog_generation: int = 1,
) -> EndpointBindingFingerprint:
    """
    Computes a deterministic SHA-256 fingerprint for an execution EndpointSpec.
    """
    canonical_dict = canonicalize_endpoint_spec(spec, catalog_generation=catalog_generation)
    canonical_json = json.dumps(canonical_dict, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    fp_sha256 = hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()

    return EndpointBindingFingerprint(
        fingerprint_sha256=fp_sha256,
        canonical_payload_json=canonical_json,
        algorithm="SHA-256",
    )

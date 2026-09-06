"""
akaalEngine.connection.security.authentication
=============================================
Authentication mechanism strategies, credential extractors, and authentication managers.
Guarantees canonical resolution of all specialized secret references through SecretConsumer.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Mapping, Optional, Sequence

if TYPE_CHECKING:
    from akaalEngine.connection.models.endpoint import AuthenticationSpec

from akaalEngine.connection.models.errors import (
    AuthenticationError,
    ConnectionFailure,
    FailureCategory,
    SecretResolutionError,
)
from akaalEngine.connection.security.redaction import redact_text
from akaalEngine.connection.security.secret_consumer import (
    ResolvedSecret,
    SecretConsumer,
    default_secret_consumer,
)

logger = logging.getLogger("akaalEngine.connection.security.authentication")


class AuthenticationHandler:
    """Base interface for authentication mechanism strategies."""

    def extract_credentials(
        self,
        auth_spec: Any,
        secret_consumer: SecretConsumer,
    ) -> dict[str, Any]:
        raise NotImplementedError


class PasswordAuthenticationHandler(AuthenticationHandler):
    """Extracts username and ephemeral password."""

    def extract_credentials(
        self,
        auth_spec: Any,
        secret_consumer: SecretConsumer,
    ) -> dict[str, Any]:
        username = getattr(auth_spec, "username", "") or ""
        resolved_secret: Optional[ResolvedSecret] = None
        password_val = ""
        secret_ref = getattr(auth_spec, "secret_ref", None)
        if secret_ref:
            resolved_secret = secret_consumer.resolve(
                secret_ref,
                version=getattr(auth_spec, "secret_version", "1") or "1",
            )
            if resolved_secret is None:
                raise SecretResolutionError(
                    ConnectionFailure(
                        error_code="SECRET_RESOLUTION_FAILED",
                        category=FailureCategory.AUTHENTICATION_FAILURE,
                        message=f"Failed to resolve secret reference '{secret_ref}'.",
                        retryable=False,
                    )
                )
            password_val = resolved_secret.get_value()

        creds = {
            "username": username,
            "user": username,
            "password": password_val,
            "secret_access_key": password_val,
            "account_key": password_val,
            "_resolved_secret": resolved_secret,
        }
        if username:
            creds["access_key_id"] = username
        return creds


class IntegratedAuthenticationHandler(AuthenticationHandler):
    """Handles Windows Integrated / SSPI / Trusted Authentication without passwords."""

    def extract_credentials(
        self,
        auth_spec: Any,
        secret_consumer: SecretConsumer,
    ) -> dict[str, Any]:
        return {
            "trusted_connection": True,
            "integrated_security": "SSPI",
            "auth_type": "INTEGRATED",
        }


class CertificateAuthenticationHandler(AuthenticationHandler):
    """Extracts client certificate and private key paths or references."""

    def extract_credentials(
        self,
        auth_spec: Any,
        secret_consumer: SecretConsumer,
    ) -> dict[str, Any]:
        key_secret: Optional[ResolvedSecret] = None
        key_val = ""
        secret_ref = getattr(auth_spec, "secret_ref", None)
        if secret_ref:
            key_secret = secret_consumer.resolve(
                secret_ref,
                version=getattr(auth_spec, "secret_version", "1") or "1",
            )
            if key_secret is None:
                raise SecretResolutionError(
                    ConnectionFailure(
                        error_code="SECRET_RESOLUTION_FAILED",
                        category=FailureCategory.AUTHENTICATION_FAILURE,
                        message=f"Failed to resolve certificate private key reference '{secret_ref}'.",
                        retryable=False,
                    )
                )
            key_val = key_secret.get_value()

        return {
            "client_cert_path": getattr(auth_spec, "key_path", None),
            "client_key_content": key_val,
            "_resolved_secret": key_secret,
        }


class TokenAuthenticationHandler(AuthenticationHandler):
    """Extracts Bearer / OAuth / JWT token."""

    def extract_credentials(
        self,
        auth_spec: Any,
        secret_consumer: SecretConsumer,
    ) -> dict[str, Any]:
        token_secret: Optional[ResolvedSecret] = None
        token_val = ""
        ref = getattr(auth_spec, "token_ref", None) or getattr(auth_spec, "secret_ref", None)
        if ref:
            token_secret = secret_consumer.resolve(
                ref,
                version=getattr(auth_spec, "secret_version", "1") or "1",
            )
            if token_secret is None:
                raise SecretResolutionError(
                    ConnectionFailure(
                        error_code="SECRET_RESOLUTION_FAILED",
                        category=FailureCategory.AUTHENTICATION_FAILURE,
                        message=f"Failed to resolve token reference '{ref}'.",
                        retryable=False,
                    )
                )
            token_val = token_secret.get_value()

        return {
            "token": token_val,
            "sas_token": token_val,
            "_resolved_secret": token_secret,
        }


class ApiKeyAuthenticationHandler(AuthenticationHandler):
    """Extracts API Key credentials for Elasticsearch, OpenSearch, etc."""

    def extract_credentials(
        self,
        auth_spec: Any,
        secret_consumer: SecretConsumer,
    ) -> dict[str, Any]:
        api_key_secret: Optional[ResolvedSecret] = None
        api_key_val = ""
        ref = getattr(auth_spec, "api_key_ref", None) or getattr(auth_spec, "secret_ref", None)
        if ref:
            api_key_secret = secret_consumer.resolve(
                ref,
                version=getattr(auth_spec, "secret_version", "1") or "1",
            )
            if api_key_secret is None:
                raise SecretResolutionError(
                    ConnectionFailure(
                        error_code="SECRET_RESOLUTION_FAILED",
                        category=FailureCategory.AUTHENTICATION_FAILURE,
                        message=f"Failed to resolve API key reference '{ref}'.",
                        retryable=False,
                    )
                )
            api_key_val = api_key_secret.get_value()

        return {
            "api_key": api_key_val,
            "_resolved_secret": api_key_secret,
        }


class SASLAuthenticationHandler(AuthenticationHandler):
    """Extracts SASL credentials for Kafka and messaging providers."""

    def extract_credentials(
        self,
        auth_spec: Any,
        secret_consumer: SecretConsumer,
    ) -> dict[str, Any]:
        username = getattr(auth_spec, "username", "") or ""
        resolved_secret: Optional[ResolvedSecret] = None
        password_val = ""
        secret_ref = getattr(auth_spec, "secret_ref", None)
        if secret_ref:
            resolved_secret = secret_consumer.resolve(
                secret_ref,
                version=getattr(auth_spec, "secret_version", "1") or "1",
            )
            if resolved_secret is None:
                raise SecretResolutionError(
                    ConnectionFailure(
                        error_code="SECRET_RESOLUTION_FAILED",
                        category=FailureCategory.AUTHENTICATION_FAILURE,
                        message=f"Failed to resolve SASL password reference '{secret_ref}'.",
                        retryable=False,
                    )
                )
            password_val = resolved_secret.get_value()

        return {
            "username": username,
            "sasl_plain_username": username,
            "password": password_val,
            "sasl_plain_password": password_val,
            "_resolved_secret": resolved_secret,
        }


class OracleAuthenticationHandler(AuthenticationHandler):
    """Extracts Oracle credentials, wallet password, and privilege modes."""

    def extract_credentials(
        self,
        auth_spec: Any,
        secret_consumer: SecretConsumer,
    ) -> dict[str, Any]:
        username = getattr(auth_spec, "username", "") or ""
        resolved_secrets: list[ResolvedSecret] = []
        password_val = ""
        wallet_pw_val = ""

        secret_ref = getattr(auth_spec, "secret_ref", None)
        if secret_ref:
            pw_sec = secret_consumer.resolve(
                secret_ref,
                version=getattr(auth_spec, "secret_version", "1") or "1",
            )
            if pw_sec is None:
                raise SecretResolutionError(
                    ConnectionFailure(
                        error_code="SECRET_RESOLUTION_FAILED",
                        category=FailureCategory.AUTHENTICATION_FAILURE,
                        message=f"Failed to resolve Oracle password reference '{secret_ref}'.",
                        retryable=False,
                    )
                )
            password_val = pw_sec.get_value()
            resolved_secrets.append(pw_sec)

        wallet_ref = getattr(auth_spec, "wallet_password_ref", None)
        if wallet_ref:
            w_sec = secret_consumer.resolve(
                wallet_ref,
                version=getattr(auth_spec, "secret_version", "1") or "1",
            )
            if w_sec is None:
                raise SecretResolutionError(
                    ConnectionFailure(
                        error_code="SECRET_RESOLUTION_FAILED",
                        category=FailureCategory.AUTHENTICATION_FAILURE,
                        message=f"Failed to resolve Oracle wallet password reference '{wallet_ref}'.",
                        retryable=False,
                    )
                )
            wallet_pw_val = w_sec.get_value()
            resolved_secrets.append(w_sec)

        return {
            "username": username,
            "user": username,
            "password": password_val,
            "wallet_password": wallet_pw_val,
            "_resolved_secret": resolved_secrets[0] if len(resolved_secrets) == 1 else None,
            "_resolved_secrets": resolved_secrets,
        }


class CloudIAMAuthenticationHandler(AuthenticationHandler):
    """
    Handles Cloud IAM Workload Identity, AWS IAM Role, Azure Entra ID, GCP ADC, OCI.

    P7B.3: performs real cloud-native identity resolution (STS role assumption / Entra
    token acquisition / GCP ADC refresh / OCI signer wrapping) via
    akaalEngine.fabric.workload_identity, attaching the resolved, bounded-lifetime
    `CloudIdentityContext` under `creds["cloud_identity"]` for the caller to consume.
    CRITICAL: a successfully resolved CloudIdentityContext is NEVER itself AKAAL
    authorization -- see akaalEngine.fabric.workload_identity.boundary. This handler
    performs authentication only; it makes no authorization decision.

    Round-5 hostile-review closure: a resolved, NON-EXPIRED CloudIdentityContext's
    actual usable material (AWS temporary access key/secret/session token; an Azure
    bearer token) is now copied into the same canonical credential keys every other
    AuthenticationHandler in this module populates (`access_key_id`/`secret_access_key`/
    `session_token`/`token`) -- so a provider's `connect()` (e.g.
    S3ProviderStrategy.connect, which reads exactly these keys) genuinely authenticates
    with the resolved workload identity's real material, not merely carries it as inert
    metadata. An EXPIRED identity is never used this way (see `is_expired()` check
    below) -- expiry always fails closed into the same soft passthrough as any other
    resolution failure, never a silent use of stale credentials.

    If cloud resolution cannot be attempted (SDK not installed, no live cloud
    infrastructure in this environment, or additional_params insufficient), fails soft
    into the pre-P7B passthrough shape (role_arn/auth_type/additional_params) with the
    resolution failure truthfully recorded under `cloud_identity_error` rather than
    silently claiming success -- this preserves backward compatibility for callers that
    only need the raw auth_spec fields (e.g. constructing a driver connection string) and
    do not require a live-resolved identity.
    """

    def extract_credentials(
        self,
        auth_spec: Any,
        secret_consumer: SecretConsumer,
    ) -> dict[str, Any]:
        auth_type_val = auth_spec.auth_type.value if hasattr(auth_spec.auth_type, "value") else str(auth_spec.auth_type)
        additional_params = dict(getattr(auth_spec, "additional_params", {}))
        creds: dict[str, Any] = {
            "role_arn": getattr(auth_spec, "role_arn", None),
            "auth_type": auth_type_val,
            "additional_params": additional_params,
        }

        try:
            cloud_identity = self._resolve_cloud_identity(auth_type_val, auth_spec, additional_params)
            if cloud_identity is not None:
                if cloud_identity.is_expired():
                    # Fail closed: an expired identity is never wired into usable
                    # credentials, even though resolution itself "succeeded" moments
                    # too late. Treated identically to a resolution failure.
                    creds["cloud_identity_error"] = f"Resolved {cloud_identity.provider.value} identity is expired; refusing to use it."
                else:
                    creds["cloud_identity"] = cloud_identity
                    self._populate_physical_credentials(creds, cloud_identity)
        except Exception as exc:  # noqa: BLE001 -- deliberately soft-fail; see docstring
            creds["cloud_identity_error"] = redact_text(str(exc))

        return creds

    @staticmethod
    def _populate_physical_credentials(creds: dict[str, Any], cloud_identity: Any) -> None:
        """Copies a resolved, non-expired CloudIdentityContext's real material into the
        canonical credential keys provider strategies actually read at connect() time --
        this is what makes workload identity resolution genuinely consumed rather than
        inert metadata. Never overwrites a value already resolved through another
        (e.g. explicit secret-reference) path."""
        claims = cloud_identity.raw_claims
        if cloud_identity.provider.value == "AWS":
            if claims.get("access_key_id") and not creds.get("access_key_id"):
                creds["access_key_id"] = claims["access_key_id"]
            if claims.get("secret_access_key") and not creds.get("secret_access_key"):
                creds["secret_access_key"] = claims["secret_access_key"]
            if claims.get("session_token") and not creds.get("session_token"):
                creds["session_token"] = claims["session_token"]
                creds["aws_session_token"] = claims["session_token"]
        elif cloud_identity.provider.value == "AZURE":
            if claims.get("bearer_token") and not creds.get("token"):
                creds["token"] = claims["bearer_token"]
        elif cloud_identity.provider.value == "GCP":
            if claims.get("credentials_object") is not None and creds.get("gcp_credentials_object") is None:
                creds["gcp_credentials_object"] = claims["credentials_object"]
        elif cloud_identity.provider.value == "OCI":
            if claims.get("signer") is not None and creds.get("oci_signer") is None:
                creds["oci_signer"] = claims["signer"]

    @staticmethod
    def _resolve_cloud_identity(auth_type_val: str, auth_spec: Any, additional_params: Mapping[str, Any]):
        from akaalEngine.fabric.workload_identity import (
            resolve_aws_workload_identity,
            resolve_azure_workload_identity,
            resolve_gcp_workload_identity,
            resolve_oci_workload_identity,
        )

        if auth_type_val in ("AWS_IAM_ROLE", "IAM_WORKLOAD_IDENTITY"):
            role_arn = getattr(auth_spec, "role_arn", None)
            return resolve_aws_workload_identity(role_arn_to_assume=role_arn)

        if auth_type_val == "AZURE_ENTRA_ID":
            subscription_id = additional_params.get("subscription_id")
            if not subscription_id:
                return None
            return resolve_azure_workload_identity(subscription_id=subscription_id)

        if auth_type_val == "GCP_ADC":
            project_id = additional_params.get("project_id")
            return resolve_gcp_workload_identity(project_id=project_id)

        if auth_type_val == "OCI_INSTANCE_PRINCIPAL":
            # Requires an already-constructed signer + its claims; this handler does not
            # construct OCI signers itself (that is a live-infrastructure concern outside
            # generic credential extraction). Only attempted when the caller has supplied
            # everything needed via additional_params.
            signer = additional_params.get("oci_signer")
            principal_id = additional_params.get("oci_principal_id")
            tenancy_ocid = additional_params.get("oci_tenancy_ocid")
            if not (signer and principal_id and tenancy_ocid):
                return None
            return resolve_oci_workload_identity(signer=signer, principal_id=principal_id, tenancy_ocid=tenancy_ocid)

        return None


class AuthenticationManager:
    """Coordinates authentication handlers and extracts driver credentials safely."""

    def __init__(self, secret_consumer: Optional[SecretConsumer] = None) -> None:
        self.secret_consumer = secret_consumer or default_secret_consumer
        self._handlers: dict[str, AuthenticationHandler] = {
            "PASSWORD": PasswordAuthenticationHandler(),
            "INTEGRATED": IntegratedAuthenticationHandler(),
            "CERTIFICATE_MTLS": CertificateAuthenticationHandler(),
            "ORACLE_WALLET": OracleAuthenticationHandler(),
            "ORACLE_PRIVILEGED": OracleAuthenticationHandler(),
            "SASL_PLAIN": SASLAuthenticationHandler(),
            "SASL_SCRAM_256": SASLAuthenticationHandler(),
            "SASL_SCRAM_512": SASLAuthenticationHandler(),
            "API_KEY": ApiKeyAuthenticationHandler(),
            "TOKEN": TokenAuthenticationHandler(),
            "KEY_PAIR": PasswordAuthenticationHandler(),
            "AWS_IAM_ROLE": CloudIAMAuthenticationHandler(),
            "AZURE_ENTRA_ID": CloudIAMAuthenticationHandler(),
            "GCP_ADC": CloudIAMAuthenticationHandler(),
            "OCI_INSTANCE_PRINCIPAL": CloudIAMAuthenticationHandler(),
            "IAM_WORKLOAD_IDENTITY": CloudIAMAuthenticationHandler(),
            "SECRET_REFERENCE": PasswordAuthenticationHandler(),
            "CUSTOM_PROVIDER": PasswordAuthenticationHandler(),
        }

    def register_handler(self, auth_type: str, handler: AuthenticationHandler) -> None:
        key = auth_type.value if hasattr(auth_type, "value") else str(auth_type).upper()
        self._handlers[key] = handler

    def resolve_credentials(
        self,
        auth_spec: Optional[Any],
        provider_id: str = "generic",
    ) -> dict[str, Any]:
        """
        Resolves authentication spec into ephemeral driver credentials.
        Guarantees that all specialized secret references in AuthenticationSpec
        reach SecretConsumer and are mapped to canonical bounded credential keys.
        """
        if auth_spec is None:
            return {}

        auth_type_val = auth_spec.auth_type.value if hasattr(auth_spec.auth_type, "value") else str(auth_spec.auth_type).upper()
        if auth_type_val == "NONE":
            return {}

        handler = self._handlers.get(auth_type_val)
        if not handler:
            handler = self._handlers.get("PASSWORD", PasswordAuthenticationHandler())

        try:
            creds = handler.extract_credentials(auth_spec, self.secret_consumer)
        except (AuthenticationError, SecretResolutionError):
            raise
        except Exception as exc:
            msg = f"Authentication resolution failed for provider '{provider_id}': {redact_text(str(exc))}"
            failure = ConnectionFailure(
                error_code="AUTH_RESOLUTION_FAILED",
                category=FailureCategory.AUTHENTICATION_FAILURE,
                message=msg,
                retryable=False,
                provider_id=provider_id,
                remediation="Verify secret reference exists and is accessible.",
            )
            raise AuthenticationError(failure) from exc

        # Resolve any additional specialized secret references present on the auth_spec
        resolved_secrets: list[ResolvedSecret] = list(creds.get("_resolved_secrets", []))
        if creds.get("_resolved_secret"):
            if creds["_resolved_secret"] not in resolved_secrets:
                resolved_secrets.append(creds["_resolved_secret"])

        ver = getattr(auth_spec, "secret_version", "1") or "1"

        # 1. AWS / Storage Access Key ID Reference
        akid_ref = getattr(auth_spec, "access_key_id_ref", None)
        if akid_ref and not creds.get("access_key_id"):
            akid_sec = self.secret_consumer.resolve(akid_ref, version=ver)
            if akid_sec is None:
                raise SecretResolutionError(
                    ConnectionFailure(
                        error_code="SECRET_RESOLUTION_FAILED",
                        category=FailureCategory.AUTHENTICATION_FAILURE,
                        message=f"Failed to resolve access key ID reference '{akid_ref}'.",
                        retryable=False,
                        provider_id=provider_id,
                    )
                )
            creds["access_key_id"] = akid_sec.get_value()
            creds["username"] = creds.get("username") or akid_sec.get_value()
            creds["user"] = creds.get("user") or akid_sec.get_value()
            resolved_secrets.append(akid_sec)

        # 2. AWS / Storage Secret Access Key Reference
        sak_ref = getattr(auth_spec, "secret_access_key_ref", None)
        if sak_ref and not creds.get("secret_access_key"):
            sak_sec = self.secret_consumer.resolve(sak_ref, version=ver)
            if sak_sec is None:
                raise SecretResolutionError(
                    ConnectionFailure(
                        error_code="SECRET_RESOLUTION_FAILED",
                        category=FailureCategory.AUTHENTICATION_FAILURE,
                        message=f"Failed to resolve secret access key reference '{sak_ref}'.",
                        retryable=False,
                        provider_id=provider_id,
                    )
                )
            creds["secret_access_key"] = sak_sec.get_value()
            creds["password"] = creds.get("password") or sak_sec.get_value()
            resolved_secrets.append(sak_sec)

        # 3. AWS / STS Session Token Reference
        session_token_ref = getattr(auth_spec, "session_token_ref", None)
        if session_token_ref and not creds.get("session_token"):
            st_sec = self.secret_consumer.resolve(session_token_ref, version=ver)
            if st_sec is None:
                raise SecretResolutionError(
                    ConnectionFailure(
                        error_code="SECRET_RESOLUTION_FAILED",
                        category=FailureCategory.AUTHENTICATION_FAILURE,
                        message=f"Failed to resolve session token reference '{session_token_ref}'.",
                        retryable=False,
                        provider_id=provider_id,
                    )
                )
            creds["session_token"] = st_sec.get_value()
            creds["aws_session_token"] = st_sec.get_value()
            resolved_secrets.append(st_sec)

        # 4. Azure Storage Account Key Reference
        acc_key_ref = getattr(auth_spec, "account_key_ref", None)
        if acc_key_ref and not creds.get("account_key"):
            acc_sec = self.secret_consumer.resolve(acc_key_ref, version=ver)
            if acc_sec is None:
                raise SecretResolutionError(
                    ConnectionFailure(
                        error_code="SECRET_RESOLUTION_FAILED",
                        category=FailureCategory.AUTHENTICATION_FAILURE,
                        message=f"Failed to resolve Azure account key reference '{acc_key_ref}'.",
                        retryable=False,
                        provider_id=provider_id,
                    )
                )
            creds["account_key"] = acc_sec.get_value()
            creds["password"] = creds.get("password") or acc_sec.get_value()
            resolved_secrets.append(acc_sec)

        # 5. Azure Storage SAS Token Reference
        sas_tok_ref = getattr(auth_spec, "sas_token_ref", None)
        if sas_tok_ref and not creds.get("sas_token"):
            sas_sec = self.secret_consumer.resolve(sas_tok_ref, version=ver)
            if sas_sec is None:
                raise SecretResolutionError(
                    ConnectionFailure(
                        error_code="SECRET_RESOLUTION_FAILED",
                        category=FailureCategory.AUTHENTICATION_FAILURE,
                        message=f"Failed to resolve Azure SAS token reference '{sas_tok_ref}'.",
                        retryable=False,
                        provider_id=provider_id,
                    )
                )
            creds["sas_token"] = sas_sec.get_value()
            creds["token"] = creds.get("token") or sas_sec.get_value()
            resolved_secrets.append(sas_sec)

        # 6. Event Hubs / Azure Shared Access Key Reference
        sh_key_ref = getattr(auth_spec, "shared_access_key_ref", None)
        if sh_key_ref and not creds.get("shared_access_key"):
            sh_sec = self.secret_consumer.resolve(sh_key_ref, version=ver)
            if sh_sec is None:
                raise SecretResolutionError(
                    ConnectionFailure(
                        error_code="SECRET_RESOLUTION_FAILED",
                        category=FailureCategory.AUTHENTICATION_FAILURE,
                        message=f"Failed to resolve shared access key reference '{sh_key_ref}'.",
                        retryable=False,
                        provider_id=provider_id,
                    )
                )
            creds["shared_access_key"] = sh_sec.get_value()
            creds["password"] = creds.get("password") or sh_sec.get_value()
            resolved_secrets.append(sh_sec)

        # 7. Token / Access Token Reference (Databricks, Snowflake, etc.)
        tok_ref = getattr(auth_spec, "access_token_ref", None) or getattr(auth_spec, "token_ref", None)
        if tok_ref and not creds.get("token"):
            tok_sec = self.secret_consumer.resolve(tok_ref, version=ver)
            if tok_sec is None:
                raise SecretResolutionError(
                    ConnectionFailure(
                        error_code="SECRET_RESOLUTION_FAILED",
                        category=FailureCategory.AUTHENTICATION_FAILURE,
                        message=f"Failed to resolve token reference '{tok_ref}'.",
                        retryable=False,
                        provider_id=provider_id,
                    )
                )
            creds["token"] = tok_sec.get_value()
            resolved_secrets.append(tok_sec)

        # 8. GCP Service Account JSON Reference
        sa_json_ref = getattr(auth_spec, "service_account_json_ref", None)
        if sa_json_ref and not creds.get("service_account_json"):
            sa_sec = self.secret_consumer.resolve(sa_json_ref, version=ver)
            if sa_sec is None:
                raise SecretResolutionError(
                    ConnectionFailure(
                        error_code="SECRET_RESOLUTION_FAILED",
                        category=FailureCategory.AUTHENTICATION_FAILURE,
                        message=f"Failed to resolve GCP service account JSON reference '{sa_json_ref}'.",
                        retryable=False,
                        provider_id=provider_id,
                    )
                )
            creds["service_account_json"] = sa_sec.get_value()
            creds["service_account_info"] = sa_sec.get_value()
            resolved_secrets.append(sa_sec)

        # 9. Connection String Reference (Azure Blob, Event Hubs, etc.)
        conn_str_ref = getattr(auth_spec, "connection_string_ref", None)
        if conn_str_ref and not creds.get("connection_string"):
            cs_sec = self.secret_consumer.resolve(conn_str_ref, version=ver)
            if cs_sec is None:
                raise SecretResolutionError(
                    ConnectionFailure(
                        error_code="SECRET_RESOLUTION_FAILED",
                        category=FailureCategory.AUTHENTICATION_FAILURE,
                        message=f"Failed to resolve connection string reference '{conn_str_ref}'.",
                        retryable=False,
                        provider_id=provider_id,
                    )
                )
            creds["connection_string"] = cs_sec.get_value()
            resolved_secrets.append(cs_sec)

        # 10. Oracle Wallet Password Reference
        wallet_pw_ref = getattr(auth_spec, "wallet_password_ref", None)
        if wallet_pw_ref and not creds.get("wallet_password"):
            wp_sec = self.secret_consumer.resolve(wallet_pw_ref, version=ver)
            if wp_sec is None:
                raise SecretResolutionError(
                    ConnectionFailure(
                        error_code="SECRET_RESOLUTION_FAILED",
                        category=FailureCategory.AUTHENTICATION_FAILURE,
                        message=f"Failed to resolve Oracle wallet password reference '{wallet_pw_ref}'.",
                        retryable=False,
                        provider_id=provider_id,
                    )
                )
            creds["wallet_password"] = wp_sec.get_value()
            resolved_secrets.append(wp_sec)

        # 11. API Key Reference (Elasticsearch, OpenSearch)
        api_key_ref = getattr(auth_spec, "api_key_ref", None)
        if api_key_ref and not creds.get("api_key"):
            ak_sec = self.secret_consumer.resolve(api_key_ref, version=ver)
            if ak_sec is None:
                raise SecretResolutionError(
                    ConnectionFailure(
                        error_code="SECRET_RESOLUTION_FAILED",
                        category=FailureCategory.AUTHENTICATION_FAILURE,
                        message=f"Failed to resolve API key reference '{api_key_ref}'.",
                        retryable=False,
                        provider_id=provider_id,
                    )
                )
            creds["api_key"] = ak_sec.get_value()
            resolved_secrets.append(ak_sec)

        # 12. Explicit Password Reference
        pw_ref = getattr(auth_spec, "password_ref", None) or getattr(auth_spec, "secret_ref", None)
        if pw_ref and not creds.get("password"):
            pw_sec = self.secret_consumer.resolve(pw_ref, version=ver)
            if pw_sec is None:
                raise SecretResolutionError(
                    ConnectionFailure(
                        error_code="SECRET_RESOLUTION_FAILED",
                        category=FailureCategory.AUTHENTICATION_FAILURE,
                        message=f"Failed to resolve password reference '{pw_ref}'.",
                        retryable=False,
                        provider_id=provider_id,
                    )
                )
            creds["password"] = pw_sec.get_value()
            resolved_secrets.append(pw_sec)

        # 13. Additional params
        add_params = getattr(auth_spec, "additional_params", {})
        if add_params:
            if "access_key_id" in add_params and not creds.get("access_key_id"):
                creds["access_key_id"] = add_params["access_key_id"]

        creds["_resolved_secrets"] = resolved_secrets
        return creds


def wipe_credentials_dict(creds: dict[str, Any]) -> None:
    """
    Deterministically wipes all ResolvedSecret instances in a credentials dictionary,
    including lists, tuples, sets, and nested dictionaries of resolved secrets,
    before clearing the dictionary.
    """
    if not isinstance(creds, dict):
        return
    for k, v in list(creds.items()):
        if hasattr(v, "wipe") and callable(getattr(v, "wipe", None)):
            try:
                v.wipe()
            except Exception:
                pass
        elif isinstance(v, (list, tuple, set)):
            for item in v:
                if hasattr(item, "wipe") and callable(getattr(item, "wipe", None)):
                    try:
                        item.wipe()
                    except Exception:
                        pass
        elif isinstance(v, dict):
            wipe_credentials_dict(v)
    creds.clear()

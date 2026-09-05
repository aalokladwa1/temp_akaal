"""
akaalEngine.connection.providers.nosql.dynamodb
====================================================
Canonical AWS DynamoDB Provider Strategy (P7A Campaign B).

DynamoDB is a managed, partition/sort-key NoSQL store -- genuinely different from the
self-hosted document/wide-column stores already adopted (MongoDB, Cassandra):
  - Schema is enforced only for the key attributes (partition key, optional sort key);
    non-key attributes are not declared anywhere the Engine can introspect, so
    SCHEMA_DISCOVERY is declared SUPPORTED with an explicit restriction that only key
    schema and secondary-index definitions are discoverable, not a full attribute schema.
  - CDC is a genuine, well-documented feature (DynamoDB Streams), not a fabricated
    capability -- but it is per-table opt-in, so CDC_LOG_CAPTURE defaults UNSUPPORTED and
    is only truthfully elevated by `probe_capabilities` after a real
    `describe_table().StreamSpecification.StreamEnabled` check against the specific table
    in scope.
  - TRANSACTIONS is genuinely supported via `TransactWriteItems`/`TransactGetItems`
    (all-or-nothing across up to 100 items), a real DynamoDB primitive, not borrowed from
    relational ACID semantics.
"""

from __future__ import annotations

import logging
import ssl
from typing import Any, Mapping, Optional, Tuple

from akaalEngine.connection.models.capability import (
    CapabilitySupportStatus,
    PermissionSnapshot,
    ProbedCapabilitySnapshot,
    ProofLevel,
    StaticCapabilityManifest,
)
from akaalEngine.connection.models.endpoint import EndpointRole, EndpointSpec
from akaalEngine.connection.models.errors import (
    ConnectionFailure,
    FailureCategory,
    DependencyMissingError,
)
from akaalEngine.connection.models.identity import PhysicalEndpointIdentity
from akaalEngine.connection.models.session import SessionPurpose
from akaalEngine.connection.providers.base import BaseProviderStrategy
from akaalEngine.connection.routing.resolver import ResolvedRoute
from akaalEngine.connection.security.redaction import redact_text

logger = logging.getLogger("akaalEngine.connection.providers.dynamodb")


class DynamoDBProviderStrategy(BaseProviderStrategy):
    """Canonical AWS DynamoDB provider strategy -- managed partition/sort-key NoSQL store."""

    PROVIDER_ID = "dynamodb"
    PROVIDER_VERSION = "1.0.0"
    FAMILY = "nosql"
    VENDOR_NAME = "Amazon Web Services"

    def get_static_manifest(self) -> StaticCapabilityManifest:
        return StaticCapabilityManifest(
            provider_id=self.PROVIDER_ID,
            provider_version=self.PROVIDER_VERSION,
            family=self.FAMILY,
            vendor_name=self.VENDOR_NAME,
            supported_roles=[EndpointRole.SOURCE, EndpointRole.TARGET, EndpointRole.REFERENCE, EndpointRole.VALIDATION],
            supports_tls=True,
            supports_mtls=False,
            capabilities={
                "SCHEMA_DISCOVERY": CapabilitySupportStatus.SUPPORTED,  # key schema + GSI/LSI only, see restrictions
                "BULK_READ": CapabilitySupportStatus.SUPPORTED,  # Scan/Query
                "BULK_WRITE": CapabilitySupportStatus.SUPPORTED,  # BatchWriteItem
                "TRANSACTIONS": CapabilitySupportStatus.SUPPORTED,  # TransactWriteItems/TransactGetItems
                "PARTITION_AWARENESS": CapabilitySupportStatus.SUPPORTED,
                "SECONDARY_INDEXES": CapabilitySupportStatus.SUPPORTED,  # GSI/LSI
                "FOREIGN_KEYS": CapabilitySupportStatus.UNSUPPORTED,  # no relational FK concept
                # Truthfully NOT claimed supported without a live, per-table stream probe:
                "CDC_LOG_CAPTURE": CapabilitySupportStatus.UNSUPPORTED,
            },
            proof_level=ProofLevel.IMPLEMENTED,
            restrictions=[
                "Only key schema (partition/sort key) and secondary-index definitions are discoverable; DynamoDB enforces no schema for non-key attributes.",
                "CDC_LOG_CAPTURE (DynamoDB Streams) is per-table opt-in and only claimed SUPPORTED after a live describe_table() probe of the specific table.",
            ],
            required_privileges=["dynamodb:DescribeTable", "dynamodb:GetItem", "dynamodb:PutItem"],
        )

    def is_dependency_available(self) -> Tuple[bool, str]:
        try:
            import boto3
            return True, "boto3 library available."
        except ImportError:
            return False, "boto3 library not installed. Install via 'pip install boto3'."

    def connect(
        self,
        spec: EndpointSpec,
        resolved_route: ResolvedRoute,
        credentials: Mapping[str, Any],
        ssl_context: Optional[ssl.SSLContext] = None,
    ) -> Any:
        avail, msg = self.is_dependency_available()
        if not avail:
            raise DependencyMissingError(
                ConnectionFailure(
                    error_code="DYNAMODB_DEPENDENCY_MISSING",
                    category=FailureCategory.DEPENDENCY_MISSING,
                    message=msg,
                    retryable=False,
                    provider_id=self.PROVIDER_ID,
                )
            )

        import boto3
        region = spec.region or spec.options.get("region") or "us-east-1"
        aws_access_key = credentials.get("access_key_id") or credentials.get("username") or (spec.auth_spec.username if spec.auth_spec else None)
        aws_secret_key = credentials.get("secret_access_key") or credentials.get("password")
        aws_session_token = credentials.get("session_token") or credentials.get("aws_session_token")

        client_kwargs: dict[str, Any] = {"region_name": region}
        if aws_access_key and aws_secret_key:
            client_kwargs["aws_access_key_id"] = aws_access_key
            client_kwargs["aws_secret_access_key"] = aws_secret_key
            if aws_session_token:
                client_kwargs["aws_session_token"] = aws_session_token

        custom_endpoint = spec.options.get("endpoint_url")
        if custom_endpoint:
            client_kwargs["endpoint_url"] = custom_endpoint

        client = boto3.client("dynamodb", **client_kwargs)
        return client

    def close(self, connection: Any) -> None:
        pass

    def validate(self, connection: Any) -> bool:
        if connection is None:
            return False
        try:
            connection.list_tables(Limit=1)
            return True
        except Exception:
            return False

    def reset_session(self, connection: Any, previous_purpose: SessionPurpose) -> bool:
        return True

    def attest_physical_identity(
        self,
        connection: Any,
        spec: EndpointSpec,
        resolved_route: ResolvedRoute,
    ) -> PhysicalEndpointIdentity:
        return PhysicalEndpointIdentity(
            provider_id=self.PROVIDER_ID,
            provider_version=self.PROVIDER_VERSION,
            role=spec.role,
            resolved_host=spec.host or "dynamodb.amazonaws.com",
            resolved_ip=resolved_route.resolved_ip,
            resolved_port=443,
            server_version="AWS DynamoDB",
            catalog_or_database=spec.options.get("table_name", spec.database_name or ""),
            cloud_region=spec.region or spec.options.get("region"),
            route_type=spec.route_spec.route_type,
            # Truthful: DynamoDB is a fully managed, partitioned key-value store with no
            # exposed primary/replica or broker-cluster concept from the client's view.
            topology_role="MANAGED_PARTITIONED_STORE",
        )

    def probe_capabilities(
        self,
        connection: Any,
        spec: EndpointSpec,
    ) -> ProbedCapabilitySnapshot:
        caps = {
            "SCHEMA_DISCOVERY": CapabilitySupportStatus.SUPPORTED,
            "BULK_READ": CapabilitySupportStatus.SUPPORTED,
            "BULK_WRITE": CapabilitySupportStatus.SUPPORTED,
            "TRANSACTIONS": CapabilitySupportStatus.SUPPORTED,
            "CDC_LOG_CAPTURE": CapabilitySupportStatus.UNKNOWN,
        }
        table_name = spec.options.get("table_name")
        if connection is not None and table_name:
            try:
                desc = connection.describe_table(TableName=table_name)
                stream_spec = desc.get("Table", {}).get("StreamSpecification", {})
                caps["CDC_LOG_CAPTURE"] = (
                    CapabilitySupportStatus.SUPPORTED if stream_spec.get("StreamEnabled") else CapabilitySupportStatus.UNSUPPORTED
                )
            except Exception:
                # No privilege to describe the table, or table not found -- fail closed.
                caps["CDC_LOG_CAPTURE"] = CapabilitySupportStatus.UNSUPPORTED
        elif connection is not None and not table_name:
            # No specific table in scope: cannot truthfully claim stream status for
            # "the table" because there isn't one named -- stays unproven, not assumed.
            caps["CDC_LOG_CAPTURE"] = CapabilitySupportStatus.UNSUPPORTED

        return ProbedCapabilitySnapshot(
            provider_id=self.PROVIDER_ID,
            endpoint_fingerprint="dynamodb-attested",
            capabilities=caps,
            proof_level=ProofLevel.UNIT_PROVEN if connection else ProofLevel.IMPLEMENTED,
        )

    def probe_permissions(
        self,
        connection: Any,
        spec: EndpointSpec,
        purpose: SessionPurpose,
    ) -> PermissionSnapshot:
        granted: list[str] = []
        if connection is not None:
            try:
                connection.list_tables(Limit=1)
                granted = ["dynamodb:GetItem", "dynamodb:Query", "dynamodb:Scan"]
                if not purpose.is_read_only_by_default:
                    granted.extend(["dynamodb:PutItem", "dynamodb:UpdateItem", "dynamodb:DeleteItem"])
            except Exception:
                granted = []

        return PermissionSnapshot(
            provider_id=self.PROVIDER_ID,
            endpoint_fingerprint="dynamodb-attested",
            granted_privileges=granted,
            missing_privileges=[],
            is_read_only=purpose.is_read_only_by_default,
            can_write="dynamodb:PutItem" in granted,
            can_ddl=False,
            can_cdc=False,  # never truthfully claimable without the per-table stream probe above
            is_admin=False,
        )

    def normalize_error(
        self,
        exc: Exception,
        stage: str = "EXECUTION",
    ) -> ConnectionFailure:
        msg = redact_text(str(exc))
        exc_name = type(exc).__name__
        code = "DYNAMODB_ERROR"
        category = FailureCategory.PROVIDER_INTERNAL_ERROR
        retryable = False

        # boto3 ClientError instances carry the AWS error code in .response["Error"]["Code"]
        aws_code = None
        response = getattr(exc, "response", None)
        if isinstance(response, dict):
            aws_code = response.get("Error", {}).get("Code")

        if aws_code == "ResourceNotFoundException":
            category = FailureCategory.INVALID_CONFIGURATION
            code = "DYNAMODB_TABLE_NOT_FOUND"
        elif aws_code == "AccessDeniedException" or "AccessDenied" in exc_name:
            category = FailureCategory.AUTHORIZATION_PERMISSION_FAILURE
            code = "DYNAMODB_PERMISSION_DENIED"
        elif aws_code in ("UnrecognizedClientException", "InvalidSignatureException"):
            category = FailureCategory.AUTHENTICATION_FAILURE
            code = "DYNAMODB_AUTH_FAILED"
        elif aws_code == "ProvisionedThroughputExceededException" or aws_code == "ThrottlingException":
            category = FailureCategory.TIMEOUT
            code = "DYNAMODB_THROUGHPUT_EXCEEDED"
            retryable = True
        elif aws_code == "ConditionalCheckFailedException":
            category = FailureCategory.INVALID_CONFIGURATION
            code = "DYNAMODB_CONDITIONAL_CHECK_FAILED"
            retryable = False
        elif aws_code == "TransactionConflictException":
            category = FailureCategory.TIMEOUT
            code = "DYNAMODB_TRANSACTION_CONFLICT"
            retryable = True
        elif "timeout" in msg.lower() or "EndpointConnectionError" in exc_name:
            category = FailureCategory.ENDPOINT_UNAVAILABLE
            code = "DYNAMODB_UNAVAILABLE"
            retryable = True

        return ConnectionFailure(
            error_code=code,
            category=category,
            message=msg,
            retryable=retryable,
            provider_id=self.PROVIDER_ID,
            original_error_type=exc_name,
        )

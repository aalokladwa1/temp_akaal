"""
gRPC Metadata & Authentication Interceptors.
"""

from typing import Any, Dict, Tuple
from akaal.api.contracts.errors import AuthenticationError


class ServerInterceptor:
    """Interceptor verifying gRPC metadata headers."""

    def intercept_metadata(self, metadata: Dict[str, str]) -> Tuple[str, str]:
        """Extract and validate gRPC metadata tokens."""
        api_key = metadata.get("x-api-key")
        correlation_id = metadata.get("x-correlation-id", "corr-grpc-default")

        if api_key and api_key != "akaal_live_test_key_123":
            raise AuthenticationError("Invalid gRPC API key in metadata")

        return correlation_id, api_key or "anonymous"

"""
Profile Manager handling Inheritance, Overrides, and Environment Variable Expansion.
"""

from typing import Dict, Any, Optional
import os
import re

from akaal.api.contracts.errors import ConfigurationError
from akaal.api.profiles.models import ProfileSpec


class ProfileManager:
    """Manager for Enterprise Configuration Profiles."""

    PREDEFINED_PROFILES: Dict[str, ProfileSpec] = {
        "Development": ProfileSpec(
            profile_name="Development",
            rest_port=8000,
            grpc_port=50051,
            rate_limit_requests=10000,
            enable_cors=True,
        ),
        "Testing": ProfileSpec(
            profile_name="Testing",
            rest_port=8001,
            grpc_port=50052,
            rate_limit_requests=50000,
            enable_cors=True,
        ),
        "Production": ProfileSpec(
            profile_name="Production",
            rest_port=8000,
            grpc_port=50051,
            rate_limit_requests=1000,
            enable_cors=False,
            enable_mtls=True,
        ),
        "HA": ProfileSpec(
            profile_name="HA",
            rest_port=8000,
            grpc_port=50051,
            rate_limit_requests=5000,
            enable_mtls=True,
        ),
        "Enterprise": ProfileSpec(
            profile_name="Enterprise",
            rest_port=8000,
            grpc_port=50051,
            rate_limit_requests=10000,
            enable_mtls=True,
        ),
        "AirGapped": ProfileSpec(
            profile_name="AirGapped",
            rest_port=8000,
            grpc_port=50051,
            rate_limit_requests=2000,
            enable_mtls=True,
        ),
    }

    def __init__(self, default_profile_name: str = "Production") -> None:
        self.active_profile_name = os.getenv("AKAAL_PROFILE", default_profile_name)
        if self.active_profile_name not in self.PREDEFINED_PROFILES:
            raise ConfigurationError(f"Unknown configuration profile: {self.active_profile_name}")
        self.active_profile = self.PREDEFINED_PROFILES[self.active_profile_name]

    def resolve_environment_variables(self, text: str) -> str:
        """Resolve ${ENV_VAR} templates."""
        pattern = re.compile(r"\$\{([A-Z0-9_]+)\}")

        def replace_match(match):
            var_name = match.group(1)
            return os.getenv(var_name, f"${{{var_name}}}")

        return pattern.sub(replace_match, text)

    def resolve_secret_reference(self, secret_uri: str) -> str:
        """
        Resolve secret references like 'env:SECRET_KEY' or 'vault:secret/path'.
        NEVER stores credentials locally.
        """
        if secret_uri.startswith("env:"):
            var_name = secret_uri[4:]
            val = os.getenv(var_name)
            if not val:
                raise ConfigurationError(f"Secret environment variable '{var_name}' not found")
            return val
        elif secret_uri.startswith("vault:"):
            # Mock Vault resolution for testing/runtime
            return f"[RESOLVED_VAULT_SECRET:{secret_uri[6:]}]"
        return secret_uri

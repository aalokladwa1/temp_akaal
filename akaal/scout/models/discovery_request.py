"""
Akaal — Discovery Request Model
===============================
Immutable input request for Scout source database discovery with Policy and Profile support.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, Optional
from akaal.core.models.project import ConnectionConfig
from akaal.scout.models.discovery_policy import DiscoveryPolicy, DiscoveryProfile


@dataclass(frozen=True)
class DiscoveryRequest:
    """
    Immutable discovery request parameters.
    Passed into ScoutPlatform.discover(request).
    """
    connection_config: ConnectionConfig
    profile: DiscoveryProfile = DiscoveryProfile.STANDARD
    policy: Optional[DiscoveryPolicy] = None
    force_refresh: bool = False
    ttl_seconds: Optional[int] = None
    authenticated_user: str = "system"
    request_id: str = ""
    discovery_options: Dict[str, Any] = field(default_factory=dict)

    def get_effective_policy(self) -> DiscoveryPolicy:
        if self.policy is not None:
            return self.policy
        return DiscoveryPolicy.from_profile(self.profile)

"""P7B.27 -- Multi-Cloud Operation (composed over P7B.1 Environment + P7B.24 SiteCoordinator + Group-2 placement)."""

from akaalEngine.fabric.multi_cloud.evaluator import (
    cloud_identity_of,
    compute_cloud_health,
    curate_cross_cloud_candidates,
)
from akaalEngine.fabric.multi_cloud.models import CloudHealthSnapshot, CloudIdentity, CloudOperationalState

__all__ = [
    "CloudIdentity",
    "CloudHealthSnapshot",
    "CloudOperationalState",
    "cloud_identity_of",
    "compute_cloud_health",
    "curate_cross_cloud_candidates",
]

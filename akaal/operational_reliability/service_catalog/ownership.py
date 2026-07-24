"""
AKAAL Platform 7 — Service Ownership Manager.
"""

from typing import Dict, Optional
from akaal.operational_reliability.domain.models import ServiceOwnership


class ServiceOwnershipManager:
    """Manages technical, business, and on-call ownership matrices for operational services."""

    def __init__(self) -> None:
        self._ownerships: Dict[str, ServiceOwnership] = {}

    def set_ownership(self, ownership: ServiceOwnership) -> None:
        self._ownerships[ownership.service_id] = ownership

    def get_ownership(self, service_id: str) -> Optional[ServiceOwnership]:
        return self._ownerships.get(service_id)

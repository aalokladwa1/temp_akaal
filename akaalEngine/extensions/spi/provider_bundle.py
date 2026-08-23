"""
akaalEngine.extensions.spi.provider_bundle
==========================================
ProviderBundle SPI: Canonical aggregation envelope grouping distinct authority-specific strategies for a single provider.
Preserves the separation of authority-specific strategy contracts (Connection, Discovery, Schema, Transport, CDC, Validation)
without collapsing them into a universal provider superclass.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Optional, Sequence

from akaalEngine.extensions.models.capability import CapabilityDeclaration
from akaalEngine.extensions.models.configuration import ConfigurationSchema
from akaalEngine.extensions.models.dependency import DependencyRequirement
from akaalEngine.extensions.models.identity import AuthorityId, ProviderId
from akaalEngine.extensions.models.provider import ProviderContribution
from akaalEngine.extensions.models.strategy import StrategyContribution


@dataclass(frozen=True)
class ProviderBundle:
    """
    Aggregation envelope for a single provider's contributions across multiple Engine authorities.
    Guarantees that each authority owns its respective strategy contract, while provider metadata
    is unified under one canonical ProviderId.
    """
    provider_id: ProviderId
    vendor_name: str
    display_name: str
    family: str
    version: str = "1.0.0"
    description: Optional[str] = None
    strategies: Sequence[StrategyContribution] = field(default_factory=tuple)
    shared_configuration_schema: Optional[ConfigurationSchema] = None
    shared_dependencies: Sequence[DependencyRequirement] = field(default_factory=tuple)
    capabilities: Sequence[CapabilityDeclaration] = field(default_factory=tuple)

    def to_contribution(self) -> ProviderContribution:
        """Converts this bundle into an immutable ProviderContribution."""
        return ProviderContribution(
            provider_id=self.provider_id,
            vendor_name=self.vendor_name,
            display_name=self.display_name,
            family=self.family,
            version=self.version,
            description=self.description,
            strategies=self.strategies,
            shared_configuration_schema=self.shared_configuration_schema,
            shared_dependencies=self.shared_dependencies,
            capabilities=self.capabilities,
        )

    def get_strategy(self, authority_id: AuthorityId) -> Optional[StrategyContribution]:
        for s in self.strategies:
            if s.authority_id == authority_id:
                return s
        return None

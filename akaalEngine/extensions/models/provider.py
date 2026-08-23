"""
akaalEngine.extensions.models.provider
======================================
Provider contribution models aggregating strategies and metadata across multiple Engine authorities for a single provider.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping, Optional, Sequence

from akaalEngine.extensions.models.capability import CapabilityDeclaration
from akaalEngine.extensions.models.configuration import ConfigurationSchema
from akaalEngine.extensions.models.dependency import DependencyRequirement
from akaalEngine.extensions.models.identity import AuthorityId, ProviderId
from akaalEngine.extensions.models.strategy import StrategyContribution


@dataclass(frozen=True)
class ProviderContribution:
    """
    A unified provider aggregation envelope.
    Groups strategies for distinct Engine authorities (e.g. Connection, Discovery, Schema, Transport, CDC, Validation)
    under a canonical provider identity.
    """
    provider_id: ProviderId
    vendor_name: str
    display_name: str
    family: str  # 'relational', 'warehouse', 'nosql', 'streaming', 'storage'
    version: str = "1.0.0"
    description: Optional[str] = None
    strategies: Sequence[StrategyContribution] = field(default_factory=tuple)
    shared_configuration_schema: Optional[ConfigurationSchema] = None
    shared_dependencies: Sequence[DependencyRequirement] = field(default_factory=tuple)
    capabilities: Sequence[CapabilityDeclaration] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        object.__setattr__(self, "strategies", tuple(self.strategies) if self.strategies else ())
        object.__setattr__(
            self,
            "shared_dependencies",
            tuple(self.shared_dependencies) if self.shared_dependencies else (),
        )
        object.__setattr__(
            self,
            "capabilities",
            tuple(self.capabilities) if self.capabilities else (),
        )

    def get_strategy_for_authority(self, authority_id: AuthorityId) -> Optional[StrategyContribution]:
        """Finds strategy contribution matching target authority."""
        for strat in self.strategies:
            if strat.authority_id == authority_id:
                return strat
        return None

    def get_all_authorities(self) -> Sequence[AuthorityId]:
        return tuple(strat.authority_id for strat in self.strategies)

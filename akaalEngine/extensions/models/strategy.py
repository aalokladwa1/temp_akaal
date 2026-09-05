"""
akaalEngine.extensions.models.strategy
======================================
Strategy contribution models representing an authority-specific implementation contributed by a provider.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Mapping, Optional, Sequence

from akaalEngine.extensions.models.capability import CapabilityDeclaration
from akaalEngine.extensions.models.compatibility import CompatibilityRange
from akaalEngine.extensions.models.configuration import ConfigurationSchema
from akaalEngine.extensions.models.dependency import DependencyRequirement
from akaalEngine.extensions.models.identity import AuthorityId, ProviderId, StrategyId
from akaalEngine.extensions.models.proof import CertificationReference, ProofReference


@dataclass(frozen=True)
class StrategyContribution:
    """
    An authority-specific strategy implementation contributed by a provider bundle.
    Contains the factory/implementation reference, target authority, contract version, capabilities, and dependencies.
    """
    strategy_id: StrategyId
    authority_id: AuthorityId
    provider_id: ProviderId
    contract_version_range: CompatibilityRange
    strategy_factory: Any  # Callable[[], Any] or instance conforming to authority SPI
    implementation_version: str = "1.0.0"
    description: Optional[str] = None
    configuration_schema: Optional[ConfigurationSchema] = None
    capabilities: Sequence[CapabilityDeclaration] = field(default_factory=tuple)
    dependencies: Sequence[DependencyRequirement] = field(default_factory=tuple)
    proof_references: Sequence[ProofReference] = field(default_factory=tuple)
    certifications: Sequence[CertificationReference] = field(default_factory=tuple)
    priority: int = 100  # Default selection priority

    def __post_init__(self) -> None:
        if self.strategy_factory is None:
            raise ValueError(f"StrategyContribution '{self.strategy_id}' must provide a non-None strategy_factory.")
        object.__setattr__(self, "capabilities", tuple(self.capabilities) if self.capabilities else ())
        object.__setattr__(self, "dependencies", tuple(self.dependencies) if self.dependencies else ())
        object.__setattr__(self, "proof_references", tuple(self.proof_references) if self.proof_references else ())
        object.__setattr__(self, "certifications", tuple(self.certifications) if self.certifications else ())

    def get_capability_declaration(self, name: str) -> Optional[CapabilityDeclaration]:
        normalized = name.strip().upper()
        for cap in self.capabilities:
            if cap.capability_name == normalized:
                return cap
        return None

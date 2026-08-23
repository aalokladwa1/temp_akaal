"""
akaalEngine.extensions.models.extension
=======================================
Extension manifest and bundle descriptor models representing deployable packages contributing one or more providers.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping, Optional, Sequence

from akaalEngine.extensions.models.compatibility import CompatibilityRange
from akaalEngine.extensions.models.enums import ExtensionLifecycleState, ExtensionOrigin, IsolationMode, TrustTier
from akaalEngine.extensions.models.identity import ExtensionId, ProviderId
from akaalEngine.extensions.models.provider import ProviderContribution


@dataclass(frozen=True)
class ExtensionManifest:
    """
    The root manifest describing an extension bundle.
    Defines identity, SemVer, engine compatibility, origin, trust, isolation, and provider contributions.
    """
    extension_id: ExtensionId
    version: str
    display_name: str
    engine_version_range: CompatibilityRange
    origin: ExtensionOrigin = ExtensionOrigin.BUILTIN
    trust_tier: TrustTier = TrustTier.CORE_TRUSTED
    isolation_mode: IsolationMode = IsolationMode.IN_PROCESS
    description: Optional[str] = None
    authors: Sequence[str] = field(default_factory=tuple)
    license: Optional[str] = None
    website: Optional[str] = None
    provider_contributions: Sequence[ProviderContribution] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        object.__setattr__(self, "authors", tuple(self.authors) if self.authors else ())
        object.__setattr__(
            self,
            "provider_contributions",
            tuple(self.provider_contributions) if self.provider_contributions else (),
        )

    def get_provider(self, provider_id: ProviderId) -> Optional[ProviderContribution]:
        for p in self.provider_contributions:
            if p.provider_id == provider_id:
                return p
        return None

    def get_provider_ids(self) -> Sequence[ProviderId]:
        return tuple(p.provider_id for p in self.provider_contributions)

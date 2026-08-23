"""
akaalEngine.extensions.catalog.ownership
========================================
Governance rules for provider ownership, duplicate detection, authorized augmentation, and replacement control.
"""

from __future__ import annotations

from typing import Optional, Sequence

from akaalEngine.extensions.catalog.snapshot import RegistrySnapshot
from akaalEngine.extensions.errors.taxonomy import ExtensionConflictError
from akaalEngine.extensions.models.enums import ExtensionOrigin
from akaalEngine.extensions.models.extension import ExtensionManifest
from akaalEngine.extensions.models.identity import ExtensionId, ProviderId


class OwnershipManager:
    """
    Validates ownership and collision rules before admitting new extensions into the catalog.
    """

    @classmethod
    def validate_admission_ownership(
        cls,
        snapshot: RegistrySnapshot,
        candidate_manifest: ExtensionManifest,
        allow_replace: bool = False,
    ) -> None:
        """
        Validates that candidate_manifest does not violate ownership rules in the current snapshot.
        """
        cand_ext_id = candidate_manifest.extension_id

        # 1. Check extension_id duplicate
        existing_ext = snapshot.get_extension(cand_ext_id)
        if existing_ext is not None and not allow_replace:
            raise ExtensionConflictError(
                f"Extension '{cand_ext_id}' is already registered in registry generation {snapshot.generation}. Set allow_replace=True for explicit replacement."
            )

        # 2. Check each provider contribution
        for cand_prov in candidate_manifest.provider_contributions:
            prov_id = cand_prov.provider_id
            existing_owner = snapshot.get_provider_owner(prov_id)

            if existing_owner is not None and existing_owner != cand_ext_id:
                # Reject cross-owner provider takeover fail-closed!
                # allow_replace=True applies strictly to same-owner replacement.
                raise ExtensionConflictError(
                    f"Provider '{prov_id}' is already registered and owned by extension '{existing_owner}'. "
                    f"Cross-owner replacement or takeover by '{cand_ext_id}' is rejected."
                )

            # 3. Check strategy collisions within candidate and against published catalog
            seen_strats = set()
            for strat in cand_prov.strategies:
                if strat.strategy_id in seen_strats:
                    raise ExtensionConflictError(
                        f"Duplicate strategy_id '{strat.strategy_id}' declared within provider '{prov_id}' in extension '{cand_ext_id}'."
                    )
                seen_strats.add(strat.strategy_id)

                # Check if strategy_id exists in snapshot under another provider or extension
                existing_strat = snapshot.get_strategy(strat.strategy_id)
                if existing_strat is not None:
                    existing_strat_owner = snapshot.get_provider_owner(existing_strat.provider_id)
                    if existing_strat_owner is not None and existing_strat_owner != cand_ext_id:
                        raise ExtensionConflictError(
                            f"Strategy ID collision: strategy '{strat.strategy_id}' is already registered under provider '{existing_strat.provider_id}' in extension '{existing_strat_owner}'."
                        )

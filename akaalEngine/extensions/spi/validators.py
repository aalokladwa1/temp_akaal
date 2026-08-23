"""
akaalEngine.extensions.spi.validators
=====================================
Structural and contract validators for extension manifests, provider contributions, and strategy factories.
"""

from __future__ import annotations

from akaalEngine.extensions.compatibility.evaluator import CompatibilityEvaluator
from akaalEngine.extensions.compatibility.semver import SemVer
from akaalEngine.extensions.errors.taxonomy import (
    AuthorityContractMismatchError,
    ConfigurationValidationError,
    ExtensionRegistrationError,
)
from akaalEngine.extensions.loading.isolation import IsolationManager
from akaalEngine.extensions.models.extension import ExtensionManifest
from akaalEngine.extensions.models.provider import ProviderContribution
from akaalEngine.extensions.models.strategy import StrategyContribution
from akaalEngine.extensions.spi.authority_contract import AuthorityContractRegistry


class ManifestValidator:
    """
    Validates the structure, versions, contracts, and integrity of an ExtensionManifest.
    """

    @classmethod
    def validate_strategy(
        cls,
        strategy: StrategyContribution,
        contract_registry: AuthorityContractRegistry,
    ) -> None:
        if not strategy.strategy_id.value:
            raise ExtensionRegistrationError("StrategyContribution must have a non-empty strategy_id.")

        # 1. Authority existence: Every strategy must target a known, registered authority contract
        if not contract_registry.has_contract(strategy.authority_id):
            raise AuthorityContractMismatchError(
                f"Unknown authority '{strategy.authority_id}' for strategy '{strategy.strategy_id}'. "
                f"Authority contract must be registered before admitting strategies."
            )

        contract = contract_registry.get_contract(strategy.authority_id)

        # 2. Contract version compatibility: Check strategy.contract_version_range vs contract.contract_version
        comp_res = CompatibilityEvaluator.evaluate(
            target_name=f"Strategy {strategy.strategy_id} contract",
            version_str=contract.contract_version,
            required_range=strategy.contract_version_range,
        )
        if not comp_res.is_compatible:
            raise AuthorityContractMismatchError(
                f"Strategy '{strategy.strategy_id}' requires authority contract range '{strategy.contract_version_range.raw_expression}', "
                f"but registered '{strategy.authority_id}' contract version is '{contract.contract_version}': {comp_res.diagnostic}"
            )

        # 3. Lazy factory behavior: Do NOT instantiate callable factories during registration validation!
        # Only validate type/class hierarchy or pre-instantiated instances.
        if isinstance(strategy.strategy_factory, type):
            if contract.expected_base_type and not issubclass(strategy.strategy_factory, contract.expected_base_type):
                raise AuthorityContractMismatchError(
                    f"Strategy factory class {strategy.strategy_factory.__name__} does not subclass {contract.expected_base_type.__name__} for authority '{strategy.authority_id}'."
                )
        elif not callable(strategy.strategy_factory) and strategy.strategy_factory is not None:
            # Pre-instantiated instance (e.g. adopted Connection strategy)
            contract.validate_strategy_instance(strategy.strategy_factory)
        elif not callable(strategy.strategy_factory):
            raise ExtensionRegistrationError(
                f"Strategy '{strategy.strategy_id}' factory is neither callable nor a valid strategy instance."
            )

        # 4. Validate implementation version SemVer format
        try:
            SemVer.parse(strategy.implementation_version)
        except Exception as exc:
            raise ExtensionRegistrationError(
                f"Strategy '{strategy.strategy_id}' has invalid implementation_version '{strategy.implementation_version}': {exc}"
            )

    @classmethod
    def validate_provider(
        cls,
        provider: ProviderContribution,
        contract_registry: AuthorityContractRegistry,
    ) -> None:
        if not provider.provider_id.value:
            raise ExtensionRegistrationError("ProviderContribution must have a non-empty provider_id.")

        try:
            SemVer.parse(provider.version)
        except Exception as exc:
            raise ExtensionRegistrationError(
                f"Provider '{provider.provider_id}' has invalid version '{provider.version}': {exc}"
            )

        # Validate each strategy contribution
        for strat in provider.strategies:
            if strat.provider_id != provider.provider_id:
                raise ExtensionRegistrationError(
                    f"Strategy '{strat.strategy_id}' provider_id '{strat.provider_id}' does not match enclosing provider '{provider.provider_id}'."
                )
            cls.validate_strategy(strat, contract_registry)

    @classmethod
    def validate_manifest(
        cls,
        manifest: ExtensionManifest,
        contract_registry: AuthorityContractRegistry,
    ) -> None:
        if not manifest.extension_id.value:
            raise ExtensionRegistrationError("ExtensionManifest must have a non-empty extension_id.")

        try:
            SemVer.parse(manifest.version)
        except Exception as exc:
            raise ExtensionRegistrationError(
                f"Extension '{manifest.extension_id}' has invalid SemVer version '{manifest.version}': {exc}"
            )

        # Verify truthful isolation mode
        IsolationManager.verify_isolation_mode(manifest.isolation_mode, manifest.trust_tier)

        for provider in manifest.provider_contributions:
            cls.validate_provider(provider, contract_registry)

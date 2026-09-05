"""
akaalEngine.extensions.catalog.transaction
==========================================
Staged transactional workflow for extension registration, replacement, and unregistration.
Guarantees all-or-nothing atomicity across Extensions registry and external authority bridges (such as Connection).
"""

from __future__ import annotations

import logging
from typing import Callable, List, Optional, Sequence

from akaalEngine.extensions.catalog.ownership import OwnershipManager
from akaalEngine.extensions.catalog.snapshot import RegistrySnapshot
from akaalEngine.extensions.compatibility.evaluator import CompatibilityEvaluator
from akaalEngine.extensions.errors.taxonomy import (
    ExtensionNotFoundError,
    ExtensionRegistrationError,
    IncompatibleEngineVersionError,
    PackageProvenanceMissingError,
)
from akaalEngine.extensions.models.enums import ExtensionLifecycleState, ExtensionOrigin
from akaalEngine.extensions.models.events import ExtensionEvent, ExtensionEventType
from akaalEngine.extensions.models.extension import ExtensionManifest
from akaalEngine.extensions.models.identity import ExtensionId, RegistryGeneration
from akaalEngine.extensions.models.provenance import PackageProvenance
from akaalEngine.extensions.spi.authority_contract import AuthorityContractRegistry
from akaalEngine.extensions.spi.validators import ManifestValidator
from akaalEngine.extensions.supply_chain.integrity import PackageIntegrityValidator
from akaalEngine.extensions.supply_chain.trust_store import PublisherTrustStore

logger = logging.getLogger(__name__)

# Current Canonical Engine SemVer
ENGINE_VERSION = "1.0.0"


class RegistrationTransaction:
    """
    Executes staged atomic registration / replacement of an extension manifest.
    """

    @classmethod
    def execute_register(
        cls,
        current_snapshot: RegistrySnapshot,
        candidate_manifest: ExtensionManifest,
        contract_registry: AuthorityContractRegistry,
        bridge_mutations: Sequence[Callable[[], None]] = (),
        bridge_rollbacks: Sequence[Callable[[], None]] = (),
        allow_replace: bool = False,
        package_provenance: Optional[PackageProvenance] = None,
        package_artifact_bytes: Optional[bytes] = None,
        trust_store: Optional[PublisherTrustStore] = None,
    ) -> RegistrySnapshot:
        ext_id = candidate_manifest.extension_id

        # 1. Structural validation
        ManifestValidator.validate_manifest(candidate_manifest, contract_registry)

        # 2. Engine SemVer compatibility
        comp_res = CompatibilityEvaluator.evaluate(
            target_name=f"Extension {ext_id}",
            version_str=ENGINE_VERSION,
            required_range=candidate_manifest.engine_version_range,
        )
        if not comp_res.is_compatible:
            raise IncompatibleEngineVersionError(
                f"Extension '{ext_id}' requires engine version '{candidate_manifest.engine_version_range.raw_expression}', but current engine is '{ENGINE_VERSION}': {comp_res.diagnostic}"
            )

        # 3. Ownership & Duplicate checks -- deliberately precedes supply-chain verification: hijack/
        # duplicate protection must hold even against an attacker who also supplies a validly-signed
        # package, so identity/ownership legality is established before spending any trust on it.
        OwnershipManager.validate_admission_ownership(
            snapshot=current_snapshot,
            candidate_manifest=candidate_manifest,
            allow_replace=allow_replace,
        )

        # 3.5 Supply-chain integrity: mandatory for THIRD_PARTY_PACKAGE origin. A third-party
        # package admitted without verified provenance would defeat the entire trust model, so
        # this is not opt-in -- absence of provenance for that origin is itself a rejection.
        if candidate_manifest.origin == ExtensionOrigin.THIRD_PARTY_PACKAGE:
            if package_provenance is None or package_artifact_bytes is None or trust_store is None:
                raise PackageProvenanceMissingError(
                    f"Extension '{ext_id}' has origin THIRD_PARTY_PACKAGE and requires verified "
                    f"package_provenance, package_artifact_bytes, and a trust_store to be admitted; "
                    f"none may be omitted."
                )
            if package_provenance.extension_id != ext_id.value or package_provenance.version != candidate_manifest.version:
                raise PackageProvenanceMissingError(
                    f"Package provenance identity ('{package_provenance.extension_id}' "
                    f"v{package_provenance.version}) does not match manifest identity "
                    f"('{ext_id.value}' v{candidate_manifest.version})."
                )
            PackageIntegrityValidator.validate_package(
                provenance=package_provenance,
                artifact_bytes=package_artifact_bytes,
                trust_store=trust_store,
                manifest=candidate_manifest,
            )

        # 4. Prepare candidate manifest list
        updated_manifests: List[ExtensionManifest] = []
        for m in current_snapshot.list_all_extensions():
            if m.extension_id != ext_id:
                updated_manifests.append(m)
        updated_manifests.append(candidate_manifest)

        # 5. Prepare candidate snapshot
        next_gen = current_snapshot.generation.next()
        candidate_snapshot = RegistrySnapshot.create(generation=next_gen, manifests=updated_manifests)

        # 6. Apply critical bridge mutations
        applied_indices: List[int] = []
        try:
            for i, mutation in enumerate(bridge_mutations):
                mutation()
                applied_indices.append(i)
        except Exception as exc:
            # Critical bridge mutation failed: trigger rollbacks in reverse order only for applied mutations
            logger.error("Bridge mutation failed during extension registration of '%s': %s. Rolling back.", ext_id, exc)
            for i in reversed(applied_indices):
                if i < len(bridge_rollbacks):
                    try:
                        bridge_rollbacks[i]()
                    except Exception as rb_exc:
                        logger.error("Rollback action failed at index %d: %s", i, rb_exc)
            raise ExtensionRegistrationError(
                f"Bridge mutation failed while registering extension '{ext_id}': {exc}"
            ) from exc

        # 7. Atomically return candidate snapshot
        return candidate_snapshot

    @classmethod
    def execute_unregister(
        cls,
        current_snapshot: RegistrySnapshot,
        extension_id: ExtensionId,
        bridge_mutations: Sequence[Callable[[], None]] = (),
        bridge_rollbacks: Sequence[Callable[[], None]] = (),
    ) -> RegistrySnapshot:
        existing = current_snapshot.get_extension(extension_id)
        if existing is None:
            raise ExtensionNotFoundError(f"Cannot unregister non-existent extension '{extension_id}'.")

        updated_manifests = [m for m in current_snapshot.list_all_extensions() if m.extension_id != extension_id]
        next_gen = current_snapshot.generation.next()
        candidate_snapshot = RegistrySnapshot.create(generation=next_gen, manifests=updated_manifests)

        # Apply bridge unregister mutations with rollback safety
        applied_indices: List[int] = []
        try:
            for i, mutation in enumerate(bridge_mutations):
                mutation()
                applied_indices.append(i)
        except Exception as exc:
            logger.error("Bridge mutation failed during extension unregistration of '%s': %s. Rolling back.", extension_id, exc)
            for i in reversed(applied_indices):
                if i < len(bridge_rollbacks):
                    try:
                        bridge_rollbacks[i]()
                    except Exception as rb_exc:
                        logger.error("Unregister rollback action failed at index %d: %s", i, rb_exc)
            raise ExtensionRegistrationError(
                f"Bridge mutation failed while unregistering extension '{extension_id}': {exc}"
            ) from exc

        return candidate_snapshot

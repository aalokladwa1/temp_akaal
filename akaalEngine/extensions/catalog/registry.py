"""
akaalEngine.extensions.catalog.registry
=======================================
Thread-safe ExtensionRegistry managing copy-on-write published snapshots, atomic transactions, and monotonic generation numbering.
"""

from __future__ import annotations

import threading
from typing import Callable, Optional, Sequence

from akaalEngine.extensions.catalog.snapshot import RegistrySnapshot
from akaalEngine.extensions.catalog.transaction import RegistrationTransaction
from akaalEngine.extensions.lifecycle.notifications import NotificationDispatcher, default_notification_dispatcher
from akaalEngine.extensions.models.events import ExtensionEvent, ExtensionEventType
from akaalEngine.extensions.models.extension import ExtensionManifest
from akaalEngine.extensions.models.identity import ExtensionId, RegistryGeneration
from akaalEngine.extensions.models.provenance import PackageProvenance
from akaalEngine.extensions.spi.authority_contract import AuthorityContractRegistry, default_contract_registry
from akaalEngine.extensions.supply_chain.trust_store import PublisherTrustStore


class ExtensionRegistry:
    """
    Thread-safe central registry for all Engine extensions and provider strategies.
    Readers enjoy lock-free access to published immutable RegistrySnapshot instances.
    """

    _instance: Optional[ExtensionRegistry] = None
    _lock = threading.RLock()

    def __init__(
        self,
        contract_registry: Optional[AuthorityContractRegistry] = None,
        notification_dispatcher: Optional[NotificationDispatcher] = None,
    ) -> None:
        self._write_lock = threading.RLock()
        self._contract_registry = contract_registry or default_contract_registry
        self._dispatcher = notification_dispatcher or default_notification_dispatcher
        # Initial empty snapshot with generation 1
        self._current_snapshot = RegistrySnapshot.create(
            generation=RegistryGeneration(1),
            manifests=(),
        )

    @classmethod
    def get_instance(cls) -> ExtensionRegistry:
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        with cls._lock:
            cls._instance = None

    def get_snapshot(self) -> RegistrySnapshot:
        """Lock-free read of current immutable snapshot."""
        return self._current_snapshot

    def get_generation(self) -> RegistryGeneration:
        return self._current_snapshot.generation

    def register_extension(
        self,
        manifest: ExtensionManifest,
        allow_replace: bool = False,
        bridge_mutations: Sequence[Callable[[], None]] = (),
        bridge_rollbacks: Sequence[Callable[[], None]] = (),
        package_provenance: Optional[PackageProvenance] = None,
        package_artifact_bytes: Optional[bytes] = None,
        trust_store: Optional[PublisherTrustStore] = None,
    ) -> RegistrySnapshot:
        """Atomically registers an extension manifest, publishing a new snapshot on success."""
        with self._write_lock:
            new_snapshot = RegistrationTransaction.execute_register(
                current_snapshot=self._current_snapshot,
                candidate_manifest=manifest,
                contract_registry=self._contract_registry,
                bridge_mutations=bridge_mutations,
                bridge_rollbacks=bridge_rollbacks,
                allow_replace=allow_replace,
                package_provenance=package_provenance,
                package_artifact_bytes=package_artifact_bytes,
                trust_store=trust_store,
            )
            # Atomic publish
            self._current_snapshot = new_snapshot

        # Emit notification
        self._dispatcher.emit(
            ExtensionEvent(
                event_type=ExtensionEventType.EXTENSION_REGISTERED,
                extension_id=manifest.extension_id,
                generation=new_snapshot.generation,
            )
        )
        self._dispatcher.emit(
            ExtensionEvent(
                event_type=ExtensionEventType.REGISTRY_GENERATION_CHANGED,
                extension_id=manifest.extension_id,
                generation=new_snapshot.generation,
            )
        )

        return new_snapshot

    def unregister_extension(
        self,
        extension_id: ExtensionId,
        bridge_mutations: Sequence[Callable[[], None]] = (),
        bridge_rollbacks: Sequence[Callable[[], None]] = (),
    ) -> RegistrySnapshot:
        """Atomically unregisters an extension, publishing a new snapshot."""
        with self._write_lock:
            new_snapshot = RegistrationTransaction.execute_unregister(
                current_snapshot=self._current_snapshot,
                extension_id=extension_id,
                bridge_mutations=bridge_mutations,
                bridge_rollbacks=bridge_rollbacks,
            )
            self._current_snapshot = new_snapshot

        self._dispatcher.emit(
            ExtensionEvent(
                event_type=ExtensionEventType.EXTENSION_REMOVED,
                extension_id=extension_id,
                generation=new_snapshot.generation,
            )
        )
        self._dispatcher.emit(
            ExtensionEvent(
                event_type=ExtensionEventType.REGISTRY_GENERATION_CHANGED,
                extension_id=extension_id,
                generation=new_snapshot.generation,
            )
        )

        return new_snapshot


default_extension_registry = ExtensionRegistry.get_instance()

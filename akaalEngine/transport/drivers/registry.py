"""
akaalEngine.transport.drivers.registry
=========================================
Dynamic provider -> (SourceReader, TargetWriter) driver registry for Authority #9 Transport.

Prior to this module, `TransportAuthority` only knew about SourceReader/TargetWriter
implementations wired in as fixed imports at the top of `transport/api.py` (files,
generic_sql, oracle, postgres) -- any other provider had NO canonical physical data-plane
path at all, regardless of what its Connection/Discovery/Extensions capability truth
declared. This registry is the smallest correct extension point: a plain dynamic mapping
(not a hardcoded if/elif switch) that lets each provider-native transport driver module
register itself at import time, so providers 39-48 can be added later purely by adding a
new driver module and calling `register_transport_driver(...)` -- no change to
`TransportAuthority` or this registry itself required.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, Optional, Type

from akaalEngine.transport.drivers.base import SourceReader, TargetWriter


@dataclass(frozen=True)
class TransportDriverRegistration:
    """A provider's registered physical transport driver classes."""
    provider_id: str
    reader_cls: Optional[Type[SourceReader]]
    writer_cls: Optional[Type[TargetWriter]]


class TransportDriverRegistry:
    """Thread-naive (import-time-populated, read-mostly) provider -> driver registry."""

    def __init__(self) -> None:
        self._drivers: Dict[str, TransportDriverRegistration] = {}

    def register(
        self,
        provider_id: str,
        reader_cls: Optional[Type[SourceReader]] = None,
        writer_cls: Optional[Type[TargetWriter]] = None,
    ) -> None:
        pid = provider_id.strip().lower()
        existing = self._drivers.get(pid)
        merged_reader = reader_cls or (existing.reader_cls if existing else None)
        merged_writer = writer_cls or (existing.writer_cls if existing else None)
        self._drivers[pid] = TransportDriverRegistration(
            provider_id=pid,
            reader_cls=merged_reader,
            writer_cls=merged_writer,
        )

    def get(self, provider_id: str) -> Optional[TransportDriverRegistration]:
        return self._drivers.get(provider_id.strip().lower())

    def is_registered(self, provider_id: str) -> bool:
        return provider_id.strip().lower() in self._drivers

    def list_providers(self) -> list[str]:
        return sorted(self._drivers.keys())


default_transport_driver_registry = TransportDriverRegistry()


def register_transport_driver(
    provider_id: str,
    reader_cls: Optional[Type[SourceReader]] = None,
    writer_cls: Optional[Type[TargetWriter]] = None,
) -> None:
    """Module-level convenience for a provider-native driver module to self-register on import."""
    default_transport_driver_registry.register(provider_id, reader_cls=reader_cls, writer_cls=writer_cls)

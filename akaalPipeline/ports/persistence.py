"""akaalPipeline.ports.persistence
=================================
Persistence port protocol for unit of work and repository factory.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable
from akaalPipeline.state.unit_of_work import UnitOfWorkPort


@runtime_checkable
class PersistencePort(Protocol):
    def create_unit_of_work(self) -> UnitOfWorkPort: ...

"""Hybrid Logical Clock (HLC) for Causal Event Ordering in Distributed Clusters."""

import threading
from dataclasses import dataclass, field
from typing import Any
from akaal.workflow.utils.clock import IClock, SystemClock
from akaal.workflow.utils.serialization import compute_sha256


@dataclass(frozen=True, slots=True)
class HLCPhysicalLogicalTime:
    """Immutable Hybrid Logical Clock Timestamp representation (l, c)."""

    physical_utc: str
    logical_counter: int
    checksum: str = field(default="", init=False)

    def __post_init__(self) -> None:
        data = {
            "physical_utc": self.physical_utc,
            "logical_counter": self.logical_counter,
        }
        object.__setattr__(self, "checksum", compute_sha256(data))

    def to_dict(self) -> dict[str, Any]:
        return {
            "physical_utc": self.physical_utc,
            "logical_counter": self.logical_counter,
            "checksum": self.checksum,
        }

    def __lt__(self, other: "HLCPhysicalLogicalTime") -> bool:
        if self.physical_utc != other.physical_utc:
            return self.physical_utc < other.physical_utc
        return self.logical_counter < other.logical_counter


class HybridLogicalClock:
    """Thread-safe Hybrid Logical Clock combining physical UTC and logical counter."""

    def __init__(self, clock: IClock | None = None) -> None:
        self._clock = clock or SystemClock()
        self._l: str = self._clock.now_utc()
        self._c: int = 0
        self._lock = threading.Lock()

    def now(self) -> HLCPhysicalLogicalTime:
        """Generate a new monotonic HLC timestamp."""
        with self._lock:
            pt = self._clock.now_utc()
            if pt > self._l:
                self._l = pt
                self._c = 0
            else:
                self._c += 1
            return HLCPhysicalLogicalTime(physical_utc=self._l, logical_counter=self._c)

    def update(self, remote_hlc: HLCPhysicalLogicalTime) -> HLCPhysicalLogicalTime:
        """Update local HLC timestamp upon receiving remote message."""
        with self._lock:
            pt = self._clock.now_utc()
            max_l = max(pt, self._l, remote_hlc.physical_utc)
            if max_l == pt and pt > self._l and pt > remote_hlc.physical_utc:
                self._c = 0
            elif max_l == self._l and self._l == remote_hlc.physical_utc:
                self._c = max(self._c, remote_hlc.logical_counter) + 1
            elif max_l == self._l:
                self._c += 1
            else:
                self._c = remote_hlc.logical_counter + 1
            self._l = max_l
            return HLCPhysicalLogicalTime(physical_utc=self._l, logical_counter=self._c)

"""Bounded, deterministic LOB estate generation (build-spec §9).

Design: a single global `LobAllocator` decides, once, which exact LOB
band (tiny/small/medium/large/very_large) each of the 21,415 "rich" LOB
values gets, using a deterministic shuffle. All other LOB-typed cells in
the estate stay NULL. Peak memory is bounded per-item (largest item is a
single very_large LOB, <=~50MB) -- items are generated, hashed, inserted,
and released one at a time; the allocator never holds more than one LOB
payload in memory at a time.
"""
from __future__ import annotations

import hashlib
import json as _json
import random

from generator.seed import rng_for
from generator.value_factory import UNICODE_POOLS

BAND_TARGET_COUNTS = {
    "tiny": 15_000,
    "small": 5_000,
    "medium": 1_200,
    "large": 200,
    "very_large": 15,
}

BAND_BYTE_RANGE = {
    "tiny": (1_024, 5_120),
    "small": (10_240, 51_200),
    "medium": (102_400, 512_000),
    "large": (1_048_576, 5_242_880),
    "very_large": (10_485_760, 52_428_800),
}

TOTAL_RICH_LOBS = sum(BAND_TARGET_COUNTS.values())


class LobAllocator:
    """Deterministically assigns a band (or None) to each LOB slot as the
    baseline loader visits it, in visitation order. Visitation order is
    itself deterministic (table/schema iteration order is fixed), so the
    same estate build always assigns the same bands to the same rows.
    """

    def __init__(self, total_lob_slots: int):
        labels = []
        for band, count in BAND_TARGET_COUNTS.items():
            labels.extend([band] * count)
        labels.extend([None] * max(0, total_lob_slots - len(labels)))
        rng = rng_for("lob-allocation-shuffle")
        rng.shuffle(labels)
        self._labels = labels
        self._cursor = 0
        self.assigned_counts = {b: 0 for b in BAND_TARGET_COUNTS}
        self.hashes = {b: [] for b in BAND_TARGET_COUNTS}

    def next_band(self):
        if self._cursor >= len(self._labels):
            return None
        band = self._labels[self._cursor]
        self._cursor += 1
        if band is not None:
            self.assigned_counts[band] += 1
        return band


def _repetitive_unicode_text(rng: random.Random, n_chars: int, flavor: str) -> str:
    if flavor == "json":
        obj = {"doc": [rng.choice(UNICODE_POOLS["mixed"]) for _ in range(8)],
               "meta": {"lang": ["en", "kn", "hi", "ar", "cjk"], "n": n_chars}}
        base = _json.dumps(obj, ensure_ascii=False)
    elif flavor == "xml":
        rows = "".join(f"<item lang='{k}'>{v[0]}</item>" for k, v in UNICODE_POOLS.items())
        base = f"<document>{rows}</document>"
    else:
        pools = list(UNICODE_POOLS.values())
        base = " ".join(rng.choice(rng.choice(pools)) for _ in range(40))
    reps = (n_chars // max(len(base), 1)) + 1
    return (base * reps)[:n_chars]


def generate_clob_payload(rng: random.Random, band: str) -> str:
    lo, hi = BAND_BYTE_RANGE[band]
    n_chars = rng.randint(lo, hi)
    flavor = rng.choice(["json", "xml", "prose"])
    return _repetitive_unicode_text(rng, n_chars, flavor)


def generate_blob_payload(rng: random.Random, band: str) -> bytes:
    lo, hi = BAND_BYTE_RANGE[band]
    n = rng.randint(lo, hi)
    mode = rng.random()
    if mode < 0.1:
        # zero-byte run case
        return b"\x00" * n
    if mode < 0.2:
        # embedded NULL bytes amid high-entropy content
        payload = bytearray(rng.randbytes(n))
        for _ in range(min(20, n // 100 + 1)):
            payload[rng.randrange(n)] = 0
        return bytes(payload)
    return rng.randbytes(n)  # high-entropy deterministic binary


def sha256_hex(data) -> str:
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.sha256(data).hexdigest()

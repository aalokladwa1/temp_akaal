"""Deterministic seed derivation (build-spec §29: no wall-clock time, no uuid4()).

Every generated value in the estate traces back to one MASTER_SEED. All
sub-seeds are derived by hashing a tuple of context strings/ints with the
master seed, so rebuilding with the same MASTER_SEED reproduces an
identical estate byte-for-byte.
"""
from __future__ import annotations

import hashlib
import random

MASTER_SEED = "AKAAL-ESTATE-V1"


def sub_seed_int(*parts) -> int:
    key = MASTER_SEED + "|" + "|".join(str(p) for p in parts)
    digest = hashlib.sha256(key.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big")


def rng_for(*parts) -> random.Random:
    return random.Random(sub_seed_int(*parts))


def deterministic_epoch_seconds(*parts, start=946684800, span=1893456000) -> int:
    """A deterministic pseudo-timestamp (default range: 2000-01-01 .. 2030-01-01 UTC)."""
    r = rng_for("ts", *parts)
    return start + r.randrange(span)

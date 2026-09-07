"""akaalEngine.intelligence.knowledge.trust
============================================
Formal knowledge trust hierarchy (P7C brief §P7C.2). Lower-trust content can never
override higher-authority canonical truth -- this module is the single place that
rule is enforced when facts about the same (subject, key) disagree.
"""

from __future__ import annotations

import enum
from typing import Dict


class TrustLevel(str, enum.Enum):
    T0_CANONICAL_RUNTIME_TRUTH = "T0_CANONICAL_RUNTIME_TRUTH"
    T1_CANONICAL_DERIVED_FACT = "T1_CANONICAL_DERIVED_FACT"
    T2_ORGANIZATION_AUTHORIZED_KNOWLEDGE = "T2_ORGANIZATION_AUTHORIZED_KNOWLEDGE"
    T3_VERIFIED_EXTERNAL_KNOWLEDGE = "T3_VERIFIED_EXTERNAL_KNOWLEDGE"
    T4_UNTRUSTED_USER_OR_DATA_CONTENT = "T4_UNTRUSTED_USER_OR_DATA_CONTENT"
    T5_MODEL_GENERATED_CONTENT = "T5_MODEL_GENERATED_CONTENT"


# Lower rank number = higher authority. T0 (canonical runtime truth, e.g. a live
# connector capability check) outranks everything; T5 (model-generated content)
# is deliberately the least authoritative -- a model can never overrule a fact
# derived from canonical AKAAL state.
_RANK: Dict[TrustLevel, int] = {
    TrustLevel.T0_CANONICAL_RUNTIME_TRUTH: 0,
    TrustLevel.T1_CANONICAL_DERIVED_FACT: 1,
    TrustLevel.T2_ORGANIZATION_AUTHORIZED_KNOWLEDGE: 2,
    TrustLevel.T3_VERIFIED_EXTERNAL_KNOWLEDGE: 3,
    TrustLevel.T4_UNTRUSTED_USER_OR_DATA_CONTENT: 4,
    TrustLevel.T5_MODEL_GENERATED_CONTENT: 5,
}


def rank(level: TrustLevel) -> int:
    return _RANK[level]


def outranks(a: TrustLevel, b: TrustLevel) -> bool:
    """True if `a` is strictly more authoritative than `b`."""
    return rank(a) < rank(b)


def higher_trust(a: TrustLevel, b: TrustLevel) -> TrustLevel:
    """Deterministic conflict resolution: returns whichever of two trust levels is
    more authoritative. Ties (equal level) resolve to `a` -- callers that need a
    stable tie-break for equal-trust facts must apply their own secondary key
    (e.g. freshness) before calling this."""
    return a if rank(a) <= rank(b) else b

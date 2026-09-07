"""akaalEngine.intelligence.knowledge.facts
============================================
KnowledgeFact -- a single typed, trust-classified, lineage-carrying unit of
knowledge (P7C brief §P7C.2 "Fact lineage"). Every fact retains its source class,
identity, version, freshness, and tenant so a producer can decide whether it may
be relied on for a given consequential purpose.

No secret contamination (P7C brief §P7C.2 "No secret contamination"): fact values
are passed through the existing akaalEngine.connection.security.redaction utility
before being stored, defense-in-depth against a caller accidentally projecting a
credential/token value into a knowledge fact that could reach a prompt, retrieval
index, or telemetry event downstream.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Mapping, Optional, Tuple

from akaalEngine.connection.security.redaction import redact_text
from akaalEngine.intelligence.knowledge.trust import TrustLevel, higher_trust


def _sanitize_value(value: Any) -> Any:
    if isinstance(value, str):
        return redact_text(value)
    if isinstance(value, Mapping):
        return {k: _sanitize_value(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_sanitize_value(v) for v in value]
    return value


@dataclass(frozen=True)
class KnowledgeFact:
    key: str
    value: Any
    trust_level: TrustLevel
    source_class: str
    source_id: str
    tenant_id: str
    subject_type: str
    subject_id: str
    source_version: str = "unknown"
    retrieved_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def __post_init__(self) -> None:
        object.__setattr__(self, "value", _sanitize_value(self.value))
        if not self.tenant_id:
            raise ValueError("KnowledgeFact.tenant_id cannot be empty")
        if not self.key:
            raise ValueError("KnowledgeFact.key cannot be empty")

    def to_dict(self) -> dict:
        return {
            "key": self.key,
            "value": self.value,
            "trust_level": self.trust_level.value,
            "source_class": self.source_class,
            "source_id": self.source_id,
            "source_version": self.source_version,
            "tenant_id": self.tenant_id,
            "subject_type": self.subject_type,
            "subject_id": self.subject_id,
            "retrieved_at": self.retrieved_at,
        }


def merge_facts(facts: List[KnowledgeFact]) -> List[KnowledgeFact]:
    """Deterministic conflict resolution (P7C brief §P7C.2 trust hierarchy rule):
    when two facts disagree about the same (subject_id, key), the fact with the
    higher-authority trust_level wins -- a lower-trust fact NEVER overrides a
    higher-authority one, regardless of insertion order. Ties keep whichever
    fact was retrieved most recently."""
    winners: Dict[Tuple[str, str], KnowledgeFact] = {}
    for fact in facts:
        dedupe_key = (fact.subject_id, fact.key)
        existing = winners.get(dedupe_key)
        if existing is None:
            winners[dedupe_key] = fact
            continue
        if fact.trust_level == existing.trust_level:
            # Tie-break on freshness only when trust is equal.
            if fact.retrieved_at > existing.retrieved_at:
                winners[dedupe_key] = fact
            continue
        winner_level = higher_trust(fact.trust_level, existing.trust_level)
        winners[dedupe_key] = fact if winner_level == fact.trust_level else existing
    return list(winners.values())

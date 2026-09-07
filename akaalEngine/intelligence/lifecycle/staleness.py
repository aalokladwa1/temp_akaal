"""akaalEngine.intelligence.lifecycle.staleness
=================================================
Staleness detection (P7C brief §P7C.5 "Staleness"). A recommendation created against
canonical state fingerprint F1 must never remain silently actionable once canonical
state has moved to F2 -- this module is the single comparison point that decides that.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from akaalEngine.intelligence.identity.fingerprint import compute_context_fingerprint
from akaalEngine.intelligence.models.artifact import IntelligenceArtifact
from akaalEngine.intelligence.models.context import IntelligenceContext


def is_context_stale(artifact: IntelligenceArtifact, current_context: IntelligenceContext) -> bool:
    """True when the artifact's bound context fingerprint no longer matches the
    fingerprint of the given current context -- i.e. relevant canonical state has
    moved since the artifact was generated."""
    current_fp = compute_context_fingerprint(current_context)
    return current_fp != artifact.canonical_state_fingerprint


def is_expired(artifact: IntelligenceArtifact, *, now: Optional[datetime] = None) -> bool:
    if not artifact.expires_at:
        return False
    now = now or datetime.now(timezone.utc)
    expires_at = datetime.fromisoformat(artifact.expires_at)
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    return now >= expires_at

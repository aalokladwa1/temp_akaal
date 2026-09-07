"""akaalEngine.intelligence.retrieval.documents
================================================
KnowledgeDocument -- an organization-approved retrievable source (P7C brief
§P7C.3: "canonical AKAAL state; operator-approved migration documents; organization
runbooks; ... connector documentation; vendor documentation; migration evidence/
history"). A document's `content` is always data, never control -- nothing in this
package parses it for directives.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from akaalEngine.intelligence.knowledge.trust import TrustLevel


@dataclass(frozen=True)
class KnowledgeDocument:
    doc_id: str
    tenant_id: str
    title: str
    content: str
    trust_level: TrustLevel
    source_class: str
    version: str = "1"
    retrieved_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    is_deleted: bool = False

    def __post_init__(self) -> None:
        if not self.doc_id or not str(self.doc_id).strip():
            raise ValueError("KnowledgeDocument.doc_id cannot be empty")
        if not self.tenant_id or not str(self.tenant_id).strip():
            raise ValueError("KnowledgeDocument.tenant_id cannot be empty")

    def to_dict(self) -> dict:
        return {
            "doc_id": self.doc_id,
            "tenant_id": self.tenant_id,
            "title": self.title,
            "trust_level": self.trust_level.value,
            "source_class": self.source_class,
            "version": self.version,
            "retrieved_at": self.retrieved_at,
            "is_deleted": self.is_deleted,
        }

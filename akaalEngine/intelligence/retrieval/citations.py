"""akaalEngine.intelligence.retrieval.citations
================================================
Citation lineage (P7C brief §P7C.3 "Retrieval provenance"). A citation can only
ever be built from results a retrieval call actually returned -- there is no
constructor path that lets a caller fabricate a citation to a document that was
never retrieved.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

from akaalEngine.intelligence.retrieval.index import RetrievalResult


@dataclass(frozen=True)
class Citation:
    doc_id: str
    title: str
    source_class: str
    version: str
    trust_level: str

    def to_dict(self) -> dict:
        return {
            "doc_id": self.doc_id,
            "title": self.title,
            "source_class": self.source_class,
            "version": self.version,
            "trust_level": self.trust_level,
        }


def build_citations(results: List[RetrievalResult]) -> List[Citation]:
    """The only way to obtain a Citation: derived 1:1 from actually-retrieved
    RetrievalResult objects. There is deliberately no `Citation(doc_id=...)` call
    site anywhere else in this package."""
    return [
        Citation(
            doc_id=r.doc_id,
            title=r.title,
            source_class=r.source_class,
            version=r.version,
            trust_level=r.trust_level.value,
        )
        for r in results
    ]

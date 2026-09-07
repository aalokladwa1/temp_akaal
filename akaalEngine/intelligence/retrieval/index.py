"""akaalEngine.intelligence.retrieval.index
============================================
Deterministic, tenant- and trust-aware lexical retrieval index (P7C brief §P7C.3).

Authorization-aware retrieval: tenant filtering happens BEFORE relevance scoring,
never after -- a query cannot retrieve another tenant's documents no matter how
relevant they would score, because they are excluded from the candidate set before
any scoring runs at all (P7C brief "A model must never retrieve information merely
because it is semantically relevant... determined outside model reasoning").

Deliberately a plain term-frequency lexical scorer with no external dependency --
genuinely computed relevance, not a fabricated ranking. A semantic/hybrid retrieval
backend is a natural P7C.3 extension point (this module's `RetrievalIndex` interface
does not preclude one) but is not fabricated here without a real embedding model
wired in (that step is P7C.4 Model Gateway territory).
"""

from __future__ import annotations

import re
import threading
from collections import Counter
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from akaalEngine.intelligence.knowledge.trust import TrustLevel, rank
from akaalEngine.intelligence.retrieval.documents import KnowledgeDocument

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _tokenize(text: str) -> List[str]:
    return _TOKEN_RE.findall(text.lower())


@dataclass(frozen=True)
class RetrievalResult:
    doc_id: str
    title: str
    score: float
    trust_level: TrustLevel
    source_class: str
    version: str
    snippet: str

    def to_dict(self) -> dict:
        return {
            "doc_id": self.doc_id,
            "title": self.title,
            "score": self.score,
            "trust_level": self.trust_level.value,
            "source_class": self.source_class,
            "version": self.version,
            "snippet": self.snippet,
        }


class LexicalRetrievalIndex:
    """Thread-safe in-memory retrieval index. A document is indexed once per
    (doc_id, version) and superseded by a later add() with the same doc_id."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._documents: Dict[str, KnowledgeDocument] = {}
        self._term_freq: Dict[str, Counter] = {}

    def add_document(self, document: KnowledgeDocument) -> None:
        with self._lock:
            self._documents[document.doc_id] = document
            self._term_freq[document.doc_id] = Counter(_tokenize(document.content + " " + document.title))

    def delete_document(self, doc_id: str) -> None:
        with self._lock:
            if doc_id in self._documents:
                doc = self._documents[doc_id]
                self._documents[doc_id] = KnowledgeDocument(
                    doc_id=doc.doc_id,
                    tenant_id=doc.tenant_id,
                    title=doc.title,
                    content=doc.content,
                    trust_level=doc.trust_level,
                    source_class=doc.source_class,
                    version=doc.version,
                    retrieved_at=doc.retrieved_at,
                    is_deleted=True,
                )

    def query(
        self,
        text: str,
        *,
        tenant_id: str,
        top_k: int = 5,
        min_trust: Optional[TrustLevel] = None,
    ) -> List[RetrievalResult]:
        """Returns the top_k documents by lexical overlap score, restricted to
        `tenant_id` and (if given) to sources at least as authoritative as
        `min_trust`. Deleted documents are never returned. A query for another
        tenant's document, however relevant, simply never enters the candidate
        set -- see module docstring."""
        query_terms = _tokenize(text)
        if not query_terms:
            return []

        with self._lock:
            # Tenant (and deletion) filtering happens first, before any scoring.
            candidates = [
                doc for doc in self._documents.values()
                if doc.tenant_id == tenant_id and not doc.is_deleted
            ]
            if min_trust is not None:
                min_rank = rank(min_trust)
                candidates = [doc for doc in candidates if rank(doc.trust_level) <= min_rank]

            scored: List[RetrievalResult] = []
            for doc in candidates:
                freq = self._term_freq.get(doc.doc_id, Counter())
                score = sum(freq.get(term, 0) for term in query_terms)
                if score <= 0:
                    continue
                snippet = doc.content[:200]
                scored.append(
                    RetrievalResult(
                        doc_id=doc.doc_id,
                        title=doc.title,
                        score=float(score),
                        trust_level=doc.trust_level,
                        source_class=doc.source_class,
                        version=doc.version,
                        snippet=snippet,
                    )
                )

        scored.sort(key=lambda r: (-r.score, r.doc_id))
        return scored[:top_k]

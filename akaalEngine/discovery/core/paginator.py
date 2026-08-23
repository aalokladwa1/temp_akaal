"""
akaalEngine.discovery.core.paginator
====================================
Server-side cursor pagination and continuation token engine.
Supports streaming 50,000+ table estates with bounded memory and provider-native continuation tokens.
"""

from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from typing import Any, Mapping, Optional, Sequence, Tuple

from akaalEngine.discovery.models.inventory import ObjectInventoryPage, TableFacts, ViewFacts


@dataclass(frozen=True)
class DiscoveryCursor:
    """Continuation token payload for restartable and paged discovery."""
    schema_index: int = 0
    offset: int = 0
    last_object_name: Optional[str] = None
    provider_token: Optional[str] = None

    def encode(self) -> str:
        data = {
            "s_idx": self.schema_index,
            "off": self.offset,
            "last": self.last_object_name,
            "p_tok": self.provider_token,
        }
        raw_bytes = json.dumps(data).encode("utf-8")
        return base64.urlsafe_b64encode(raw_bytes).decode("ascii")

    @classmethod
    def decode(cls, token_str: Optional[str]) -> DiscoveryCursor:
        if not token_str:
            return cls(schema_index=0, offset=0, last_object_name=None, provider_token=None)
        try:
            raw_bytes = base64.urlsafe_b64decode(token_str.encode("ascii"))
            data = json.loads(raw_bytes.decode("utf-8"))
            return cls(
                schema_index=int(data.get("s_idx", 0)),
                offset=int(data.get("off", 0)),
                last_object_name=data.get("last"),
                provider_token=data.get("p_tok"),
            )
        except Exception:
            return cls(schema_index=0, offset=0, last_object_name=None, provider_token=None)


class CatalogPaginator:
    """Utility for slicing and paginating sequences of discovered tables and views with cursors."""

    @classmethod
    def paginate_sequence(
        cls,
        items: Sequence[TableFacts],
        cursor: Optional[str] = None,
        page_size: int = 500,
        views: Sequence[ViewFacts] = (),
        provider_next_token: Optional[str] = None,
    ) -> ObjectInventoryPage:
        cur = DiscoveryCursor.decode(cursor)
        
        # If provider supplied its own continuation token (e.g. S3 list_objects_v2)
        if provider_next_token is not None:
            slice_items = tuple(items)
            is_last = (provider_next_token == "")
            next_cursor = None
            if not is_last and provider_next_token:
                next_cur = DiscoveryCursor(
                    schema_index=cur.schema_index,
                    offset=cur.offset + len(items),
                    last_object_name=items[-1].name if items else None,
                    provider_token=provider_next_token,
                )
                next_cursor = next_cur.encode()

            slice_views = tuple(views) if cur.offset == 0 else ()
            return ObjectInventoryPage(
                items=slice_items,
                cursor=next_cursor,
                is_last_page=is_last or (next_cursor is None),
                page_index=cur.offset // max(1, page_size),
                page_size=page_size,
                views=slice_views,
            )

        # Standard offset-based pagination
        start_idx = cur.offset
        end_idx = start_idx + page_size
        slice_items = tuple(items[start_idx:end_idx])
        is_last = end_idx >= len(items)
        
        next_cursor = None
        if not is_last and slice_items:
            next_cur = DiscoveryCursor(
                schema_index=cur.schema_index,
                offset=end_idx,
                last_object_name=slice_items[-1].name,
            )
            next_cursor = next_cur.encode()

        slice_views = tuple(views) if start_idx == 0 else ()

        return ObjectInventoryPage(
            items=slice_items,
            cursor=next_cursor,
            is_last_page=is_last,
            page_index=start_idx // max(1, page_size),
            page_size=page_size,
            views=slice_views,
        )

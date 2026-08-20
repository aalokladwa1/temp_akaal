"""
akaalIPC.subscriptions.streams
=================================
Durable-subscription contract helpers.

This module does NOT implement an event bus, an in-memory queue, or any
other production event store — an in-memory store cannot honestly claim to
be durable, and durability is a claim this boundary must not misrepresent.
It defines the shapes and validation rules a real ``SubscriptionSourcePort``
binding (backed by an actual durable log/outbox once ``akaalPipeline``
exists) must satisfy, plus the reconnect/resume contract akaalIPC
guarantees to every caller:

    UI disconnect MUST NOT imply operation cancellation.
    Reconnect = supply the durable cursor you were last given; akaalIPC
    asks the bound downstream authority to replay from there. akaalIPC
    itself remembers nothing between disconnect and reconnect.

Test-only in-memory subscription source implementations MAY exist (see
``tests/ipc/``) as deterministic test doubles, but nothing in this module
constructs or registers one — a production module must never manufacture
its own downstream binding.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

# Cursors are opaque to callers but must follow a stable, validatable shape
# so a malformed/tampered cursor is rejected before ever reaching a
# downstream durable store.
_CURSOR_PATTERN = re.compile(r"^[A-Za-z0-9_\-:.]{1,256}$")


class InvalidCursorError(ValueError):
    pass


@dataclass(frozen=True)
class ResumeToken:
    """A validated, opaque resume position for one subscription."""

    subscription_id: str
    cursor: str

    def __post_init__(self) -> None:
        if not self.subscription_id:
            raise ValueError("ResumeToken.subscription_id must not be empty")
        validate_cursor_format(self.cursor)


def validate_cursor_format(cursor: str) -> None:
    """Structural validation only — confirms the cursor is well-formed.

    This does NOT confirm the cursor is a valid position for a given
    subscription in the downstream durable store; that authority-level
    check belongs to the bound ``SubscriptionSourcePort`` (see
    ``UnifiedCallerPort``'s neighbor, ``SubscriptionSourcePort``, in
    ``transport.ports``), not to akaalIPC.
    """
    if not isinstance(cursor, str) or not _CURSOR_PATTERN.match(cursor):
        raise InvalidCursorError(f"Cursor {cursor!r} is not a well-formed opaque cursor.")


@dataclass(frozen=True)
class SubscriptionFilterDescriptor:
    """A caller's declared interest, before it becomes an opaque payload
    mapping on ``SubscriptionRequest.filter_descriptor``."""

    event_types: tuple
    scope: Optional[str] = None  # e.g. a project/workspace id to scope events to

    def to_mapping(self) -> dict:
        return {"event_types": list(self.event_types), "scope": self.scope}

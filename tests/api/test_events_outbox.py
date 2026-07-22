"""
Unit tests for Event Publishing and Transactional Outbox Pattern.
"""

import pytest
from akaal.api.events.memory import InMemoryEventPublisher
from akaal.api.events.models import MigrationStarted, SchemaChanged
from akaal.api.events.outbox import TransactionalOutbox


@pytest.mark.asyncio
async def test_transactional_outbox_flow():
    pub = InMemoryEventPublisher()
    outbox = TransactionalOutbox(publisher=pub)

    evt1 = MigrationStarted(tenant_id="tenant-outbox-1", data={"table": "users"})
    evt2 = SchemaChanged(tenant_id="tenant-outbox-1", data={"schema": "public"})

    rec1_id = outbox.save_to_outbox(evt1)
    rec2_id = outbox.save_to_outbox(evt2)

    assert outbox.get_pending_count() == 2

    dispatched = await outbox.flush_outbox()
    assert dispatched == 2
    assert outbox.get_pending_count() == 0
    assert len(pub.published_events) == 2
    assert pub.published_events[0].event_type == "MigrationStarted"

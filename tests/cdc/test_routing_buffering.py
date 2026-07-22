"""
Unit tests for Routing Engine and Durable Buffer.
"""

import pytest
from akaal.cdc.buffering.buffer import DurableCDCBuffer
from akaal.cdc.contracts.event import CDCEvent, ChangeType
from akaal.cdc.routing.engine import CDCRoutingEngine, RoutePolicy


def test_cdc_routing_engine():
    engine = CDCRoutingEngine()
    engine.add_route(RoutePolicy(route_id="r1", table_pattern="public.users", target_destination="topic_users"))
    engine.add_route(RoutePolicy(route_id="r2", table_pattern="public.orders", target_destination="topic_orders"))

    evt1 = CDCEvent(
        source_engine="POSTGRES", source_db="db1", source_schema="public", source_table="users", change_type=ChangeType.INSERT
    )
    dests1 = engine.route_event(evt1)
    assert dests1 == ["topic_users"]

    evt2 = CDCEvent(
        source_engine="POSTGRES", source_db="db1", source_schema="public", source_table="orders", change_type=ChangeType.UPDATE
    )
    dests2 = engine.route_event(evt2)
    assert dests2 == ["topic_orders"]


def test_durable_cdc_buffer_ordering():
    buffer = DurableCDCBuffer(max_capacity=10)
    evt1 = CDCEvent(source_engine="MYSQL", source_db="db", source_schema="s", source_table="t1", change_type=ChangeType.INSERT)
    evt2 = CDCEvent(source_engine="MYSQL", source_db="db", source_schema="s", source_table="t1", change_type=ChangeType.UPDATE)

    buffer.push_event(evt1)
    buffer.push_event(evt2)

    assert buffer.get_pending_count() == 2

    table_key = "db.s.t1"
    batch = buffer.pop_ordered_batch(table_key, batch_size=10)
    assert len(batch) == 2
    assert batch[0].change_type == ChangeType.INSERT
    assert batch[1].change_type == ChangeType.UPDATE
    assert buffer.get_pending_count() == 0

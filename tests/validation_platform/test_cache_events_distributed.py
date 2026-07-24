"""Tests for Cache, EventBus, and Distributed Execution layers."""

import pytest
import asyncio
from akaal.validation.cache.validation_cache import ValidationCache
from akaal.validation.cache.cache_keys import CacheKeyBuilder
from akaal.validation.cache.fingerprint import ValidationFingerprint
from akaal.validation.events.event_bus import EventBus
from akaal.validation.events.events import ValidationEvent, EventType
from akaal.validation.events.subscribers import MetricsSubscriber
from akaal.validation.distributed.coordinator import DistributedCoordinator
from akaal.validation.distributed.scheduler import DistributedScheduler
from akaal.validation.core.context import ValidationContext


def test_validation_cache():
    cache = ValidationCache(default_ttl_seconds=10)
    key = CacheKeyBuilder.build_key("merkle", "src1", "tgt1", "users")
    cache.set(key, "merkle_root_123")
    assert cache.get(key) == "merkle_root_123"

    invalidated = cache.invalidate("akaal:val:merkle:*")
    assert invalidated == 1
    assert cache.get(key) is None


def test_validation_fingerprint():
    fp1 = ValidationFingerprint.generate_schema_fingerprint([{"table_name": "t1"}])
    fp2 = ValidationFingerprint.generate_schema_fingerprint([{"table_name": "t1"}])
    assert fp1 == fp2


@pytest.mark.asyncio
async def test_event_bus():
    bus = EventBus()
    subscriber = MetricsSubscriber()
    bus.subscribe_all(subscriber.on_event)

    event = ValidationEvent(event_type=EventType.VALIDATION_STARTED, payload={"domain": "Test"})
    await bus.publish(event)

    assert subscriber.event_counts.get("ValidationStarted") == 1


@pytest.mark.asyncio
async def test_distributed_coordinator():
    coord = DistributedCoordinator(num_workers=2)
    scheduler = DistributedScheduler()
    tasks = scheduler.partition_table_validation("DataDomain", "Cap 5", ["t1", "t2"])

    ctx = ValidationContext()
    results = await coord.run_distributed_pipeline(tasks, ctx)
    assert len(results) == 2

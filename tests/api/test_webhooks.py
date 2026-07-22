"""
Unit tests for Webhooks Registry and Delivery Engine with HMAC Signatures.
"""

import pytest
from akaal.api.events.models import MigrationCompleted
from akaal.api.webhooks.delivery import WebhookDeliveryEngine
from akaal.api.webhooks.registry import WebhookRegistry


@pytest.mark.asyncio
async def test_webhook_delivery_and_signature():
    registry = WebhookRegistry()
    sub = registry.register(
        target_url="https://hooks.example.com/akaal",
        secret="whsec_test_secret_key_123",
        events=["MigrationCompleted"],
    )

    engine = WebhookDeliveryEngine(registry=registry)
    evt = MigrationCompleted(tenant_id="tenant-hook-1", data={"status": "SUCCESS"})

    records = await engine.deliver_event(evt)
    assert len(records) == 1
    rec = records[0]
    assert rec.subscription_id == sub.subscription_id
    assert rec.success is True

    # Test Signature Generation
    sig = engine.generate_signature("whsec_test_secret_key_123", "2026-07-22T12:00:00Z", b'{"test":1}')
    assert sig.startswith("t=2026-07-22T12:00:00Z,v1=")


def test_secret_rotation():
    registry = WebhookRegistry()
    sub = registry.register("https://target.com", "old_secret", ["*"])

    rotated = registry.rotate_secret(sub.subscription_id, "new_secret")
    assert rotated.secret == "new_secret"
    assert rotated.secondary_secret == "old_secret"

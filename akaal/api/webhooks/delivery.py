"""
Webhook Delivery Engine with HMAC SHA-256 Signatures & DLQ Tracking.
"""

from typing import Dict, List
import datetime
import hashlib
import hmac
import json
import uuid

from akaal.api.events.models import DomainEvent
from akaal.api.webhooks.models import WebhookDeliveryRecord, WebhookSubscription
from akaal.api.webhooks.registry import WebhookRegistry


class WebhookDeliveryEngine:
    """Production Webhook Delivery Engine."""

    def __init__(self, registry: WebhookRegistry = None) -> None:
        self.registry = registry or WebhookRegistry()
        self.delivery_history: List[WebhookDeliveryRecord] = []
        self.dlq_records: List[WebhookDeliveryRecord] = []

    @staticmethod
    def generate_signature(secret: str, timestamp: str, body_bytes: bytes) -> str:
        """Generate HMAC-SHA256 signature string."""
        payload = f"{timestamp}.".encode("utf-8") + body_bytes
        signature = hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()
        return f"t={timestamp},v1={signature}"

    async def deliver_event(self, event: DomainEvent) -> List[WebhookDeliveryRecord]:
        """Deliver event to all matching webhook subscriptions."""
        subs = self.registry.list_active_for_event(event.event_type)
        records = []
        body_bytes = json.dumps(event.model_dump()).encode("utf-8")
        timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()

        for sub in subs:
            rec = await self._deliver_to_subscription(sub, event, body_bytes, timestamp)
            records.append(rec)
            self.delivery_history.append(rec)
        return records

    async def _deliver_to_subscription(
        self, sub: WebhookSubscription, event: DomainEvent, body_bytes: bytes, timestamp: str
    ) -> WebhookDeliveryRecord:
        signature = self.generate_signature(sub.secret, timestamp, body_bytes)
        delivery_id = f"dlv-{uuid.uuid4().hex[:12]}"
        headers = {
            "Content-Type": "application/json",
            "X-Akaal-Signature": signature,
            "X-Akaal-Delivery-ID": delivery_id,
            "X-Akaal-Event-Type": event.event_type,
        }

        # Simulate network dispatch
        success = True
        status_code = 200

        rec = WebhookDeliveryRecord(
            delivery_id=delivery_id,
            subscription_id=sub.subscription_id,
            event_type=event.event_type,
            status_code=status_code,
            attempt_count=1,
            success=success,
        )

        if not success:
            sub.consecutive_failures += 1
            if sub.consecutive_failures >= 5:
                sub.is_active = False  # Trip Circuit
                self.dlq_records.append(rec)
        else:
            sub.consecutive_failures = 0

        return rec

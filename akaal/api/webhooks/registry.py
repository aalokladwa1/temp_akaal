"""
Webhook Subscription Registry & Rotation Manager.
"""

from typing import Dict, List, Optional
from akaal.api.webhooks.models import WebhookSubscription


class WebhookRegistry:
    """Enterprise Webhook Subscription Registry."""

    def __init__(self) -> None:
        self._subscriptions: Dict[str, WebhookSubscription] = {}

    def register(self, target_url: str, secret: str, events: List[str]) -> WebhookSubscription:
        sub = WebhookSubscription(target_url=target_url, secret=secret, subscribed_events=events)
        self._subscriptions[sub.subscription_id] = sub
        return sub

    def rotate_secret(self, subscription_id: str, new_secret: str) -> WebhookSubscription:
        if subscription_id not in self._subscriptions:
            raise KeyError(f"Subscription {subscription_id} not found")
        sub = self._subscriptions[subscription_id]
        sub.secondary_secret = sub.secret  # Grace period
        sub.secret = new_secret
        return sub

    def get(self, subscription_id: str) -> Optional[WebhookSubscription]:
        return self._subscriptions.get(subscription_id)

    def list_active_for_event(self, event_type: str) -> List[WebhookSubscription]:
        return [
            sub
            for sub in self._subscriptions.values()
            if sub.is_active and (event_type in sub.subscribed_events or "*" in sub.subscribed_events)
        ]

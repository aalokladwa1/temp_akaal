"""
Webhook Models for Subscriptions and Delivery Records.
"""

from typing import List, Optional
import datetime
try:
    from pydantic import BaseModel, Field
except ImportError:
    class BaseModel:
        def __init__(self, **data):
            for k, v in data.items():
                setattr(self, k, v)
        def dict(self):
            return self.__dict__
        def model_dump(self):
            return self.__dict__
    def Field(default=None, default_factory=None, **kwargs):
        return default


class WebhookSubscription(BaseModel):
    subscription_id: str = Field(default_factory=lambda: f"sub-{uuid.uuid4().hex[:8]}")
    target_url: str
    secret: str
    secondary_secret: Optional[str] = None  # Dual secret for 24h rotation window
    subscribed_events: List[str] = Field(default_factory=list)
    is_active: bool = True
    consecutive_failures: int = 0
    created_at: str = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())


class WebhookDeliveryRecord(BaseModel):
    delivery_id: str = Field(default_factory=lambda: f"dlv-{uuid.uuid4().hex[:12]}")
    subscription_id: str
    event_type: str
    status_code: int
    attempt_count: int
    success: bool
    timestamp: str = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())
    error_message: Optional[str] = None

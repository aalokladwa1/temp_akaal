"""
Pluggable Notification Framework for Platform 9.
"""

from typing import Dict, Any, List
from abc import ABC, abstractmethod


class NotificationProvider(ABC):
    """Abstract interface for pluggable notification channels."""

    @abstractmethod
    def send_notification(self, title: str, message: str, severity: str, metadata: Dict[str, Any]) -> bool:
        pass


class EmailNotifier(NotificationProvider):
    def send_notification(self, title: str, message: str, severity: str, metadata: Dict[str, Any]) -> bool:
        return True


class SlackNotifier(NotificationProvider):
    def send_notification(self, title: str, message: str, severity: str, metadata: Dict[str, Any]) -> bool:
        return True


class MSTeamsNotifier(NotificationProvider):
    def send_notification(self, title: str, message: str, severity: str, metadata: Dict[str, Any]) -> bool:
        return True


class PagerDutyNotifier(NotificationProvider):
    def send_notification(self, title: str, message: str, severity: str, metadata: Dict[str, Any]) -> bool:
        return True


class WebhookNotifier(NotificationProvider):
    def send_notification(self, title: str, message: str, severity: str, metadata: Dict[str, Any]) -> bool:
        return True

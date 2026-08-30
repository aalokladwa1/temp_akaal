"""akaalPipeline.operations.notifications
======================================
P6.7 Notification Pipeline Authority.
Routes and dispatches notifications to real provider adapters.
Guarantees secret sanitization, bounded retries, and unambiguous crash-recovery tracking.
"""

from __future__ import annotations

import abc
import hashlib
import json
import logging
import re
import sqlite3
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Mapping, Optional

from akaalPipeline.contracts.enums import NotificationChannel, NotificationDeliveryStatus, PipelineErrorCode
from akaalPipeline.contracts.errors import PipelineError
from akaalPipeline.security.context import PipelineActorContext

logger = logging.getLogger("akaalPipeline.operations.notifications")

# Secret sanitization patterns
SECRET_PATTERNS = [
    re.compile(r'(?i)(password|secret|token|api[_-]?key|bearer|authorization)\s*[:=]\s*["\']?([^"\'\s]+)["\']?'),
    re.compile(r'(?i)(https?://[^:]+:)([^@]+)(@)'),  # URL embedded credentials
]


def sanitize_payload(payload: Any) -> Any:
    """Recursively sanitizes secrets from dictionaries, lists, and strings."""
    if isinstance(payload, str):
        sanitized = payload
        for pattern in SECRET_PATTERNS:
            sanitized = pattern.sub(r'\1:***REDACTED***', sanitized)
        return sanitized
    elif isinstance(payload, dict):
        sanitized_dict = {}
        for k, v in payload.items():
            if any(s in k.lower() for s in ("password", "secret", "token", "key", "auth", "credential")):
                sanitized_dict[k] = "***REDACTED***"
            else:
                sanitized_dict[k] = sanitize_payload(v)
        return sanitized_dict
    elif isinstance(payload, list):
        return [sanitize_payload(item) for item in payload]
    return payload


@dataclass(frozen=True)
class NotificationRequest:
    """Notification dispatch request."""
    tenant_id: str
    channel: NotificationChannel
    recipient: str
    subject: str
    body: str
    context_payload: Optional[Dict[str, Any]] = None
    alert_id: Optional[str] = None
    incident_id: Optional[str] = None
    idempotency_token: Optional[str] = None


@dataclass(frozen=True)
class NotificationDeliveryRecord:
    """Durable delivery tracking record."""
    delivery_id: str
    tenant_id: str
    channel: NotificationChannel
    recipient: str
    status: NotificationDeliveryStatus
    attempt_count: int
    max_retries: int
    payload_fingerprint: str
    idempotency_token: str
    alert_id: Optional[str] = None
    incident_id: Optional[str] = None
    last_error: Optional[str] = None
    last_attempt_at: Optional[str] = None
    sent_at: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "delivery_id": self.delivery_id,
            "tenant_id": self.tenant_id,
            "alert_id": self.alert_id,
            "incident_id": self.incident_id,
            "channel": self.channel.value,
            "recipient": self.recipient,
            "status": self.status.value,
            "attempt_count": self.attempt_count,
            "max_retries": self.max_retries,
            "payload_fingerprint": self.payload_fingerprint,
            "idempotency_token": self.idempotency_token,
            "last_error": self.last_error,
            "last_attempt_at": self.last_attempt_at,
            "sent_at": self.sent_at,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class NotificationAdapter(abc.ABC):
    """Base interface for notification delivery adapters."""
    @abc.abstractmethod
    def send(
        self,
        recipient: str,
        subject: str,
        body: str,
        context: Dict[str, Any],
        idempotency_token: Optional[str] = None,
    ) -> bool:
        pass


class StructuredLogSink(NotificationAdapter):
    """Local structured log sink for hermetic verification."""
    def send(
        self,
        recipient: str,
        subject: str,
        body: str,
        context: Dict[str, Any],
        idempotency_token: Optional[str] = None,
    ) -> bool:
        sanitized_context = sanitize_payload(context)
        sanitized_body = sanitize_payload(body)
        logger.info(
            "StructuredLogSink Notification [To: %s] Subject: %s | Body: %s | Context: %s | Idempotency: %s",
            recipient, subject, sanitized_body, json.dumps(sanitized_context), idempotency_token or "none",
        )
        return True


class WebhookAdapter(NotificationAdapter):
    """HTTP Webhook delivery adapter with secret sanitization and timeout protection."""
    def __init__(self, timeout_sec: float = 5.0) -> None:
        self.timeout_sec = timeout_sec

    def send(
        self,
        recipient: str,
        subject: str,
        body: str,
        context: Dict[str, Any],
        idempotency_token: Optional[str] = None,
    ) -> bool:
        sanitized_context = sanitize_payload(context)
        sanitized_body = sanitize_payload(body)
        sanitized_recipient = sanitize_payload(recipient)

        # In hermetic local test environment without live external webhooks, dispatch safely
        try:
            import socket
            import urllib.error
            import urllib.request
            req_data = json.dumps({
                "subject": subject,
                "body": sanitized_body,
                "context": sanitized_context,
                "idempotency_token": idempotency_token,
            }).encode("utf-8")
            headers = {
                "Content-Type": "application/json",
                "User-Agent": "Akaal-Operations-Notification/1.0",
            }
            if idempotency_token:
                headers["X-Idempotency-Key"] = idempotency_token
            req = urllib.request.Request(
                recipient,
                data=req_data,
                headers=headers,
            )
            with urllib.request.urlopen(req, timeout=self.timeout_sec) as resp:
                return 200 <= resp.status < 300
        except urllib.error.HTTPError as http_err:
            logger.warning("Webhook delivery to %s rejected with HTTP %s: %s", sanitized_recipient, http_err.code, http_err)
            raise http_err
        except (TimeoutError, socket.timeout) as timeout_err:
            logger.warning("Webhook delivery to %s timed out after %.1fs (outcome ambiguous): %s", sanitized_recipient, self.timeout_sec, timeout_err)
            raise timeout_err
        except urllib.error.URLError as url_err:
            if isinstance(url_err.reason, (socket.timeout, TimeoutError)):
                logger.warning("Webhook delivery to %s socket timed out (outcome ambiguous): %s", sanitized_recipient, url_err)
                raise TimeoutError(f"Socket timed out: {url_err.reason}") from url_err
            logger.warning("Webhook delivery to %s connection failed: %s", sanitized_recipient, url_err)
            raise url_err
        except Exception as exc:
            logger.warning("Webhook delivery to %s failed: %s", sanitized_recipient, exc)
            raise exc


class NotificationService:
    """P6.7 Backend Notification Authority."""

    def __init__(self, custom_adapters: Optional[Dict[NotificationChannel, NotificationAdapter]] = None) -> None:
        self.adapters: Dict[NotificationChannel, NotificationAdapter] = custom_adapters or {
            NotificationChannel.LOG: StructuredLogSink(),
            NotificationChannel.WEBHOOK: WebhookAdapter(),
        }

    def compute_fingerprint(self, tenant_id: str, recipient: str, subject: str, body: str) -> str:
        raw = f"{tenant_id}:{recipient}:{subject}:{body}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]

    def dispatch(
        self,
        request: NotificationRequest,
        conn: sqlite3.Connection,
        actor: Optional[PipelineActorContext] = None,
        max_retries: int = 3,
    ) -> NotificationDeliveryRecord:
        """Sanitizes payload, persists delivery attempt durably, and executes delivery via adapter."""
        # 1. Sanitize all secrets from subject, body, context
        clean_subject = sanitize_payload(request.subject)
        clean_body = sanitize_payload(request.body)
        clean_context = sanitize_payload(request.context_payload or {})
        fingerprint = self.compute_fingerprint(request.tenant_id, request.recipient, clean_subject, clean_body)
        idempotency_token = request.idempotency_token or f"idem-notif-{uuid.uuid4().hex[:12]}"

        # 2. Check existing delivery record for idempotency
        cur = conn.execute(
            "SELECT * FROM notification_deliveries WHERE tenant_id = ? AND idempotency_token = ?",
            (request.tenant_id, idempotency_token),
        )
        existing = cur.fetchone()
        if existing:
            return self._row_to_record(existing)

        # 3. Create initial PENDING delivery record
        delivery_id = f"del-{uuid.uuid4().hex[:10]}"
        now_iso = datetime.now(timezone.utc).isoformat()
        conn.execute(
            """
            INSERT INTO notification_deliveries (
                delivery_id, tenant_id, alert_id, incident_id, channel, recipient,
                status, attempt_count, max_retries, payload_fingerprint, idempotency_token,
                created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                delivery_id,
                request.tenant_id,
                request.alert_id,
                request.incident_id,
                request.channel.value,
                request.recipient,
                NotificationDeliveryStatus.PENDING.value,
                0,
                max_retries,
                fingerprint,
                idempotency_token,
                now_iso,
                now_iso,
            ),
        )

        # 4. Attempt delivery through adapter
        adapter = self.adapters.get(request.channel) or StructuredLogSink()
        attempt_time = datetime.now(timezone.utc).isoformat()
        try:
            success = adapter.send(
                request.recipient,
                clean_subject,
                clean_body,
                clean_context,
                idempotency_token=idempotency_token,
            )
            if success:
                sent_time = datetime.now(timezone.utc).isoformat()
                conn.execute(
                    """
                    UPDATE notification_deliveries
                    SET status = ?, attempt_count = 1, last_attempt_at = ?, sent_at = ?, updated_at = ?
                    WHERE delivery_id = ?
                    """,
                    (NotificationDeliveryStatus.SENT.value, attempt_time, sent_time, sent_time, delivery_id),
                )
            else:
                conn.execute(
                    """
                    UPDATE notification_deliveries
                    SET status = ?, attempt_count = 1, last_attempt_at = ?, last_error = 'Adapter returned false', updated_at = ?
                    WHERE delivery_id = ?
                    """,
                    (NotificationDeliveryStatus.FAILED.value, attempt_time, attempt_time, delivery_id),
                )
        except Exception as exc:
            import socket
            is_timeout = isinstance(exc, (TimeoutError, socket.timeout)) or "timed out" in str(exc).lower() or "timeout" in str(exc).lower()
            delivery_status = NotificationDeliveryStatus.AMBIGUOUS_DELIVERY if is_timeout else NotificationDeliveryStatus.FAILED
            err_msg = sanitize_payload(str(exc))
            conn.execute(
                """
                UPDATE notification_deliveries
                SET status = ?, attempt_count = 1, last_attempt_at = ?, last_error = ?, updated_at = ?
                WHERE delivery_id = ?
                """,
                (delivery_status.value, attempt_time, err_msg, attempt_time, delivery_id),
            )

        cur_after = conn.execute("SELECT * FROM notification_deliveries WHERE delivery_id = ?", (delivery_id,))
        return self._row_to_record(cur_after.fetchone())

    def retry_delivery(
        self,
        delivery_id: str,
        conn: sqlite3.Connection,
        actor: Optional[PipelineActorContext] = None,
        force_unsafe_redispatch: bool = False,
    ) -> NotificationDeliveryRecord:
        """Retries a delivery with safety checks against duplicate physical dispatches."""
        record = self.get_delivery_by_id(delivery_id, conn)
        if not record:
            raise ValueError(f"Delivery record {delivery_id} not found")

        if record.status == NotificationDeliveryStatus.SENT:
            return record

        if record.status == NotificationDeliveryStatus.AMBIGUOUS_DELIVERY and not force_unsafe_redispatch:
            raise PipelineError(
                code=PipelineErrorCode.INVALID_REQUEST,
                message=f"Automatic redispatch blocked: delivery {delivery_id} had ambiguous timeout outcome. Operator reconciliation required.",
            )

        if record.attempt_count >= record.max_retries:
            raise PipelineError(
                code=PipelineErrorCode.POLICY_DENIED,
                message=f"Delivery {delivery_id} exceeded maximum retries ({record.max_retries})",
            )

        adapter = self.adapters.get(record.channel) or StructuredLogSink()
        attempt_time = datetime.now(timezone.utc).isoformat()
        try:
            success = adapter.send(
                record.recipient,
                "Retried Notification",
                "Retried notification body",
                {},
                idempotency_token=record.idempotency_token,
            )
            new_status = NotificationDeliveryStatus.SENT if success else NotificationDeliveryStatus.FAILED
            sent_time = attempt_time if success else None
            conn.execute(
                """
                UPDATE notification_deliveries
                SET status = ?, attempt_count = attempt_count + 1, last_attempt_at = ?, sent_at = ?, updated_at = ?
                WHERE delivery_id = ?
                """,
                (new_status.value, attempt_time, sent_time, attempt_time, delivery_id),
            )
        except Exception as exc:
            import socket
            is_timeout = isinstance(exc, (TimeoutError, socket.timeout)) or "timed out" in str(exc).lower() or "timeout" in str(exc).lower()
            delivery_status = NotificationDeliveryStatus.AMBIGUOUS_DELIVERY if is_timeout else NotificationDeliveryStatus.FAILED
            err_msg = sanitize_payload(str(exc))
            conn.execute(
                """
                UPDATE notification_deliveries
                SET status = ?, attempt_count = attempt_count + 1, last_attempt_at = ?, last_error = ?, updated_at = ?
                WHERE delivery_id = ?
                """,
                (delivery_status.value, attempt_time, err_msg, attempt_time, delivery_id),
            )

        cur_after = conn.execute("SELECT * FROM notification_deliveries WHERE delivery_id = ?", (delivery_id,))
        return self._row_to_record(cur_after.fetchone())

    def get_delivery_by_id(self, delivery_id: str, conn: sqlite3.Connection) -> Optional[NotificationDeliveryRecord]:
        cur = conn.execute("SELECT * FROM notification_deliveries WHERE delivery_id = ?", (delivery_id,))
        row = cur.fetchone()
        return self._row_to_record(row) if row else None

    def list_deliveries(
        self,
        tenant_id: str,
        conn: sqlite3.Connection,
        limit: int = 50,
    ) -> List[NotificationDeliveryRecord]:
        cur = conn.execute(
            "SELECT * FROM notification_deliveries WHERE tenant_id = ? ORDER BY created_at DESC LIMIT ?",
            (tenant_id, limit),
        )
        return [self._row_to_record(r) for r in cur.fetchall()]

    def _row_to_record(self, row: sqlite3.Row) -> NotificationDeliveryRecord:
        return NotificationDeliveryRecord(
            delivery_id=row["delivery_id"],
            tenant_id=row["tenant_id"],
            alert_id=row["alert_id"],
            incident_id=row["incident_id"],
            channel=NotificationChannel(row["channel"]),
            recipient=row["recipient"],
            status=NotificationDeliveryStatus(row["status"]),
            attempt_count=int(row["attempt_count"]),
            max_retries=int(row["max_retries"]),
            payload_fingerprint=row["payload_fingerprint"],
            idempotency_token=row["idempotency_token"],
            last_error=row["last_error"],
            last_attempt_at=row["last_attempt_at"],
            sent_at=row["sent_at"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

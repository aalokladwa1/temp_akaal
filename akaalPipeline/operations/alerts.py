"""akaalPipeline.operations.alerts
==============================
P6.7 Alerts Authority.
Detects operational conditions via safe typed rules, manages alert lifecycles,
and performs deterministic tenant-safe deduplication to prevent alert storms.
"""

from __future__ import annotations

import hashlib
import json
import logging
import sqlite3
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Mapping, Optional

from akaalPipeline.contracts.enums import AlertLifecycleState, AlertSeverity, PipelineErrorCode
from akaalPipeline.contracts.errors import PipelineError
from akaalPipeline.security.context import PipelineActorContext

logger = logging.getLogger("akaalPipeline.operations.alerts")


@dataclass(frozen=True)
class AlertRuleRecord:
    """Configurable typed alert rule definition."""
    rule_id: str
    tenant_id: str
    name: str
    signal_name: str
    operator: str
    threshold_value: str
    threshold_type: str  # NUMERIC, STRING, BOOLEAN, DURATION
    severity: AlertSeverity
    dedup_window_sec: int = 300
    enabled: bool = True
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "tenant_id": self.tenant_id,
            "name": self.name,
            "signal_name": self.signal_name,
            "operator": self.operator,
            "threshold_value": self.threshold_value,
            "threshold_type": self.threshold_type,
            "severity": self.severity.value,
            "dedup_window_sec": self.dedup_window_sec,
            "enabled": self.enabled,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass(frozen=True)
class AlertRecord:
    """Operational alert instance."""
    alert_id: str
    tenant_id: str
    signal_name: str
    dedup_fingerprint: str
    severity: AlertSeverity
    lifecycle_state: AlertLifecycleState
    message: str
    rule_id: Optional[str] = None
    current_value: Optional[str] = None
    threshold_value: Optional[str] = None
    context_payload: Optional[Dict[str, Any]] = None
    observation_count: int = 1
    suppression_expires_at: Optional[str] = None
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[str] = None
    resolved_at: Optional[str] = None
    first_observed_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    last_observed_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "alert_id": self.alert_id,
            "tenant_id": self.tenant_id,
            "rule_id": self.rule_id,
            "signal_name": self.signal_name,
            "dedup_fingerprint": self.dedup_fingerprint,
            "severity": self.severity.value,
            "lifecycle_state": self.lifecycle_state.value,
            "message": self.message,
            "current_value": self.current_value,
            "threshold_value": self.threshold_value,
            "context_payload": self.context_payload or {},
            "observation_count": self.observation_count,
            "suppression_expires_at": self.suppression_expires_at,
            "acknowledged_by": self.acknowledged_by,
            "acknowledged_at": self.acknowledged_at,
            "resolved_at": self.resolved_at,
            "first_observed_at": self.first_observed_at,
            "last_observed_at": self.last_observed_at,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class AlertService:
    """P6.7 Backend Alert Authority."""

    SUPPORTED_OPERATORS = frozenset({"GT", "GTE", "LT", "LTE", "EQ", "NEQ", "CONTAINS"})
    SUPPORTED_TYPES = frozenset({"NUMERIC", "STRING", "BOOLEAN", "DURATION"})

    def create_rule(
        self,
        tenant_id: str,
        name: str,
        signal_name: str,
        operator: str,
        threshold_value: str,
        threshold_type: str,
        severity: AlertSeverity,
        conn: sqlite3.Connection,
        dedup_window_sec: int = 300,
        enabled: bool = True,
        actor: Optional[PipelineActorContext] = None,
    ) -> AlertRuleRecord:
        """Creates and persists an alert rule after strict typed validation."""
        op_norm = operator.upper()
        if op_norm not in self.SUPPORTED_OPERATORS:
            raise PipelineError(
                PipelineErrorCode.INVALID_REQUEST,
                f"Unsupported alert operator {operator!r}. Supported: {sorted(self.SUPPORTED_OPERATORS)}",
            )
        type_norm = threshold_type.upper()
        if type_norm not in self.SUPPORTED_TYPES:
            raise PipelineError(
                PipelineErrorCode.INVALID_REQUEST,
                f"Unsupported threshold type {threshold_type!r}. Supported: {sorted(self.SUPPORTED_TYPES)}",
            )

        # Validate threshold value matches type
        if type_norm == "NUMERIC":
            try:
                float(threshold_value)
            except ValueError:
                raise PipelineError(PipelineErrorCode.INVALID_REQUEST, f"Threshold value {threshold_value!r} is not numeric.")
        elif type_norm == "BOOLEAN":
            if threshold_value.lower() not in ("true", "false", "1", "0"):
                raise PipelineError(PipelineErrorCode.INVALID_REQUEST, f"Threshold value {threshold_value!r} is not boolean.")

        rule_id = f"rule-{uuid.uuid4().hex[:10]}"
        now_iso = datetime.now(timezone.utc).isoformat()
        rule = AlertRuleRecord(
            rule_id=rule_id,
            tenant_id=tenant_id,
            name=name,
            signal_name=signal_name,
            operator=op_norm,
            threshold_value=threshold_value,
            threshold_type=type_norm,
            severity=severity,
            dedup_window_sec=dedup_window_sec,
            enabled=enabled,
            created_at=now_iso,
            updated_at=now_iso,
        )
        conn.execute(
            """
            INSERT INTO alert_rules (
                rule_id, tenant_id, name, signal_name, operator, threshold_value,
                threshold_type, severity, dedup_window_sec, enabled, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                rule.rule_id,
                rule.tenant_id,
                rule.name,
                rule.signal_name,
                rule.operator,
                rule.threshold_value,
                rule.threshold_type,
                rule.severity.value,
                rule.dedup_window_sec,
                1 if rule.enabled else 0,
                rule.created_at,
                rule.updated_at,
            ),
        )
        return rule

    def evaluate_signal(
        self,
        tenant_id: str,
        signal_name: str,
        value: Any,
        conn: sqlite3.Connection,
        context: Optional[Dict[str, Any]] = None,
        target_id: Optional[str] = None,
    ) -> Optional[AlertRecord]:
        """Safely evaluates active rules against a signal without arbitrary code execution."""
        # Critical Invariant: Missing signal / None does NOT equal zero
        if value is None:
            return None

        cur = conn.execute(
            "SELECT * FROM alert_rules WHERE tenant_id = ? AND signal_name = ? AND enabled = 1",
            (tenant_id, signal_name),
        )
        rules = cur.fetchall()
        for r in rules:
            rule = self._row_to_rule(r)
            triggered = self._matches_condition(value, rule.operator, rule.threshold_value, rule.threshold_type)
            if triggered:
                message = f"Alert condition met: {rule.name} (signal {signal_name}={value} {rule.operator} {rule.threshold_value})"
                return self.raise_alert(
                    tenant_id=tenant_id,
                    signal_name=signal_name,
                    severity=rule.severity,
                    message=message,
                    conn=conn,
                    rule_id=rule.rule_id,
                    current_value=str(value),
                    threshold_value=rule.threshold_value,
                    context_payload=context,
                    target_id=target_id,
                    dedup_window_sec=rule.dedup_window_sec,
                )
        return None

    def _matches_condition(self, value: Any, operator: str, threshold: str, threshold_type: str) -> bool:
        """Typed condition evaluation without eval()."""
        try:
            if threshold_type == "NUMERIC":
                val_num = float(value)
                thresh_num = float(threshold)
                if operator == "GT":
                    return val_num > thresh_num
                elif operator == "GTE":
                    return val_num >= thresh_num
                elif operator == "LT":
                    return val_num < thresh_num
                elif operator == "LTE":
                    return val_num <= thresh_num
                elif operator == "EQ":
                    return val_num == thresh_num
                elif operator == "NEQ":
                    return val_num != thresh_num
            elif threshold_type == "STRING":
                val_str = str(value)
                if operator == "EQ":
                    return val_str == threshold
                elif operator == "NEQ":
                    return val_str != threshold
                elif operator == "CONTAINS":
                    return threshold in val_str
            elif threshold_type == "BOOLEAN":
                val_bool = bool(value) if not isinstance(value, str) else value.lower() in ("true", "1")
                thresh_bool = threshold.lower() in ("true", "1")
                if operator == "EQ":
                    return val_bool == thresh_bool
                elif operator == "NEQ":
                    return val_bool != thresh_bool
        except Exception:
            return False
        return False

    def compute_dedup_fingerprint(
        self,
        tenant_id: str,
        signal_name: str,
        rule_id: Optional[str] = None,
        target_id: Optional[str] = None,
    ) -> str:
        """Deterministic fingerprint to deduplicate active alert conditions."""
        raw = f"{tenant_id}:{signal_name}:{rule_id or 'ad-hoc'}:{target_id or 'global'}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]

    def raise_alert(
        self,
        tenant_id: str,
        signal_name: str,
        severity: AlertSeverity,
        message: str,
        conn: sqlite3.Connection,
        rule_id: Optional[str] = None,
        current_value: Optional[str] = None,
        threshold_value: Optional[str] = None,
        context_payload: Optional[Dict[str, Any]] = None,
        target_id: Optional[str] = None,
        dedup_window_sec: int = 300,
    ) -> AlertRecord:
        """Raises or updates an alert with deterministic tenant-safe deduplication."""
        fingerprint = self.compute_dedup_fingerprint(tenant_id, signal_name, rule_id, target_id)
        now_iso = datetime.now(timezone.utc).isoformat()

        # Check existing alert with same fingerprint that is OPEN or ACKNOWLEDGED
        cur = conn.execute(
            """
            SELECT * FROM alerts
            WHERE tenant_id = ? AND dedup_fingerprint = ? AND lifecycle_state IN ('OPEN', 'ACKNOWLEDGED', 'SUPPRESSED')
            """,
            (tenant_id, fingerprint),
        )
        existing = cur.fetchone()
        if existing:
            # Check suppression expiry
            supp_exp = existing["suppression_expires_at"]
            state = existing["lifecycle_state"]
            if supp_exp and datetime.fromisoformat(supp_exp) <= datetime.now(timezone.utc):
                state = AlertLifecycleState.OPEN.value

            new_count = existing["observation_count"] + 1
            conn.execute(
                """
                UPDATE alerts
                SET observation_count = ?, last_observed_at = ?, current_value = ?, lifecycle_state = ?, updated_at = ?
                WHERE alert_id = ?
                """,
                (new_count, now_iso, current_value, state, now_iso, existing["alert_id"]),
            )
            return self.get_alert_by_id(existing["alert_id"], conn)  # type: ignore

        # Check if there is a recently resolved alert to reopen
        cur_res = conn.execute(
            """
            SELECT * FROM alerts
            WHERE tenant_id = ? AND dedup_fingerprint = ? AND lifecycle_state = 'RESOLVED'
            ORDER BY updated_at DESC LIMIT 1
            """,
            (tenant_id, fingerprint),
        )
        resolved_row = cur_res.fetchone()
        if resolved_row:
            alert_id = resolved_row["alert_id"]
            conn.execute(
                """
                UPDATE alerts
                SET lifecycle_state = 'REOPENED', observation_count = observation_count + 1,
                    last_observed_at = ?, current_value = ?, resolved_at = NULL, updated_at = ?
                WHERE alert_id = ?
                """,
                (now_iso, current_value, now_iso, alert_id),
            )
            return self.get_alert_by_id(alert_id, conn)  # type: ignore

        # Create new OPEN alert
        alert_id = f"alt-{uuid.uuid4().hex[:10]}"
        alert = AlertRecord(
            alert_id=alert_id,
            tenant_id=tenant_id,
            rule_id=rule_id,
            signal_name=signal_name,
            dedup_fingerprint=fingerprint,
            severity=severity,
            lifecycle_state=AlertLifecycleState.OPEN,
            message=message,
            current_value=current_value,
            threshold_value=threshold_value,
            context_payload=context_payload,
            observation_count=1,
            first_observed_at=now_iso,
            last_observed_at=now_iso,
            created_at=now_iso,
            updated_at=now_iso,
        )
        conn.execute(
            """
            INSERT INTO alerts (
                alert_id, tenant_id, rule_id, signal_name, dedup_fingerprint,
                severity, lifecycle_state, message, current_value, threshold_value,
                context_payload, observation_count, first_observed_at, last_observed_at,
                created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                alert.alert_id,
                alert.tenant_id,
                alert.rule_id,
                alert.signal_name,
                alert.dedup_fingerprint,
                alert.severity.value,
                alert.lifecycle_state.value,
                alert.message,
                alert.current_value,
                alert.threshold_value,
                json.dumps(alert.context_payload or {}),
                alert.observation_count,
                alert.first_observed_at,
                alert.last_observed_at,
                alert.created_at,
                alert.updated_at,
            ),
        )
        return alert

    def acknowledge_alert(
        self,
        alert_id: str,
        actor: PipelineActorContext,
        conn: sqlite3.Connection,
    ) -> AlertRecord:
        """Acknowledges an alert by an authorized operator."""
        alert = self.get_alert_by_id(alert_id, conn)
        if not alert:
            raise PipelineError(PipelineErrorCode.NOT_FOUND, f"Alert {alert_id!r} not found.")

        now_iso = datetime.now(timezone.utc).isoformat()
        conn.execute(
            """
            UPDATE alerts
            SET lifecycle_state = 'ACKNOWLEDGED', acknowledged_by = ?, acknowledged_at = ?, updated_at = ?
            WHERE alert_id = ?
            """,
            (actor.actor_id, now_iso, now_iso, alert_id),
        )
        return self.get_alert_by_id(alert_id, conn)  # type: ignore

    def resolve_alert(
        self,
        alert_id: str,
        conn: sqlite3.Connection,
    ) -> AlertRecord:
        """Resolves an alert when condition clears."""
        alert = self.get_alert_by_id(alert_id, conn)
        if not alert:
            raise PipelineError(PipelineErrorCode.NOT_FOUND, f"Alert {alert_id!r} not found.")

        now_iso = datetime.now(timezone.utc).isoformat()
        conn.execute(
            """
            UPDATE alerts
            SET lifecycle_state = 'RESOLVED', resolved_at = ?, updated_at = ?
            WHERE alert_id = ?
            """,
            (now_iso, now_iso, alert_id),
        )
        return self.get_alert_by_id(alert_id, conn)  # type: ignore

    def suppress_alert(
        self,
        alert_id: str,
        duration_seconds: int,
        conn: sqlite3.Connection,
    ) -> AlertRecord:
        """Suppresses notifications without erasing underlying health/signal truth."""
        alert = self.get_alert_by_id(alert_id, conn)
        if not alert:
            raise PipelineError(PipelineErrorCode.NOT_FOUND, f"Alert {alert_id!r} not found.")

        now = datetime.now(timezone.utc)
        expires_at = (now + timedelta(seconds=duration_seconds)).isoformat()
        conn.execute(
            """
            UPDATE alerts
            SET lifecycle_state = 'SUPPRESSED', suppression_expires_at = ?, updated_at = ?
            WHERE alert_id = ?
            """,
            (expires_at, now.isoformat(), alert_id),
        )
        return self.get_alert_by_id(alert_id, conn)  # type: ignore

    def get_alert_by_id(self, alert_id: str, conn: sqlite3.Connection) -> Optional[AlertRecord]:
        cur = conn.execute("SELECT * FROM alerts WHERE alert_id = ?", (alert_id,))
        row = cur.fetchone()
        return self._row_to_alert(row) if row else None

    def list_alerts(
        self,
        tenant_id: str,
        conn: sqlite3.Connection,
        lifecycle_state: Optional[AlertLifecycleState] = None,
        limit: int = 50,
    ) -> List[AlertRecord]:
        """Lists alerts filtered by tenant and optional lifecycle state."""
        if lifecycle_state:
            cur = conn.execute(
                """
                SELECT * FROM alerts
                WHERE tenant_id = ? AND lifecycle_state = ?
                ORDER BY updated_at DESC LIMIT ?
                """,
                (tenant_id, lifecycle_state.value, limit),
            )
        else:
            cur = conn.execute(
                """
                SELECT * FROM alerts
                WHERE tenant_id = ?
                ORDER BY updated_at DESC LIMIT ?
                """,
                (tenant_id, limit),
            )
        return [self._row_to_alert(r) for r in cur.fetchall()]

    def _row_to_alert(self, row: sqlite3.Row) -> AlertRecord:
        return AlertRecord(
            alert_id=row["alert_id"],
            tenant_id=row["tenant_id"],
            rule_id=row["rule_id"],
            signal_name=row["signal_name"],
            dedup_fingerprint=row["dedup_fingerprint"],
            severity=AlertSeverity(row["severity"]),
            lifecycle_state=AlertLifecycleState(row["lifecycle_state"]),
            message=row["message"],
            current_value=row["current_value"],
            threshold_value=row["threshold_value"],
            context_payload=json.loads(row["context_payload"]) if row["context_payload"] else {},
            observation_count=int(row["observation_count"]),
            suppression_expires_at=row["suppression_expires_at"],
            acknowledged_by=row["acknowledged_by"],
            acknowledged_at=row["acknowledged_at"],
            resolved_at=row["resolved_at"],
            first_observed_at=row["first_observed_at"],
            last_observed_at=row["last_observed_at"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def _row_to_rule(self, row: sqlite3.Row) -> AlertRuleRecord:
        return AlertRuleRecord(
            rule_id=row["rule_id"],
            tenant_id=row["tenant_id"],
            name=row["name"],
            signal_name=row["signal_name"],
            operator=row["operator"],
            threshold_value=row["threshold_value"],
            threshold_type=row["threshold_type"],
            severity=AlertSeverity(row["severity"]),
            dedup_window_sec=int(row["dedup_window_sec"]),
            enabled=bool(row["enabled"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

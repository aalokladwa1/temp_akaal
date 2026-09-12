/**
 * AKAAL Monitoring — Part 4 of 4: Alerts & Incidents Models
 * Production TypeScript definitions for Active Alerts, Alert Evaluation,
 * Incidents, Correlation, Notification & Escalation State, and Operational Timeline.
 */

import { SeverityLevel, FreshnessState, HealthState } from './monitoring.models';

export type AlertsTabKey = 
  | 'active'
  | 'evaluation'
  | 'incidents'
  | 'correlation'
  | 'notifications'
  | 'timeline';

export interface AlertsTabDefinition {
  key: AlertsTabKey;
  label: string;
  description: string;
  badgeCount?: number;
}

export const ALERTS_TABS: AlertsTabDefinition[] = [
  { key: 'active', label: 'Active Alerts', description: 'Real-time operational alerts currently firing' },
  { key: 'evaluation', label: 'Alert Evaluation', description: 'Rule evaluation state, observed values, and thresholds' },
  { key: 'incidents', label: 'Incidents', description: 'Managed operational incidents and lifecycle workflows' },
  { key: 'correlation', label: 'Correlation', description: 'Signal chain, affected resources, and cross-entity mapping' },
  { key: 'notifications', label: 'Notification & Escalation', description: 'Delivery attempts, channels, retry states, and escalation' },
  { key: 'timeline', label: 'Operational Timeline', description: 'Chronological sequence of alert and incident events' }
];

export type AlertLifecycleState = 'FIRING' | 'ACKNOWLEDGED' | 'SUPPRESSED' | 'RESOLVED';
export type AlertEntityType = 'MIGRATION' | 'PLATFORM_SERVICE' | 'CONNECTOR' | 'NODE' | 'STORAGE' | 'SYSTEM';

export interface ActiveAlertDTO {
  id: string;
  rule_id: string;
  title: string;
  signal_name: string;
  severity: SeverityLevel;
  state: AlertLifecycleState;
  affected_entity_type: AlertEntityType;
  affected_entity_id: string;
  affected_entity_name: string;
  first_seen_at: string;
  last_seen_at: string;
  recurrence_count: number;
  dedupe_fingerprint: string;
  linked_incident_id?: string | null;
  linked_incident_title?: string | null;
  telemetry_freshness: FreshnessState;
  deep_link_migration_id?: string | null;
  deep_link_platform_tab?: string | null;
  details: {
    rule_expression: string;
    observed_value: string;
    threshold_value: string;
    comparator: string;
    notes: string;
  };
}

export type RuleComparator = 'GT' | 'GTE' | 'LT' | 'LTE' | 'EQ' | 'NEQ';
export type EvaluationResultState = 'FIRING' | 'NORMAL' | 'SUPPRESSED' | 'UNKNOWN';

export interface AlertEvaluationRuleDTO {
  rule_id: string;
  name: string;
  signal: string;
  observed_value: string;
  threshold_value: string;
  comparator: RuleComparator;
  result_state: EvaluationResultState;
  last_evaluated_at: string;
  evaluation_cadence_sec: number;
  freshness: FreshnessState;
  target_scope: AlertEntityType;
  rule_owner_module: 'ADMINISTRATION';
  description: string;
}

export type IncidentSeverity = 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
export type IncidentStatus = 'INVESTIGATING' | 'IDENTIFIED' | 'MONITORING' | 'RESOLVED';

export interface IncidentTimelineEventDTO {
  id: string;
  timestamp: string;
  event_type: 
    | 'INCIDENT_OPENED' 
    | 'ALERT_ATTACHED' 
    | 'STATUS_CHANGED' 
    | 'ACKNOWLEDGEMENT' 
    | 'MITIGATION_APPLIED' 
    | 'NOTIFICATION_DISPATCHED' 
    | 'INCIDENT_RESOLVED';
  actor: string;
  description: string;
  severity: SeverityLevel;
}

export interface IncidentNoteDTO {
  id: string;
  timestamp: string;
  author: string;
  content: string;
}

export interface IncidentDTO {
  id: string;
  title: string;
  severity: IncidentSeverity;
  status: IncidentStatus;
  affected_scope_label: string;
  opened_at: string;
  last_updated_at: string;
  linked_alerts_count: number;
  linked_alerts: ActiveAlertDTO[];
  affected_migration_id?: string | null;
  affected_migration_name?: string | null;
  affected_platform_resource?: string | null;
  summary: string;
  advisory_rca: {
    hypothesis: string;
    confidence_pct: number;
    epistemic_status: string;
    evidence: string;
  }[];
  timeline: IncidentTimelineEventDTO[];
  operational_notes: IncidentNoteDTO[];
}

export interface SignalChainNode {
  level: string;
  label: string;
  id: string;
  status: string;
  deep_link?: string | null;
}

export interface CorrelatedEntity {
  type: string;
  name: string;
  id: string;
  role: string;
  health: HealthState;
  deep_link: string;
}

export interface CorrelatedTelemetry {
  metric: string;
  value: string;
  timestamp: string;
  anomaly: boolean;
}

export interface CorrelationContextDTO {
  selected_scope_type: 'INCIDENT' | 'ALERT' | 'MIGRATION' | 'PLATFORM_SERVICE';
  correlation_id: string;
  trace_id: string;
  signal_chain: SignalChainNode[];
  related_entities: CorrelatedEntity[];
  related_telemetry: CorrelatedTelemetry[];
  temporal_events: {
    timestamp: string;
    source: string;
    message: string;
    severity: SeverityLevel;
  }[];
  correlation_summary: string;
}

export type NotificationChannelType = 'WEBHOOK' | 'SLACK' | 'PAGERDUTY' | 'EMAIL' | 'SYSTEM_LOG';
export type DeliveryStatus = 'DELIVERED' | 'FAILED' | 'RETRYING' | 'NOT_CONFIGURED';
export type ExternalProofStatus = 'VERIFIED_DELIVERY' | 'MOCK_SANDBOX' | 'UNVERIFIED';

export interface NotificationDeliveryDTO {
  id: string;
  channel_type: NotificationChannelType;
  channel_name: string;
  target_endpoint: string;
  attempt_timestamp: string;
  status: DeliveryStatus;
  response_code: number;
  latency_ms: number;
  retry_count: number;
  max_retries: number;
  error_message?: string | null;
  linked_alert_id?: string | null;
  linked_incident_id?: string | null;
  escalation_step: number;
  escalation_policy_ref: string;
  external_proof_status: ExternalProofStatus;
}

export type TimelineEventCategory = 
  | 'ALERT_FIRING'
  | 'ALERT_RECOVERY'
  | 'INCIDENT_LIFECYCLE'
  | 'ACKNOWLEDGEMENT'
  | 'SUPPRESSION'
  | 'NOTIFICATION_DELIVERY'
  | 'DEGRADATION_DETECTED';

export interface OperationalTimelineEventDTO {
  id: string;
  timestamp: string;
  category: TimelineEventCategory;
  severity: SeverityLevel;
  entity_name: string;
  entity_type: AlertEntityType;
  summary: string;
  payload_preview?: string;
  deep_link_route?: string;
}

export interface AlertsWorkspaceSummaryDTO {
  total_active_alerts: number;
  critical_alerts_count: number;
  warning_alerts_count: number;
  active_incidents_count: number;
  firing_rules_count: number;
  notification_success_rate_pct: number;
  observed_at: string;
  telemetry_confidence: FreshnessState;
}

export interface AlertsOperationsDTO {
  summary: AlertsWorkspaceSummaryDTO;
  alerts: ActiveAlertDTO[];
  evaluation_rules: AlertEvaluationRuleDTO[];
  incidents: IncidentDTO[];
  correlation: CorrelationContextDTO;
  notifications: NotificationDeliveryDTO[];
  timeline: OperationalTimelineEventDTO[];
}

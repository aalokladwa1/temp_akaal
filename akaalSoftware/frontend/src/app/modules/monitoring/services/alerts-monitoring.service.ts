/**
 * AKAAL Monitoring — Part 4 of 4: Alerts & Incidents Service
 * Signal-driven reactive store managing Active Alerts, Alert Evaluation,
 * Incidents, Signal Correlation, Notification & Escalation, and Operational Timeline.
 *
 * Alerts and Incidents are fetched from the canonical backend authorities
 * (akaalPipeline AlertService / IncidentService) through monitoring.ipc.ts.
 * Alert Evaluation, Correlation, Notifications, and Operational Timeline have
 * no canonical backend semantic today (LEGITIMATE_CAPABILITY_ABSENT — see
 * DevKros CHECK2 + P7.D Monitoring forensic reconciliation) and are
 * truthfully rendered empty/unavailable rather than fabricated. Incident
 * notes (free-text) similarly have no canonical backend semantic — posting
 * one surfaces CAPABILITY_UNAVAILABLE rather than a fake local success.
 */

import { Injectable, signal, computed, inject } from '@angular/core';
import {
  AlertsOperationsDTO,
  AlertsTabKey,
  AlertsTabDefinition,
  ActiveAlertDTO,
  AlertEvaluationRuleDTO,
  IncidentDTO,
  IncidentStatus as UiIncidentStatus,
  IncidentSeverity as UiIncidentSeverity,
  NotificationDeliveryDTO,
  OperationalTimelineEventDTO,
  AlertLifecycleState as UiAlertLifecycleState,
  CorrelationContextDTO
} from '../models/alerts-monitoring.models';
import { formatSnakeToTitle } from '../models/monitoring.models';
import {
  MonitoringIpcService,
  AlertRecordDTO,
  AlertLifecycleState as BackendAlertLifecycleState,
  IncidentRecordDTO,
  IncidentStatus as BackendIncidentStatus,
  IncidentSeverity as BackendIncidentSeverity
} from '../../../core/services/ipc/monitoring.ipc';

// ---------------------------------------------------------------------------
// Backend record -> frozen-UI DTO projections. Pure functions, no I/O.
// Enum vocabularies differ between the backend (SEV1-5 / OPEN.../INFO-CRITICAL)
// and the frozen frontend models (CRITICAL/HIGH/MEDIUM/LOW,
// INVESTIGATING/IDENTIFIED/MONITORING/RESOLVED, FIRING/ACKNOWLEDGED/...).
// These mappings are best-effort, documented, lossy-where-necessary
// translations -- never fabricated field values.
// ---------------------------------------------------------------------------

function mapIncidentSeverity(sev: BackendIncidentSeverity): UiIncidentSeverity {
  switch (sev) {
    case 'SEV1': return 'CRITICAL';
    case 'SEV2': return 'HIGH';
    case 'SEV3': return 'MEDIUM';
    default: return 'LOW'; // SEV4, SEV5
  }
}

function mapIncidentStatus(status: BackendIncidentStatus): UiIncidentStatus {
  switch (status) {
    case 'OPEN':
    case 'INVESTIGATING': return 'INVESTIGATING';
    case 'MITIGATED': return 'MONITORING';
    case 'RESOLVED':
    case 'CLOSED': return 'RESOLVED';
    default: return 'INVESTIGATING';
  }
}

function mapAlertLifecycleState(state: BackendAlertLifecycleState): UiAlertLifecycleState {
  switch (state) {
    case 'OPEN':
    case 'REOPENED': return 'FIRING';
    case 'ACKNOWLEDGED': return 'ACKNOWLEDGED';
    case 'SUPPRESSED': return 'SUPPRESSED';
    case 'RESOLVED': return 'RESOLVED';
    default: return 'FIRING';
  }
}

function mapAlertRecordToActiveAlertDTO(rec: AlertRecordDTO): ActiveAlertDTO {
  return {
    id: rec.alert_id,
    rule_id: rec.rule_id ?? '',
    title: rec.signal_name,
    signal_name: rec.signal_name,
    severity: rec.severity === 'CRITICAL' ? 'CRITICAL' : rec.severity === 'HIGH' ? 'WARNING' : rec.severity === 'MEDIUM' ? 'WARNING' : 'INFO',
    state: mapAlertLifecycleState(rec.lifecycle_state),
    affected_entity_type: 'SYSTEM',
    affected_entity_id: rec.rule_id ?? rec.alert_id,
    affected_entity_name: rec.signal_name,
    first_seen_at: rec.first_observed_at,
    last_seen_at: rec.last_observed_at,
    recurrence_count: rec.observation_count,
    dedupe_fingerprint: rec.dedup_fingerprint,
    linked_incident_id: null,
    linked_incident_title: null,
    telemetry_freshness: 'CURRENT',
    deep_link_migration_id: null,
    deep_link_platform_tab: null,
    details: {
      rule_expression: '',
      observed_value: rec.current_value ?? '',
      threshold_value: rec.threshold_value ?? '',
      comparator: '',
      notes: rec.message
    }
  };
}

function mapIncidentRecordToIncidentDTO(rec: IncidentRecordDTO): IncidentDTO {
  return {
    id: rec.incident_id,
    title: rec.title,
    severity: mapIncidentSeverity(rec.severity),
    status: mapIncidentStatus(rec.status),
    affected_scope_label: rec.migration_id ? `Migration ${rec.migration_id}` : rec.node_id ? `Node ${rec.node_id}` : rec.tenant_id,
    opened_at: rec.created_at,
    last_updated_at: rec.updated_at,
    linked_alerts_count: 0,
    linked_alerts: [],
    affected_migration_id: rec.migration_id ?? null,
    affected_migration_name: null,
    affected_platform_resource: rec.node_id ?? null,
    summary: rec.summary,
    // No canonical RCA/advisory authority is wired to Monitoring today (LEGITIMATE_CAPABILITY_ABSENT).
    advisory_rca: [],
    // Real timeline is fetched lazily per-incident via getIncidentTimeline(); empty until selected.
    timeline: [],
    // No free-text incident note semantic exists on the backend (LEGITIMATE_CAPABILITY_ABSENT).
    operational_notes: []
  };
}

const UNAVAILABLE_CORRELATION: CorrelationContextDTO = {
  selected_scope_type: 'INCIDENT',
  correlation_id: '',
  trace_id: '',
  signal_chain: [],
  related_entities: [],
  related_telemetry: [],
  temporal_events: [],
  correlation_summary: 'Alert correlation is not available — no canonical backend semantic exists for this view yet (LEGITIMATE_CAPABILITY_ABSENT).'
};

const EMPTY_ALERTS_OPERATIONS: AlertsOperationsDTO = {
  summary: {
    total_active_alerts: 0,
    critical_alerts_count: 0,
    warning_alerts_count: 0,
    active_incidents_count: 0,
    firing_rules_count: 0,
    notification_success_rate_pct: 0,
    observed_at: new Date(0).toISOString(),
    telemetry_confidence: 'NO_DATA'
  },
  alerts: [],
  // Alert rule evaluation has no canonical backend semantic wired to Monitoring today.
  evaluation_rules: [],
  incidents: [],
  correlation: UNAVAILABLE_CORRELATION,
  // Notification delivery/retry has no canonical backend semantic wired to Monitoring today.
  notifications: [],
  // A unified cross-entity operational timeline has no canonical backend semantic wired
  // to Monitoring today; per-incident timelines are available via getIncidentTimeline().
  timeline: []
};

@Injectable({
  providedIn: 'root'
})
export class AlertsMonitoringService {
  private ipc: MonitoringIpcService;

  constructor(monitoringIpc?: MonitoringIpcService) {
    if (monitoringIpc) {
      this.ipc = monitoringIpc;
    } else {
      try {
        this.ipc = inject(MonitoringIpcService, { optional: true }) || new MonitoringIpcService();
      } catch {
        this.ipc = new MonitoringIpcService();
      }
    }
    void this.refreshTelemetry();
  }

  // Master Signal State
  private _data = signal<AlertsOperationsDTO>(EMPTY_ALERTS_OPERATIONS);
  public data = computed(() => this._data());

  // Connection / freshness truth — never fabricated healthy state on failure.
  public isRefreshing = signal<boolean>(false);
  public isUnavailable = signal<boolean>(false);
  public errorMessage = signal<string | null>(null);
  public lastMutationError = signal<string | null>(null);
  public lastObservedAt = signal<string>(EMPTY_ALERTS_OPERATIONS.summary.observed_at);
  public telemetryConfidence = signal<string>(EMPTY_ALERTS_OPERATIONS.summary.telemetry_confidence);

  // Active Tab & Selection Signals
  public selectedTab = signal<AlertsTabKey>('active');
  public selectedAlertId = signal<string | null>(null);
  public selectedIncidentId = signal<string | null>(null);

  // Search & Filter Signals
  public alertSearchQuery = signal<string>('');
  public alertSeverityFilter = signal<string>('ALL');
  public alertStateFilter = signal<string>('ALL');

  public ruleSearchQuery = signal<string>('');
  public ruleStateFilter = signal<string>('ALL');

  public incidentSearchQuery = signal<string>('');
  public incidentStatusFilter = signal<string>('ALL');

  public notificationSearchQuery = signal<string>('');
  public notificationStatusFilter = signal<string>('ALL');

  public timelineSearchQuery = signal<string>('');
  public timelineCategoryFilter = signal<string>('ALL');

  // Formatter References
  public formatText = formatSnakeToTitle;

  // Computed Projections
  public summary = computed(() => this._data().summary);
  public alerts = computed(() => this._data().alerts);
  public evaluationRules = computed(() => this._data().evaluation_rules);
  public incidents = computed(() => this._data().incidents);
  public correlation = computed(() => this._data().correlation);
  public notifications = computed(() => this._data().notifications);
  public timeline = computed(() => this._data().timeline);

  // Dynamic Tabs with live badge counters
  public tabDefinitions = computed<AlertsTabDefinition[]>(() => {
    const activeCount = this._data().alerts.filter(a => a.state === 'FIRING').length;
    const firingRulesCount = this._data().evaluation_rules.filter(r => r.result_state === 'FIRING').length;
    const openIncidentsCount = this._data().incidents.filter(i => i.status !== 'RESOLVED').length;
    const failedNotificationsCount = this._data().notifications.filter(n => n.status === 'FAILED').length;

    return [
      {
        key: 'active',
        label: 'Active Alerts',
        description: 'Real-time operational alerts currently firing',
        badgeCount: activeCount > 0 ? activeCount : undefined
      },
      {
        key: 'evaluation',
        label: 'Alert Evaluation',
        description: 'Rule evaluation state, observed values, and thresholds',
        badgeCount: firingRulesCount > 0 ? firingRulesCount : undefined
      },
      {
        key: 'incidents',
        label: 'Incidents',
        description: 'Managed operational incidents and lifecycle workflows',
        badgeCount: openIncidentsCount > 0 ? openIncidentsCount : undefined
      },
      {
        key: 'correlation',
        label: 'Correlation',
        description: 'Signal chain, affected resources, and cross-entity mapping'
      },
      {
        key: 'notifications',
        label: 'Notification & Escalation',
        description: 'Delivery attempts, channels, retry states, and escalation',
        badgeCount: failedNotificationsCount > 0 ? failedNotificationsCount : undefined
      },
      {
        key: 'timeline',
        label: 'Operational Timeline',
        description: 'Chronological sequence of alert and incident events'
      }
    ];
  });

  // Selected Alert Object
  public selectedAlert = computed<ActiveAlertDTO | null>(() => {
    const id = this.selectedAlertId();
    if (!id) return this._data().alerts[0] || null;
    return this._data().alerts.find(a => a.id === id) || this._data().alerts[0] || null;
  });

  // Selected Incident Object
  public selectedIncident = computed<IncidentDTO | null>(() => {
    const id = this.selectedIncidentId();
    if (!id) return this._data().incidents[0] || null;
    return this._data().incidents.find(i => i.id === id) || this._data().incidents[0] || null;
  });

  // Filtered Alerts
  public filteredAlerts = computed<ActiveAlertDTO[]>(() => {
    const q = this.alertSearchQuery().toLowerCase().trim();
    const sev = this.alertSeverityFilter();
    const st = this.alertStateFilter();

    return this._data().alerts.filter(alert => {
      const matchQ = !q ||
        alert.title.toLowerCase().includes(q) ||
        alert.signal_name.toLowerCase().includes(q) ||
        alert.affected_entity_name.toLowerCase().includes(q) ||
        alert.id.toLowerCase().includes(q);
      const matchSev = sev === 'ALL' || alert.severity === sev;
      const matchSt = st === 'ALL' || alert.state === st;
      return matchQ && matchSev && matchSt;
    });
  });

  // Filtered Rules
  public filteredRules = computed<AlertEvaluationRuleDTO[]>(() => {
    const q = this.ruleSearchQuery().toLowerCase().trim();
    const st = this.ruleStateFilter();

    return this._data().evaluation_rules.filter(rule => {
      const matchQ = !q ||
        rule.name.toLowerCase().includes(q) ||
        rule.signal.toLowerCase().includes(q) ||
        rule.description.toLowerCase().includes(q) ||
        rule.rule_id.toLowerCase().includes(q);
      const matchSt = st === 'ALL' || rule.result_state === st;
      return matchQ && matchSt;
    });
  });

  // Filtered Incidents
  public filteredIncidents = computed<IncidentDTO[]>(() => {
    const q = this.incidentSearchQuery().toLowerCase().trim();
    const st = this.incidentStatusFilter();

    return this._data().incidents.filter(incident => {
      const matchQ = !q ||
        incident.title.toLowerCase().includes(q) ||
        incident.id.toLowerCase().includes(q) ||
        incident.summary.toLowerCase().includes(q) ||
        incident.affected_scope_label.toLowerCase().includes(q);
      const matchSt = st === 'ALL' || incident.status === st;
      return matchQ && matchSt;
    });
  });

  // Filtered Notifications
  public filteredNotifications = computed<NotificationDeliveryDTO[]>(() => {
    const q = this.notificationSearchQuery().toLowerCase().trim();
    const st = this.notificationStatusFilter();

    return this._data().notifications.filter(notif => {
      const matchQ = !q ||
        notif.channel_name.toLowerCase().includes(q) ||
        notif.target_endpoint.toLowerCase().includes(q) ||
        (notif.linked_incident_id && notif.linked_incident_id.toLowerCase().includes(q)) ||
        (notif.linked_alert_id && notif.linked_alert_id.toLowerCase().includes(q)) ||
        notif.id.toLowerCase().includes(q);
      const matchSt = st === 'ALL' || notif.status === st;
      return matchQ && matchSt;
    });
  });

  // Filtered Timeline
  public filteredTimeline = computed<OperationalTimelineEventDTO[]>(() => {
    const q = this.timelineSearchQuery().toLowerCase().trim();
    const cat = this.timelineCategoryFilter();

    return this._data().timeline.filter(item => {
      const matchQ = !q ||
        item.summary.toLowerCase().includes(q) ||
        item.entity_name.toLowerCase().includes(q) ||
        item.id.toLowerCase().includes(q) ||
        (item.payload_preview && item.payload_preview.toLowerCase().includes(q));
      const matchCat = cat === 'ALL' || item.category === cat;
      return matchQ && matchCat;
    });
  });

  // -- Navigation / selection (local UI state — legitimately client-owned) --

  public selectTab(tab: AlertsTabKey): void {
    this.selectedTab.set(tab);
  }

  public selectAlert(alertId: string | null): void {
    this.selectedAlertId.set(alertId);
  }

  public selectIncident(incidentId: string | null): void {
    this.selectedIncidentId.set(incidentId);
  }

  // -- Real backend refresh --------------------------------------------

  public async refreshTelemetry(): Promise<void> {
    this.isRefreshing.set(true);
    this.errorMessage.set(null);
    try {
      const [alertsRes, incidentsRes] = await Promise.all([
        this.ipc.listAlerts(),
        this.ipc.listIncidents()
      ]);

      if (alertsRes.status !== 'SUCCESS' || !alertsRes.data || !Array.isArray(alertsRes.data.alerts)) {
        this.isUnavailable.set(true);
        this.errorMessage.set(alertsRes.error || 'Alerts backend unavailable.');
        this.telemetryConfidence.set('NO_DATA');
        this.isRefreshing.set(false);
        return;
      }
      if (incidentsRes.status !== 'SUCCESS' || !incidentsRes.data || !Array.isArray(incidentsRes.data.incidents)) {
        this.isUnavailable.set(true);
        this.errorMessage.set(incidentsRes.error || 'Incidents backend unavailable.');
        this.telemetryConfidence.set('NO_DATA');
        this.isRefreshing.set(false);
        return;
      }

      const alerts = alertsRes.data.alerts.map(mapAlertRecordToActiveAlertDTO);
      const incidents = incidentsRes.data.incidents.map(mapIncidentRecordToIncidentDTO);
      const observedAt = new Date().toISOString();

      this._data.set({
        ...EMPTY_ALERTS_OPERATIONS,
        summary: {
          total_active_alerts: alerts.filter(a => a.state === 'FIRING').length,
          critical_alerts_count: alerts.filter(a => a.severity === 'CRITICAL').length,
          warning_alerts_count: alerts.filter(a => a.severity === 'WARNING').length,
          active_incidents_count: incidents.filter(i => i.status !== 'RESOLVED').length,
          firing_rules_count: 0,
          notification_success_rate_pct: 0,
          observed_at: observedAt,
          telemetry_confidence: 'CURRENT'
        },
        alerts,
        incidents
      });
      this.lastObservedAt.set(observedAt);
      this.telemetryConfidence.set('CURRENT');
      this.isUnavailable.set(false);
    } catch (err: any) {
      this.isUnavailable.set(true);
      this.errorMessage.set(err?.message || 'Alerts/Incidents refresh failed.');
      this.telemetryConfidence.set('NO_DATA');
    } finally {
      this.isRefreshing.set(false);
    }
  }

  /** Loads the real incident timeline for the given incident from the canonical IncidentService. */
  public async loadIncidentTimeline(incidentId: string): Promise<void> {
    const res = await this.ipc.getIncidentTimeline(incidentId);
    if (res.status !== 'SUCCESS' || !res.data) {
      return;
    }
    const timeline = res.data.timeline.map(ev => ({
      id: ev.event_id,
      timestamp: ev.created_at,
      event_type: (
        ev.event_type === 'CREATED' ? 'INCIDENT_OPENED' :
        ev.event_type === 'STATUS_CHANGED' ? 'STATUS_CHANGED' :
        ev.event_type === 'ALERT_ATTACHED' ? 'ALERT_ATTACHED' : 'STATUS_CHANGED'
      ) as any,
      actor: ev.actor_id,
      description: JSON.stringify(ev.details),
      severity: 'INFO' as const
    }));
    const current = this._data();
    this._data.set({
      ...current,
      incidents: current.incidents.map(inc => inc.id === incidentId ? { ...inc, timeline } : inc)
    });
  }

  // -- Real backend mutations --------------------------------------------
  // Each calls the real canonical command. Success updates local state from
  // the AUTHORITATIVE returned record. Failure never mutates local state —
  // it surfaces on lastMutationError so the UI can show it truthfully.

  public async acknowledgeAlert(alertId: string): Promise<void> {
    await this.applyAlertMutation(this.ipc.acknowledgeAlert(alertId));
  }

  public async suppressAlert(alertId: string, durationSeconds = 3600): Promise<void> {
    await this.applyAlertMutation(this.ipc.suppressAlert(alertId, durationSeconds));
  }

  public async resolveAlert(alertId: string): Promise<void> {
    await this.applyAlertMutation(this.ipc.resolveAlert(alertId));
  }

  private async applyAlertMutation(pending: ReturnType<MonitoringIpcService['acknowledgeAlert']>): Promise<void> {
    this.lastMutationError.set(null);
    const res = await pending;
    if (res.status !== 'SUCCESS' || !res.data?.alert) {
      this.lastMutationError.set(res.error || 'Alert mutation was rejected by the backend.');
      return;
    }
    const updated = mapAlertRecordToActiveAlertDTO(res.data.alert);
    const current = this._data();
    this._data.set({
      ...current,
      alerts: current.alerts.map(a => a.id === updated.id ? updated : a)
    });
  }

  public async updateIncidentStatus(incidentId: string, status: UiIncidentStatus): Promise<void> {
    this.lastMutationError.set(null);
    const backendStatus: BackendIncidentStatus =
      status === 'INVESTIGATING' ? 'INVESTIGATING' :
      status === 'IDENTIFIED' ? 'INVESTIGATING' :
      status === 'MONITORING' ? 'MITIGATED' : 'RESOLVED';
    const res = await this.ipc.updateIncidentStatus(incidentId, backendStatus);
    if (res.status !== 'SUCCESS' || !res.data?.incident) {
      this.lastMutationError.set(res.error || 'Incident status update was rejected by the backend.');
      return;
    }
    const updated = mapIncidentRecordToIncidentDTO(res.data.incident);
    const current = this._data();
    this._data.set({
      ...current,
      incidents: current.incidents.map(inc => inc.id === updated.id ? { ...updated, timeline: inc.timeline, operational_notes: inc.operational_notes } : inc)
    });
    await this.loadIncidentTimeline(incidentId);
  }

  /**
   * LEGITIMATE_CAPABILITY_ABSENT: no free-text incident-note semantic exists
   * on the canonical IncidentService (only structured timeline events).
   * This must never fabricate local success — see DevKros CHECK2 + P7.D
   * Monitoring forensic reconciliation, Issue D / Part 19.
   */
  public async addIncidentNote(_incidentId: string, _content: string): Promise<void> {
    this.lastMutationError.set('Incident notes are not available: no canonical backend semantic exists for free-text operator notes (owner decision required).');
  }

  /**
   * LEGITIMATE_CAPABILITY_ABSENT: no notification delivery/retry authority is
   * wired to Monitoring today.
   */
  public async retryNotification(_notificationId: string): Promise<void> {
    this.lastMutationError.set('Notification retry is not available: no canonical backend semantic is wired to Monitoring yet.');
  }
}

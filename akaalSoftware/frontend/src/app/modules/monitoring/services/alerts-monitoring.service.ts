/**
 * AKAAL Monitoring — Part 4 of 4: Alerts & Incidents Service
 * Signal-driven reactive store managing Active Alerts, Alert Evaluation,
 * Incidents, Signal Correlation, Notification & Escalation, and Operational Timeline.
 */

import { Injectable, signal, computed } from '@angular/core';
import { 
  AlertsOperationsDTO, 
  AlertsTabKey, 
  AlertsTabDefinition,
  ActiveAlertDTO,
  AlertEvaluationRuleDTO,
  IncidentDTO,
  IncidentStatus,
  NotificationDeliveryDTO,
  OperationalTimelineEventDTO,
  AlertLifecycleState
} from '../models/alerts-monitoring.models';
import { MOCK_ALERTS_OPERATIONS } from '../fixtures/alerts-monitoring.fixtures';
import { formatSnakeToTitle } from '../models/monitoring.models';

@Injectable({
  providedIn: 'root'
})
export class AlertsMonitoringService {
  // Master Signal State
  private _data = signal<AlertsOperationsDTO>(MOCK_ALERTS_OPERATIONS);
  public data = computed(() => this._data());

  // Active Tab & Selection Signals
  public selectedTab = signal<AlertsTabKey>('active');
  public selectedAlertId = signal<string | null>(null);
  public selectedIncidentId = signal<string | null>('INC-2026-0841');

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

  // Refresh & Freshness State
  public isRefreshing = signal<boolean>(false);
  public lastObservedAt = signal<string>(MOCK_ALERTS_OPERATIONS.summary.observed_at);
  public telemetryConfidence = signal<string>(MOCK_ALERTS_OPERATIONS.summary.telemetry_confidence);

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

  // Mutator Actions
  public selectTab(tab: AlertsTabKey): void {
    this.selectedTab.set(tab);
  }

  public selectAlert(alertId: string | null): void {
    this.selectedAlertId.set(alertId);
  }

  public selectIncident(incidentId: string | null): void {
    this.selectedIncidentId.set(incidentId);
  }

  public setAlertState(alertId: string, newState: AlertLifecycleState): void {
    const current = this._data();
    const updatedAlerts = current.alerts.map(a => {
      if (a.id === alertId) {
        return { ...a, state: newState };
      }
      return a;
    });
    this._data.set({ ...current, alerts: updatedAlerts });
  }

  public acknowledgeAlert(alertId: string): void {
    this.setAlertState(alertId, 'ACKNOWLEDGED');
  }

  public suppressAlert(alertId: string): void {
    this.setAlertState(alertId, 'SUPPRESSED');
  }

  public resolveAlert(alertId: string): void {
    this.setAlertState(alertId, 'RESOLVED');
  }

  public updateIncidentStatus(incidentId: string, status: IncidentStatus): void {
    const current = this._data();
    const updatedIncidents = current.incidents.map(inc => {
      if (inc.id === incidentId) {
        const newTimelineEvent = {
          id: `evt-stat-${Date.now()}`,
          timestamp: new Date().toISOString(),
          event_type: status === 'RESOLVED' ? 'INCIDENT_RESOLVED' as const : 'STATUS_CHANGED' as const,
          actor: 'Operations Console (Operator)',
          description: `Incident status updated to ${status}.`,
          severity: inc.severity === 'CRITICAL' ? 'CRITICAL' as const : 'WARNING' as const
        };
        return {
          ...inc,
          status,
          last_updated_at: new Date().toISOString(),
          timeline: [newTimelineEvent, ...inc.timeline]
        };
      }
      return inc;
    });
    this._data.set({ ...current, incidents: updatedIncidents });
  }

  public addIncidentNote(incidentId: string, content: string): void {
    if (!content.trim()) return;
    const current = this._data();
    const updatedIncidents = current.incidents.map(inc => {
      if (inc.id === incidentId) {
        const newNote = {
          id: `note-${Date.now()}`,
          timestamp: new Date().toISOString(),
          author: 'Lead SRE Operator',
          content: content.trim()
        };
        return {
          ...inc,
          last_updated_at: new Date().toISOString(),
          operational_notes: [newNote, ...inc.operational_notes]
        };
      }
      return inc;
    });
    this._data.set({ ...current, incidents: updatedIncidents });
  }

  public retryNotification(notificationId: string): void {
    const current = this._data();
    const updatedNotifs = current.notifications.map(n => {
      if (n.id === notificationId) {
        return {
          ...n,
          status: 'DELIVERED' as const,
          response_code: 200,
          latency_ms: 184,
          attempt_timestamp: new Date().toISOString(),
          retry_count: n.retry_count + 1,
          error_message: null
        };
      }
      return n;
    });
    this._data.set({ ...current, notifications: updatedNotifs });
  }

  public refreshTelemetry(): void {
    this.isRefreshing.set(true);
    setTimeout(() => {
      this.lastObservedAt.set(new Date().toISOString());
      this.isRefreshing.set(false);
    }, 400);
  }
}

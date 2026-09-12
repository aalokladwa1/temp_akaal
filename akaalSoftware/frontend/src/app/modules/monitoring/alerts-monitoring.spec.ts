/**
 * AKAAL Monitoring — Part 4 of 4: Alerts & Incidents Test Suite
 * Comprehensive unit and integration verification for the Alerts & Incidents workspace,
 * reactive service stores, filtering projections, mutators, and navigation.
 */

import { describe, it, expect, beforeEach } from 'vitest';
import { AlertsMonitoringService } from './services/alerts-monitoring.service';

describe('AlertsMonitoringService', () => {
  let service: AlertsMonitoringService;

  beforeEach(() => {
    service = new AlertsMonitoringService();
  });

  describe('Initialization and State Projection', () => {
    it('should initialize with baseline mock data and correct summary metrics', () => {
      const summary = service.summary();
      expect(summary.total_active_alerts).toBeGreaterThan(0);
      expect(summary.critical_alerts_count).toBeGreaterThanOrEqual(0);
      expect(summary.active_incidents_count).toBeGreaterThan(0);
      expect(summary.notification_success_rate_pct).toBe(94.2);
    });

    it('should project 6 primary workspace tabs with contextual badge counters', () => {
      const tabs = service.tabDefinitions();
      expect(tabs.length).toBe(6);
      expect(tabs.map(t => t.key)).toEqual([
        'active',
        'evaluation',
        'incidents',
        'correlation',
        'notifications',
        'timeline'
      ]);

      const activeTab = tabs.find(t => t.key === 'active');
      expect(activeTab?.badgeCount).toBeGreaterThan(0);
    });

    it('should correctly select default alert and incident', () => {
      const selectedAlert = service.selectedAlert();
      expect(selectedAlert).toBeDefined();
      expect(selectedAlert?.id).toBe('alt-01');

      const selectedInc = service.selectedIncident();
      expect(selectedInc).toBeDefined();
      expect(selectedInc?.id).toBe('INC-2026-0841');
    });
  });

  describe('Alerts Filtering and Lifecycle Mutations', () => {
    it('should filter alerts by search term across title and signal', () => {
      service.alertSearchQuery.set('Aurora');
      const filtered = service.filteredAlerts();
      expect(filtered.length).toBeGreaterThan(0);
      expect(filtered.every(a => 
        a.title.toLowerCase().includes('aurora') || 
        a.affected_entity_name.toLowerCase().includes('aurora')
      )).toBe(true);
    });

    it('should filter alerts by severity level', () => {
      service.alertSeverityFilter.set('CRITICAL');
      const filtered = service.filteredAlerts();
      expect(filtered.every(a => a.severity === 'CRITICAL')).toBe(true);
    });

    it('should filter alerts by lifecycle state', () => {
      service.alertStateFilter.set('FIRING');
      const filtered = service.filteredAlerts();
      expect(filtered.every(a => a.state === 'FIRING')).toBe(true);
    });

    it('should acknowledge, suppress, and resolve active alerts', () => {
      const targetAlertId = 'alt-01';
      
      // Acknowledge
      service.acknowledgeAlert(targetAlertId);
      let alert = service.alerts().find(a => a.id === targetAlertId);
      expect(alert?.state).toBe('ACKNOWLEDGED');

      // Suppress
      service.suppressAlert(targetAlertId);
      alert = service.alerts().find(a => a.id === targetAlertId);
      expect(alert?.state).toBe('SUPPRESSED');

      // Resolve
      service.resolveAlert(targetAlertId);
      alert = service.alerts().find(a => a.id === targetAlertId);
      expect(alert?.state).toBe('RESOLVED');
    });
  });

  describe('Evaluation Rules and Cadence', () => {
    it('should filter rules by text search', () => {
      service.ruleSearchQuery.set('CDC');
      const filtered = service.filteredRules();
      expect(filtered.length).toBeGreaterThan(0);
      expect(filtered.every(r => 
        r.name.toLowerCase().includes('cdc') || 
        r.signal.toLowerCase().includes('cdc') ||
        r.description.toLowerCase().includes('cdc')
      )).toBe(true);
    });

    it('should filter rules by evaluation state', () => {
      service.ruleStateFilter.set('FIRING');
      const filtered = service.filteredRules();
      expect(filtered.every(r => r.result_state === 'FIRING')).toBe(true);
    });
  });

  describe('Incidents Workbench and Collaborative Notes', () => {
    it('should transition incident lifecycle status and append audit timeline event', () => {
      const incidentId = 'INC-2026-0841';
      const initialInc = service.incidents().find(i => i.id === incidentId);
      const initialTimelineCount = initialInc?.timeline.length || 0;

      service.updateIncidentStatus(incidentId, 'RESOLVED');
      
      const updatedInc = service.incidents().find(i => i.id === incidentId);
      expect(updatedInc?.status).toBe('RESOLVED');
      expect(updatedInc?.timeline.length).toBe(initialTimelineCount + 1);
      expect(updatedInc?.timeline[0].event_type).toBe('INCIDENT_RESOLVED');
    });

    it('should post operational notes to the selected incident', () => {
      const incidentId = 'INC-2026-0841';
      const initialNotesCount = service.incidents().find(i => i.id === incidentId)?.operational_notes.length || 0;

      const noteText = 'Target RDS max_connections parameter verified at 5000.';
      service.addIncidentNote(incidentId, noteText);

      const updatedInc = service.incidents().find(i => i.id === incidentId);
      expect(updatedInc?.operational_notes.length).toBe(initialNotesCount + 1);
      expect(updatedInc?.operational_notes[0].content).toBe(noteText);
      expect(updatedInc?.operational_notes[0].author).toBe('Lead SRE Operator');
    });
  });

  describe('Signal Correlation and Topology', () => {
    it('should provide multi-tier signal chain nodes from root symptom to active incident', () => {
      const correlation = service.correlation();
      expect(correlation.signal_chain.length).toBe(5);
      expect(correlation.signal_chain[0].level).toBe('Primary Signal');
      expect(correlation.signal_chain[2].level).toBe('Active Incident');
    });

    it('should contain correlated topology entities with health and deep link info', () => {
      const entities = service.correlation().related_entities;
      expect(entities.length).toBeGreaterThan(0);
      expect(entities.every(e => e.deep_link && e.health)).toBe(true);
    });
  });

  describe('Notification Dispatch and Retry Mutators', () => {
    it('should filter notifications by status', () => {
      service.notificationStatusFilter.set('RETRYING');
      const filtered = service.filteredNotifications();
      expect(filtered.every(n => n.status === 'RETRYING')).toBe(true);
    });

    it('should retry a failed or retrying notification dispatch and transition to DELIVERED', () => {
      const retryingNotif = service.notifications().find(n => n.status === 'RETRYING');
      expect(retryingNotif).toBeDefined();

      if (retryingNotif) {
        service.retryNotification(retryingNotif.id);
        const updated = service.notifications().find(n => n.id === retryingNotif.id);
        expect(updated?.status).toBe('DELIVERED');
        expect(updated?.response_code).toBe(200);
        expect(updated?.retry_count).toBe(retryingNotif.retry_count + 1);
      }
    });
  });

  describe('Operational Timeline Stream', () => {
    it('should filter timeline events by category', () => {
      service.timelineCategoryFilter.set('ALERT_FIRING');
      const filtered = service.filteredTimeline();
      expect(filtered.every(t => t.category === 'ALERT_FIRING')).toBe(true);
    });

    it('should filter timeline events by search keyword', () => {
      service.timelineSearchQuery.set('Kafka');
      const filtered = service.filteredTimeline();
      expect(filtered.length).toBeGreaterThan(0);
      expect(filtered.every(t => 
        t.summary.toLowerCase().includes('kafka') || 
        t.entity_name.toLowerCase().includes('kafka') ||
        (t.payload_preview && t.payload_preview.toLowerCase().includes('kafka'))
      )).toBe(true);
    });
  });
});

/**
 * AKAAL Monitoring — Part 4 of 4: Alerts & Incidents Test Suite
 * Verifies the real IPC-backed integration: successful fetch population,
 * fail-closed behavior when the backend is unavailable/rejects, and that
 * absent capabilities (incident notes, notification retry) never fabricate
 * local success.
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { AlertsMonitoringService } from './services/alerts-monitoring.service';
import { MonitoringIpcService, AlertRecordDTO, IncidentRecordDTO } from './services/monitoring.ipc';

function makeAlert(overrides: Partial<AlertRecordDTO> = {}): AlertRecordDTO {
  return {
    alert_id: 'alt-01',
    tenant_id: 'default',
    signal_name: 'cdc_lag_seconds',
    dedup_fingerprint: 'fp-1',
    severity: 'CRITICAL',
    lifecycle_state: 'OPEN',
    message: 'CDC lag exceeded threshold',
    rule_id: 'rule-1',
    current_value: '420',
    threshold_value: '300',
    context_payload: null,
    observation_count: 3,
    suppression_expires_at: null,
    acknowledged_by: null,
    acknowledged_at: null,
    resolved_at: null,
    first_observed_at: '2026-09-17T00:00:00Z',
    last_observed_at: '2026-09-17T00:05:00Z',
    created_at: '2026-09-17T00:00:00Z',
    ...overrides
  };
}

function makeIncident(overrides: Partial<IncidentRecordDTO> = {}): IncidentRecordDTO {
  return {
    incident_id: 'INC-01',
    tenant_id: 'default',
    title: 'Core Ledger Migration degraded',
    severity: 'SEV1',
    status: 'OPEN',
    summary: 'CDC lag breached SLA',
    migration_id: 'mig-01',
    node_id: null,
    correlation_key: null,
    owner_actor_id: null,
    created_at: '2026-09-17T00:00:00Z',
    updated_at: '2026-09-17T00:00:00Z',
    resolved_at: null,
    ...overrides
  };
}

function makeFakeIpc(overrides: Partial<MonitoringIpcService> = {}): MonitoringIpcService {
  const base = {
    listAlerts: vi.fn().mockResolvedValue({ status: 'SUCCESS', data: { alerts: [makeAlert()] } }),
    listIncidents: vi.fn().mockResolvedValue({ status: 'SUCCESS', data: { incidents: [makeIncident()] } }),
    getIncidentTimeline: vi.fn().mockResolvedValue({ status: 'SUCCESS', data: { timeline: [] } }),
    getIncident: vi.fn(),
    getAlert: vi.fn(),
    getFleetStatus: vi.fn(),
    updateIncidentStatus: vi.fn().mockResolvedValue({
      status: 'SUCCESS',
      data: { incident: makeIncident({ status: 'RESOLVED' }) }
    }),
    acknowledgeAlert: vi.fn().mockResolvedValue({ status: 'SUCCESS', data: { alert: makeAlert({ lifecycle_state: 'ACKNOWLEDGED' }) } }),
    resolveAlert: vi.fn().mockResolvedValue({ status: 'SUCCESS', data: { alert: makeAlert({ lifecycle_state: 'RESOLVED' }) } }),
    suppressAlert: vi.fn().mockResolvedValue({ status: 'SUCCESS', data: { alert: makeAlert({ lifecycle_state: 'SUPPRESSED' }) } }),
  };
  return { ...base, ...overrides } as unknown as MonitoringIpcService;
}

describe('AlertsMonitoringService', () => {
  describe('Successful backend refresh', () => {
    let service: AlertsMonitoringService;

    beforeEach(async () => {
      service = new AlertsMonitoringService(makeFakeIpc());
      await service.refreshTelemetry();
    });

    it('should populate real alerts and incidents from the backend, not fixtures', () => {
      expect(service.alerts().length).toBe(1);
      expect(service.alerts()[0].id).toBe('alt-01');
      expect(service.incidents().length).toBe(1);
      expect(service.incidents()[0].id).toBe('INC-01');
      expect(service.isUnavailable()).toBe(false);
    });

    it('should project 6 primary workspace tabs', () => {
      const tabs = service.tabDefinitions();
      expect(tabs.map(t => t.key)).toEqual(['active', 'evaluation', 'incidents', 'correlation', 'notifications', 'timeline']);
    });

    it('should truthfully report correlation/notifications/evaluation as unavailable rather than fabricate data', () => {
      expect(service.correlation().signal_chain.length).toBe(0);
      expect(service.correlation().correlation_summary).toContain('not available');
      expect(service.notifications().length).toBe(0);
      expect(service.evaluationRules().length).toBe(0);
    });

    it('should filter alerts by search term and severity', () => {
      service.alertSearchQuery.set('cdc_lag');
      expect(service.filteredAlerts().length).toBe(1);
      service.alertSeverityFilter.set('CRITICAL');
      expect(service.filteredAlerts().every(a => a.severity === 'CRITICAL')).toBe(true);
    });

    it('should acknowledge, suppress, and resolve an alert via real backend calls and reflect the authoritative result', async () => {
      await service.acknowledgeAlert('alt-01');
      expect(service.alerts().find(a => a.id === 'alt-01')?.state).toBe('ACKNOWLEDGED');

      await service.suppressAlert('alt-01');
      expect(service.alerts().find(a => a.id === 'alt-01')?.state).toBe('SUPPRESSED');

      await service.resolveAlert('alt-01');
      expect(service.alerts().find(a => a.id === 'alt-01')?.state).toBe('RESOLVED');
    });

    it('should update incident status via the real backend command and reflect the authoritative result', async () => {
      await service.updateIncidentStatus('INC-01', 'RESOLVED');
      expect(service.incidents().find(i => i.id === 'INC-01')?.status).toBe('RESOLVED');
    });
  });

  describe('Backend failure — fail closed, never fabricate healthy state', () => {
    it('should mark the service unavailable and keep data empty when the backend errors', async () => {
      const fakeIpc = makeFakeIpc({
        listAlerts: vi.fn().mockResolvedValue({ status: 'ERROR', error: 'ENGINE_DISCONNECTED' })
      });
      const service = new AlertsMonitoringService(fakeIpc);
      await service.refreshTelemetry();

      expect(service.isUnavailable()).toBe(true);
      expect(service.errorMessage()).toBe('ENGINE_DISCONNECTED');
      expect(service.alerts().length).toBe(0);
      expect(service.incidents().length).toBe(0);
    });

    it('should not mutate local alert state when a mutation is rejected by the backend', async () => {
      const fakeIpc = makeFakeIpc({
        acknowledgeAlert: vi.fn().mockResolvedValue({ status: 'ERROR', error: 'PERMISSION_DENIED' })
      });
      const service = new AlertsMonitoringService(fakeIpc);
      await service.refreshTelemetry();

      await service.acknowledgeAlert('alt-01');
      expect(service.alerts().find(a => a.id === 'alt-01')?.state).toBe('FIRING');
      expect(service.lastMutationError()).toBe('PERMISSION_DENIED');
    });
  });

  describe('Absent capabilities — must never fabricate success', () => {
    let service: AlertsMonitoringService;

    beforeEach(async () => {
      service = new AlertsMonitoringService(makeFakeIpc());
      await service.refreshTelemetry();
    });

    it('should not append a fake incident note locally', async () => {
      const before = service.incidents().find(i => i.id === 'INC-01')?.operational_notes.length ?? 0;
      await service.addIncidentNote('INC-01', 'attempted note');
      const after = service.incidents().find(i => i.id === 'INC-01')?.operational_notes.length ?? 0;
      expect(after).toBe(before);
      expect(service.lastMutationError()).toContain('not available');
    });

    it('should not fabricate a delivered notification retry', async () => {
      await service.retryNotification('notif-1');
      expect(service.notifications().length).toBe(0);
      expect(service.lastMutationError()).toContain('not available');
    });
  });
});

import { describe, it, expect, vi } from 'vitest';
import { MonitoringService } from './services/monitoring.service';
import { CANONICAL_MODES, CanonicalMigrationMode } from './models/monitoring.models';
import {
  MonitoringIpcService,
  MigrationAggregateDTO,
  IncidentRecordDTO,
  AlertRecordDTO,
  FleetNodeSnapshotDTO
} from './services/monitoring.ipc';

function makeMigration(overrides: Partial<MigrationAggregateDTO> = {}): MigrationAggregateDTO {
  return {
    migration_id: 'mig-01', revision: 1, name: 'Core Ledger Migration', mode: 'M2', state: 'ACTIVE',
    tenant_id: 'default', workspace_id: 'ws-1', project_id: 'proj-1', configuration: {},
    plan_id: null, initialization_id: null, active_attempt_id: null, active_schedule_id: null,
    lineage: {}, created_at: '2026-09-17T00:00:00Z', updated_at: '2026-09-17T00:00:00Z',
    ...overrides
  };
}

function makeIncident(overrides: Partial<IncidentRecordDTO> = {}): IncidentRecordDTO {
  return {
    incident_id: 'INC-01', tenant_id: 'default', title: 'CDC lag breach', severity: 'SEV1', status: 'OPEN',
    summary: 'Replication lag exceeded threshold', migration_id: 'mig-01', node_id: null, correlation_key: null,
    owner_actor_id: null, created_at: new Date(Date.now() - 5 * 60000).toISOString(), updated_at: '2026-09-17T00:00:00Z',
    resolved_at: null, ...overrides
  };
}

function makeAlert(overrides: Partial<AlertRecordDTO> = {}): AlertRecordDTO {
  return {
    alert_id: 'alt-01', tenant_id: 'default', signal_name: 'cdc_lag_seconds', dedup_fingerprint: 'fp-1',
    severity: 'CRITICAL', lifecycle_state: 'OPEN', message: 'lag exceeded', rule_id: 'r-1', current_value: '400',
    threshold_value: '300', context_payload: null, observation_count: 1, suppression_expires_at: null,
    acknowledged_by: null, acknowledged_at: null, resolved_at: null,
    first_observed_at: '2026-09-17T00:00:00Z', last_observed_at: '2026-09-17T00:00:00Z', created_at: '2026-09-17T00:00:00Z',
    ...overrides
  };
}

function makeNode(overrides: Partial<FleetNodeSnapshotDTO> = {}): FleetNodeSnapshotDTO {
  return {
    node_id: 'node-1', address: '127.0.0.1', port: 9000, liveness: 'ALIVE', drain_state: 'ACTIVE',
    active_executions: 0, assigned_workloads: 0, capabilities: [], last_heartbeat_ago_sec: 0,
    registered_at_iso: '2026-09-17T00:00:00Z', ...overrides
  };
}

function makeFakeIpc(overrides: Partial<MonitoringIpcService> = {}): MonitoringIpcService {
  return {
    listMigrations: vi.fn().mockResolvedValue({ status: 'SUCCESS', data: { migrations: [makeMigration()], limit: 200, offset: 0, total: 1, next_offset: null } }),
    listIncidents: vi.fn().mockResolvedValue({ status: 'SUCCESS', data: { incidents: [makeIncident()] } }),
    listAlerts: vi.fn().mockResolvedValue({ status: 'SUCCESS', data: { alerts: [makeAlert()] } }),
    getFleetStatus: vi.fn().mockResolvedValue({ status: 'SUCCESS', data: { nodes: [makeNode()] } }),
    ...overrides
  } as unknown as MonitoringIpcService;
}

describe('AKAAL Monitoring Home (Part 1 of 4) — real backend integration', () => {
  describe('Canonical Modes (M1-M7)', () => {
    it('should define all M1-M7 canonical migration modes and exclude M8', () => {
      const modes: CanonicalMigrationMode[] = ['M1_BULK', 'M2_BULK_CDC', 'M3_CDC', 'M4_INCREMENTAL', 'M5_STATE_SYNC', 'M6_SCHEMA_ONLY', 'M7_DATA_ONLY'];
      modes.forEach(mode => expect(CANONICAL_MODES[mode]).toBeDefined());
      expect((CANONICAL_MODES as any)['M8_VALIDATION_ONLY']).toBeUndefined();
    });
  });

  describe('Real composition from canonical backend queries', () => {
    it('should populate summary, active migrations, needs-attention, and alerts from real data', async () => {
      const service = new MonitoringService(makeFakeIpc());
      await service.initializeState();

      expect(service.isUnavailable()).toBe(false);
      expect(service.summary()?.total_migrations_count).toBe(1);
      expect(service.activeMigrations()[0].id).toBe('mig-01');
      expect(service.activeMigrations()[0].mode).toBe('M2_BULK_CDC');
      expect(service.needsAttention()[0].entity_type).toBe('INCIDENT');
      expect(service.needsAttention()[0].entity_id).toBe('INC-01');
      expect(service.activeAlerts()[0].id).toBe('alt-01');
      expect(service.summary()?.overall_platform_health).toBe('HEALTHY');
      expect(service.summary()?.engine_connection_state).toBe('CONNECTED');
    });

    it('should exclude M8 migrations from the Overview roster', async () => {
      const ipc = makeFakeIpc({
        listMigrations: vi.fn().mockResolvedValue({
          status: 'SUCCESS',
          data: { migrations: [makeMigration({ migration_id: 'a', mode: 'M2' }), makeMigration({ migration_id: 'b', mode: 'M8' })], limit: 200, offset: 0, total: 2, next_offset: null }
        })
      });
      const service = new MonitoringService(ipc);
      await service.initializeState();
      expect(service.activeMigrations().map(m => m.id)).toEqual(['a']);
    });

    it('should preserve unknown per-migration health as UNKNOWN rather than fabricate it', async () => {
      const service = new MonitoringService(makeFakeIpc());
      await service.initializeState();
      expect(service.activeMigrations()[0].health).toBe('UNKNOWN');
      expect(service.activeMigrations()[0].progress_percent).toBeNull();
    });

    it('should leave platform_health, operational_pressure, and recentEvents truthfully empty (no canonical source)', async () => {
      const service = new MonitoringService(makeFakeIpc());
      await service.initializeState();
      expect(service.platformHealth()).toEqual([]);
      expect(service.operationalPressure()).toEqual([]);
      expect(service.recentEvents()).toEqual([]);
    });

    it('should mark overall_platform_health UNHEALTHY when any fleet node is DEAD', async () => {
      const ipc = makeFakeIpc({ getFleetStatus: vi.fn().mockResolvedValue({ status: 'SUCCESS', data: { nodes: [makeNode({ liveness: 'DEAD' })] } }) });
      const service = new MonitoringService(ipc);
      await service.initializeState();
      expect(service.summary()?.overall_platform_health).toBe('UNHEALTHY');
    });

    it('should filter active migrations by search query', async () => {
      const service = new MonitoringService(makeFakeIpc());
      await service.initializeState();
      service.migrationSearchQuery.set('Core Ledger');
      expect(service.filteredActiveMigrations().length).toBe(1);
      service.migrationSearchQuery.set('nonexistent');
      expect(service.filteredActiveMigrations().length).toBe(0);
    });

    it('should format relative observation time', () => {
      const service = new MonitoringService(makeFakeIpc());
      const now = new Date().toISOString();
      expect(service.formatObservationTime(now)).toBe('Just now');
    });
  });

  describe('Backend failure — fail closed, never fabricate a baseline', () => {
    it('should mark unavailable and never populate a deterministic baseline when migration.list fails', async () => {
      const service = new MonitoringService(makeFakeIpc({ listMigrations: vi.fn().mockResolvedValue({ status: 'ERROR', error: 'ENGINE_DISCONNECTED' }) }));
      await service.initializeState();

      expect(service.isUnavailable()).toBe(true);
      expect(service.errorMessage()).toBeTruthy();
      expect(service.activeMigrations().length).toBe(0);
      expect(service.summary()).toBeNull();
    });

    it('should set isRefreshing true during refresh and false on completion', async () => {
      const service = new MonitoringService(makeFakeIpc());
      const p = service.refresh();
      expect(service.isRefreshing()).toBe(true);
      await p;
      expect(service.isRefreshing()).toBe(false);
    });

    it('should handle a thrown IPC error cleanly without an uncaught exception', async () => {
      const ipc = makeFakeIpc({ listMigrations: vi.fn().mockRejectedValueOnce(new Error('IPC socket connection refused')) });
      const service = new MonitoringService(ipc);
      await service.initializeState();
      expect(service.isLoading()).toBe(false);
      expect(service.isUnavailable()).toBe(true);
    });
  });
});

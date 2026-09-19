import { describe, it, expect, vi } from 'vitest';
import { MigrationMonitoringService } from './services/migration-monitoring.service';
import { CANONICAL_MODES } from './models/migration-monitoring.models';
import { MonitoringIpcService, MigrationAggregateDTO } from '../../core/services/ipc/monitoring.ipc';

function makeMigration(overrides: Partial<MigrationAggregateDTO> = {}): MigrationAggregateDTO {
  return {
    migration_id: 'mig-01',
    revision: 1,
    name: 'Core Banking Migration',
    mode: 'M2',
    state: 'ACTIVE',
    tenant_id: 'default',
    workspace_id: 'ws-1',
    project_id: 'proj-1',
    configuration: {},
    plan_id: 'plan-1',
    initialization_id: null,
    active_attempt_id: null,
    active_schedule_id: null,
    lineage: {},
    created_at: '2026-09-17T00:00:00Z',
    updated_at: '2026-09-17T00:10:00Z',
    ...overrides
  };
}

function makeFakeIpc(migrations: MigrationAggregateDTO[]): MonitoringIpcService {
  return {
    listMigrations: vi.fn().mockResolvedValue({
      status: 'SUCCESS',
      data: { migrations, limit: 200, offset: 0, total: migrations.length, next_offset: null }
    }),
  } as unknown as MonitoringIpcService;
}

describe('AKAAL Monitoring — Migration Operations (real backend integration)', () => {
  describe('Fleet roster — real backend projection', () => {
    it('should populate the fleet from real migration.list records, mapping M1-M7 modes and excluding M8', async () => {
      const ipc = makeFakeIpc([
        makeMigration({ migration_id: 'mig-01', mode: 'M2', state: 'ACTIVE' }),
        makeMigration({ migration_id: 'mig-02', mode: 'M8', state: 'ACTIVE' }), // validation-only, must be excluded
        makeMigration({ migration_id: 'mig-03', mode: 'M4', state: 'PAUSED' }),
      ]);
      const service = new MigrationMonitoringService(ipc);
      await service.initializeState();

      const fleet = service.fleetList();
      expect(fleet.length).toBe(2);
      expect(fleet.map(f => f.id)).toEqual(['mig-01', 'mig-03']);
      expect(fleet.find(f => f.id === 'mig-01')?.mode).toBe('M2_BULK_CDC');
      expect(fleet.find(f => f.id === 'mig-03')?.mode).toBe('M4_INCREMENTAL');

      const canonicalKeys = Object.keys(CANONICAL_MODES);
      expect(canonicalKeys).not.toContain('M8_VALIDATION_ONLY');
      expect(canonicalKeys.length).toBe(7);
    });

    it('should map backend lifecycle states to the frozen operational_state vocabulary deterministically', async () => {
      const ipc = makeFakeIpc([
        makeMigration({ migration_id: 'a', state: 'ACTIVE' }),
        makeMigration({ migration_id: 'b', state: 'PAUSING' }),
        makeMigration({ migration_id: 'c', state: 'INITIALIZED' }),
        makeMigration({ migration_id: 'd', state: 'COMPLETED' }),
        makeMigration({ migration_id: 'e', state: 'FAILED' }),
      ]);
      const service = new MigrationMonitoringService(ipc);
      await service.initializeState();

      const byId = (id: string) => service.fleetList().find(f => f.id === id);
      expect(byId('a')?.operational_state).toBe('ACTIVE');
      expect(byId('b')?.operational_state).toBe('PAUSED');
      expect(byId('c')?.operational_state).toBe('INITIALIZING');
      expect(byId('d')?.operational_state).toBe('COMPLETED');
      expect(byId('e')?.operational_state).toBe('FAILED');
    });

    it('should compute a real fleet count summary from the projected roster', async () => {
      const ipc = makeFakeIpc([
        makeMigration({ migration_id: 'a', state: 'ACTIVE' }),
        makeMigration({ migration_id: 'b', state: 'ACTIVE' }),
      ]);
      const service = new MigrationMonitoringService(ipc);
      await service.initializeState();

      expect(service.fleetCountSummary().total).toBe(2);
      expect(service.summary()?.total_fleet_count).toBe(2);
    });
  });

  describe('Backend failure — fail closed, never fabricate a fleet', () => {
    it('should mark unavailable and keep the fleet empty when migration.list errors', async () => {
      const ipc = {
        listMigrations: vi.fn().mockResolvedValue({ status: 'ERROR', error: 'ENGINE_DISCONNECTED' })
      } as unknown as MonitoringIpcService;
      const service = new MigrationMonitoringService(ipc);
      await service.initializeState();

      expect(service.isUnavailable()).toBe(true);
      expect(service.fleetList().length).toBe(0);
      expect(service.summary()).toBeNull();
    });
  });

  describe('Fleet search & filtering', () => {
    it('should filter fleet by search query and mode', async () => {
      const ipc = makeFakeIpc([
        makeMigration({ migration_id: 'a', name: 'Oracle to Postgres', mode: 'M1' }),
        makeMigration({ migration_id: 'b', name: 'MySQL to Snowflake', mode: 'M3' }),
      ]);
      const service = new MigrationMonitoringService(ipc);
      await service.initializeState();

      service.setSearchQuery('Oracle');
      expect(service.filteredFleet().map(f => f.id)).toEqual(['a']);

      service.resetFilters();
      service.setModeFilter('M3_CDC');
      expect(service.filteredFleet().map(f => f.id)).toEqual(['b']);
    });
  });

  describe('Selected migration detail — truthful absence, not fabrication', () => {
    it('should set selectedMigration to null and flag detail-unavailable for a real migration with no canonical deep-telemetry source', async () => {
      const ipc = makeFakeIpc([makeMigration({ migration_id: 'mig-01' })]);
      const service = new MigrationMonitoringService(ipc);
      await service.initializeState();

      service.selectMigration('mig-01');
      await service.loadSelectedMigrationDetail('mig-01');

      // Frozen UI's own @if (mms.selectedMigrationId() && mms.selectedMigration()) guard
      // already renders nothing when selectedMigration() is null -- this is truthful
      // unavailable state, not shrinkage of the UI.
      expect(service.selectedMigration()).toBeNull();
      expect(service.selectedMigrationDetailUnavailable()).toBe(true);
    });

    it('should never invent a fabricated migration for an unknown id (no fallback item)', async () => {
      const ipc = makeFakeIpc([makeMigration({ migration_id: 'mig-01' })]);
      const service = new MigrationMonitoringService(ipc);
      await service.initializeState();

      service.selectMigration('does-not-exist');
      await service.loadSelectedMigrationDetail('does-not-exist');

      expect(service.selectedMigration()).toBeNull();
      expect(service.selectedMigrationDetailUnavailable()).toBe(false);
      expect(service.fleetList().some(f => f.id === 'does-not-exist')).toBe(false);
    });
  });
});

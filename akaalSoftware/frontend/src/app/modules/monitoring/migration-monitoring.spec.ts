import { describe, it, expect, beforeEach } from 'vitest';
import { MigrationMonitoringService } from './services/migration-monitoring.service';
import { MOCK_MIGRATION_FLEET, MOCK_FLEET_SUMMARY, MOCK_SELECTED_MIGRATION_M2 } from './fixtures/migration-monitoring.fixtures';
import { MIGRATION_TABS, CANONICAL_MODES } from './models/migration-monitoring.models';

describe('AKAAL Monitoring — Part 2 of 4: Migration Operations Master Integrity Suite', () => {
  let service: MigrationMonitoringService;

  beforeEach(() => {
    service = new MigrationMonitoringService();
  });

  describe('1. Fleet State & Canonical Mode Coverage (M1-M7 Only)', () => {
    it('should initialize with all 7 canonical migration fleet items', () => {
      const fleet = service.fleetList();
      expect(fleet.length).toBe(7);
      
      const modesInFleet = fleet.map(f => f.mode);
      expect(modesInFleet).toContain('M1_BULK');
      expect(modesInFleet).toContain('M2_BULK_CDC');
      expect(modesInFleet).toContain('M3_CDC');
      expect(modesInFleet).toContain('M4_INCREMENTAL');
      expect(modesInFleet).toContain('M5_STATE_SYNC');
      expect(modesInFleet).toContain('M6_SCHEMA_ONLY');
      expect(modesInFleet).toContain('M7_DATA_ONLY');
    });

    it('must strictly exclude M8 Validation Only from Migration Monitoring fleet and mode lists', () => {
      const fleet = service.fleetList();
      const hasM8 = fleet.some(f => (f.mode as string).includes('M8') || (f.mode as string).includes('VALIDATION'));
      expect(hasM8).toBe(false);

      const canonicalKeys = Object.keys(CANONICAL_MODES);
      expect(canonicalKeys).not.toContain('M8_VALIDATION_ONLY');
      expect(canonicalKeys.length).toBe(7);
    });

    it('should compute fleet count summary correctly', () => {
      const summary = service.fleetCountSummary();
      expect(summary.total).toBe(7);
      expect(summary.running).toBeGreaterThan(0);
      expect(summary.healthy).toBeGreaterThan(0);
    });
  });

  describe('2. Fleet Search & Multi-Dimensional Filtering', () => {
    it('should filter fleet by text search query across name, project, and providers', () => {
      service.setSearchQuery('Oracle');
      const results = service.filteredFleet();
      expect(results.length).toBeGreaterThan(0);
      expect(results.every(r => 
        r.name.toLowerCase().includes('oracle') ||
        r.source_provider.toLowerCase().includes('oracle') ||
        r.target_provider.toLowerCase().includes('oracle')
      )).toBe(true);

      // Search non-existent
      service.setSearchQuery('NonExistentDatabaseXYZ');
      expect(service.filteredFleet().length).toBe(0);
    });

    it('should filter fleet strictly by canonical migration mode', () => {
      service.setModeFilter('M2_BULK_CDC');
      const results = service.filteredFleet();
      expect(results.length).toBe(1);
      expect(results[0].mode).toBe('M2_BULK_CDC');
      expect(results[0].id).toBe('mig-core-banking-01');
    });

    it('should filter fleet by health state', () => {
      service.setHealthFilter('DEGRADED');
      const results = service.filteredFleet();
      expect(results.length).toBe(2);
      expect(results.every(r => r.health === 'DEGRADED')).toBe(true);
    });

    it('should filter fleet by operational state', () => {
      service.setStateFilter('ATTENTION');
      const results = service.filteredFleet();
      expect(results.length).toBe(2);
      expect(results.every(r => r.operational_state === 'ATTENTION')).toBe(true);
    });

    it('should reset all filters cleanly to restore full fleet view', () => {
      service.setSearchQuery('Core');
      service.setModeFilter('M2_BULK_CDC');
      service.setHealthFilter('HEALTHY');
      service.setStateFilter('RUNNING');
      expect(service.filteredFleet().length).toBe(1);

      service.resetFilters();
      expect(service.searchQuery()).toBe('');
      expect(service.modeFilter()).toBe('ALL');
      expect(service.healthFilter()).toBe('ALL');
      expect(service.stateFilter()).toBe('ALL');
      expect(service.filteredFleet().length).toBe(7);
    });
  });

  describe('3. Selected Migration Workspace & 8 Investigation Areas', () => {
    it('should contain exactly 8 standard investigation tab definitions in correct order', () => {
      expect(MIGRATION_TABS.length).toBe(8);
      const tabKeys = MIGRATION_TABS.map(t => t.key);
      expect(tabKeys).toEqual([
        'overview',
        'execution',
        'performance',
        'resources',
        'health',
        'reliability',
        'alerts',
        'diagnostics'
      ]);
    });

    it('should load rich composite detail when selecting migration', () => {
      service.selectMigration('mig-core-banking-01');
      expect(service.selectedMigrationId()).toBe('mig-core-banking-01');
      
      const detail = service.selectedMigration();
      expect(detail).toBeDefined();
      expect(detail?.header.id).toBe('mig-core-banking-01');
      expect(detail?.overview).toBeDefined();
      expect(detail?.execution).toBeDefined();
      expect(detail?.performance).toBeDefined();
      expect(detail?.resources).toBeDefined();
      expect(detail?.health).toBeDefined();
      expect(detail?.reliability).toBeDefined();
      expect(detail?.alerts).toBeDefined();
      expect(detail?.diagnostics).toBeDefined();
    });

    it('should switch tabs properly', () => {
      expect(service.selectedTab()).toBe('overview');
      service.selectTab('performance');
      expect(service.selectedTab()).toBe('performance');
      service.selectTab('reliability');
      expect(service.selectedTab()).toBe('reliability');
    });

    it('should clear selection when selecting null', () => {
      service.selectMigration('mig-core-banking-01');
      expect(service.selectedMigration()).not.toBeNull();
      service.selectMigration(null);
      expect(service.selectedMigrationId()).toBeNull();
      expect(service.selectedMigration()).toBeNull();
    });
  });

  describe('4. Truthful Progress & Continuous Stream Semantics', () => {
    it('should preserve progress_percent as null for continuous CDC stream migrations (no fake 0%)', () => {
      const cdcItem = service.fleetList().find(m => m.id === 'mig-orders-stream-03');
      expect(cdcItem).toBeDefined();
      expect(cdcItem?.mode).toBe('M3_CDC');
      expect(cdcItem?.progress_percent).toBeNull();
    });

    it('should provide exact numeric progress_percent for bounded migrations', () => {
      const snapshotItem = service.fleetList().find(m => m.id === 'mig-analytics-warehouse-02');
      expect(snapshotItem).toBeDefined();
      expect(snapshotItem?.progress_percent).toBe(75);
    });
  });

  describe('5. M1 through M7 Specialized Mode Telemetries', () => {
    it('should provide M1 Bulk Snapshot specific metrics', () => {
      service.selectMigration('mig-analytics-warehouse-02');
      const detail = service.selectedMigration();
      expect(detail?.execution.m1_bulk).toBeDefined();
      expect(detail?.execution.m1_bulk?.active_partitions).toBe(6);
      expect(detail?.execution.m1_bulk?.target_write_latency_ms).toBeGreaterThan(0);
    });

    it('should provide M2 Bulk + CDC with 4 phases and cutover readiness signals', () => {
      service.selectMigration('mig-core-banking-01');
      const detail = service.selectedMigration();
      expect(detail?.execution.m2_bulk_cdc).toBeDefined();
      expect(detail?.execution.m2_bulk_cdc?.current_phase).toBe('CONTINUOUS_SYNC');
      expect(detail?.execution.m2_bulk_cdc?.cutover_readiness_signals).toBeDefined();
      expect(detail?.execution.m2_bulk_cdc?.cutover_readiness_signals.schema_barriers_count).toBe(0);
    });

    it('should provide M3 Continuous CDC specific metrics', () => {
      service.selectMigration('mig-orders-stream-03');
      const detail = service.selectedMigration();
      expect(detail?.execution.m3_cdc).toBeDefined();
      expect(detail?.execution.m3_cdc?.replication_lag_ms).toBeGreaterThan(0);
      expect(detail?.execution.m3_cdc?.ring_buffer_fill_pct).toBeGreaterThan(0);
    });

    it('should provide M4 Incremental Polling watermark metrics', () => {
      service.selectMigration('mig-customer-polling-04');
      const detail = service.selectedMigration();
      expect(detail?.execution.m4_incremental).toBeDefined();
      expect(detail?.execution.m4_incremental?.watermark_field).toBe('UPDATED_AT_TIMESTAMP');
    });

    it('should provide M5 State-Based Sync scan and drift metrics', () => {
      service.selectMigration('mig-inventory-reconcile-05');
      const detail = service.selectedMigration();
      expect(detail?.execution.m5_state_sync).toBeDefined();
      expect(detail?.execution.m5_state_sync?.drift_detected_count).toBe(840);
    });

    it('should provide M6 Schema Only DDL metrics', () => {
      service.selectMigration('mig-billing-schema-06');
      const detail = service.selectedMigration();
      expect(detail?.execution.m6_schema).toBeDefined();
      expect(detail?.execution.m6_schema?.objects_applied).toBe(45);
    });

    it('should provide M7 Data Only transfer metrics', () => {
      service.selectMigration('mig-logs-archive-07');
      const detail = service.selectedMigration();
      expect(detail?.execution.m7_data_only).toBeDefined();
      expect(detail?.execution.m7_data_only?.transfer_rate_rows_per_sec).toBe(42000);
    });
  });

  describe('6. 7-Dimensional Composed Health Evaluation', () => {
    it('should evaluate all 7 dimensions of health composition', () => {
      service.selectMigration('mig-core-banking-01');
      const health = service.selectedMigration()?.health;
      expect(health?.composed_states.length).toBe(7);

      const dimensions = health?.composed_states.map(d => d.dimension);
      expect(dimensions).toContain('Applicability');
      expect(dimensions).toContain('Configuration');
      expect(dimensions).toContain('Authorization');
      expect(dimensions).toContain('Availability');
      expect(dimensions).toContain('Endpoint Health');
      expect(dimensions).toContain('Freshness');
      expect(dimensions).toContain('Completeness');
    });
  });

  describe('7. Advisory Root Cause Analysis & Epistemic Intelligence', () => {
    it('should phrase RCA hypotheses as advisory candidate hypotheses with confidence', () => {
      service.selectMigration('mig-core-banking-01');
      const rcaList = service.selectedMigration()?.reliability.rca_candidates;
      expect(rcaList).toBeDefined();
      expect(rcaList!.length).toBeGreaterThan(0);
      
      const firstRca = rcaList![0];
      expect(firstRca.rank).toBe(1);
      expect(firstRca.confidence_percent).toBeGreaterThan(0);
      expect(['ADVISORY_HYPOTHESIS', 'CORRELATED_ANOMALY']).toContain(firstRca.epistemic_status);
      expect(firstRca.supporting_evidence.length).toBeGreaterThan(5);
    });
  });

  describe('8. Zero Snake_Case / Clean UI Typography Integrity', () => {
    it('should format all canonical modes without underscores', () => {
      const modes = [
        'M1_BULK',
        'M2_BULK_CDC',
        'M3_CDC',
        'M4_INCREMENTAL',
        'M5_STATE_SYNC',
        'M6_SCHEMA_ONLY',
        'M7_DATA_ONLY'
      ];

      for (const mode of modes) {
        const formatted = service.formatModeLabel(mode);
        expect(formatted).not.toContain('_');
      }

      expect(service.formatModeLabel('M2_BULK_CDC')).toBe('Bulk + CDC');
      expect(service.formatModeLabel('M1_BULK')).toBe('Bulk Snapshot');
      expect(service.formatModeLabel('M3_CDC')).toBe('Continuous CDC');
    });

    it('should format operational states without underscores', () => {
      const states = ['RUNNING', 'ACTIVE', 'PAUSED', 'ATTENTION', 'INITIALIZING', 'COMPLETED', 'FAILED'];
      for (const state of states) {
        const formatted = service.formatOperationalState(state);
        expect(formatted).not.toContain('_');
      }
      expect(service.formatOperationalState('ATTENTION')).toBe('Needs Attention');
    });
  });
});

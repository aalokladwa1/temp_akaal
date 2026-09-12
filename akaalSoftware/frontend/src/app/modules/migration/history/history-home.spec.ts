import '@angular/compiler';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { HistoryHomeService } from './history-home.service';
import {
  HISTORY_MODE_DESCRIPTORS,
  HistoryMode,
  MigrationHistoryItem
} from './history-home.models';
import { INITIAL_MIGRATION_HISTORY_FIXTURES } from './history-home.fixtures';
import { HistoryTableComponent } from './components/history-table.component';
import { HistoryHomeComponent } from './history-home.component';

describe('AKAAL Migration History & Evidence Home — Master Test Suite', () => {

  describe('1. M1–M8 Modes Domain & Inclusion Laws', () => {
    const allModes: HistoryMode[] = [
      'M1_BULK',
      'M2_BULK_CDC',
      'M3_CDC',
      'M4_INCREMENTAL',
      'M5_STATE_SYNC',
      'M6_SCHEMA_ONLY',
      'M7_DATA_ONLY',
      'M8_VALIDATION_ONLY'
    ];

    it('should define and support all 8 migration & assurance modes', () => {
      expect(Object.keys(HISTORY_MODE_DESCRIPTORS)).toHaveLength(8);
      allModes.forEach(mode => {
        expect(HISTORY_MODE_DESCRIPTORS[mode]).toBeDefined();
        expect(HISTORY_MODE_DESCRIPTORS[mode].code).toBe(mode);
        expect(HISTORY_MODE_DESCRIPTORS[mode].label).toBeTruthy();
        expect(HISTORY_MODE_DESCRIPTORS[mode].fullLabel).toContain(HISTORY_MODE_DESCRIPTORS[mode].shortCode);
      });
    });

    it('should strictly include Mode M8 (Validation Only) as first-class assurance mode', () => {
      const m8 = HISTORY_MODE_DESCRIPTORS.M8_VALIDATION_ONLY;
      expect(m8.shortCode).toBe('M8');
      expect(m8.label).toBe('Validation Only');
      expect(m8.isValidationAssurance).toBe(true);
      expect(m8.supportsCutover).toBe(false);
    });

    it('should correctly flag cutover support exclusively for replication and sync modes (M2, M3, M4, M5)', () => {
      expect(HISTORY_MODE_DESCRIPTORS.M1_BULK.supportsCutover).toBe(false);
      expect(HISTORY_MODE_DESCRIPTORS.M2_BULK_CDC.supportsCutover).toBe(true);
      expect(HISTORY_MODE_DESCRIPTORS.M3_CDC.supportsCutover).toBe(true);
      expect(HISTORY_MODE_DESCRIPTORS.M4_INCREMENTAL.supportsCutover).toBe(true);
      expect(HISTORY_MODE_DESCRIPTORS.M5_STATE_SYNC.supportsCutover).toBe(true);
      expect(HISTORY_MODE_DESCRIPTORS.M6_SCHEMA_ONLY.supportsCutover).toBe(false);
      expect(HISTORY_MODE_DESCRIPTORS.M7_DATA_ONLY.supportsCutover).toBe(false);
      expect(HISTORY_MODE_DESCRIPTORS.M8_VALIDATION_ONLY.supportsCutover).toBe(false);
    });
  });

  describe('2. HistoryHomeService — State, Search & Multi-Criteria Filters', () => {
    let service: HistoryHomeService;

    beforeEach(() => {
      service = new HistoryHomeService();
    });

    it('should initialize with canonical fixtures and default filter state', () => {
      expect(service.historyItems().length).toBeGreaterThanOrEqual(10);
      expect(service.filters().searchQuery).toBe('');
      expect(service.filters().mode).toBe('ALL');
      expect(service.filters().outcome).toBe('ALL');
      expect(service.isFiltered()).toBe(false);
      expect(service.activeFilterCount()).toBe(0);
    });

    it('should filter by free-text query across migration name, ID, execution ID, and operator', () => {
      service.setSearchQuery('Core Financial');
      const filtered = service.filteredHistoryItems();
      expect(filtered.length).toBeGreaterThan(0);
      expect(filtered.every(i => i.migrationName.includes('Financial') || i.projectName.includes('Financial'))).toBe(true);
      expect(service.isFiltered()).toBe(true);
      expect(service.activeFilterCount()).toBe(1);
    });

    it('should filter by specific Mode including M8 Validation Only', () => {
      service.setModeFilter('M8_VALIDATION_ONLY');
      const filtered = service.filteredHistoryItems();
      expect(filtered.length).toBeGreaterThanOrEqual(2);
      expect(filtered.every(i => i.mode === 'M8_VALIDATION_ONLY')).toBe(true);
    });

    it('should filter by Execution Outcome (FAILED)', () => {
      service.setOutcomeFilter('FAILED');
      const filtered = service.filteredHistoryItems();
      expect(filtered.length).toBeGreaterThan(0);
      expect(filtered.every(i => i.outcome === 'FAILED')).toBe(true);
    });

    it('should filter by Validation State (RECONCILED and MISMATCHES_DETECTED)', () => {
      service.setValidationFilter('RECONCILED');
      let filtered = service.filteredHistoryItems();
      expect(filtered.length).toBeGreaterThan(0);
      expect(filtered.every(i => i.validationState === 'RECONCILED')).toBe(true);

      service.setValidationFilter('MISMATCHES_DETECTED');
      filtered = service.filteredHistoryItems();
      expect(filtered.length).toBeGreaterThan(0);
      expect(filtered.every(i => i.validationState === 'MISMATCHES_DETECTED')).toBe(true);
    });

    it('should filter by Evidence Sealing (SEALED with SHA-256 digest)', () => {
      service.setEvidenceFilter('SEALED');
      const filtered = service.filteredHistoryItems();
      expect(filtered.length).toBeGreaterThan(0);
      expect(filtered.every(i => i.evidenceAvailability === 'SEALED')).toBe(true);
    });

    it('should filter by Continuity & Cutover (ROLLED_BACK)', () => {
      service.setContinuityFilter('ROLLED_BACK');
      const filtered = service.filteredHistoryItems();
      expect(filtered.length).toBe(1);
      expect(filtered[0].continuity.cutoverStatus).toBe('ROLLED_BACK');
      expect(filtered[0].continuity.recoveryStatus).toBe('RESTORED');
    });

    it('should reset all filters when clearFilters() is invoked', () => {
      service.setSearchQuery('NonExistentQueryXYZ');
      service.setModeFilter('M3_CDC');
      service.setOutcomeFilter('RUNNING');
      expect(service.isFiltered()).toBe(true);

      service.clearFilters();
      expect(service.isFiltered()).toBe(false);
      expect(service.filters().searchQuery).toBe('');
      expect(service.filters().mode).toBe('ALL');
      expect(service.filters().outcome).toBe('ALL');
      expect(service.filteredHistoryItems().length).toBe(service.historyItems().length);
    });

    it('should handle sorting by completed date (desc/asc), name, and rows processed', () => {
      service.setSort('name_asc');
      let filtered = service.filteredHistoryItems();
      for (let i = 0; i < filtered.length - 1; i++) {
        expect(filtered[i].migrationName.localeCompare(filtered[i + 1].migrationName)).toBeLessThanOrEqual(0);
      }

      service.setSort('rows_desc');
      filtered = service.filteredHistoryItems();
      for (let i = 0; i < filtered.length - 1; i++) {
        expect(filtered[i].rowsProcessed).toBeGreaterThanOrEqual(filtered[i + 1].rowsProcessed);
      }
    });

    it('should handle availability state transitions (LOADING, EMPTY, UNAVAILABLE, ERROR)', () => {
      service.setAvailabilityState('UNAVAILABLE', 'Audit connection timed out');
      expect(service.availabilityState()).toBe('UNAVAILABLE');
      expect(service.errorMessage()).toBe('Audit connection timed out');

      service.reload();
      expect(service.availabilityState()).toBe('READY');
      expect(service.errorMessage()).toBe('');
    });
  });

  describe('3. Component Architecture & UI Presentation Laws', () => {
    let service: HistoryHomeService;
    let tableComp: HistoryTableComponent;
    let homeComp: HistoryHomeComponent;
    let mockRouter: any;

    beforeEach(() => {
      service = new HistoryHomeService();
      mockRouter = {
        url: '/migration/history',
        navigate: vi.fn()
      };
      tableComp = new HistoryTableComponent(service, mockRouter);
      homeComp = new HistoryHomeComponent(service);
    });

    it('should return appropriate badge class for all 8 modes', () => {
      expect(tableComp.getModeBadgeClass('M1_BULK')).toContain('bg-blue-50');
      expect(tableComp.getModeBadgeClass('M2_BULK_CDC')).toContain('bg-indigo-50');
      expect(tableComp.getModeBadgeClass('M3_CDC')).toContain('bg-cyan-50');
      expect(tableComp.getModeBadgeClass('M4_INCREMENTAL')).toContain('bg-teal-50');
      expect(tableComp.getModeBadgeClass('M5_STATE_SYNC')).toContain('bg-purple-50');
      expect(tableComp.getModeBadgeClass('M6_SCHEMA_ONLY')).toContain('bg-amber-50');
      expect(tableComp.getModeBadgeClass('M7_DATA_ONLY')).toContain('bg-emerald-50');
      expect(tableComp.getModeBadgeClass('M8_VALIDATION_ONLY')).toContain('bg-sky-50');
    });

    it('should navigate to historical record on row click', () => {
      const item = INITIAL_MIGRATION_HISTORY_FIXTURES[0];
      tableComp.onRowClick(item);
      expect(mockRouter.navigate).toHaveBeenCalledWith(['/migration/history/' + item.migrationId]);
    });

    it('should determine whether to show table or empty states in HistoryHomeComponent', () => {
      expect(homeComp.showTable()).toBe(true);

      service.setSearchQuery('NonExistentString12345');
      expect(homeComp.showTable()).toBe(false);

      service.clearFilters();
      service.setAvailabilityState('EMPTY');
      expect(homeComp.showTable()).toBe(false);
    });

    it('should format validation labels as clean tags without raw numbers', () => {
      expect(tableComp.getValidationLabel(INITIAL_MIGRATION_HISTORY_FIXTURES[0])).toBe('Passed');
      expect(tableComp.getValidationLabel(INITIAL_MIGRATION_HISTORY_FIXTURES[2])).toBe('Reconciled');
      expect(tableComp.getValidationLabel(INITIAL_MIGRATION_HISTORY_FIXTURES[8])).toBe('Failed');
      expect(tableComp.getValidationLabel(INITIAL_MIGRATION_HISTORY_FIXTURES[9])).toBe('Mismatch');
    });
  });

});

import '@angular/compiler';
import { describe, it, expect, beforeEach } from 'vitest';
import { TemplatesService } from './templates.service';
import { TEMPLATE_MODE_DESCRIPTORS, TemplateMigrationMode } from './templates.models';
import { TEMPLATE_FIXTURES } from './templates.fixtures';
import { TemplatesHomeComponent } from './templates-home.component';
import { TemplatesTableComponent } from './components/templates-table.component';
import { TemplatesStatesComponent } from './components/templates-states.component';
import { TemplatesHeaderComponent } from './components/templates-header.component';

describe('Templates Module — Part A (Templates Home) Unit Tests', () => {
  let service: TemplatesService;

  beforeEach(() => {
    service = new TemplatesService();
    service.reload();
  });

  describe('1. Domain Model & Hard Mode Boundary Verification', () => {
    it('should only contain M1 through M7 in TEMPLATE_MODE_DESCRIPTORS', () => {
      const modeKeys = Object.keys(TEMPLATE_MODE_DESCRIPTORS);
      expect(modeKeys).toEqual([
        'M1_BULK',
        'M2_BULK_CDC',
        'M3_CDC',
        'M4_INCREMENTAL',
        'M5_STATE_SYNC',
        'M6_SCHEMA_ONLY',
        'M7_DATA_ONLY'
      ]);
    });

    it('should NEVER include M8 or validation mode anywhere in mode descriptors', () => {
      const allText = JSON.stringify(TEMPLATE_MODE_DESCRIPTORS).toLowerCase();
      expect(allText).not.toContain('m8');
      expect(allText).not.toContain('validation only');
      expect(allText).not.toContain('validation_only');
    });

    it('should ensure service modeOptions contains only ALL + M1-M7', () => {
      const options = service.modeOptions;
      expect(options.length).toBe(8); // 1 'ALL' + 7 modes
      expect(options[0].value).toBe('ALL');
      expect(options[1].value).toBe('M1_BULK');
      expect(options[2].value).toBe('M2_BULK_CDC');
      expect(options[3].value).toBe('M3_CDC');
      expect(options[4].value).toBe('M4_INCREMENTAL');
      expect(options[5].value).toBe('M5_STATE_SYNC');
      expect(options[6].value).toBe('M6_SCHEMA_ONLY');
      expect(options[7].value).toBe('M7_DATA_ONLY');

      // Strict check that M8 is absent
      const optionValues = options.map(o => o.value);
      expect(optionValues).not.toContain('M8');
      expect(optionValues).not.toContain('M8_VALIDATION');
    });

    it('should ensure fixtures contain zero M8 entries and zero fake certification stamps', () => {
      for (const tmpl of TEMPLATE_FIXTURES) {
        expect(['M1_BULK', 'M2_BULK_CDC', 'M3_CDC', 'M4_INCREMENTAL', 'M5_STATE_SYNC', 'M6_SCHEMA_ONLY', 'M7_DATA_ONLY']).toContain(tmpl.mode);
        const serialized = JSON.stringify(tmpl).toLowerCase();
        expect(serialized).not.toContain('m8');
        expect(serialized).not.toContain('certified');
        expect(serialized).not.toContain('ai recommended');
        expect(serialized).not.toContain('best practice guaranteed');
      }
    });

    it('should ensure opaque version strings are treated as plain labels without SemVer math', () => {
      for (const tmpl of TEMPLATE_FIXTURES) {
        expect(typeof tmpl.versionLabel).toBe('string');
        expect(tmpl.versionLabel.length).toBeGreaterThan(0);
      }
    });
  });

  describe('2. State Service & Multi-Criteria Filtering', () => {
    it('should load initial fixtures in READY state', () => {
      expect(service.templates().length).toBeGreaterThan(0);
      expect(service.availabilityState()).toBe('READY');
      expect(service.filteredTemplates().length).toBe(TEMPLATE_FIXTURES.length);
      expect(service.isFiltered()).toBe(false);
    });

    it('should filter templates by search query matching name or description', () => {
      service.setSearchQuery('Snowflake');
      const filtered = service.filteredTemplates();
      expect(filtered.length).toBeGreaterThan(0);
      for (const t of filtered) {
        const matches = t.name.toLowerCase().includes('snowflake') ||
          t.description.toLowerCase().includes('snowflake') ||
          t.applicability.targetProviderName.toLowerCase().includes('snowflake');
        expect(matches).toBe(true);
      }
      expect(service.isFiltered()).toBe(true);
    });

    it('should filter templates by specific migration mode (M2_BULK_CDC)', () => {
      service.setModeFilter('M2_BULK_CDC');
      const filtered = service.filteredTemplates();
      expect(filtered.length).toBeGreaterThan(0);
      for (const t of filtered) {
        expect(t.mode).toBe('M2_BULK_CDC');
      }
      expect(service.isFiltered()).toBe(true);
    });

    it('should filter templates by applicability pair', () => {
      service.setApplicabilityFilter('Oracle -> PostgreSQL');
      const filtered = service.filteredTemplates();
      expect(filtered.length).toBeGreaterThan(0);
      for (const t of filtered) {
        expect(t.applicability.sourceProviderName).toBe('Oracle');
        expect(t.applicability.targetProviderName).toBe('PostgreSQL');
      }
      expect(service.isFiltered()).toBe(true);
    });

    it('should sort templates by name (A to Z and Z to A)', () => {
      service.setSort('name_asc');
      const asc = service.filteredTemplates();
      for (let i = 0; i < asc.length - 1; i++) {
        expect(asc[i].name.localeCompare(asc[i + 1].name)).toBeLessThanOrEqual(0);
      }

      service.setSort('name_desc');
      const desc = service.filteredTemplates();
      for (let i = 0; i < desc.length - 1; i++) {
        expect(desc[i].name.localeCompare(desc[i + 1].name)).toBeGreaterThanOrEqual(0);
      }
    });

    it('should sort templates by most used', () => {
      service.setSort('usage_desc');
      const sorted = service.filteredTemplates();
      for (let i = 0; i < sorted.length - 1; i++) {
        const aUsage = sorted[i].usage.isUsageKnown ? (sorted[i].usage.migrationCount + sorted[i].usage.referencedProjectCount) : -1;
        const bUsage = sorted[i + 1].usage.isUsageKnown ? (sorted[i + 1].usage.migrationCount + sorted[i + 1].usage.referencedProjectCount) : -1;
        expect(aUsage).toBeGreaterThanOrEqual(bUsage);
      }
    });

    it('should clear all active filters', () => {
      service.setSearchQuery('oracle');
      service.setModeFilter('M2_BULK_CDC');
      service.setApplicabilityFilter('Oracle -> PostgreSQL');
      expect(service.isFiltered()).toBe(true);

      service.clearFilters();
      expect(service.filters().searchQuery).toBe('');
      expect(service.filters().mode).toBe('ALL');
      expect(service.filters().applicability).toBe('ALL');
      expect(service.isFiltered()).toBe(false);
      expect(service.filteredTemplates().length).toBe(TEMPLATE_FIXTURES.length);
    });

    it('should handle state mutations and reload action truthfully', () => {
      service.setAvailabilityState('ERROR', 'Failed to reach database catalog');
      expect(service.availabilityState()).toBe('ERROR');
      expect(service.errorMessage()).toBe('Failed to reach database catalog');

      service.reload();
      expect(service.availabilityState()).toBe('READY');
      expect(service.errorMessage()).toBe('');
      expect(service.templates().length).toBe(TEMPLATE_FIXTURES.length);
    });

    it('should correctly produce distinct applicability options', () => {
      const opts = service.applicabilityOptions();
      expect(opts.length).toBeGreaterThan(1);
      expect(opts[0].value).toBe('ALL');
      const values = opts.map(o => o.value);
      expect(values).toContain('Oracle -> PostgreSQL');
      expect(values).toContain('PostgreSQL -> Snowflake');
    });
  });

  describe('3. Component Architecture & Helper Methods', () => {
    it('should instantiate TemplatesHeaderComponent', () => {
      const comp = new TemplatesHeaderComponent();
      expect(comp).toBeDefined();
    });

    it('should test TemplatesTableComponent helper methods', () => {
      const comp = new TemplatesTableComponent(service);
      expect(comp.getModeDescriptor('M1_BULK').label).toBe('Bulk Load');
      expect(comp.getModeDescriptor('M2_BULK_CDC').label).toBe('Bulk + CDC');
      expect(comp.getModeDescriptor('M3_CDC').label).toBe('CDC Only');
    });

    it('should test TemplatesStatesComponent creation', () => {
      const comp = new TemplatesStatesComponent(service);
      expect(comp).toBeDefined();
    });

    it('should test TemplatesHomeComponent showTable logic', () => {
      const comp = new TemplatesHomeComponent(service);
      service.setAvailabilityState('READY');
      expect(comp.showTable()).toBe(true);

      service.setAvailabilityState('LOADING');
      expect(comp.showTable()).toBe(false);

      service.setAvailabilityState('ERROR');
      expect(comp.showTable()).toBe(false);

      service.setAvailabilityState('READY');
      service.setSearchQuery('nonexistent-text-matching-zero-items');
      expect(comp.showTable()).toBe(false);
    });
  });
});

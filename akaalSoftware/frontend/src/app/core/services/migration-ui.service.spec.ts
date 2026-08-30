import { describe, it, expect, beforeEach } from 'vitest';
import { MigrationUiService } from './migration-ui.service';
import { MigrationDevFixturesAdapter } from '../fixtures/migration-dev-fixtures.adapter';

describe('MigrationUiService', () => {
  let service: MigrationUiService;
  let fixtures: MigrationDevFixturesAdapter;

  beforeEach(() => {
    fixtures = new MigrationDevFixturesAdapter();
    service = new MigrationUiService(fixtures);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });

  it('should initialize with zero fake data by default', () => {
    expect(service.summaryCounters().total).toBe(0);
    expect(service.portfolioMigrations().length).toBe(0);
    expect(service.attentionItems().length).toBe(0);
    expect(service.projects().length).toBe(0);
    expect(service.connections().length).toBe(0);
  });

  it('should filter migrations correctly when items are added', () => {
    service.portfolioMigrations.set([
      {
        id: 'mig-1',
        name: 'User Database Migration',
        sourceEngine: 'PostgreSQL',
        sourceInstance: 'localhost:5432',
        targetEngine: 'PostgreSQL',
        targetInstance: 'target:5432',
        mode: 'M1_BULK',
        environment: 'Production',
        lifecycleState: 'ACTIVE',
        currentStage: 'Running',
        progressPercent: 50,
        throughputRowsSec: 1000,
        etaString: '10m',
        health: 'HEALTHY',
        attentionCount: 0,
        requiresApproval: false,
        planVersion: 'v1.0.0',
        planFingerprint: 'sha256:test',
        updatedAt: '2026-08-28T00:00:00Z'
      }
    ]);
    expect(service.summaryCounters().total).toBe(1);
    expect(service.summaryCounters().active).toBe(1);

    service.filterSearch.set('User');
    expect(service.filteredMigrations().length).toBe(1);

    service.filterSearch.set('NonExistent');
    expect(service.filteredMigrations().length).toBe(0);
  });

  describe('Step 6 Strict Mode Configuration Filtering', () => {
    it('M1_BULK must NOT include CDC domains (Domain M and N)', () => {
      service.updateWizardMode('M1_BULK');
      const domains = service.wizardConfigDomains();
      const domainIds = domains.map(d => d.id);
      expect(domainIds).not.toContain('M'); // CDC Log Capture
      expect(domainIds).not.toContain('N'); // CDC Buffer
      expect(domainIds).toContain('H'); // Bulk Transport
    });

    it('M2_BULK_CDC must include BOTH Bulk and CDC domains', () => {
      service.updateWizardMode('M2_BULK_CDC');
      const domains = service.wizardConfigDomains();
      const domainIds = domains.map(d => d.id);
      expect(domainIds).toContain('H'); // Bulk
      expect(domainIds).toContain('M'); // CDC Capture
      expect(domainIds).toContain('N'); // CDC Buffer
    });

    it('M3_CDC must include CDC domains but NOT Bulk Transport (Domain H)', () => {
      service.updateWizardMode('M3_CDC');
      const domains = service.wizardConfigDomains();
      const domainIds = domains.map(d => d.id);
      expect(domainIds).toContain('M');
      expect(domainIds).not.toContain('H');
    });

    it('M4_INCREMENTAL must include Watermark (Domain Q) but NOT CDC', () => {
      service.updateWizardMode('M4_INCREMENTAL');
      const domains = service.wizardConfigDomains();
      const domainIds = domains.map(d => d.id);
      expect(domainIds).toContain('Q'); // Watermark
      expect(domainIds).not.toContain('M'); // CDC
    });

    it('M5_STATE_SYNC must include Merkle (Domain R) but NOT CDC or Watermark', () => {
      service.updateWizardMode('M5_STATE_SYNC');
      const domains = service.wizardConfigDomains();
      const domainIds = domains.map(d => d.id);
      expect(domainIds).toContain('R'); // Merkle
      expect(domainIds).not.toContain('M');
      expect(domainIds).not.toContain('Q');
    });

    it('M6_SCHEMA_ONLY must include Schema (Domain U) but NOT Bulk Transport', () => {
      service.updateWizardMode('M6_SCHEMA_ONLY');
      const domains = service.wizardConfigDomains();
      const domainIds = domains.map(d => d.id);
      expect(domainIds).toContain('U'); // Schema DDL
      expect(domainIds).not.toContain('H'); // Bulk Transport
      expect(domainIds).not.toContain('M'); // CDC
    });

    it('M7_DATA_ONLY must include Bulk Transport (Domain H) but NOT CDC', () => {
      service.updateWizardMode('M7_DATA_ONLY');
      const domains = service.wizardConfigDomains();
      const domainIds = domains.map(d => d.id);
      expect(domainIds).toContain('H');
      expect(domainIds).not.toContain('M');
    });

    it('changing mode should mark plan as stale and set hasInvalidatedConfig flag', () => {
      service.updateWizardMode('M2_BULK_CDC');
      expect(service.wizardDraft().hasInvalidatedConfig).toBe(true);
      expect(service.wizardDraft().planStale).toBe(true);
    });
  });
});

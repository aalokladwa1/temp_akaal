import { describe, it, expect, beforeEach } from 'vitest';
import { ValidationHomeService } from './validation-home.service';

describe('ValidationHomeService', () => {
  let service: ValidationHomeService;

  beforeEach(() => {
    service = new ValidationHomeService();
  });

  it('should initialize with truthful empty baseline when disconnected', () => {
    expect(service.validations().length).toBe(0);
    expect(service.attentionItems().length).toBe(0);
    expect(service.upcomingValidations().length).toBe(0);
    expect(service.recentResults().length).toBe(0);
    expect(service.activities().length).toBe(0);
  });

  it('should compute KPI counters correctly when items exist', () => {
    service.validations.set([
      { id: 'v1', name: 'Banking Test', source_provider: 'Oracle', target_provider: 'PostgreSQL', strategy: 'Sync', state: 'RUNNING', outcome: 'Running' },
      { id: 'v2', name: 'Catalog Test', source_provider: 'MySQL', target_provider: 'Snowflake', strategy: 'Sync', state: 'COMPLETED', outcome: 'Validated' }
    ]);
    const counters = service.computedCounters();
    expect(counters.total).toBe(2);
    expect(counters.active).toBe(1);
    expect(counters.completed).toBe(1);
  });

  it('should filter active validations correctly', () => {
    service.validations.set([
      { id: 'v1', name: 'Banking Test', source_provider: 'Oracle', target_provider: 'PostgreSQL', strategy: 'Sync', state: 'RUNNING', outcome: 'Running' }
    ]);
    const active = service.activeValidations();
    expect(active.length).toBe(1);
    for (const v of active) {
      expect(['ACTIVE', 'RUNNING']).toContain(v.state);
    }
  });

  it('should filter by KPI selection', () => {
    service.validations.set([
      { id: 'v1', name: 'Banking Test', source_provider: 'Oracle', target_provider: 'PostgreSQL', strategy: 'Sync', state: 'RUNNING', outcome: 'Running' }
    ]);
    service.kpiFilter.set('ACTIVE');
    const filtered = service.filteredValidations();
    for (const v of filtered) {
      expect(['ACTIVE', 'RUNNING']).toContain(v.state);
    }
  });

  it('should filter by search query', () => {
    service.validations.set([
      { id: 'v1', name: 'Banking Test', source_provider: 'Oracle', target_provider: 'PostgreSQL', strategy: 'Sync', state: 'RUNNING', outcome: 'Running' }
    ]);
    service.searchQuery.set('Banking');
    const filtered = service.filteredValidations();
    expect(filtered.length).toBe(1);
    expect(filtered[0].name).toContain('Banking');
  });

  it('should filter by status', () => {
    service.validations.set([
      { id: 'v1', name: 'Catalog Test', source_provider: 'MySQL', target_provider: 'Snowflake', strategy: 'Sync', state: 'COMPLETED', outcome: 'Validated' }
    ]);
    service.statusFilter.set('VALIDATED');
    const filtered = service.filteredValidations();
    for (const v of filtered) {
      expect(v.outcome).toBe('Validated');
    }
  });

  it('should filter by strategy', () => {
    service.validations.set([
      { id: 'v1', name: 'Catalog Test', source_provider: 'MySQL', target_provider: 'Snowflake', strategy: 'Sync', state: 'COMPLETED', outcome: 'Validated' }
    ]);
    service.strategyFilter.set('Sync');
    const filtered = service.filteredValidations();
    for (const v of filtered) {
      expect(v.strategy).toBe('Sync');
    }
  });

  it('should format relative time correctly', () => {
    const res = service.formatRelativeTime('2026-09-06T12:00:00Z');
    expect(res.relative).toBeDefined();
    expect(res.exactTime).toContain('UTC');
  });
});

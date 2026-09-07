import { describe, it, expect, beforeEach } from 'vitest';
import { ValidationHomeService } from './validation-home.service';

describe('ValidationHomeService', () => {
  let service: ValidationHomeService;

  beforeEach(() => {
    service = new ValidationHomeService();
  });

  it('should initialize with baseline validation items', () => {
    expect(service.validations().length).toBeGreaterThan(0);
    expect(service.attentionItems().length).toBeGreaterThan(0);
    expect(service.upcomingValidations().length).toBeGreaterThan(0);
    expect(service.recentResults().length).toBeGreaterThan(0);
    expect(service.activities().length).toBeGreaterThan(0);
  });

  it('should compute KPI counters correctly', () => {
    const counters = service.computedCounters();
    expect(counters.total).toBe(service.validations().length);
    expect(counters.active).toBeGreaterThanOrEqual(1);
    expect(counters.attention).toBeGreaterThanOrEqual(1);
    expect(counters.scheduled).toBeGreaterThanOrEqual(1);
    expect(counters.completed).toBeGreaterThanOrEqual(1);
  });

  it('should filter active validations correctly', () => {
    const active = service.activeValidations();
    expect(active.length).toBeGreaterThanOrEqual(1);
    for (const v of active) {
      expect(['ACTIVE', 'RUNNING']).toContain(v.state);
    }
  });

  it('should filter by KPI selection', () => {
    service.kpiFilter.set('ACTIVE');
    const filtered = service.filteredValidations();
    for (const v of filtered) {
      expect(['ACTIVE', 'RUNNING']).toContain(v.state);
    }
  });

  it('should filter by search query', () => {
    service.searchQuery.set('Banking');
    const filtered = service.filteredValidations();
    expect(filtered.length).toBe(1);
    expect(filtered[0].name).toContain('Banking');
  });

  it('should filter by status', () => {
    service.statusFilter.set('VALIDATED');
    const filtered = service.filteredValidations();
    for (const v of filtered) {
      expect(v.outcome).toBe('Validated');
    }
  });

  it('should filter by strategy', () => {
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

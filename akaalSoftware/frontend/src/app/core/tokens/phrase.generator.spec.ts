import { describe, it, expect } from 'vitest';
import { generateGreetingContext } from './phrase.generator';
import { DashboardSummary } from '../models/dashboard.models';

describe('PhraseGenerator & Deterministic Greeting Logic', () => {
  it('should generate a truthful greeting with the operator name', () => {
    const ctx = generateGreetingContext('Aalok', null, 'connected');
    expect(ctx.greeting).toContain('Aalok');
    expect(ctx.formattedDate).toBeTruthy();
  });

  it('should fallback to Operator when name is null or empty', () => {
    const ctx = generateGreetingContext(null, null, 'connected');
    expect(ctx.greeting).toContain('Operator');
  });

  it('should select offline phrase when connectionState is disconnected', () => {
    const ctx = generateGreetingContext('Aalok', null, 'disconnected');
    expect(ctx.statePhrase).toBe('Engine connection offline. Reconnecting to local socket...');
  });

  it('should select connecting phrase when connectionState is connecting', () => {
    const ctx = generateGreetingContext('Aalok', null, 'connecting');
    expect(ctx.statePhrase).toBe('Connecting to DevKros motherboard IPC...');
  });

  it('should select critical incident phrase when critical incidents exist', () => {
    const summary: DashboardSummary = {
      runningCount: 2,
      scheduledCount: 0,
      attentionCount: 1,
      completedTodayCount: 0,
      activeMigrations: [],
      attentionItems: [],
      subsystems: [],
      pendingApprovals: [],
      capacityMetrics: [],
      incidents: [{ id: 'INC-1', severity: 'critical', subject: 'CDC Lag Spilled', context: 'Heap limit', age: '2m', isActionable: true }],
      fleet: null,
      security: null,
      recentEvents: []
    };
    const ctx = generateGreetingContext('Aalok', summary, 'connected');
    expect(ctx.statePhrase).toBe('A few things need a closer look today.');
  });

  it('should select approvals phrase when decisions are waiting', () => {
    const summary: DashboardSummary = {
      runningCount: 1,
      scheduledCount: 0,
      attentionCount: 1,
      completedTodayCount: 0,
      activeMigrations: [],
      attentionItems: [],
      subsystems: [],
      pendingApprovals: [{ id: '1', migrationName: 'Core', operation: 'Cutover', boundary: '', requester: 'DBA', requestedAt: 'now', quorum: '2/3', severity: 'critical' }],
      capacityMetrics: [],
      incidents: [],
      fleet: null,
      security: null,
      recentEvents: []
    };
    const ctx = generateGreetingContext('Aalok', summary, 'connected');
    expect(ctx.statePhrase).toBe('A few decisions are waiting on you.');
  });

  it('should select busy phrase when high activity (>3 running)', () => {
    const summary: DashboardSummary = {
      runningCount: 5,
      scheduledCount: 1,
      attentionCount: 0,
      completedTodayCount: 2,
      activeMigrations: [],
      attentionItems: [],
      subsystems: [],
      pendingApprovals: [],
      capacityMetrics: [],
      incidents: [],
      fleet: null,
      security: null,
      recentEvents: []
    };
    const ctx = generateGreetingContext('Aalok', summary, 'connected');
    expect(ctx.statePhrase).toBe('The fleet is busy. The important bits are below.');
  });
});

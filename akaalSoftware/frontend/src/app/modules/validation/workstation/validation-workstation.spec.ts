import '@angular/compiler';
import { describe, it, expect, beforeEach } from 'vitest';
import { ValidationWorkstationService } from './validation-workstation.service';
import {
  FIXTURE_NOT_CONNECTED,
  FIXTURE_RUNNING_DIFFS,
  FIXTURE_PASSED,
  FIXTURE_BLOCKED,
  FIXTURE_INTERRUPTED,
  WORKSTATION_FIXTURES
} from './validation-workstation-fixtures';

describe('Validation Workstation Presentation Store & Integrity Specs', () => {
  let service: ValidationWorkstationService;

  beforeEach(() => {
    service = new ValidationWorkstationService();
    service.resetToProductionDefault();
  });

  it('Mandate 5 & 6: Production default is strictly truthful NOT_CONNECTED and NOT_EVALUATED', () => {
    const state = service.state();
    expect(state.executionState).toBe('NOT_CONNECTED');
    expect(state.verdict).toBe('NOT_EVALUATED');
    expect(state.isProductionDefault).toBe(true);

    // Optional telemetry fields must be undefined/null in production default
    expect(state.elapsedFormatted).toBeUndefined();
    expect(state.throughputFormatted).toBeUndefined();
    expect(state.etaFormatted).toBeUndefined();
    expect(state.activeWorkers).toBeUndefined();
    expect(state.checkpointsCount).toBeUndefined();

    // Donut chart must be in NOT_CONNECTED mode with no synthetic numbers
    expect(state.donut.mode).toBe('NOT_CONNECTED');
    expect(state.donut.centerPercentage).toBeNull();
    expect(state.donut.centerLabel).toBe('Comparison State Unavailable');
    expect(state.donut.centerSubtext).toBe('Awaiting Canonical Engine Link');
  });

  it('Mandate 7 & 8: Execution State and Validation Verdict are completely decoupled', () => {
    // Test RUNNING with FAILED verdict (discrepancies found while running)
    service.setFixture('RUNNING_DIFFS');
    expect(service.state().executionState).toBe('RUNNING');
    expect(service.state().verdict).toBe('NOT_EVALUATED'); // verdict withheld or failed
    expect(service.state().isProductionDefault).toBe(false);

    // Test COMPLETED with PASSED verdict
    service.setFixture('PASSED');
    expect(service.state().executionState).toBe('COMPLETED');
    expect(service.state().verdict).toBe('PASSED');

    // Test INTERRUPTED with WITHHELD verdict
    service.setFixture('INTERRUPTED');
    expect(service.state().executionState).toBe('INTERRUPTED');
    expect(service.state().verdict).toBe('WITHHELD');
  });

  it('Mandate 10, 11, 12: Hero Donut semantic modes and telemetry suppression', () => {
    // Default state has no percentage
    expect(service.state().donut.centerPercentage).toBeNull();

    // In RUNNING_DIFFS, percentage is 42 and label describes progress
    service.setFixture('RUNNING_DIFFS');
    expect(service.state().donut.mode).toBe('INDEPENDENT_VALIDATION');
    expect(service.state().donut.centerPercentage).toBe(42);
    expect(service.state().donut.centerLabel).toBe('42% Evaluated');

    // In PASSED, percentage is 100 and label communicates canonical comparison mode (SYNC)
    service.setFixture('PASSED');
    expect(service.state().donut.centerPercentage).toBe(100);
    expect(service.state().donut.centerLabel).toBe('SYNC');
  });

  it('Mandate 14: Validation Proof tiers strictly enforce 4 tiers with Hostile XOR Guard', () => {
    const proofTiers = service.state().proofTiers;
    expect(proofTiers.length).toBe(4);

    expect(proofTiers[0].id).toBe('structural');
    expect(proofTiers[0].tierNumber).toBe(1);

    expect(proofTiers[1].id).toBe('cardinality');
    expect(proofTiers[1].tierNumber).toBe(2);

    expect(proofTiers[2].id).toBe('partition');
    expect(proofTiers[2].tierNumber).toBe(3);
    // Explicit Hostile XOR Defect Guard check
    expect(proofTiers[2].note).toContain('Hostile XOR Defect Guard');

    expect(proofTiers[3].id).toBe('attribute');
    expect(proofTiers[3].tierNumber).toBe(4);
  });

  it('Mandate 15: Scope coverage separates execution progress from validation findings', () => {
    service.setFixture('RUNNING_DIFFS');
    const coverage = service.state().coverage;
    expect(coverage.length).toBe(3);

    const recordsRow = coverage.find(c => c.dimension === 'Records');
    expect(recordsRow).toBeDefined();
    // In scope, evaluated, remaining are execution metrics
    expect(recordsRow?.inScope).toBe(18200000);
    expect(recordsRow?.evaluated).toBe(7600000);
    expect(recordsRow?.remaining).toBe(10600000);
    // Differences detected and inconclusive are validation findings
    expect(recordsRow?.differencesDetected).toBe(18);
    expect(recordsRow?.inconclusive).toBe(0);
  });

  it('Mandate 17 & 18: Technical drawer state management and safe action boundaries', () => {
    expect(service.drawerOpen()).toBe(false);
    service.toggleDrawer(true);
    expect(service.drawerOpen()).toBe(true);
    service.toggleDrawer(false);
    expect(service.drawerOpen()).toBe(false);

    // In production default, triggering an action gives non-blocking feedback
    service.resetToProductionDefault();
    service.triggerAction('RUN');
    expect(service.actionFeedback()).toContain('P7D Authority Boundary');
    expect(service.actionFeedback()).toContain('disabled');
  });

  it('Mandate 4: Workspace navigation tabs transition between overview, discrepancies, repair, evidence', () => {
    expect(service.activeTab()).toBe('overview');
    service.setActiveTab('discrepancies');
    expect(service.activeTab()).toBe('discrepancies');
    service.setActiveTab('repair');
    expect(service.activeTab()).toBe('repair');
    service.setActiveTab('evidence');
    expect(service.activeTab()).toBe('evidence');
    service.setActiveTab('overview');
    expect(service.activeTab()).toBe('overview');
  });

  it('Mandate 14, 15, 34: Completed + canonical SYNC displays SYNC in donut', () => {
    service.setFixture('COMPLETED_PASSED_SYNC');
    const state = service.state();
    expect(state.executionState).toBe('COMPLETED');
    expect(state.verdict).toBe('PASSED');
    expect(state.donut.canonicalComparisonMode).toBe('SYNC');
    expect(state.donut.centerLabel).toBe('SYNC');
  });

  it('Mandate 14, 15, 34: Completed + canonical ASYNC displays ASYNC in donut', () => {
    service.setFixture('COMPLETED_PASSED_ASYNC');
    const state = service.state();
    expect(state.executionState).toBe('COMPLETED');
    expect(state.verdict).toBe('PASSED');
    expect(state.donut.canonicalComparisonMode).toBe('ASYNC');
    expect(state.donut.centerLabel).toBe('ASYNC');
  });

  it('Mandate 34: Completed + unknown mode does not guess SYNC or ASYNC', () => {
    service.setFixture('COMPLETED_UNKNOWN_MODE');
    const state = service.state();
    expect(state.executionState).toBe('COMPLETED');
    expect(state.donut.canonicalComparisonMode).toBe('UNKNOWN');
    expect(state.donut.centerLabel).not.toBe('SYNC');
    expect(state.donut.centerLabel).not.toBe('ASYNC');
    expect(state.donut.centerSubtext).toBe('Relationship Mode Unspecified');
  });

  it('Mandate 34: FAILED + SYNC: chart displays SYNC while validation verdict is FAILED', () => {
    service.setFixture('COMPLETED_FAILED_SYNC');
    const state = service.state();
    expect(state.executionState).toBe('COMPLETED');
    expect(state.verdict).toBe('FAILED');
    // SYNC is canonical comparison mode, NOT verdict!
    expect(state.donut.canonicalComparisonMode).toBe('SYNC');
    expect(state.donut.centerLabel).toBe('SYNC');
  });

  it('Mandate 34: PASSED + ASYNC: chart displays ASYNC while validation verdict is PASSED', () => {
    service.setFixture('COMPLETED_PASSED_ASYNC');
    const state = service.state();
    expect(state.executionState).toBe('COMPLETED');
    expect(state.verdict).toBe('PASSED');
    // ASYNC is canonical comparison mode, NOT verdict!
    expect(state.donut.canonicalComparisonMode).toBe('ASYNC');
    expect(state.donut.centerLabel).toBe('ASYNC');
  });

  it('Mandate 16: Running state displays progress percentage and does not misuse SYNC/ASYNC as verdict', () => {
    service.setFixture('RUNNING_CLEAN');
    const state = service.state();
    expect(state.executionState).toBe('RUNNING');
    expect(state.verdict).toBe('NOT_EVALUATED');
    expect(state.donut.centerPercentage).toBe(68);
    expect(state.donut.centerLabel).toBe('68% Evaluated');
  });

  it('Mandate 25: Baseline invalid/stale promoted to attention item without phantom discrepancies', () => {
    service.setFixture('BASELINE_INVALID');
    const state = service.state();
    expect(state.remediation.baselineStatus).toBe('STALE');
    const baselineAttn = state.attentionItems.find(i => i.category === 'baseline');
    expect(baselineAttn).toBeDefined();
    expect(baselineAttn?.title).toContain('Comparison Baseline Requires Attention');
  });

  it('Mandate 28: Audit-only mission explicitly forbids target mutation', () => {
    service.setFixture('AUDIT_ONLY_REPAIR_FORBIDDEN');
    const state = service.state();
    expect(state.remediation.autoRepairPolicy).toContain('Mutation Prohibited');
  });

  it('Mandate 33: Large enterprise scale (2.45B records) renders cleanly', () => {
    service.setFixture('LARGE_ENTERPRISE');
    const state = service.state();
    const records = state.coverage.find(c => c.dimension === 'Records');
    expect(records?.inScope).toBe(2450000000);
    expect(records?.evaluated).toBe(2450000000);
  });
});

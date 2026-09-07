import { describe, it, expect, beforeEach } from 'vitest';
import { ValidationRepairService } from './validation-repair.service';
import { REPAIR_FIXTURES } from './validation-repair.fixtures';

describe('ValidationRepair Workspace & Invariants', () => {
  let service: ValidationRepairService;

  beforeEach(() => {
    service = new ValidationRepairService();
  });

  it('should default strictly to truthful UNAVAILABLE / NOT_CONNECTED standby state', () => {
    const state = service.state();
    expect(state.viewStatus).toBe('UNAVAILABLE');
    expect(service.summary().isExecutorAvailable).toBe(false);
    expect(service.summary().overallState).toContain('Standby');
    expect(service.summary().conciseExplanation).toContain('Controlled repair execution is not currently available');
  });

  it('should load single update proposal with separate Source, Current Target, and Proposed Target', () => {
    service.setFixture('SINGLE_UPDATE_PROPOSAL');
    const prop = service.proposal();
    expect(prop).toBeTruthy();
    expect(prop?.targetObject).toBe('enterprise_customers');
    expect(prop?.recordKey).toBe('CUST-009281');
    expect(prop?.proposedChanges.length).toBe(3);

    const statusChange = prop?.proposedChanges.find(c => c.attributeName === 'account_status');
    expect(statusChange?.sourceValue).toBe('ACTIVE');
    expect(statusChange?.currentTargetValue).toBe('SUSPENDED');
    expect(statusChange?.proposedTargetValue).toBe('ACTIVE');
  });

  it('should preserve sensitive data fail-closed masking in SENSITIVE_DATA_TRANSFORMATION fixture', () => {
    service.setFixture('SENSITIVE_DATA_TRANSFORMATION');
    const prop = service.proposal();
    const panChange = prop?.proposedChanges.find(c => c.attributeName === 'tokenized_pan');
    expect(panChange?.isSensitive).toBe(true);
    expect(panChange?.sourceValueKind).toBe('PROTECTED');
    expect(panChange?.sourceValue).toBe('••••••••••••4921');
    expect(service.impact()?.protectedDataInvolved).toBe(true);
  });

  it('should handle governance dual-approval and require quorum before authorization', () => {
    service.setFixture('SENSITIVE_DATA_TRANSFORMATION');
    const gov = service.governance();
    expect(gov?.state).toBe('PENDING');
    expect(gov?.quorumRequired).toBe(2);
    expect(gov?.quorumSatisfied).toBe(1);
    expect(gov?.isAuthorized).toBe(false);

    // Sign off as second approver
    service.approveProposal('Security Officer 2 / Compliance Lead');
    const updatedGov = service.governance();
    expect(updatedGov?.quorumSatisfied).toBe(2);
    expect(updatedGov?.isAuthorized).toBe(true);
    expect(updatedGov?.state).toBe('APPROVED');
  });

  it('should enforce governance rejection and block execution', () => {
    service.setFixture('APPROVAL_REJECTED');
    const gov = service.governance();
    expect(gov?.state).toBe('REJECTED');
    expect(gov?.isAuthorized).toBe(false);
    expect(gov?.rejectionReason).toContain('un-settled intraday transfer');
  });

  it('should preserve UNKNOWN commit outcome without blind retry', () => {
    service.setFixture('EXECUTION_INTERRUPTED_UNKNOWN_OUTCOME');
    const exec = service.execution();
    expect(exec?.state).toBe('OUTCOME_UNKNOWN');
    expect(exec?.providerCommitState).toBe('UNKNOWN');
    expect(exec?.unknownOutcomeCount).toBe(1);
    expect(exec?.unknownOutcomeWarning).toContain('CRITICAL: The target mutation was submitted');
    expect(service.revalidation()?.state).toBe('INTERRUPTED');
  });

  it('should prove that Repair Success != Validation Success (REVALIDATION_FAILED fixture)', () => {
    service.setFixture('REVALIDATION_FAILED');
    expect(service.execution()?.state).toBe('COMPLETED');
    expect(service.execution()?.appliedCount).toBe(1);
    expect(service.revalidation()?.state).toBe('FAILED');
    expect(service.revalidation()?.remainingDiscrepanciesCount).toBe(1);
    expect(service.revalidation()?.proofTiers.find(t => t.tier === 'Tier 4')?.status).toBe('FAILED');
  });

  it('should reflect 100% proof satisfaction when Revalidation passes (REVALIDATION_PASSED fixture)', () => {
    service.setFixture('REVALIDATION_PASSED');
    expect(service.execution()?.state).toBe('COMPLETED');
    expect(service.revalidation()?.state).toBe('PASSED');
    expect(service.revalidation()?.remainingDiscrepanciesCount).toBe(0);
    expect(service.revalidation()?.proofTiers.every(t => t.status === 'PASSED')).toBe(true);
  });

  it('should correctly render destructive deletion proposal in EXTRA_RECORD_DELETE fixture', () => {
    service.setFixture('EXTRA_RECORD_DELETE');
    const prop = service.proposal();
    expect(prop?.operationFamily).toBe('DELETE_EXTRA_TARGET');
    expect(service.impact()?.riskLevel).toBe('CONSEQUENTIAL_DESTRUCTIVE');
  });

  it('should indicate structural remediation is unsupported when schema mismatch exists', () => {
    service.setFixture('STRUCTURAL_UNSUPPORTED');
    expect(service.summary().eligibility).toBe('INELIGIBLE');
    expect(service.proposal()?.operationFamily).toBe('STRUCTURAL_UNSUPPORTED');
    expect(service.impact()?.estimatedWriteScope).toContain('DDL required');
  });

  it('should support large bulk aggregate batch with 1,420 operations', () => {
    service.setFixture('LARGE_BULK_REPAIR');
    expect(service.selectedScope().isBulkAggregate).toBe(true);
    expect(service.selectedScope().totalSelectedFindings).toBe(1420);
    expect(service.execution()?.totalOperations).toBe(1420);
  });

  it('should handle audit-only mission policy', () => {
    service.setFixture('AUDIT_ONLY_MISSION');
    expect(service.viewStatus()).toBe('AUDIT_ONLY');
    expect(service.summary().isReadonlyMission).toBe(true);
  });

  it('should handle zero discrepancies / no remediation required state', () => {
    service.setFixture('NO_REMEDIATION_REQUIRED');
    expect(service.viewStatus()).toBe('NO_REMEDIATION_REQUIRED');
    expect(service.selectedScope().totalSelectedFindings).toBe(0);
  });

  it('should toggle technical details drawer and confirm modal', () => {
    expect(service.isTechnicalDrawerOpen()).toBe(false);
    service.toggleTechnicalDrawer(true);
    expect(service.isTechnicalDrawerOpen()).toBe(true);
    service.toggleTechnicalDrawer(false);
    expect(service.isTechnicalDrawerOpen()).toBe(false);

    expect(service.isConfirmModalOpen()).toBe(false);
    service.openConfirmModal();
    expect(service.isConfirmModalOpen()).toBe(true);
    service.closeConfirmModal();
    expect(service.isConfirmModalOpen()).toBe(false);
  });

  it('should load all fixtures without throwing errors', () => {
    const fixtureKeys = Object.keys(REPAIR_FIXTURES);
    expect(fixtureKeys.length).toBeGreaterThanOrEqual(15);
    for (const key of fixtureKeys) {
      service.setFixture(key);
      expect(service.state().activeScenarioId).toBe(key);
    }
  });
});

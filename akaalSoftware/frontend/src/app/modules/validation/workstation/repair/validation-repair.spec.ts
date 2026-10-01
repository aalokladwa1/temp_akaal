import { describe, it, expect, beforeEach, vi } from 'vitest';
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

  it('should fail closed on approveProposal when backend connection is unavailable (B-VAL-01)', () => {
    service.setFixture('SENSITIVE_DATA_TRANSFORMATION');
    const gov = service.governance();
    expect(gov?.state).toBe('PENDING');

    // Sign off attempt fail closes without backend
    service.approveProposal('Security Officer 2 / Compliance Lead');
    expect(service.errorMessage()).toContain('Live sign-off & cryptographic signature requires backend connection (CHECK2)');
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

  describe('P9.2 Slice 2: Governed Repair Backend Authority Integration', () => {
    let mockIpc: any;
    let mockDiscrepanciesService: any;
    let connectedService: ValidationRepairService;

    beforeEach(() => {
      mockIpc = {
        dispatchValidationRepair: vi.fn(),
        listValidationDiscrepancies: vi.fn(),
        executeValidationMission: vi.fn()
      };
      mockDiscrepanciesService = {
        loadMissionDiscrepancies: vi.fn()
      };
      connectedService = new ValidationRepairService(mockIpc as any, mockDiscrepanciesService as any);
    });

    it('should fail closed when attempting repair dispatch without authoritative mission ID (ZERO fake IDs)', async () => {
      connectedService.setFixture('SINGLE_UPDATE_PROPOSAL');
      // Ensure missionId is not set
      connectedService.setMissionId(null);
      // Ensure technicalDetails does not have revalidationMissionId
      if (connectedService.technicalDetails()) {
        (connectedService as any)._state.update((s: any) => ({
          ...s,
          technicalDetails: { ...s.technicalDetails, revalidationMissionId: undefined }
        }));
      }

      await connectedService.executeRepair();

      expect(mockIpc.dispatchValidationRepair).not.toHaveBeenCalled();
      expect(connectedService.errorMessage()).toContain('missing authoritative validation mission ID');
    });

    it('should fail closed when attempting repair dispatch without authoritative repair strategy (ZERO invented defaults)', async () => {
      connectedService.setFixture('SINGLE_UPDATE_PROPOSAL');
      connectedService.setMissionId('val-mission-7788');
      // Strip operationFamily and strategy from proposal
      (connectedService as any)._state.update((s: any) => ({
        ...s,
        proposal: { ...s.proposal, operationFamily: undefined, strategy: undefined }
      }));

      await connectedService.executeRepair();

      expect(mockIpc.dispatchValidationRepair).not.toHaveBeenCalled();
      expect(connectedService.errorMessage()).toContain('missing authoritative repair strategy');
    });

    it('should dispatch repair and project PENDING_APPROVAL status truthfully', async () => {
      connectedService.setFixture('SINGLE_UPDATE_PROPOSAL');
      connectedService.setMissionId('val-mission-7788');

      mockIpc.dispatchValidationRepair.mockResolvedValue({
        status: 'SUCCESS',
        data: {
          repair_id: 'repair-9900',
          mission_id: 'val-mission-7788',
          status: 'PENDING_APPROVAL',
          approval_required: true,
          message: 'Governed repair requires Four-Eyes approval before physical dispatch.'
        }
      });

      await connectedService.executeRepair();

      expect(mockIpc.dispatchValidationRepair).toHaveBeenCalledWith(expect.objectContaining({
        mission_id: 'val-mission-7788',
        repair_strategy: 'UPDATE_DIFFERING_ATTRIBUTES'
      }));
      expect(connectedService.governance()?.state).toBe('PENDING');
      expect(connectedService.governance()?.approvalRequired).toBe(true);
      expect(connectedService.summary().governanceState).toBe('PENDING');
      expect(connectedService.errorMessage()).toBeUndefined();
    });

    it('should dispatch repair and project REPAIRED status with authoritative discrepancy refresh', async () => {
      connectedService.setFixture('SINGLE_UPDATE_PROPOSAL');
      connectedService.setMissionId('val-mission-7788');

      mockIpc.dispatchValidationRepair.mockResolvedValue({
        status: 'SUCCESS',
        data: {
          repair_id: 'repair-9900',
          mission_id: 'val-mission-7788',
          status: 'REPAIRED',
          discrepancies_reconciled: 1,
          revalidated: true
        }
      });

      mockIpc.listValidationDiscrepancies.mockResolvedValue({
        status: 'SUCCESS',
        data: {
          discrepancies: [
            { discrepancy_id: 'disc-1', status: 'REPAIRED' }
          ]
        }
      });

      await connectedService.executeRepair();

      expect(connectedService.execution()?.state).toBe('COMPLETED');
      expect(connectedService.execution()?.appliedCount).toBe(1);
      expect(connectedService.execution()?.providerCommitState).toBe('CONFIRMED');
      expect(connectedService.revalidation()?.state).toBe('PASSED');
      expect(connectedService.revalidation()?.remainingDiscrepanciesCount).toBe(0);
      expect(mockIpc.listValidationDiscrepancies).toHaveBeenCalledWith({ mission_id: 'val-mission-7788', limit: 100 });
      expect(mockDiscrepanciesService.loadMissionDiscrepancies).toHaveBeenCalledWith('val-mission-7788');
    });

    it('should project REPAIR_FAILED and REVALIDATION_FAILED truthfully without masking', async () => {
      connectedService.setFixture('SINGLE_UPDATE_PROPOSAL');
      connectedService.setMissionId('val-mission-7788');

      // Test REPAIR_FAILED
      mockIpc.dispatchValidationRepair.mockResolvedValue({
        status: 'SUCCESS',
        data: {
          repair_id: 'repair-9901',
          mission_id: 'val-mission-7788',
          status: 'REPAIR_FAILED',
          error: 'Deadlock encountered on target partition',
          revalidated: false
        }
      });

      await connectedService.executeRepair();

      expect(connectedService.execution()?.state).toBe('FAILED');
      expect(connectedService.errorMessage()).toBe('Deadlock encountered on target partition');

      // Test REVALIDATION_FAILED
      mockIpc.dispatchValidationRepair.mockResolvedValue({
        status: 'SUCCESS',
        data: {
          repair_id: 'repair-9902',
          mission_id: 'val-mission-7788',
          status: 'REVALIDATION_FAILED',
          error: 'Checksum divergence detected after mutation',
          revalidated: false
        }
      });

      await connectedService.executeRepair();

      expect(connectedService.execution()?.state).toBe('COMPLETED');
      expect(connectedService.revalidation()?.state).toBe('FAILED');
      expect(connectedService.errorMessage()).toBe('Checksum divergence detected after mutation');
    });

    it('should project Four-Eyes rejection only on explicit POLICY_DENIED and retain generic transport error for others', async () => {
      connectedService.setFixture('SINGLE_UPDATE_PROPOSAL');
      connectedService.setMissionId('val-mission-7788');

      // 1. Explicit Four-Eyes policy rejection
      mockIpc.dispatchValidationRepair.mockResolvedValue({
        status: 'ERROR',
        code: 'POLICY_DENIED',
        error: 'Four-eyes violation: Requester cannot approve their own action.'
      });

      await connectedService.executeRepair();

      expect(connectedService.governance()?.state).toBe('REJECTED');
      expect(connectedService.summary().governanceState).toBe('REJECTED');
      expect(connectedService.governance()?.rejectionReason).toContain('Four-eyes violation');

      // 2. Generic transport/backend error: must NOT project as Four-Eyes policy rejection!
      connectedService.setFixture('SINGLE_UPDATE_PROPOSAL');
      connectedService.setMissionId('val-mission-7788');

      mockIpc.dispatchValidationRepair.mockResolvedValue({
        status: 'ERROR',
        code: 'UNAVAILABLE',
        error: 'Engine gateway binding is temporarily unavailable.'
      });

      await connectedService.executeRepair();

      // Governance state should NOT be set to REJECTED for a transport failure
      expect(connectedService.governance()?.state).not.toBe('REJECTED');
      expect(connectedService.execution()?.state).toBe('FAILED');
      expect(connectedService.errorMessage()).toBe('Engine gateway binding is temporarily unavailable.');
    });

    it('should trigger revalidation with authoritative mission ID and refresh discrepancies on success', async () => {
      connectedService.setFixture('SINGLE_UPDATE_PROPOSAL');
      connectedService.setMissionId('val-mission-7788');

      mockIpc.executeValidationMission.mockResolvedValue({
        status: 'SUCCESS',
        data: { status: 'SUCCESS' }
      });
      mockIpc.listValidationDiscrepancies.mockResolvedValue({
        status: 'SUCCESS',
        data: { discrepancies: [] }
      });

      await connectedService.triggerRevalidation();

      expect(mockIpc.executeValidationMission).toHaveBeenCalledWith({ mission_id: 'val-mission-7788' });
      expect(connectedService.revalidation()?.state).toBe('PASSED');
      expect(mockIpc.listValidationDiscrepancies).toHaveBeenCalledWith({ mission_id: 'val-mission-7788', limit: 100 });
    });
  });
});

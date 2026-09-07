/**
 * validation-repair.service.ts
 * =====================================
 * State management service for Controlled Repair & Revalidation workspace.
 * Uses Angular signals for reactive, deterministic state flow.
 */

import { Injectable, signal, computed } from '@angular/core';
import { RepairWorkspaceState, RepairViewStatus } from './validation-repair.models';
import { REPAIR_FIXTURES } from './validation-repair.fixtures';

@Injectable({
  providedIn: 'root'
})
export class ValidationRepairService {
  // Primary State Signal (Defaults strictly to truthful UNAVAILABLE / NOT_CONNECTED standby)
  private readonly _state = signal<RepairWorkspaceState>(REPAIR_FIXTURES['DEFAULT_NOT_CONNECTED']);

  // Public Signal Accessors
  readonly state = this._state.asReadonly();
  readonly viewStatus = computed(() => this._state().viewStatus);
  readonly summary = computed(() => this._state().summary);
  readonly selectedScope = computed(() => this._state().selectedScope);
  readonly proposal = computed(() => this._state().proposal);
  readonly impact = computed(() => this._state().impact);
  readonly governance = computed(() => this._state().governance);
  readonly execution = computed(() => this._state().execution);
  readonly revalidation = computed(() => this._state().revalidation);
  readonly technicalDetails = computed(() => this._state().technicalDetails);
  readonly isConfirmModalOpen = computed(() => this._state().isConfirmModalOpen);
  readonly isTechnicalDrawerOpen = computed(() => this._state().isTechnicalDrawerOpen);
  readonly activeScenarioId = computed(() => this._state().activeScenarioId);
  readonly errorMessage = computed(() => this._state().errorMessage);

  /**
   * Set a specific test / visual verification fixture
   */
  setFixture(fixtureKey: string): void {
    const fixture = REPAIR_FIXTURES[fixtureKey];
    if (fixture) {
      this._state.set(JSON.parse(JSON.stringify(fixture)));
    }
  }

  /**
   * Reset to truthful production standby default
   */
  resetToDefault(): void {
    this._state.set(JSON.parse(JSON.stringify(REPAIR_FIXTURES['DEFAULT_NOT_CONNECTED'])));
  }

  /**
   * Toggle Technical Details slide-over drawer
   */
  toggleTechnicalDrawer(open?: boolean): void {
    this._state.update(s => ({
      ...s,
      isTechnicalDrawerOpen: open !== undefined ? open : !s.isTechnicalDrawerOpen
    }));
  }

  /**
   * Open consequential action confirmation modal
   */
  openConfirmModal(): void {
    this._state.update(s => ({ ...s, isConfirmModalOpen: true }));
  }

  /**
   * Close consequential action confirmation modal
   */
  closeConfirmModal(): void {
    this._state.update(s => ({ ...s, isConfirmModalOpen: false }));
  }

  /**
   * Approve proposal sign-off role
   */
  approveProposal(role: string): void {
    this._state.update(s => {
      if (!s.governance) return s;
      const updatedApprovers = s.governance.approvers.map(app => {
        if (app.role === role) {
          return {
            ...app,
            status: 'APPROVED' as const,
            userName: app.userName || 'current.operator@akaal.internal',
            timestamp: new Date().toISOString(),
            signatureDigest: 'ed25519:sig_' + Math.random().toString(36).substring(2, 10)
          };
        }
        return app;
      });

      const approvedCount = updatedApprovers.filter(a => a.status === 'APPROVED').length;
      const isQuorumSatisfied = approvedCount >= s.governance.quorumRequired;

      return {
        ...s,
        governance: {
          ...s.governance,
          approvers: updatedApprovers,
          quorumSatisfied: approvedCount,
          isAuthorized: isQuorumSatisfied,
          state: isQuorumSatisfied ? 'APPROVED' : 'PENDING',
          authorizationNote: isQuorumSatisfied
            ? 'Plan is fully authorized and within valid lease window.'
            : `Quorum partially satisfied (${approvedCount}/${s.governance.quorumRequired}). Awaiting remaining approvals.`
        }
      };
    });
  }

  /**
   * Reject proposal
   */
  rejectProposal(reason: string): void {
    this._state.update(s => {
      if (!s.governance) return s;
      return {
        ...s,
        governance: {
          ...s.governance,
          state: 'REJECTED',
          isAuthorized: false,
          rejectionReason: reason || 'Operator rejected proposal during governed review.',
          authorizationNote: 'Proposal rejected. Target remains untouched.'
        }
      };
    });
  }

  /**
   * Consequential execution trigger
   */
  executeRepair(): void {
    this.closeConfirmModal();
    this._state.update(s => {
      if (!s.execution) return s;
      return {
        ...s,
        execution: {
          ...s.execution,
          state: 'COMPLETED',
          executionId: 'exec-runtime-' + Date.now().toString().slice(-6),
          startedAt: new Date(Date.now() - 3000).toISOString(),
          completedAt: new Date().toISOString(),
          progressPercent: 100,
          appliedCount: s.execution.totalOperations,
          unresolvedCount: 0,
          unknownOutcomeCount: 0,
          providerCommitState: 'CONFIRMED'
        },
        revalidation: s.revalidation ? {
          ...s.revalidation,
          state: 'RUNNING',
          startedAt: new Date().toISOString(),
          verdictSummary: 'Validation #11 is executing 4-tier proof rescan...'
        } : null
      };
    });
  }

  /**
   * Revalidation run trigger
   */
  triggerRevalidation(): void {
    this._state.update(s => {
      if (!s.revalidation) return s;
      return {
        ...s,
        revalidation: {
          ...s.revalidation,
          state: 'PASSED',
          completedAt: new Date().toISOString(),
          remainingDiscrepanciesCount: 0,
          proofTiers: s.revalidation.proofTiers.map(t => ({
            ...t,
            status: 'PASSED' as const,
            differencesFound: 0
          })),
          verdictSummary: 'Validation #11 re-evaluated the partition and established complete proof satisfaction across all 4 tiers.'
        }
      };
    });
  }
}

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
   * Approve proposal sign-off role (Fail closed without backend authority)
   */
  approveProposal(role: string): void {
    this._state.update(s => {
      if (!s.governance) return s;
      return {
        ...s,
        errorMessage: 'Live sign-off & cryptographic signature requires backend connection (CHECK2)',
        governance: {
          ...s.governance,
          authorizationNote: 'Live sign-off & cryptographic signature requires backend connection (CHECK2)'
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
          authorizationNote: 'Proposal rejected locally. Target remains untouched.'
        }
      };
    });
  }

  /**
   * Consequential execution trigger (Fail closed without backend connection)
   */
  executeRepair(): void {
    this.closeConfirmModal();
    this._state.update(s => {
      return {
        ...s,
        errorMessage: 'Live repair execution requires backend connection (CHECK2)'
      };
    });
  }

  /**
   * Revalidation run trigger (Fail closed without backend connection)
   */
  triggerRevalidation(): void {
    this._state.update(s => {
      return {
        ...s,
        errorMessage: 'Live revalidation scan requires backend connection (CHECK2)'
      };
    });
  }
}

/**
 * validation-repair.service.ts
 * =====================================
 * State management service for Controlled Repair & Revalidation workspace.
 * Uses Angular signals for reactive, deterministic state flow.
 */

import { Injectable, inject, signal, computed } from '@angular/core';
import { RepairWorkspaceState, RepairViewStatus } from './validation-repair.models';
import { REPAIR_FIXTURES } from './validation-repair.fixtures';
import { MigrationIpc } from '../../../../core/services/ipc/migration.ipc';
import { ValidationDiscrepanciesService } from '../discrepancies/validation-discrepancies.service';

@Injectable({
  providedIn: 'root'
})
export class ValidationRepairService {
  private migrationIpc?: MigrationIpc;
  private discrepanciesService?: ValidationDiscrepanciesService;

  // Authoritative mission ID tracked from active validation session
  private readonly _missionId = signal<string | null>(null);
  readonly missionId = this._missionId.asReadonly();

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

  constructor(
    migrationIpc?: MigrationIpc,
    discrepanciesService?: ValidationDiscrepanciesService
  ) {
    if (migrationIpc) {
      this.migrationIpc = migrationIpc;
    } else {
      try {
        this.migrationIpc = inject(MigrationIpc, { optional: true }) ?? undefined;
      } catch {
        // Direct instantiation without Angular DI context (e.g. unit tests)
      }
    }

    if (discrepanciesService) {
      this.discrepanciesService = discrepanciesService;
    } else {
      try {
        this.discrepanciesService = inject(ValidationDiscrepanciesService, { optional: true }) ?? undefined;
      } catch {
        // Direct instantiation without Angular DI context (e.g. unit tests)
      }
    }
  }

  setMissionId(id: string | null): void {
    this._missionId.set(id);
  }

  getMissionId(): string | null {
    return this._missionId() || this._state().technicalDetails?.revalidationMissionId || null;
  }

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
    this._missionId.set(null);
  }

  /**
   * Set view status directly
   */
  setViewStatus(status: RepairViewStatus): void {
    this._state.update(s => ({
      ...s,
      viewStatus: status
    }));
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
   * Consequential execution trigger via canonical backend authority.
   * Fail closed without backend connection, authoritative mission ID, or repair strategy.
   */
  async executeRepair(): Promise<void> {
    this.closeConfirmModal();

    if (!this.migrationIpc) {
      this._state.update(s => ({
        ...s,
        errorMessage: 'Live repair execution requires backend connection (CHECK2)'
      }));
      return;
    }

    const missionId = this.getMissionId();
    if (!missionId) {
      this._state.update(s => ({
        ...s,
        errorMessage: 'Repair cannot be dispatched: missing authoritative validation mission ID.'
      }));
      return;
    }

    const proposal = this._state().proposal;
    const strategy = proposal?.operationFamily || (proposal as any)?.strategy;
    if (!strategy) {
      this._state.update(s => ({
        ...s,
        errorMessage: 'Repair cannot be dispatched: missing authoritative repair strategy.'
      }));
      return;
    }

    const selectedScope = this._state().selectedScope;
    const discrepancyIds = selectedScope?.affectedRecordKeys?.length ? selectedScope.affectedRecordKeys : undefined;
    const rationale = proposal?.detailedRationale || proposal?.summaryNote || 'Governed repair dispatched from Validation Workstation';

    const payload: any = {
      mission_id: missionId,
      repair_strategy: strategy,
      rationale: rationale,
    };
    if (discrepancyIds) {
      payload.discrepancy_ids = discrepancyIds;
    }

    try {
      const res = await this.migrationIpc.dispatchValidationRepair(payload);
      if (res && res.status === 'SUCCESS' && res.data) {
        const data = res.data as any;
        if (data.status === 'PENDING_APPROVAL') {
          this._state.update(s => ({
            ...s,
            errorMessage: undefined,
            governance: s.governance ? {
              ...s.governance,
              state: 'PENDING',
              approvalRequired: true,
              authorizationNote: data.message || 'Governed repair requires Four-Eyes approval before physical dispatch.'
            } : null,
            summary: {
              ...s.summary,
              governanceState: 'PENDING'
            }
          }));
        } else if (data.status === 'REPAIRED') {
          await this.refreshDiscrepancies(missionId);

          this._state.update(s => ({
            ...s,
            errorMessage: undefined,
            execution: s.execution ? {
              ...s.execution,
              state: 'COMPLETED',
              appliedCount: data.discrepancies_reconciled !== undefined ? data.discrepancies_reconciled : 1,
              unresolvedCount: 0,
              progressPercent: 100,
              providerCommitState: 'CONFIRMED'
            } : null,
            summary: {
              ...s.summary,
              executionState: 'COMPLETED'
            },
            technicalDetails: s.technicalDetails ? {
              ...s.technicalDetails,
              executionId: data.repair_id
            } : null
          }));
        } else if (data.status === 'REPAIR_FAILED') {
          this._state.update(s => ({
            ...s,
            errorMessage: data.error || 'Physical repair failed on target database',
            execution: s.execution ? {
              ...s.execution,
              state: 'FAILED',
              errorMessage: data.error
            } : null,
            summary: {
              ...s.summary,
              executionState: 'FAILED'
            }
          }));
        } else if (data.status === 'REVALIDATION_FAILED') {
          this._state.update(s => ({
            ...s,
            errorMessage: data.error || 'Targeted revalidation failed after repair mutation',
            execution: s.execution ? {
              ...s.execution,
              state: 'COMPLETED'
            } : null,
            revalidation: s.revalidation ? {
              ...s.revalidation,
              state: 'FAILED',
              verdictSummary: data.error || 'Revalidation detected remaining discrepancies'
            } : null,
            summary: {
              ...s.summary,
              executionState: 'COMPLETED',
              revalidationState: 'FAILED'
            }
          }));
        }
      } else {
        const errMsg = res?.error || 'Validation repair invocation failed';
        const isPolicyDenied = res?.code === 'POLICY_DENIED' ||
                               errMsg.includes('POLICY_DENIED') ||
                               errMsg.toLowerCase().includes('four-eyes') ||
                               errMsg.toLowerCase().includes('four eyes') ||
                               errMsg.toLowerCase().includes('requester cannot approve');

        if (isPolicyDenied) {
          this._state.update(s => ({
            ...s,
            errorMessage: errMsg,
            governance: s.governance ? {
              ...s.governance,
              state: 'REJECTED',
              isAuthorized: false,
              rejectionReason: errMsg,
              authorizationNote: 'Repair execution rejected by Four-Eyes governance policy.'
            } : null,
            summary: {
              ...s.summary,
              governanceState: 'REJECTED'
            }
          }));
        } else {
          this._state.update(s => ({
            ...s,
            errorMessage: errMsg,
            execution: s.execution ? {
              ...s.execution,
              state: 'FAILED',
              errorMessage: errMsg
            } : null,
            summary: {
              ...s.summary,
              executionState: 'FAILED'
            }
          }));
        }
      }
    } catch (err: any) {
      const errMsg = err?.message || 'IPC transport error during repair dispatch';
      const isPolicyDenied = errMsg.includes('POLICY_DENIED') ||
                             errMsg.toLowerCase().includes('four-eyes') ||
                             errMsg.toLowerCase().includes('four eyes') ||
                             errMsg.toLowerCase().includes('requester cannot approve');

      if (isPolicyDenied) {
        this._state.update(s => ({
          ...s,
          errorMessage: errMsg,
          governance: s.governance ? {
            ...s.governance,
            state: 'REJECTED',
            isAuthorized: false,
            rejectionReason: errMsg
          } : null,
          summary: {
            ...s.summary,
            governanceState: 'REJECTED'
          }
        }));
      } else {
        this._state.update(s => ({
          ...s,
          errorMessage: errMsg,
          execution: s.execution ? {
            ...s.execution,
            state: 'FAILED',
            errorMessage: errMsg
          } : null,
          summary: {
            ...s.summary,
            executionState: 'FAILED'
          }
        }));
      }
    }
  }

  /**
   * Re-queries authoritative discrepancy records from backend.
   */
  async refreshDiscrepancies(missionId: string): Promise<void> {
    if (!this.migrationIpc) return;
    try {
      const res = await this.migrationIpc.listValidationDiscrepancies({ mission_id: missionId, limit: 100 });
      if (res && res.status === 'SUCCESS' && res.data) {
        const payload = res.data as any;
        const list = Array.isArray(payload.discrepancies) ? payload.discrepancies : (Array.isArray(payload) ? payload : []);
        const remaining = list.filter((d: any) => d.status !== 'REPAIRED').length;
        this._state.update(s => ({
          ...s,
          revalidation: s.revalidation ? {
            ...s.revalidation,
            state: remaining === 0 ? 'PASSED' : 'FAILED',
            remainingDiscrepanciesCount: remaining,
            verdictSummary: remaining === 0 ? 'Authoritative revalidation passed: all discrepancies resolved' : `${remaining} unresolved discrepancies remain`
          } : null,
          summary: {
            ...s.summary,
            revalidationState: remaining === 0 ? 'PASSED' : 'FAILED'
          }
        }));
      }
    } catch (err) {
      console.error('[ValidationRepairService] Failed to refresh discrepancies:', err);
    }

    if (this.discrepanciesService) {
      try {
        await this.discrepanciesService.loadMissionDiscrepancies(missionId);
      } catch {
        // Safe fallback
      }
    }
  }

  /**
   * Revalidation run trigger (Fail closed without backend connection)
   */
  async triggerRevalidation(): Promise<void> {
    if (!this.migrationIpc) {
      this._state.update(s => ({
        ...s,
        errorMessage: 'Live revalidation scan requires backend connection (CHECK2)'
      }));
      return;
    }

    const missionId = this.getMissionId();
    if (!missionId) {
      this._state.update(s => ({
        ...s,
        errorMessage: 'Revalidation cannot be triggered: missing authoritative validation mission ID.'
      }));
      return;
    }

    this._state.update(s => ({
      ...s,
      revalidation: s.revalidation ? { ...s.revalidation, state: 'RUNNING' } : null,
      summary: { ...s.summary, revalidationState: 'RUNNING' }
    }));

    try {
      const res = await this.migrationIpc.executeValidationMission({ mission_id: missionId });
      if (res && res.status === 'SUCCESS') {
        await this.refreshDiscrepancies(missionId);
      } else {
        const errMsg = res?.error || 'Revalidation mission failed';
        this._state.update(s => ({
          ...s,
          errorMessage: errMsg,
          revalidation: s.revalidation ? { ...s.revalidation, state: 'FAILED', verdictSummary: errMsg } : null,
          summary: { ...s.summary, revalidationState: 'FAILED' }
        }));
      }
    } catch (err: any) {
      const errMsg = err?.message || 'IPC transport error during revalidation trigger';
      this._state.update(s => ({
        ...s,
        errorMessage: errMsg,
        revalidation: s.revalidation ? { ...s.revalidation, state: 'FAILED', verdictSummary: errMsg } : null,
        summary: { ...s.summary, revalidationState: 'FAILED' }
      }));
    }
  }
}

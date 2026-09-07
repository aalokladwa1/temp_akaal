import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ValidationRepairService } from '../validation-repair.service';
import { CustomSelectComponent } from '../../../../../shared/components/custom-select.component';
import { LucideIconComponent } from '../../../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-repair-summary-band',
  standalone: true,
  imports: [CommonModule, FormsModule, CustomSelectComponent, LucideIconComponent],
  template: `
    <section class="bg-white border border-slate-200/80 rounded-xl p-6 lg:p-7 shadow-2xs flex flex-col gap-6">
      
      <!-- Top Row: Identity, State, and Action Triggers -->
      <div class="flex flex-col lg:flex-row items-start lg:items-center justify-between gap-4">
        
        <!-- Identity & Status Header -->
        <div class="flex items-start gap-4">
          <div [ngClass]="getHeaderIconBgClass()" class="w-12 h-12 rounded-xl flex items-center justify-center shrink-0 border">
            <app-lucide-icon [name]="getHeaderIconName()" [size]="24"></app-lucide-icon>
          </div>

          <div class="flex flex-col gap-1">
            <div class="flex items-center gap-3 flex-wrap">
              <span class="text-xs font-bold text-slate-500 uppercase tracking-wider font-heading">
                Workspace 3 / Governed Remediation
              </span>
              <span [ngClass]="getOverallStateBadgeClass()" class="px-2.5 py-0.5 rounded-md text-[11px] font-semibold border flex items-center gap-1.5">
                <app-lucide-icon [name]="getOverallStateIconName()" [size]="12"></app-lucide-icon>
                <span>{{ store.summary().overallState }}</span>
              </span>
            </div>

            <h1 class="text-xl font-bold text-slate-900 font-heading tracking-tight">
              Controlled Repair &amp; Scoped Revalidation
            </h1>
            <p class="text-xs text-slate-600 max-w-3xl leading-relaxed">
              {{ store.summary().conciseExplanation }}
            </p>
          </div>
        </div>

        <!-- Right Side: Secondary Actions & Fixture Selector -->
        <div class="flex items-center gap-2.5 self-stretch lg:self-auto justify-end flex-wrap">
          
          <!-- Scenario / Fixture Selector for Visual Verification -->
          <div class="w-64">
            <app-custom-select
              [options]="scenarioOptions"
              [ngModel]="store.activeScenarioId()"
              (ngModelChange)="store.setFixture($event)"
              placeholder="Select Test Scenario"
              size="sm">
            </app-custom-select>
          </div>

          <!-- Technical Details Trigger -->
          <button
            type="button"
            (click)="store.toggleTechnicalDrawer(true)"
            class="h-8.5 px-3.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 text-xs font-semibold flex items-center gap-1.5 cursor-pointer transition-colors shadow-2xs">
            <app-lucide-icon name="code-2" [size]="13"></app-lucide-icon>
            <span>Technical Architecture</span>
          </button>

          <!-- Reset Default Button -->
          <button
            type="button"
            (click)="store.resetToDefault()"
            title="Reset to production standby default"
            class="h-8.5 px-2.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-slate-500 hover:text-slate-800 text-xs font-semibold flex items-center cursor-pointer transition-colors shadow-2xs">
            <app-lucide-icon name="rotate-ccw" [size]="13"></app-lucide-icon>
          </button>

        </div>

      </div>

      <!-- Bottom Dimension Metrics Row -->
      <div class="pt-5 border-t border-slate-100 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-4">
        
        <!-- Dimension 1: Eligibility -->
        <div class="flex flex-col gap-2 p-4 sm:p-4.5 rounded-xl bg-slate-50/80 border border-slate-200/90 shadow-2xs">
          <span class="text-[10.5px] font-bold uppercase tracking-wider text-slate-500 font-heading">Repair Eligibility</span>
          <div class="flex items-center gap-2 text-xs font-semibold text-slate-900 leading-snug">
            <app-lucide-icon [name]="getEligibilityIcon()" [size]="15" class="text-slate-600 shrink-0"></app-lucide-icon>
            <span class="break-words">{{ formatEligibility(store.summary().eligibility) }}</span>
          </div>
        </div>

        <!-- Dimension 2: Proposal -->
        <div class="flex flex-col gap-2 p-4 sm:p-4.5 rounded-xl bg-slate-50/80 border border-slate-200/90 shadow-2xs">
          <span class="text-[10.5px] font-bold uppercase tracking-wider text-slate-500 font-heading">Proposal State</span>
          <div class="flex items-center gap-2 text-xs font-semibold text-slate-900 leading-snug">
            <app-lucide-icon [name]="getProposalIcon()" [size]="15" class="text-slate-600 shrink-0"></app-lucide-icon>
            <span class="break-words">{{ formatProposal(store.summary().proposalState) }}</span>
          </div>
        </div>

        <!-- Dimension 3: Governance -->
        <div class="flex flex-col gap-2 p-4 sm:p-4.5 rounded-xl bg-slate-50/80 border border-slate-200/90 shadow-2xs">
          <span class="text-[10.5px] font-bold uppercase tracking-wider text-slate-500 font-heading">Governance &amp; Policy</span>
          <div class="flex items-center gap-2 text-xs font-semibold text-slate-900 leading-snug">
            <app-lucide-icon [name]="getGovernanceIcon()" [size]="15" class="text-slate-600 shrink-0"></app-lucide-icon>
            <span class="break-words">{{ formatGovernance(store.summary().governanceState) }}</span>
          </div>
        </div>

        <!-- Dimension 4: Execution -->
        <div class="flex flex-col gap-2 p-4 sm:p-4.5 rounded-xl bg-slate-50/80 border border-slate-200/90 shadow-2xs">
          <span class="text-[10.5px] font-bold uppercase tracking-wider text-slate-500 font-heading">Controlled Execution</span>
          <div class="flex items-center gap-2 text-xs font-semibold text-slate-900 leading-snug">
            <app-lucide-icon [name]="getExecutionIcon()" [size]="15" class="text-slate-600 shrink-0"></app-lucide-icon>
            <span class="break-words">{{ formatExecution(store.summary().executionState) }}</span>
          </div>
        </div>

        <!-- Dimension 5: Revalidation -->
        <div class="flex flex-col gap-2 p-4 sm:p-4.5 rounded-xl bg-slate-50/80 border border-slate-200/90 shadow-2xs col-span-1 sm:col-span-2 lg:col-span-3 xl:col-span-1">
          <span class="text-[10.5px] font-bold uppercase tracking-wider text-slate-500 font-heading">Validation #11 Result</span>
          <div class="flex items-center gap-2 text-xs font-semibold text-slate-900 leading-snug">
            <app-lucide-icon [name]="getRevalidationIcon()" [size]="15" class="text-slate-600 shrink-0"></app-lucide-icon>
            <span class="break-words">{{ formatRevalidation(store.summary().revalidationState) }}</span>
          </div>
        </div>

      </div>

    </section>
  `
})
export class RepairSummaryBandComponent {
  readonly store = inject(ValidationRepairService);

  readonly scenarioOptions = [
    { value: 'DEFAULT_NOT_CONNECTED', label: '1. Production Standby (Unavailable)' },
    { value: 'SINGLE_UPDATE_PROPOSAL', label: '2. Single Update Proposal (Review)' },
    { value: 'MISSING_RECORD_INSERT', label: '3. Missing Record Insert (Authorized)' },
    { value: 'EXTRA_RECORD_DELETE', label: '4. Extra Record Delete (Destructive)' },
    { value: 'SENSITIVE_DATA_TRANSFORMATION', label: '5. Sensitive Data & Tokenization' },
    { value: 'LARGE_BULK_REPAIR', label: '6. Bulk Aggregate Batch (1,420 Ops)' },
    { value: 'APPROVAL_REJECTED', label: '7. Governance Rejection' },
    { value: 'EXECUTION_INTERRUPTED_UNKNOWN_OUTCOME', label: '8. Unknown Commit Outcome (Law)' },
    { value: 'REVALIDATION_PASSED', label: '9. Repair Completed + Revalidation Passed' },
    { value: 'REVALIDATION_FAILED', label: '10. Repair Succeeded + Reval Failed' },
    { value: 'STRUCTURAL_UNSUPPORTED', label: '11. Structural Unsupported (DDL Req)' },
    { value: 'AUDIT_ONLY_MISSION', label: '12. Audit-Only Mission (Policy Read-Only)' },
    { value: 'NO_REMEDIATION_REQUIRED', label: '13. No Remediation Required (Clean)' },
    { value: 'LOADING_SKELETON', label: '14. Loading Skeleton' },
    { value: 'ERROR_STATE', label: '15. Error State' }
  ];

  getHeaderIconName(): string {
    const s = this.store.summary();
    if (s.revalidationState === 'PASSED') return 'check-circle-2';
    if (s.revalidationState === 'FAILED' || s.executionState === 'OUTCOME_UNKNOWN') return 'alert-triangle';
    if (s.governanceState === 'REJECTED') return 'shield-x';
    if (s.isReadonlyMission) return 'lock';
    return 'wrench';
  }

  getHeaderIconBgClass(): string {
    const s = this.store.summary();
    if (s.revalidationState === 'PASSED') return 'bg-emerald-50 border-emerald-200 text-emerald-600';
    if (s.revalidationState === 'FAILED' || s.executionState === 'OUTCOME_UNKNOWN') return 'bg-rose-50 border-rose-200 text-rose-600';
    if (s.governanceState === 'REJECTED') return 'bg-amber-50 border-amber-200 text-amber-600';
    if (s.isReadonlyMission) return 'bg-slate-100 border-slate-200 text-slate-600';
    return 'bg-purple-50 border-purple-200 text-purple-600';
  }

  getOverallStateBadgeClass(): string {
    const s = this.store.summary();
    if (s.revalidationState === 'PASSED') return 'bg-emerald-50 text-emerald-800 border-emerald-200';
    if (s.revalidationState === 'FAILED' || s.executionState === 'OUTCOME_UNKNOWN') return 'bg-rose-50 text-rose-800 border-rose-200';
    if (s.governanceState === 'APPROVED') return 'bg-blue-50 text-blue-800 border-blue-200';
    if (s.governanceState === 'REJECTED') return 'bg-red-50 text-red-800 border-red-200';
    if (s.governanceState === 'APPROVAL_REQUIRED' || s.governanceState === 'PENDING') return 'bg-amber-50 text-amber-800 border-amber-200';
    return 'bg-slate-100 text-slate-700 border-slate-200';
  }

  getOverallStateIconName(): string {
    const s = this.store.summary();
    if (s.revalidationState === 'PASSED') return 'check';
    if (s.revalidationState === 'FAILED' || s.executionState === 'OUTCOME_UNKNOWN') return 'alert-triangle';
    if (s.governanceState === 'APPROVED') return 'shield-check';
    if (s.governanceState === 'REJECTED') return 'shield-x';
    if (s.governanceState === 'APPROVAL_REQUIRED' || s.governanceState === 'PENDING') return 'clock';
    return 'info';
  }

  formatEligibility(e: string): string {
    switch (e) {
      case 'ELIGIBLE': return 'Eligible for remediation';
      case 'INELIGIBLE': return 'Ineligible for repair';
      case 'NOT_EVALUATED': return 'Not evaluated';
      case 'UNAVAILABLE': return 'Eligibility unavailable';
      default: return e;
    }
  }

  getEligibilityIcon(): string {
    switch (this.store.summary().eligibility) {
      case 'ELIGIBLE': return 'check-circle-2';
      case 'INELIGIBLE': return 'circle-x';
      default: return 'help-circle';
    }
  }

  formatProposal(p: string): string {
    switch (p) {
      case 'ESTABLISHED': return 'Proposal established';
      case 'DRAFT': return 'Draft proposal';
      case 'READY_FOR_EVALUATION': return 'Ready for evaluation';
      case 'UNAVAILABLE': return 'No proposal available';
      default: return p;
    }
  }

  getProposalIcon(): string {
    switch (this.store.summary().proposalState) {
      case 'ESTABLISHED': return 'file-code';
      default: return 'file';
    }
  }

  formatGovernance(g: string): string {
    switch (g) {
      case 'APPROVED': return 'Fully authorized';
      case 'APPROVAL_REQUIRED': return 'Approval required';
      case 'PENDING': return 'Approval pending';
      case 'NO_APPROVAL_REQUIRED': return 'Auto-authorized (Policy)';
      case 'REJECTED': return 'Proposal rejected';
      case 'EXPIRED': return 'Authorization expired';
      case 'NOT_EVALUATED': return 'Not evaluated';
      case 'UNAVAILABLE': return 'Governance unavailable';
      default: return g;
    }
  }

  getGovernanceIcon(): string {
    switch (this.store.summary().governanceState) {
      case 'APPROVED':
      case 'NO_APPROVAL_REQUIRED': return 'shield-check';
      case 'REJECTED': return 'shield-x';
      case 'APPROVAL_REQUIRED':
      case 'PENDING': return 'clock';
      default: return 'shield';
    }
  }

  formatExecution(e: string): string {
    switch (e) {
      case 'NOT_STARTED': return 'Not started';
      case 'SCHEDULED': return 'Scheduled';
      case 'RUNNING': return 'Executing...';
      case 'COMPLETED': return 'Completed';
      case 'INTERRUPTED': return 'Interrupted';
      case 'RECOVERING': return 'Recovering';
      case 'OUTCOME_UNKNOWN': return 'Outcome unknown';
      case 'FAILED': return 'Execution failed';
      case 'UNAVAILABLE': return 'Executor unavailable';
      default: return e;
    }
  }

  getExecutionIcon(): string {
    switch (this.store.summary().executionState) {
      case 'COMPLETED': return 'check-circle-2';
      case 'RUNNING': return 'play-circle';
      case 'OUTCOME_UNKNOWN':
      case 'INTERRUPTED':
      case 'FAILED': return 'alert-triangle';
      default: return 'circle';
    }
  }

  formatRevalidation(r: string): string {
    switch (r) {
      case 'PASSED': return 'Revalidation passed';
      case 'FAILED': return 'Revalidation failed';
      case 'WITHHELD': return 'Result withheld';
      case 'RUNNING': return 'Revalidating...';
      case 'REQUIRED': return 'Revalidation required';
      case 'NOT_REQUIRED': return 'Not required';
      case 'NOT_STARTED': return 'Not started';
      case 'INTERRUPTED': return 'Interrupted';
      case 'UNAVAILABLE': return 'Unavailable';
      default: return r;
    }
  }

  getRevalidationIcon(): string {
    switch (this.store.summary().revalidationState) {
      case 'PASSED': return 'check-circle-2';
      case 'FAILED': return 'alert-octagon';
      case 'WITHHELD': return 'help-circle';
      case 'RUNNING': return 'refresh-cw';
      case 'REQUIRED': return 'clock';
      default: return 'circle';
    }
  }
}

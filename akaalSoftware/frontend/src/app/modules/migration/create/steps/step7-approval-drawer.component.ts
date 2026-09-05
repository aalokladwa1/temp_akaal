import { Component, inject, signal, computed, effect } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';
import { CustomSelectComponent, CustomSelectOption } from '../../../../shared/components/custom-select.component';
import { Step7PlanStoreService } from '../../../../core/services/step7-plan-store.service';
import { ApprovalBarrierConfig, ApprovalBarrierPolicy, ApprovalRejectionAction, ApprovalTimeoutAction } from './step7-plan.models';

@Component({
  selector: 'app-step7-approval-drawer',
  standalone: true,
  imports: [CommonModule, FormsModule, LucideIconComponent, CustomSelectComponent],
  template: `
    <!-- BACKDROP -->
    <div
      (click)="store.closeGateDrawer()"
      class="fixed inset-0 bg-slate-900/40 z-40 transition-opacity">
    </div>

    <!-- SLIDE-OVER DRAWER -->
    <aside
      class="fixed inset-y-0 right-0 w-[540px] max-w-full bg-white border-l border-slate-200 z-50 flex flex-col font-sans select-none shadow-none">
      
      <!-- 1. HEADER -->
      <header class="p-4 border-b border-slate-200 flex items-center justify-between gap-3 shrink-0 bg-amber-50">
        <div class="flex items-center gap-3 min-w-0">
          <div class="w-8 h-8 rounded-lg bg-amber-100 border border-amber-300 text-amber-900 flex items-center justify-center shrink-0">
            <app-lucide-icon name="shield-check" [size]="16"></app-lucide-icon>
          </div>
          <div class="flex flex-col min-w-0">
            <div class="flex items-center gap-2">
              <span class="px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider bg-amber-200 text-amber-950">
                {{ gate()?.isMandatory ? 'Mandatory Policy Barrier' : 'Configured Gate' }}
              </span>
            </div>
            <h3 class="text-sm font-bold text-slate-900 m-0 truncate">{{ gate()?.gateName }}</h3>
          </div>
        </div>

        <button
          type="button"
          (click)="store.closeGateDrawer()"
          class="w-7 h-7 rounded-lg border border-slate-200 bg-white hover:bg-slate-100 text-slate-500 hover:text-slate-800 flex items-center justify-center cursor-pointer transition-colors"
          title="Close Gate Details">
          <app-lucide-icon name="x" [size]="14"></app-lucide-icon>
        </button>
      </header>

      <!-- 2. SCROLLABLE FORM BODY -->
      <div class="flex-1 overflow-y-auto p-5 flex flex-col gap-5 text-xs">
        
        <!-- MANDATORY POLICY LOCK BANNER -->
        @if (gate()?.isMandatory) {
          <div class="p-3 rounded-lg bg-amber-50 border border-amber-300 text-amber-950 flex items-start gap-2.5">
            <app-lucide-icon name="lock" [size]="14" class="text-amber-700 shrink-0 mt-0.5"></app-lucide-icon>
            <div class="flex flex-col gap-0.5 text-xs">
              <span class="font-bold">SOX-404 Cutover Governance Rule</span>
              <p class="m-0 text-amber-900 text-[11.5px]">
                This barrier is enforced by production enterprise governance. It cannot be deleted. Parameters are strictly bound to compliance policy invariants.
              </p>
            </div>
          </div>
        }

        <!-- GATE NAME & DESCRIPTION -->
        <div class="flex flex-col gap-3">
          <div class="flex flex-col gap-1">
            <label class="text-[11px] font-bold text-slate-700 uppercase tracking-wider">Gate Name</label>
            <input
              type="text"
              [(ngModel)]="draftGateName"
              [disabled]="!!gate()?.policyLocked"
              class="h-8 px-3 rounded-lg border border-slate-200 bg-white text-slate-900 text-xs focus:outline-none focus:border-blue-500 disabled:bg-slate-50 disabled:text-slate-600" />
          </div>

          <div class="flex flex-col gap-1">
            <label class="text-[11px] font-bold text-slate-700 uppercase tracking-wider">Protected Operation</label>
            <input
              type="text"
              [(ngModel)]="draftProtectedOperation"
              [disabled]="!!gate()?.policyLocked"
              class="h-8 px-3 rounded-lg border border-slate-200 bg-white text-slate-900 text-xs focus:outline-none focus:border-blue-500 disabled:bg-slate-50 disabled:text-slate-600" />
          </div>
        </div>

        <!-- SIGNER POLICY & QUORUM -->
        <div class="bg-slate-50 border border-slate-200 rounded-lg p-3.5 flex flex-col gap-3">
          <h4 class="text-xs font-bold text-slate-900 uppercase tracking-wider m-0 flex items-center gap-1.5">
            <app-lucide-icon name="users" [size]="13" class="text-slate-500"></app-lucide-icon>
            <span>Signer Policy & Quorum</span>
          </h4>

          <div class="grid grid-cols-2 gap-3">
            <div class="flex flex-col gap-1">
              <label class="text-[11px] text-slate-600 font-medium">Policy Rule</label>
              <app-custom-select
                [options]="signerPolicyOptions"
                [value]="draftSignerPolicy"
                (valueChange)="draftSignerPolicy = $event"
                [disabled]="!!gate()?.policyLocked"
                [size]="'sm'">
              </app-custom-select>
            </div>

            <div class="flex flex-col gap-1">
              <label class="text-[11px] text-slate-600 font-medium">Required Signatures</label>
              <input
                type="number"
                min="1"
                max="5"
                [(ngModel)]="draftRequiredSignatures"
                [disabled]="!!gate()?.policyLocked"
                class="h-8 px-3 rounded-lg border border-slate-200 bg-white text-slate-900 text-xs focus:outline-none focus:border-blue-500 disabled:bg-slate-50 disabled:text-slate-600" />
            </div>
          </div>

          <!-- Separation of Duties Checkbox -->
          <label class="flex items-start gap-2 pt-1 cursor-pointer select-none">
            <input
              type="checkbox"
              [(ngModel)]="draftSeparationOfDuties"
              [disabled]="!!gate()?.policyLocked"
              class="mt-0.5 rounded border-slate-300 text-blue-600 focus:ring-0" />
            <div class="flex flex-col text-xs">
              <span class="font-bold text-slate-800">Enforce Separation of Duties (SoD)</span>
              <span class="text-slate-500 text-[11px]">Migration creator/initiator is cryptographically barred from signing this gate.</span>
            </div>
          </label>
        </div>

        <!-- EXECUTION PRECONDITIONS -->
        <div class="bg-slate-50 border border-slate-200 rounded-lg p-3.5 flex flex-col gap-3">
          <h4 class="text-xs font-bold text-slate-900 uppercase tracking-wider m-0 flex items-center gap-1.5">
            <app-lucide-icon name="check-square" [size]="13" class="text-slate-500"></app-lucide-icon>
            <span>Execution Preconditions</span>
          </h4>

          <div class="flex flex-col gap-2">
            <label class="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                [(ngModel)]="draftRequireDlqEmpty"
                [disabled]="!!gate()?.policyLocked"
                class="rounded border-slate-300 text-blue-600 focus:ring-0" />
              <span class="text-slate-800 font-medium">Require Dead Letter Queue (DLQ) completely empty</span>
            </label>

            <label class="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                [(ngModel)]="draftRequireCheckpointClean"
                [disabled]="!!gate()?.policyLocked"
                class="rounded border-slate-300 text-blue-600 focus:ring-0" />
              <span class="text-slate-800 font-medium">Require all stream checkpoints committed and verified</span>
            </label>

            <label class="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                [(ngModel)]="draftRequireValidationPass"
                [disabled]="!!gate()?.policyLocked"
                class="rounded border-slate-300 text-blue-600 focus:ring-0" />
              <span class="text-slate-800 font-medium">Require pre-cutover validation checksums to pass 100%</span>
            </label>

            <div class="flex items-center justify-between pt-1">
              <span class="text-slate-700 font-medium">Max CDC Replication Lag:</span>
              <div class="flex items-center gap-1">
                <input
                  type="number"
                  [(ngModel)]="draftCdcMaxLagMs"
                  [disabled]="!!gate()?.policyLocked"
                  class="w-24 h-7 px-2 text-right rounded border border-slate-200 bg-white text-xs disabled:bg-slate-50" />
                <span class="text-slate-500 font-mono text-[11px]">ms</span>
              </div>
            </div>
          </div>
        </div>

        <!-- TIMEOUT & REJECTION ACTION -->
        <div class="bg-slate-50 border border-slate-200 rounded-lg p-3.5 flex flex-col gap-3">
          <h4 class="text-xs font-bold text-slate-900 uppercase tracking-wider m-0 flex items-center gap-1.5">
            <app-lucide-icon name="alert-octagon" [size]="13" class="text-slate-500"></app-lucide-icon>
            <span>Timeout & Rejection Handling</span>
          </h4>

          <div class="grid grid-cols-2 gap-3">
            <div class="flex flex-col gap-1">
              <label class="text-[11px] text-slate-600 font-medium">Timeout Action</label>
              <app-custom-select
                [options]="timeoutActionOptions"
                [value]="draftTimeoutAction"
                (valueChange)="draftTimeoutAction = $event"
                [disabled]="!!gate()?.policyLocked"
                [size]="'sm'">
              </app-custom-select>
            </div>

            <div class="flex flex-col gap-1">
              <label class="text-[11px] text-slate-600 font-medium">Rejection Action</label>
              <app-custom-select
                [options]="rejectionActionOptions"
                [value]="draftRejectionAction"
                (valueChange)="draftRejectionAction = $event"
                [disabled]="!!gate()?.policyLocked"
                [size]="'sm'">
              </app-custom-select>
            </div>
          </div>
        </div>

        <!-- GOVERNANCE NOTICE -->
        <div class="p-3 rounded-lg bg-blue-50 border border-blue-200 text-blue-900 flex items-start gap-2.5">
          <app-lucide-icon name="info" [size]="14" class="text-blue-600 shrink-0 mt-0.5"></app-lucide-icon>
          <p class="m-0 text-[11px] leading-relaxed">
            <strong>Planned Governance Boundary:</strong> Signatures and approval tokens are formally executed during <strong>Step 8: Governance & Execution</strong>. Step 7 establishes the formal plan topology barrier.
          </p>
        </div>

      </div>

      <!-- 3. FOOTER ACTIONS -->
      <footer class="p-4 border-t border-slate-200 flex items-center justify-between gap-3 bg-white shrink-0">
        @if (!gate()?.isMandatory) {
          <button
            type="button"
            (click)="deleteGate()"
            class="h-8 px-3 rounded-lg border border-red-200 bg-red-50 hover:bg-red-100 text-red-700 text-xs font-semibold flex items-center gap-1.5 cursor-pointer transition-colors">
            <app-lucide-icon name="trash-2" [size]="13"></app-lucide-icon>
            <span>Delete Gate</span>
          </button>
        } @else {
          <div class="text-[11px] text-slate-400 font-medium">Policy Locked Gate</div>
        }

        <div class="flex items-center gap-2">
          <button
            type="button"
            (click)="store.closeGateDrawer()"
            class="h-8 px-3 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 text-xs font-medium cursor-pointer transition-colors">
            Cancel
          </button>

          @if (!gate()?.policyLocked) {
            <button
              type="button"
              (click)="saveGate()"
              class="h-8 px-4 rounded-lg bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold cursor-pointer transition-colors">
              Save Configuration
            </button>
          }
        </div>
      </footer>

    </aside>
  `
})
export class Step7ApprovalDrawerComponent {
  public store = inject(Step7PlanStoreService);

  public gate = computed(() => this.store.selectedGate());

  public draftGateName = '';
  public draftProtectedOperation = '';
  public draftSignerPolicy: ApprovalBarrierPolicy = 'FOUR_EYES';
  public draftRequiredSignatures = 2;
  public draftSeparationOfDuties = true;
  public draftRequireDlqEmpty = true;
  public draftRequireCheckpointClean = true;
  public draftRequireValidationPass = true;
  public draftCdcMaxLagMs = 5000;
  public draftTimeoutAction: ApprovalTimeoutAction = 'ALERT_AND_HOLD';
  public draftRejectionAction: ApprovalRejectionAction = 'HALT_MIGRATION';

  public signerPolicyOptions: CustomSelectOption[] = [
    { label: 'Four-Eyes Principle', value: 'FOUR_EYES', icon: 'users' },
    { label: 'Sole Owner', value: 'SOLE_OWNER', icon: 'user-round' },
    { label: 'CAB Committee', value: 'CAB_COMMITTEE', icon: 'shield-check' },
    { label: 'Dual DBA & Security', value: 'DUAL_DBA_SEC', icon: 'lock' }
  ];

  public timeoutActionOptions: CustomSelectOption[] = [
    { label: 'Alert & Hold', value: 'ALERT_AND_HOLD', icon: 'pause' },
    { label: 'Auto-Reject', value: 'AUTO_REJECT', icon: 'circle-x' },
    { label: 'Rollback Stage', value: 'ROLLBACK_STAGE', icon: 'rotate-ccw' }
  ];

  public rejectionActionOptions: CustomSelectOption[] = [
    { label: 'Halt Migration', value: 'HALT_MIGRATION', icon: 'square' },
    { label: 'Fail Fast', value: 'FAIL_FAST', icon: 'zap' },
    { label: 'Rollback to Checkpoint', value: 'ROLLBACK_TO_CHECKPOINT', icon: 'rotate-ccw' }
  ];

  constructor() {
    effect(() => {
      const g = this.gate();
      if (g) {
        this.draftGateName = g.gateName;
        this.draftProtectedOperation = g.protectedOperation;
        this.draftSignerPolicy = g.signerPolicy;
        this.draftRequiredSignatures = g.requiredSignatures;
        this.draftSeparationOfDuties = g.separationOfDuties;
        this.draftRequireDlqEmpty = g.requireDlqEmpty;
        this.draftRequireCheckpointClean = g.requireCheckpointClean;
        this.draftRequireValidationPass = g.requireValidationPass;
        this.draftCdcMaxLagMs = g.cdcMaxLagMs || 5000;
        this.draftTimeoutAction = g.timeoutAction;
        this.draftRejectionAction = g.rejectionAction;
      }
    });
  }

  public saveGate(): void {
    const current = this.gate();
    if (!current) return;
    const updated: ApprovalBarrierConfig = {
      ...current,
      gateName: this.draftGateName,
      protectedOperation: this.draftProtectedOperation,
      signerPolicy: this.draftSignerPolicy,
      requiredSignatures: this.draftRequiredSignatures,
      separationOfDuties: this.draftSeparationOfDuties,
      requireDlqEmpty: this.draftRequireDlqEmpty,
      requireCheckpointClean: this.draftRequireCheckpointClean,
      requireValidationPass: this.draftRequireValidationPass,
      cdcMaxLagMs: this.draftCdcMaxLagMs,
      timeoutAction: this.draftTimeoutAction,
      rejectionAction: this.draftRejectionAction
    };
    this.store.updateApprovalGate(updated);
  }

  public deleteGate(): void {
    const current = this.gate();
    if (!current || current.isMandatory) return;
    this.store.removeApprovalGate(current.id);
  }
}

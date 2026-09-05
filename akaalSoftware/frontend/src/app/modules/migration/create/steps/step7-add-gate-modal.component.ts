import { Component, inject, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';
import { CustomSelectComponent, CustomSelectOption } from '../../../../shared/components/custom-select.component';
import { Step7PlanStoreService } from '../../../../core/services/step7-plan-store.service';
import { NewGateDraft, ApprovalBarrierPolicy, ApprovalTimeoutAction, ApprovalRejectionAction } from './step7-plan.models';

@Component({
  selector: 'app-step7-add-gate-modal',
  standalone: true,
  imports: [CommonModule, FormsModule, LucideIconComponent, CustomSelectComponent],
  template: `
    <!-- BACKDROP -->
    <div
      (click)="store.closeAddGateModal()"
      class="fixed inset-0 bg-slate-900/50 z-50 flex items-center justify-center p-4 select-none font-sans">
      
      <!-- MODAL CARD -->
      <div
        (click)="$event.stopPropagation()"
        class="w-full max-w-xl bg-white rounded-xl border border-slate-200 overflow-hidden flex flex-col max-h-[90vh] shadow-none">
        
        <!-- HEADER -->
        <header class="p-4 border-b border-slate-200 flex items-center justify-between gap-3 bg-slate-50/80">
          <div class="flex items-center gap-2.5 min-w-0">
            <div class="w-8 h-8 rounded-lg bg-blue-50 border border-blue-200 text-blue-600 flex items-center justify-center shrink-0">
              <app-lucide-icon name="shield-plus" [size]="16"></app-lucide-icon>
            </div>
            <div class="flex flex-col min-w-0">
              <h3 class="text-sm font-bold text-slate-900 m-0">Add Approval Gate</h3>
              <span class="text-[11px] text-slate-500">Establish a formal approval barrier in execution topology.</span>
            </div>
          </div>

          <button
            type="button"
            (click)="store.closeAddGateModal()"
            class="w-7 h-7 rounded-lg border border-slate-200 bg-white hover:bg-slate-100 text-slate-500 hover:text-slate-800 flex items-center justify-center cursor-pointer transition-colors"
            title="Close Modal">
            <app-lucide-icon name="x" [size]="14"></app-lucide-icon>
          </button>
        </header>

        <!-- BODY -->
        <div class="p-5 overflow-y-auto flex flex-col gap-4 text-xs">
          
          <!-- PLACEMENT BOUNDARY SELECTOR -->
          <div class="flex flex-col gap-1.5">
            <label class="text-[11px] font-bold text-slate-700 uppercase tracking-wider">
              Placement Boundary (Between Stages)
            </label>
            <app-custom-select
              [options]="placementOptions()"
              [value]="placementEdgeId"
              (valueChange)="placementEdgeId = $event"
              [size]="'md'">
            </app-custom-select>
          </div>

          <!-- GATE NAME & PROTECTED OP -->
          <div class="grid grid-cols-2 gap-3">
            <div class="flex flex-col gap-1">
              <label class="text-[11px] font-bold text-slate-700 uppercase tracking-wider">Gate Name</label>
              <input
                type="text"
                [(ngModel)]="gateName"
                placeholder="e.g. Pre-Load Verification Gate"
                class="h-8 px-3 rounded-lg border border-slate-200 bg-white text-slate-900 text-xs focus:outline-none focus:border-blue-500" />
            </div>

            <div class="flex flex-col gap-1">
              <label class="text-[11px] font-bold text-slate-700 uppercase tracking-wider">Protected Operation</label>
              <input
                type="text"
                [(ngModel)]="protectedOperation"
                placeholder="e.g. Bulk Load Ingestion"
                class="h-8 px-3 rounded-lg border border-slate-200 bg-white text-slate-900 text-xs focus:outline-none focus:border-blue-500" />
            </div>
          </div>

          <!-- SIGNER POLICY & QUORUM -->
          <div class="grid grid-cols-2 gap-3">
            <div class="flex flex-col gap-1">
              <label class="text-[11px] font-bold text-slate-700 uppercase tracking-wider">Signer Policy</label>
              <app-custom-select
                [options]="signerPolicyOptions"
                [value]="signerPolicy"
                (valueChange)="signerPolicy = $event"
                [size]="'sm'">
              </app-custom-select>
            </div>

            <div class="flex flex-col gap-1">
              <label class="text-[11px] font-bold text-slate-700 uppercase tracking-wider">Required Signatures</label>
              <input
                type="number"
                min="1"
                max="5"
                [(ngModel)]="requiredSignatures"
                class="h-8 px-3 rounded-lg border border-slate-200 bg-white text-slate-900 text-xs focus:outline-none focus:border-blue-500" />
            </div>
          </div>

          <!-- PRECONDITIONS -->
          <div class="bg-slate-50 border border-slate-200 rounded-lg p-3 flex flex-col gap-2">
            <span class="text-[11px] font-bold text-slate-700 uppercase tracking-wider">Execution Preconditions</span>
            
            <label class="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                [(ngModel)]="requireDlqEmpty"
                class="rounded border-slate-300 text-blue-600 focus:ring-0" />
              <span class="text-slate-800">Require Dead Letter Queue (DLQ) to be empty</span>
            </label>

            <label class="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                [(ngModel)]="requireCheckpointClean"
                class="rounded border-slate-300 text-blue-600 focus:ring-0" />
              <span class="text-slate-800">Require all preceding checkpoints verified</span>
            </label>

            <div class="flex items-center justify-between pt-1">
              <span class="text-slate-700">Max Allowable CDC Lag:</span>
              <div class="flex items-center gap-1">
                <input
                  type="number"
                  [(ngModel)]="cdcMaxLagMs"
                  class="w-20 h-6 px-2 text-right rounded border border-slate-200 bg-white text-xs" />
                <span class="text-slate-500 text-[11px]">ms</span>
              </div>
            </div>
          </div>

        </div>

        <!-- FOOTER -->
        <footer class="p-4 border-t border-slate-200 flex items-center justify-end gap-2.5 bg-slate-50/50 shrink-0">
          <button
            type="button"
            (click)="store.closeAddGateModal()"
            class="h-8 px-3.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 text-xs font-medium cursor-pointer transition-colors">
            Cancel
          </button>

          <button
            type="button"
            (click)="submitAddGate()"
            class="h-8 px-4 rounded-lg bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold cursor-pointer transition-colors flex items-center gap-1.5">
            <app-lucide-icon name="check" [size]="13"></app-lucide-icon>
            <span>Insert Approval Gate</span>
          </button>
        </footer>

      </div>
    </div>
  `
})
export class Step7AddGateModalComponent {
  public store = inject(Step7PlanStoreService);

  public placementEdgeId = this.store.selectedPlacementEdgeId() || (this.store.eligibleEdges()[0]?.id || '');
  public gateName = 'Intermediate Verification Gate';
  public description = 'Mandatory operational verification checkpoint prior to next execution stage.';
  public protectedOperation = 'Downstream Stage Execution';
  public signerPolicy: ApprovalBarrierPolicy = 'FOUR_EYES';
  public requiredSignatures = 2;
  public cdcMaxLagMs = 5000;

  public placementOptions = computed<CustomSelectOption[]>(() => {
    return this.store.eligibleEdges().map(edge => ({
      label: `Between ${this.getStageLabel(edge.source)} → ${this.getStageLabel(edge.target)}`,
      value: edge.id,
      icon: 'git-compare'
    }));
  });

  public signerPolicyOptions: CustomSelectOption[] = [
    { label: 'Four-Eyes Principle (2 signers)', value: 'FOUR_EYES', icon: 'users' },
    { label: 'Sole Migration Owner', value: 'SOLE_OWNER', icon: 'user-round' },
    { label: 'CAB Committee Review', value: 'CAB_COMMITTEE', icon: 'shield-check' },
    { label: 'Dual DBA & Security Leads', value: 'DUAL_DBA_SEC', icon: 'lock' }
  ];
  public requireDlqEmpty = true;
  public requireCheckpointClean = true;
  public requireValidationPass = true;
  public requireTargetTablesEmpty = false;
  public timeoutMinutes = 120;
  public timeoutAction: ApprovalTimeoutAction = 'ALERT_AND_HOLD';
  public rejectionAction: ApprovalRejectionAction = 'HALT_MIGRATION';

  public getStageLabel(nodeId: string): string {
    const n = this.store.nodes().find(x => x.id === nodeId);
    return n ? `${n.label} (Stage ${n.order})` : nodeId;
  }

  public submitAddGate(): void {
    if (!this.placementEdgeId) return;
    const draft: NewGateDraft = {
      placementEdgeId: this.placementEdgeId,
      gateName: this.gateName,
      description: this.description,
      protectedOperation: this.protectedOperation,
      signerPolicy: this.signerPolicy,
      requiredSignatures: this.requiredSignatures,
      cdcMaxLagMs: this.cdcMaxLagMs,
      requireDlqEmpty: this.requireDlqEmpty,
      requireCheckpointClean: this.requireCheckpointClean,
      requireValidationPass: this.requireValidationPass,
      requireTargetTablesEmpty: this.requireTargetTablesEmpty,
      timeoutMinutes: this.timeoutMinutes,
      timeoutAction: this.timeoutAction,
      rejectionAction: this.rejectionAction
    };
    this.store.addApprovalGate(draft);
  }
}

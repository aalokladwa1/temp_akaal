import { Component, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';
import { Step8GovernanceStoreService } from '../../../../core/services/step8-governance-store.service';
import { GovernanceGatePresentation } from './step8-governance.models';

@Component({
  selector: 'app-step8-approval-drawer',
  standalone: true,
  imports: [CommonModule, FormsModule, LucideIconComponent],
  template: `
    <!-- Overlay Backdrop (zero blur, standard slate-900/40) -->
    <div
      class="fixed inset-0 z-40 bg-slate-900/40 animate-in fade-in duration-100"
      (click)="store.closeApprovalDrawer()">
    </div>

    <!-- Slide-over Drawer Surface (Right-aligned, w-[480px], flat border, zero shadow) -->
    <aside
      role="dialog"
      aria-modal="true"
      aria-label="Governance Gate Approval Drawer"
      class="fixed right-0 top-0 bottom-0 z-50 w-[480px] bg-white border-l border-slate-200 flex flex-col justify-between font-sans text-xs select-none animate-in slide-in-from-right duration-150"
      (click)="$event.stopPropagation()">
      
      <!-- Drawer Header -->
      <header class="p-4 border-b border-slate-200 flex items-start justify-between gap-3 bg-slate-50 shrink-0">
        <div class="flex flex-col gap-1 min-w-0">
          <div class="flex items-center gap-2">
            <span class="font-bold text-slate-900 text-sm truncate">{{ gate()?.gateName }}</span>
            @if (gate()?.isMandatory) {
              <span class="px-1.5 py-0.5 rounded text-[10px] font-bold bg-amber-100 text-amber-900 border border-amber-200 shrink-0">
                Mandatory Policy
              </span>
            }
          </div>
          <span class="text-[11px] text-slate-500 font-mono">{{ gate()?.stagePlacementLabel }}</span>
        </div>

        <button
          type="button"
          (click)="store.closeApprovalDrawer()"
          class="w-7 h-7 rounded border border-slate-200 bg-white hover:bg-slate-100 text-slate-500 hover:text-slate-900 flex items-center justify-center cursor-pointer transition-colors shrink-0"
          title="Close drawer">
          <app-lucide-icon name="x" [size]="14"></app-lucide-icon>
        </button>
      </header>

      <!-- Drawer Scrollable Body -->
      <div class="p-5 flex-1 overflow-y-auto flex flex-col gap-4">
        
        <!-- 1. Description & Placement Info -->
        <div class="bg-white border border-slate-200 rounded-lg p-3 flex flex-col gap-2">
          <span class="text-[11px] font-bold uppercase tracking-wider text-slate-500">Gate Policy Definition</span>
          <p class="text-xs text-slate-700 m-0 leading-relaxed">{{ gate()?.description }}</p>
          <div class="grid grid-cols-2 gap-2 pt-2 border-t border-slate-100 text-[11px]">
            <div>
              <span class="text-slate-500">Signer Policy:</span>
              <p class="font-semibold text-slate-900 m-0">{{ gate()?.signerPolicyLabel }}</p>
            </div>
            <div>
              <span class="text-slate-500">Required Signatures:</span>
              <p class="font-semibold text-slate-900 m-0">{{ gate()?.requiredSignatures }} Signer(s)</p>
            </div>
          </div>
        </div>

        <!-- 2. Actor Authorization & Separation of Duties (Maker-Checker) -->
        <div class="border rounded-lg p-3.5 flex flex-col gap-2"
          [class.bg-blue-50]="gate()?.actorContext?.isCurrentActorEligible"
          [class.border-blue-200]="gate()?.actorContext?.isCurrentActorEligible"
          [class.bg-amber-50]="!gate()?.actorContext?.isCurrentActorEligible"
          [class.border-amber-200]="!gate()?.actorContext?.isCurrentActorEligible">
          
          <div class="flex items-center gap-2">
            <app-lucide-icon
              [name]="gate()?.actorContext?.isCurrentActorEligible ? 'shield-check' : 'shield-alert'"
              [size]="15"
              [class]="gate()?.actorContext?.isCurrentActorEligible ? 'text-blue-600' : 'text-amber-600'">
            </app-lucide-icon>
            <span class="font-bold text-xs"
              [class.text-blue-900]="gate()?.actorContext?.isCurrentActorEligible"
              [class.text-amber-900]="!gate()?.actorContext?.isCurrentActorEligible">
              {{ gate()?.actorContext?.isCurrentActorEligible ? 'Authorized Signatory' : 'Separation of Duties Notice' }}
            </span>
          </div>

          <p class="text-[11.5px] m-0 leading-relaxed"
            [class.text-blue-800]="gate()?.actorContext?.isCurrentActorEligible"
            [class.text-amber-800]="!gate()?.actorContext?.isCurrentActorEligible">
            @if (gate()?.actorContext?.isCurrentActorEligible) {
              Current Actor: <strong>{{ gate()?.actorContext?.currentActorName }}</strong> (Role: {{ gate()?.actorContext?.currentActorRole }}). You hold authorized signing privileges for this gate.
            } @else {
              {{ gate()?.actorContext?.sodExplanation || 'Your current role does not have authorization to sign this gate.' }}
            }
          </p>
        </div>

        <!-- 3. Preconditions Verification Checklist -->
        <div class="flex flex-col gap-2">
          <span class="text-[11px] font-bold uppercase tracking-wider text-slate-500">Preconditions Checklist</span>
          <div class="bg-white border border-slate-200 rounded-lg divide-y divide-slate-100 overflow-hidden">
            @for (pre of gate()?.preconditions || []; track pre.id) {
              <div class="p-2.5 flex items-start justify-between gap-2">
                <div class="flex items-start gap-2 min-w-0">
                  <app-lucide-icon
                    [name]="pre.satisfied ? 'check-circle-2' : 'alert-circle'"
                    [size]="14"
                    [class]="pre.satisfied ? 'text-emerald-600 mt-0.5' : 'text-amber-600 mt-0.5'">
                  </app-lucide-icon>
                  <div class="flex flex-col">
                    <span class="font-medium text-slate-800 text-[11.5px]">{{ pre.label }}</span>
                    @if (pre.requirementDetail) {
                      <span class="text-[10.5px] text-slate-500 font-mono">{{ pre.requirementDetail }}</span>
                    }
                  </div>
                </div>

                <span class="px-1.5 py-0.2 rounded text-[10px] font-bold border shrink-0"
                  [class.bg-emerald-50]="pre.satisfied"
                  [class.text-emerald-700]="pre.satisfied"
                  [class.border-emerald-200]="pre.satisfied"
                  [class.bg-amber-50]="!pre.satisfied"
                  [class.text-amber-800]="!pre.satisfied"
                  [class.border-amber-200]="!pre.satisfied">
                  {{ pre.satisfied ? 'Verified' : 'Pending' }}
                </span>
              </div>
            }
          </div>
        </div>

        <!-- 4. Approval Comment / Decision Rationale -->
        <div class="flex flex-col gap-1.5">
          <label for="gate-comment" class="text-[11px] font-bold uppercase tracking-wider text-slate-500">
            Decision Comments &amp; Audit Rationale
          </label>
          <textarea
            id="gate-comment"
            [(ngModel)]="decisionComment"
            rows="3"
            placeholder="Enter formal sign-off comments or rejection rationale for governance audit..."
            class="w-full p-2.5 bg-white border border-slate-200 rounded-lg text-xs text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-blue-500 font-sans resize-none">
          </textarea>
        </div>

      </div>

      <!-- Drawer Footer Actions -->
      <footer class="p-4 border-t border-slate-200 bg-slate-50 flex items-center justify-between gap-3 shrink-0">
        <button
          type="button"
          (click)="store.closeApprovalDrawer()"
          class="h-8 px-3 text-xs font-medium text-slate-700 border border-slate-200 rounded-md bg-white hover:bg-slate-100 transition-colors cursor-pointer">
          Cancel
        </button>

        <div class="flex items-center gap-2">
          <button
            type="button"
            (click)="handleReject()"
            [disabled]="!gate()?.actorContext?.isCurrentActorEligible"
            class="h-8 px-3 text-xs font-semibold text-rose-700 bg-rose-50 hover:bg-rose-100 border border-rose-200 rounded-md transition-colors cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed">
            Reject Gate
          </button>

          <button
            type="button"
            (click)="handleApprove()"
            [disabled]="!gate()?.actorContext?.isCurrentActorEligible"
            class="h-8 px-3.5 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded-md transition-colors cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-1.5">
            <app-lucide-icon name="check" [size]="13"></app-lucide-icon>
            <span>Approve Gate</span>
          </button>
        </div>
      </footer>

    </aside>
  `
})
export class Step8ApprovalDrawerComponent {
  public store = inject(Step8GovernanceStoreService);
  public decisionComment = '';

  public gate(): GovernanceGatePresentation | null {
    return this.store.selectedApprovalGate();
  }

  public handleApprove(): void {
    const g = this.gate();
    if (!g) return;
    this.store.approveGate(g.id, this.decisionComment.trim() || 'Approved by authorized signatory.');
  }

  public handleReject(): void {
    const g = this.gate();
    if (!g) return;
    this.store.rejectGate(g.id, this.decisionComment.trim() || 'Rejected by authorized signatory.');
  }
}

import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ValidationUiService } from '../../../core/services/validation-ui.service';
import { LucideIconComponent } from '../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-governed-repair-modal',
  standalone: true,
  imports: [CommonModule, LucideIconComponent],
  template: `
    @if (vs.isRepairModalOpen()) {
      <div 
        class="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 backdrop-blur-xs p-4 animate-in fade-in duration-150"
        (click)="vs.closeRepairModal()">
        
        <div 
          class="w-full max-w-lg rounded-2xl bg-white border border-slate-200 shadow-2xl overflow-hidden flex flex-col animate-in zoom-in-95 duration-150"
          (click)="$event.stopPropagation()">
          
          <!-- Header -->
          <div class="p-6 bg-amber-50/50 border-b border-slate-100 flex items-start gap-4">
            <div class="w-10 h-10 rounded-xl bg-amber-100 text-amber-700 flex items-center justify-center shrink-0">
              <app-lucide-icon name="shield-alert" [size]="20"></app-lucide-icon>
            </div>
            <div class="flex flex-col gap-1 flex-1">
              <span class="text-xs font-bold text-amber-700 uppercase tracking-wider">Target-Mutating Governed Repair</span>
              <h3 class="text-base font-bold text-slate-900">Authorize Governed Repair Plan</h3>
            </div>
            <button type="button" (click)="vs.closeRepairModal()" class="p-1 text-slate-400 hover:text-slate-700">
              <app-lucide-icon name="x" [size]="16"></app-lucide-icon>
            </button>
          </div>

          <!-- Body -->
          <div class="p-6 flex flex-col gap-4 text-xs text-slate-700">
            <p class="font-medium">
              A target-mutating repair plan has been synthesized to reconcile <span class="font-bold text-slate-900">18 disputed records</span> detected during validation.
            </p>

            <div class="p-3.5 rounded-xl bg-slate-50 border border-slate-200 flex flex-col gap-2">
              <span class="text-[11px] font-bold text-slate-900 uppercase">Proposed Mutation Operations</span>
              <div class="grid grid-cols-3 gap-2 text-center">
                <div class="p-2 rounded-lg bg-white border border-slate-200">
                  <span class="text-[10px] text-slate-500 font-bold block">INSERTS</span>
                  <span class="text-base font-bold text-emerald-700">{{ vs.governedRepairPlan().proposedInserts }}</span>
                </div>
                <div class="p-2 rounded-lg bg-white border border-slate-200">
                  <span class="text-[10px] text-slate-500 font-bold block">UPDATES</span>
                  <span class="text-base font-bold text-blue-700">{{ vs.governedRepairPlan().proposedUpdates }}</span>
                </div>
                <div class="p-2 rounded-lg bg-white border border-slate-200">
                  <span class="text-[10px] text-slate-500 font-bold block">DELETES</span>
                  <span class="text-base font-bold text-slate-700">{{ vs.governedRepairPlan().proposedDeletes }}</span>
                </div>
              </div>
            </div>

            <div class="p-3.5 rounded-xl bg-amber-50 border border-amber-200 text-amber-900 font-medium">
              <strong>Maker-Checker Enforced:</strong> Requires approval sign-off by Lead DBA before execution. Target will be automatically re-validated after repair.
            </div>
          </div>

          <!-- Footer -->
          <div class="p-4 bg-slate-50 border-t border-slate-100 flex items-center justify-end gap-3">
            <button type="button" (click)="vs.closeRepairModal()" class="px-4 py-2 rounded-xl bg-white border border-slate-200 text-slate-700 text-xs font-semibold">
              Cancel
            </button>
            <button type="button" (click)="vs.closeRepairModal()" class="px-4 py-2 rounded-xl bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold shadow-xs">
              Authorize &amp; Dispatch Repair
            </button>
          </div>

        </div>
      </div>
    }
  `
})
export class GovernedRepairModalComponent {
  public vs = inject(ValidationUiService);
}

import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ValidationRepairService } from '../validation-repair.service';
import { LucideIconComponent } from '../../../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-repair-confirm-dialog',
  standalone: true,
  imports: [CommonModule, LucideIconComponent],
  template: `
    @if (store.isConfirmModalOpen()) {
      <div class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs animate-in fade-in duration-150">
        
        <div class="bg-white border border-slate-200 rounded-2xl max-w-lg w-full p-6 sm:p-7 shadow-2xl flex flex-col gap-6 animate-in zoom-in-95 duration-150">
          
          <!-- Header -->
          <div class="flex items-start gap-4">
            <div [ngClass]="isDestructive() ? 'bg-red-50 text-red-600 border-red-200' : 'bg-blue-50 text-blue-600 border-blue-200'"
                 class="w-12 h-12 rounded-xl flex items-center justify-center shrink-0 border shadow-2xs">
              <app-lucide-icon [name]="isDestructive() ? 'trash-2' : 'shield-alert'" [size]="24"></app-lucide-icon>
            </div>

            <div class="flex flex-col gap-1">
              <h3 class="text-sm font-bold text-slate-900 font-heading">
                {{ isDestructive() ? 'Confirm Destructive Target Deletion' : 'Confirm Governed Repair Execution' }}
              </h3>
              <p class="text-xs text-slate-600 leading-relaxed">
                You are about to dispatch a mutating compensating operation to the target endpoint.
              </p>
            </div>
          </div>

          <!-- Execution Summary Details Box -->
          <div class="p-4.5 sm:p-5 rounded-xl bg-slate-50/80 border border-slate-200 flex flex-col gap-3 text-xs text-slate-700 shadow-2xs">
            <div class="flex items-center justify-between">
              <span class="text-slate-500 font-medium">Target Object:</span>
              <span class="font-mono font-bold text-slate-900">{{ store.proposal()?.targetObject }}</span>
            </div>
            <div class="flex items-center justify-between">
              <span class="text-slate-500 font-medium">Record Identity:</span>
              <span class="font-mono font-bold text-slate-900">{{ store.proposal()?.recordKey }}</span>
            </div>
            <div class="flex items-center justify-between">
              <span class="text-slate-500 font-medium">Operation Family:</span>
              <span class="font-bold text-slate-900">{{ store.proposal()?.operationFamily }}</span>
            </div>
            <div class="flex items-center justify-between">
              <span class="text-slate-500 font-medium">Governance Quorum:</span>
              <span class="text-emerald-700 font-bold flex items-center gap-1.5">
                <app-lucide-icon name="check-circle-2" [size]="13"></app-lucide-icon>
                <span>Satisfied ({{ store.governance()?.quorumSatisfied }}/{{ store.governance()?.quorumRequired }} signatures)</span>
              </span>
            </div>
            <div class="flex items-center justify-between">
              <span class="text-slate-500 font-medium">Post-Repair Action:</span>
              <span class="font-bold text-blue-700 flex items-center gap-1">
                <app-lucide-icon name="refresh-cw" [size]="12"></app-lucide-icon>
                <span>Mandatory Validation #11 Rescan</span>
              </span>
            </div>
          </div>

          <!-- Consequence Warning -->
          <div [ngClass]="isDestructive() ? 'bg-red-50 border-red-200 text-red-900' : 'bg-amber-50 border-amber-200 text-amber-900'"
               class="p-4 rounded-xl border text-xs leading-relaxed flex items-start gap-3 shadow-2xs">
            <app-lucide-icon name="alert-triangle" [size]="17" class="shrink-0 mt-0.5"></app-lucide-icon>
            <span class="font-normal">
              {{ isDestructive()
                ? 'Target record will be permanently deleted. Ensure target endpoint backups exist before proceeding.'
                : 'Controlled repair will apply changes directly to the target system. Execution progress and post-repair revalidation will start immediately.' }}
            </span>
          </div>

          <!-- Dialog Buttons -->
          <div class="flex items-center justify-end gap-3 pt-2 border-t border-slate-100">
            <button
              type="button"
              (click)="store.closeConfirmModal()"
              class="h-9 px-4 rounded-lg bg-white border border-slate-200 hover:bg-slate-50 text-slate-700 text-xs font-semibold cursor-pointer transition-colors shadow-2xs">
              Cancel
            </button>
            <button
              type="button"
              (click)="store.executeRepair()"
              [ngClass]="isDestructive() ? 'bg-red-600 hover:bg-red-700' : 'bg-blue-600 hover:bg-blue-700'"
              class="h-9 px-4.5 rounded-lg text-white text-xs font-semibold cursor-pointer transition-colors shadow-2xs flex items-center gap-2">
              <app-lucide-icon [name]="isDestructive() ? 'trash-2' : 'play'" [size]="13"></app-lucide-icon>
              <span>{{ isDestructive() ? 'Authorize & Delete' : 'Authorize & Execute' }}</span>
            </button>
          </div>

        </div>

      </div>
    }
  `
})
export class RepairConfirmDialogComponent {
  readonly store = inject(ValidationRepairService);

  isDestructive(): boolean {
    return this.store.proposal()?.operationFamily === 'DELETE_EXTRA_TARGET';
  }
}

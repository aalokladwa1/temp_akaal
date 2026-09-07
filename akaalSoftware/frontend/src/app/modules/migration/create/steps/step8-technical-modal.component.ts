import { Component, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';
import { Step8GovernanceStoreService } from '../../../../core/services/step8-governance-store.service';
import { GovernedPlanSnapshot } from './step8-governance.models';

@Component({
  selector: 'app-step8-technical-modal',
  standalone: true,
  imports: [CommonModule, LucideIconComponent],
  template: `
    <!-- Overlay Backdrop (zero blur) -->
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Governance Technical Details"
      class="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-4 animate-in fade-in duration-100"
      (click)="store.closeTechnicalModal()">
      
      <!-- Modal Shell (flat border, zero shadow) -->
      <div
        class="w-full max-w-xl rounded-xl bg-white border border-slate-200 flex flex-col overflow-hidden font-sans text-xs select-none"
        (click)="$event.stopPropagation()">
        
        <!-- Modal Header -->
        <header class="p-4 bg-slate-50 border-b border-slate-200 flex items-center justify-between">
          <div class="flex items-center gap-2.5">
            <div class="w-8 h-8 rounded-lg bg-blue-50 border border-blue-200 text-blue-600 flex items-center justify-center shrink-0">
              <app-lucide-icon name="shield-check" [size]="16"></app-lucide-icon>
            </div>
            <div class="flex flex-col">
              <h3 class="font-bold text-slate-900 text-sm m-0">Governance Technical Details</h3>
              <span class="text-[11px] text-slate-500 font-medium">Immutable identity &amp; policy binding metadata</span>
            </div>
          </div>

          <button
            type="button"
            (click)="store.closeTechnicalModal()"
            class="w-7 h-7 rounded border border-slate-200 bg-white hover:bg-slate-100 text-slate-500 hover:text-slate-900 flex items-center justify-center cursor-pointer transition-colors"
            title="Close modal">
            <app-lucide-icon name="x" [size]="14"></app-lucide-icon>
          </button>
        </header>

        <!-- Modal Body (2-Column Key-Value Grid) -->
        <div class="p-5 flex flex-col gap-4">
          
          <div class="bg-slate-50 border border-slate-200 rounded-lg p-3.5 grid grid-cols-2 gap-y-3 gap-x-4 text-xs">
            
            <div>
              <span class="text-[11px] text-slate-500">Plan ID:</span>
              <p class="font-mono font-bold text-slate-900 m-0">{{ snapshot().planId }}</p>
            </div>

            <div>
              <span class="text-[11px] text-slate-500">Plan Revision:</span>
              <p class="font-semibold text-slate-900 m-0">{{ snapshot().revision }}</p>
            </div>

            <div class="col-span-2">
              <div class="flex items-center justify-between">
                <span class="text-[11px] text-slate-500">Plan Fingerprint:</span>
                <button
                  type="button"
                  (click)="copyFingerprint()"
                  class="text-[10.5px] font-semibold text-blue-600 hover:text-blue-800 flex items-center gap-1 cursor-pointer">
                  <app-lucide-icon [name]="copied() ? 'check' : 'copy'" [size]="11"></app-lucide-icon>
                  <span>{{ copied() ? 'Copied' : 'Copy Hash' }}</span>
                </button>
              </div>
              <p class="font-mono text-[11px] text-slate-800 bg-white p-2 rounded border border-slate-200 m-0 break-all select-all">
                {{ snapshot().fingerprint }}
              </p>
            </div>

            <div>
              <span class="text-[11px] text-slate-500">Execution Mode:</span>
              <p class="font-semibold text-blue-700 m-0">{{ snapshot().mode }}</p>
            </div>

            <div>
              <span class="text-[11px] text-slate-500">Target Environment:</span>
              <p class="font-semibold text-slate-900 m-0">{{ snapshot().environment }}</p>
            </div>

            <div>
              <span class="text-[11px] text-slate-500">Source Endpoint:</span>
              <p class="font-semibold text-slate-900 m-0">{{ snapshot().sourceEngine }}</p>
            </div>

            <div>
              <span class="text-[11px] text-slate-500">Target Endpoint:</span>
              <p class="font-semibold text-slate-900 m-0">{{ snapshot().targetEngine }}</p>
            </div>

            <div>
              <span class="text-[11px] text-slate-500">Policy Binding:</span>
              <p class="font-mono text-slate-700 m-0">{{ snapshot().policyBindingVersion || 'AKAAL-GOV-POLICY-2026.1' }}</p>
            </div>

            <div>
              <span class="text-[11px] text-slate-500">Seal Status:</span>
              <p class="font-semibold text-emerald-700 m-0 flex items-center gap-1">
                <app-lucide-icon name="shield-check" [size]="12"></app-lucide-icon>
                <span>{{ snapshot().sealedChecksum ? 'Sealed & Valid' : 'Unsealed' }}</span>
              </p>
            </div>

          </div>

          <p class="text-[11.5px] text-slate-500 m-0 leading-relaxed">
            This cryptographic snapshot anchors the migration plan definition to ensure zero tampering between governance sign-off and runtime execution.
          </p>

        </div>

        <!-- Modal Footer -->
        <footer class="p-3.5 bg-slate-50 border-t border-slate-200 flex items-center justify-end">
          <button
            type="button"
            (click)="store.closeTechnicalModal()"
            class="h-8 px-4 text-xs font-semibold text-slate-700 border border-slate-200 rounded-md bg-white hover:bg-slate-100 transition-colors cursor-pointer">
            Close
          </button>
        </footer>

      </div>
    </div>
  `
})
export class Step8TechnicalModalComponent {
  public store = inject(Step8GovernanceStoreService);
  public copied = signal<boolean>(false);

  public snapshot(): GovernedPlanSnapshot {
    return this.store.governedPlanSnapshot();
  }

  public copyFingerprint(): void {
    const fp = this.snapshot().fingerprint;
    if (typeof navigator !== 'undefined' && navigator.clipboard) {
      navigator.clipboard.writeText(fp);
      this.copied.set(true);
      setTimeout(() => this.copied.set(false), 2000);
    }
  }
}

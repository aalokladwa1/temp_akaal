// ============================================================================
// AKAAL CREATE MIGRATION — STEP 9: REVIEW, SCHEDULE & INITIALIZE
// TECHNICAL DETAILS MODAL COMPONENT (GDS ZERO-ELEVATION MODAL)
// ============================================================================

import { Component, inject, signal, HostListener } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Step9ReviewStoreService } from '../../../../core/services/step9-review-store.service';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-step9-technical-modal',
  standalone: true,
  imports: [CommonModule, LucideIconComponent],
  template: `
    @if (store.isTechnicalModalOpen()) {
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="step9-tech-modal-title"
        class="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-4 animate-in fade-in duration-100 font-sans"
        (click)="store.closeTechnicalModal()">
        
        <div
          class="w-full max-w-2xl rounded-xl bg-white border border-slate-200 p-6 flex flex-col gap-5 select-none"
          (click)="$event.stopPropagation()">
          
          <!-- Modal Header -->
          <div class="flex items-center justify-between pb-3 border-b border-slate-200">
            <div class="flex items-center gap-3">
              <div class="w-9 h-9 rounded-lg bg-blue-50 border border-blue-200 text-blue-600 flex items-center justify-center shrink-0">
                <app-lucide-icon name="file-text" [size]="18"></app-lucide-icon>
              </div>
              <div class="flex flex-col">
                <h3 id="step9-tech-modal-title" class="text-sm font-bold text-slate-900">
                  Governed Plan Technical Details
                </h3>
                <span class="text-xs text-slate-500 font-normal">
                  Canonical compilation artifact &amp; cryptographic governance proofs
                </span>
              </div>
            </div>

            <button
              type="button"
              (click)="store.closeTechnicalModal()"
              class="w-8 h-8 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-100 flex items-center justify-center transition-colors cursor-pointer"
              title="Close Dialog">
              <app-lucide-icon name="x" [size]="16"></app-lucide-icon>
            </button>
          </div>

          <!-- Modal Body Grid -->
          <div class="flex flex-col gap-4 text-xs">
            
            <!-- Section 1: Governed Plan Fingerprint Card -->
            <div class="rounded-lg bg-slate-50 border border-slate-200 p-3.5 flex flex-col gap-2">
              <div class="flex items-center justify-between">
                <span class="text-[11px] font-bold uppercase tracking-wider text-slate-500">
                  Cryptographic Plan Fingerprint
                </span>
                <span class="px-2 py-0.5 rounded text-[10px] font-bold font-mono bg-emerald-50 text-emerald-700 border border-emerald-200">
                  {{ tech().governanceSealStatus }}
                </span>
              </div>

              <div class="flex items-center justify-between gap-2 bg-white border border-slate-200 rounded-md px-3 py-2">
                <span class="font-mono text-[11px] text-slate-700 break-all select-all">
                  {{ tech().planFingerprint }}
                </span>
                <button
                  type="button"
                  (click)="copyFingerprint()"
                  class="h-6 px-2 text-[11px] font-medium text-slate-600 hover:text-slate-900 bg-slate-50 hover:bg-slate-100 border border-slate-200 rounded flex items-center gap-1 cursor-pointer transition-colors shrink-0"
                  [title]="copied() ? 'Copied to clipboard' : 'Copy fingerprint'">
                  <app-lucide-icon [name]="copied() ? 'check' : 'copy'" [size]="12" [class]="copied() ? 'text-emerald-600' : 'text-slate-500'"></app-lucide-icon>
                  <span>{{ copied() ? 'Copied' : 'Copy' }}</span>
                </button>
              </div>
            </div>

            <!-- Section 2: 2-Column Metadata Grid -->
            <div class="grid grid-cols-2 gap-3">
              
              <div class="flex flex-col gap-1 p-2.5 rounded-lg bg-slate-50 border border-slate-200">
                <span class="text-[10px] font-bold uppercase tracking-wider text-slate-400">Migration ID</span>
                <span class="font-mono text-xs font-semibold text-slate-800 truncate">{{ tech().migrationId }}</span>
              </div>

              <div class="flex flex-col gap-1 p-2.5 rounded-lg bg-slate-50 border border-slate-200">
                <span class="text-[10px] font-bold uppercase tracking-wider text-slate-400">Plan Identifier &amp; Revision</span>
                <span class="font-mono text-xs font-semibold text-slate-800 truncate">{{ tech().planId }} (Rev {{ tech().planRevision }})</span>
              </div>

              <div class="flex flex-col gap-1 p-2.5 rounded-lg bg-slate-50 border border-slate-200">
                <span class="text-[10px] font-bold uppercase tracking-wider text-slate-400">Policy Binding</span>
                <span class="text-xs font-medium text-slate-800">{{ tech().policyBinding }}</span>
              </div>

              <div class="flex flex-col gap-1 p-2.5 rounded-lg bg-slate-50 border border-slate-200">
                <span class="text-[10px] font-bold uppercase tracking-wider text-slate-400">Execution Strategy</span>
                <span class="text-xs font-medium text-slate-800">{{ tech().executionMode }}</span>
              </div>

            </div>

            <!-- Section 3: Diagnostic Evidence -->
            <div class="flex flex-col gap-2 pt-2 border-t border-slate-200">
              <span class="text-[11px] font-bold uppercase tracking-wider text-slate-500">
                Canonical Verification Evidence
              </span>

              <div class="flex flex-col gap-1.5 text-[11px] text-slate-600 font-medium">
                <div class="flex items-center gap-2">
                  <app-lucide-icon name="shield-check" [size]="13" class="text-emerald-600 shrink-0"></app-lucide-icon>
                  <span>{{ tech().structuralRiskEvidence }}</span>
                </div>
                <div class="flex items-center gap-2">
                  <app-lucide-icon name="database" [size]="13" class="text-blue-600 shrink-0"></app-lucide-icon>
                  <span>{{ tech().scaleEvidence }}</span>
                </div>
              </div>
            </div>

          </div>

          <!-- Modal Footer -->
          <div class="flex items-center justify-end pt-3 border-t border-slate-200">
            <button
              type="button"
              (click)="store.closeTechnicalModal()"
              class="h-8 px-4 text-xs font-medium text-slate-700 bg-slate-100 hover:bg-slate-200 border border-slate-200 rounded-lg transition-colors cursor-pointer">
              Close Details
            </button>
          </div>

        </div>
      </div>
    }
  `
})
export class Step9TechnicalModalComponent {
  public store = inject(Step9ReviewStoreService);
  public tech = this.store.technicalDetails;
  public copied = signal<boolean>(false);

  public copyFingerprint(): void {
    const fp = this.tech().planFingerprint;
    if (typeof navigator !== 'undefined' && navigator.clipboard) {
      navigator.clipboard.writeText(fp);
      this.copied.set(true);
      setTimeout(() => this.copied.set(false), 2000);
    }
  }

  @HostListener('window:keydown', ['$event'])
  public handleKeydown(event: KeyboardEvent): void {
    if (event.key === 'Escape' && this.store.isTechnicalModalOpen()) {
      this.store.closeTechnicalModal();
    }
  }
}

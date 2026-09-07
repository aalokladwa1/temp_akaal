import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ValidationResultsService } from '../validation-results.service';
import { LucideIconComponent } from '../../../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-results-remediation-history',
  standalone: true,
  imports: [CommonModule, LucideIconComponent],
  template: `
    <section class="bg-white border border-slate-200 rounded-xl p-6 sm:p-7 shadow-2xs">
      
      <!-- Section Header -->
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-5 mb-5 border-b border-slate-100">
        <div class="flex items-center gap-2.5">
          <div class="w-8 h-8 rounded-lg bg-blue-50 border border-blue-200 flex items-center justify-center text-blue-700">
            <app-lucide-icon name="git-merge" [size]="16" />
          </div>
          <div>
            <h2 class="text-sm font-bold text-slate-900 font-heading">
              Repair &amp; Revalidation Lineage
            </h2>
            <p class="text-xs text-slate-500">
              Immutable audit history: Initial Validation → Controlled Remediation → Revalidation Run
            </p>
          </div>
        </div>

        <div class="text-xs text-slate-500 font-sans">
          Immutable Audit Record
        </div>
      </div>

      <!-- Remediation Lineage Content -->
      @if (store.remediationLineage().hasRemediationHistory) {
        
        <div class="grid grid-cols-1 md:grid-cols-3 gap-5 relative">
          
          <!-- Step 1: Initial Validation Run -->
          @if (store.remediationLineage().initialValidation; as initial) {
            <div class="p-5 rounded-xl bg-slate-50/80 border border-slate-200/90 flex flex-col gap-3 shadow-2xs">
              <div class="flex items-center justify-between">
                <span class="text-[11px] font-mono uppercase tracking-wider font-bold text-slate-500">
                  1. Initial Validation
                </span>
                <span
                  [ngClass]="initial.verdict === 'PASSED' ? 'bg-emerald-50 text-emerald-700 border-emerald-200' : 'bg-rose-50 text-rose-700 border-rose-200'"
                  class="px-2 py-0.5 text-[10px] font-bold rounded border">
                  {{ initial.verdict }}
                </span>
              </div>

              <div class="flex flex-col gap-1">
                <span class="text-xs font-mono font-bold text-slate-900">
                  {{ initial.runId }}
                </span>
                <span class="text-[11px] text-slate-500">
                  {{ initial.timestamp | date:'medium' }}
                </span>
              </div>

              <div class="pt-2 border-t border-slate-200 text-xs text-slate-700 flex items-center justify-between">
                <span class="text-slate-500">Discrepancies:</span>
                <strong class="font-mono text-rose-700">{{ initial.discrepancyCount }} detected</strong>
              </div>
            </div>
          }

          <!-- Step 2: Controlled Remediation -->
          @if (store.remediationLineage().controlledRemediation; as repair) {
            <div class="p-5 rounded-xl bg-slate-50/80 border border-slate-200/90 flex flex-col gap-3 shadow-2xs">
              <div class="flex items-center justify-between">
                <span class="text-[11px] font-mono uppercase tracking-wider font-bold text-slate-500">
                  2. Controlled Repair
                </span>
                <span
                  [ngClass]="repair.status === 'COMPLETED' ? 'bg-blue-50 text-blue-700 border-blue-200' : 'bg-amber-50 text-amber-700 border-amber-200'"
                  class="px-2 py-0.5 text-[10px] font-bold rounded border">
                  {{ repair.status }}
                </span>
              </div>

              <div class="flex flex-col gap-1">
                <span class="text-xs font-mono font-bold text-slate-900">
                  Plan: {{ repair.repairPlanId }}
                </span>
                <span class="text-[11px] text-slate-600 leading-snug">
                  {{ repair.strategy }}
                </span>
              </div>

              <div class="pt-2 border-t border-slate-200 text-xs text-slate-700 flex items-center justify-between">
                <span class="text-slate-500">Operations:</span>
                <strong class="font-mono text-blue-700">{{ repair.operationsCount }} applied</strong>
              </div>
            </div>
          }

          <!-- Step 3: Revalidation Run -->
          @if (store.remediationLineage().revalidation; as reval) {
            <div class="p-5 rounded-xl bg-slate-50/80 border border-slate-200/90 flex flex-col gap-3 shadow-2xs">
              <div class="flex items-center justify-between">
                <span class="text-[11px] font-mono uppercase tracking-wider font-bold text-slate-500">
                  3. Revalidation
                </span>
                <span
                  [ngClass]="reval.verdict === 'PASSED' ? 'bg-emerald-50 text-emerald-700 border-emerald-200' : 'bg-rose-50 text-rose-700 border-rose-200'"
                  class="px-2 py-0.5 text-[10px] font-bold rounded border">
                  {{ reval.verdict }}
                </span>
              </div>

              <div class="flex flex-col gap-1">
                <span class="text-xs font-mono font-bold text-slate-900">
                  {{ reval.runId }}
                </span>
                <span class="text-[11px] text-slate-500">
                  {{ reval.completedAt | date:'medium' }}
                </span>
              </div>

              <div class="pt-2 border-t border-slate-200 text-xs text-slate-700 flex items-center justify-between">
                <span class="text-slate-500">Remaining Delta:</span>
                <strong
                  [ngClass]="reval.remainingDiscrepancies === 0 ? 'text-emerald-700' : 'text-rose-700'"
                  class="font-mono">
                  {{ reval.remainingDiscrepancies }} findings
                </strong>
              </div>
            </div>
          }

        </div>

      } @else {
        
        <!-- Standby / No Remediation History -->
        <div class="p-5 rounded-xl bg-slate-50/60 border border-slate-200/80 text-center flex flex-col items-center justify-center gap-2 text-slate-500 py-8">
          <app-lucide-icon name="git-merge" [size]="24" class="text-slate-400" />
          <span class="text-xs font-medium text-slate-700">No Remediation Lineage</span>
          <p class="text-[11px] text-slate-500 max-w-md">
            This mission has not undergone controlled remediation or repair cycles. Results reflect the direct execution baseline.
          </p>
        </div>

      }

    </section>
  `
})
export class ResultsRemediationHistoryComponent {
  readonly store = inject(ValidationResultsService);
}

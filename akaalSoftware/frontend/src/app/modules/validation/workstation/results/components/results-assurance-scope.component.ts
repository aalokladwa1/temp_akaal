import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ValidationResultsService } from '../validation-results.service';
import { LucideIconComponent } from '../../../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-results-assurance-scope',
  standalone: true,
  imports: [CommonModule, LucideIconComponent],
  template: `
    <section class="bg-white border border-slate-200 rounded-xl p-6 sm:p-7 shadow-2xs">
      
      <!-- Section Header -->
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-5 mb-5 border-b border-slate-100">
        <div class="flex items-center gap-2.5">
          <div class="w-8 h-8 rounded-lg bg-emerald-50 border border-emerald-200 flex items-center justify-center text-emerald-700">
            <app-lucide-icon name="shield-check" [size]="16" />
          </div>
          <div>
            <h2 class="text-sm font-bold text-slate-900 font-heading">
              Assurance &amp; Proof Framework Results
            </h2>
            <p class="text-xs text-slate-500">
              Evaluated outcome across the 4 canonical verification tiers (Validation #11 Authority)
            </p>
          </div>
        </div>

        <div class="text-xs text-slate-500 font-sans">
          Deterministic 4-Tier Evaluation
        </div>
      </div>

      <!-- Tiers Table / Structured List -->
      <div class="border border-slate-200 rounded-xl overflow-hidden shadow-2xs">
        <div class="overflow-x-auto">
          <table class="w-full text-left border-collapse text-xs">
            <thead>
              <tr class="bg-slate-50/80 border-b border-slate-200 text-slate-600 font-semibold">
                <th class="py-3.5 px-4.5 w-16 font-mono text-[11px] uppercase tracking-wider">Tier</th>
                <th class="py-3.5 px-4.5 min-w-[220px]">Assurance Level</th>
                <th class="py-3.5 px-4.5 min-w-[180px]">Evaluated Scope</th>
                <th class="py-3.5 px-4.5 w-32">Proof Status</th>
                <th class="py-3.5 px-4.5 min-w-[280px]">Verification Details</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-200/80 text-slate-700">
              @for (tier of store.assuranceTiers(); track tier.level) {
                <tr class="hover:bg-slate-50/50 transition-colors">
                  
                  <!-- Tier Number -->
                  <td class="py-4 px-4.5 font-mono font-bold text-slate-500">
                    #0{{ tier.tierNumber }}
                  </td>

                  <!-- Tier Level & Description -->
                  <td class="py-4 px-4.5">
                    <div class="flex flex-col gap-1">
                      <span class="font-bold text-slate-900 text-xs font-heading">
                        {{ tier.title }}
                      </span>
                      <span class="text-[11px] text-slate-500 leading-snug">
                        {{ tier.description }}
                      </span>
                    </div>
                  </td>

                  <!-- Evaluated Scope -->
                  <td class="py-4 px-4.5 font-mono text-[11px] text-slate-800">
                    {{ tier.evaluatedScopeSummary }}
                  </td>

                  <!-- Proof Status Badge -->
                  <td class="py-4 px-4.5">
                    <span
                      [ngClass]="{
                        'bg-emerald-50 text-emerald-700 border-emerald-200': tier.status === 'PASSED',
                        'bg-rose-50 text-rose-700 border-rose-200': tier.status === 'FAILED',
                        'bg-slate-100 text-slate-600 border-slate-200': tier.status === 'NOT_EVALUATED',
                        'bg-amber-50 text-amber-700 border-amber-200': tier.status === 'SKIPPED'
                      }"
                      class="inline-flex items-center gap-1.5 px-2.5 py-1 text-[11px] font-bold rounded-md border tracking-wide whitespace-nowrap">
                      @if (tier.status === 'PASSED') {
                        <app-lucide-icon name="check-circle" [size]="12" class="text-emerald-600" />
                      } @else if (tier.status === 'FAILED') {
                        <app-lucide-icon name="alert-triangle" [size]="12" class="text-rose-600" />
                      } @else if (tier.status === 'SKIPPED') {
                        <app-lucide-icon name="minus-circle" [size]="12" class="text-amber-600" />
                      } @else {
                        <app-lucide-icon name="clock" [size]="12" class="text-slate-400" />
                      }
                      <span>{{ tier.status }}</span>
                    </span>
                  </td>

                  <!-- Details & Note -->
                  <td class="py-4 px-4.5">
                    <div class="flex flex-col gap-1 text-slate-600 leading-relaxed text-xs">
                      <span>{{ tier.details }}</span>
                      @if (tier.note) {
                        <span class="text-[11px] text-slate-500 italic">{{ tier.note }}</span>
                      }
                    </div>
                  </td>

                </tr>
              }
            </tbody>
          </table>
        </div>
      </div>

    </section>
  `
})
export class ResultsAssuranceScopeComponent {
  readonly store = inject(ValidationResultsService);
}

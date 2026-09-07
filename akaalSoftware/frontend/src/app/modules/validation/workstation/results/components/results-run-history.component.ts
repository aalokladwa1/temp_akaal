import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ValidationResultsService } from '../validation-results.service';
import { LucideIconComponent } from '../../../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-results-run-history',
  standalone: true,
  imports: [CommonModule, LucideIconComponent],
  template: `
    <section class="bg-white border border-slate-200 rounded-xl p-6 sm:p-7 shadow-2xs">
      
      <!-- Section Header -->
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-5 mb-5 border-b border-slate-100">
        <div class="flex items-center gap-2.5">
          <div class="w-8 h-8 rounded-lg bg-blue-50 border border-blue-200 flex items-center justify-center text-blue-700">
            <app-lucide-icon name="history" [size]="16" />
          </div>
          <div>
            <h2 class="text-sm font-bold text-slate-900 font-heading">
              Mission Execution History
            </h2>
            <p class="text-xs text-slate-500">
              Chronological log of validation execution runs and revalidations
            </p>
          </div>
        </div>

        @if (store.runs().length > 0) {
          <div class="text-xs text-slate-500 font-mono">
            {{ store.runs().length }} runs recorded
          </div>
        }
      </div>

      <!-- Runs Table -->
      @if (store.runs().length > 0) {
        
        <div class="border border-slate-200 rounded-xl overflow-hidden shadow-2xs">
          <!-- Local horizontal scroll strictly contained within table viewport (Directive #34) -->
          <div class="overflow-x-auto">
            <table class="w-full text-left border-collapse text-xs">
              <thead>
                <tr class="bg-slate-50/80 border-b border-slate-200 text-slate-600 font-semibold">
                  <th class="py-3.5 px-4.5 min-w-[140px] font-mono text-[11px] uppercase tracking-wider">Run ID</th>
                  <th class="py-3.5 px-4.5 min-w-[120px]">Trigger</th>
                  <th class="py-3.5 px-4.5 min-w-[160px]">Executed At</th>
                  <th class="py-3.5 px-4.5 min-w-[100px]">Runtime</th>
                  <th class="py-3.5 px-4.5 min-w-[90px]">Mode</th>
                  <th class="py-3.5 px-4.5 min-w-[110px]">Verdict</th>
                  <th class="py-3.5 px-4.5 min-w-[110px]">Objects</th>
                  <th class="py-3.5 px-4.5 min-w-[110px]">Unresolved</th>
                  <th class="py-3.5 px-4.5 text-right w-24">Action</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-slate-200/80 text-slate-700">
                @for (run of store.runs(); track run.runId) {
                  <tr
                    [ngClass]="{'bg-blue-50/50': store.selectedRunId() === run.runId}"
                    class="hover:bg-slate-50/50 transition-colors">
                    
                    <!-- Run ID -->
                    <td class="py-3.5 px-4.5 font-mono font-bold text-slate-900">
                      {{ run.runId }}
                    </td>

                    <!-- Trigger -->
                    <td class="py-3.5 px-4.5">
                      <span class="px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase bg-slate-100 text-slate-700 border border-slate-200">
                        {{ run.trigger }}
                      </span>
                    </td>

                    <!-- Executed At -->
                    <td class="py-3.5 px-4.5 text-slate-600 font-sans text-xs">
                      {{ run.startedAt | date:'medium' }}
                    </td>

                    <!-- Runtime -->
                    <td class="py-3.5 px-4.5 font-mono text-slate-700">
                      {{ run.durationFormatted }}
                    </td>

                    <!-- Mode -->
                    <td class="py-3.5 px-4.5 font-mono text-xs font-semibold text-slate-800">
                      {{ run.comparisonMode }}
                    </td>

                    <!-- Verdict -->
                    <td class="py-3.5 px-4.5">
                      <span
                        [ngClass]="{
                          'bg-emerald-50 text-emerald-700 border-emerald-200': run.verdict === 'PASSED',
                          'bg-rose-50 text-rose-700 border-rose-200': run.verdict === 'FAILED',
                          'bg-amber-50 text-amber-700 border-amber-200': run.verdict === 'WITHHELD',
                          'bg-slate-100 text-slate-700 border-slate-200': run.verdict === 'NOT_EVALUATED'
                        }"
                        class="px-2.5 py-0.5 text-[11px] font-bold rounded-md border tracking-wide">
                        {{ run.verdict }}
                      </span>
                    </td>

                    <!-- Objects -->
                    <td class="py-3.5 px-4.5 font-mono text-slate-700">
                      {{ run.evaluatedObjectsCount !== null ? (run.evaluatedObjectsCount | number) : '—' }}
                    </td>

                    <!-- Unresolved -->
                    <td class="py-3.5 px-4.5 font-mono">
                      @if (run.unresolvedCount !== null && run.unresolvedCount > 0) {
                        <span class="text-rose-700 font-bold">{{ run.unresolvedCount | number }}</span>
                      } @else if (run.unresolvedCount === 0) {
                        <span class="text-emerald-700 font-semibold">0</span>
                      } @else {
                        <span class="text-slate-400">—</span>
                      }
                    </td>

                    <!-- Action -->
                    <td class="py-3.5 px-4.5 text-right">
                      <button
                        type="button"
                        (click)="store.selectRun(run.runId)"
                        [ngClass]="store.selectedRunId() === run.runId ? 'bg-blue-600 text-white' : 'bg-white text-slate-700 hover:bg-slate-50'"
                        class="px-2.5 py-1 text-xs font-semibold rounded-md border border-slate-200 cursor-pointer transition-colors shadow-2xs">
                        {{ store.selectedRunId() === run.runId ? 'Selected' : 'Inspect' }}
                      </button>
                    </td>

                  </tr>
                }
              </tbody>
            </table>
          </div>
        </div>

      } @else {
        
        <!-- Truthful Unavailable State (Directive #19) -->
        <div class="p-5 rounded-xl bg-slate-50/60 border border-slate-200/80 text-center flex flex-col items-center justify-center gap-2 text-slate-500 py-8">
          <app-lucide-icon name="history" [size]="24" class="text-slate-400" />
          <span class="text-xs font-medium text-slate-700">Run history is not currently available</span>
          <p class="text-[11px] text-slate-500 max-w-md">
            Historical run tracking is recorded upon durable persistence integration. Current session reflects active execution state.
          </p>
        </div>

      }

    </section>
  `
})
export class ResultsRunHistoryComponent {
  readonly store = inject(ValidationResultsService);
}

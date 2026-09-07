import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ValidationResultsService } from '../validation-results.service';
import { LucideIconComponent } from '../../../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-results-source-target-proof',
  standalone: true,
  imports: [CommonModule, LucideIconComponent],
  template: `
    <section class="bg-white border border-slate-200 rounded-xl p-6 sm:p-7 shadow-2xs">
      
      <!-- Section Header -->
      <div class="flex items-center justify-between pb-5 mb-5 border-b border-slate-100">
        <div class="flex items-center gap-2.5">
          <div class="w-8 h-8 rounded-lg bg-blue-50 border border-blue-200 flex items-center justify-center text-blue-600">
            <app-lucide-icon name="git-compare" [size]="16" />
          </div>
          <div>
            <h2 class="text-sm font-bold text-slate-900 font-heading">
              Evaluated Topology &amp; Comparison Proof
            </h2>
            <p class="text-xs text-slate-500">
              Source and Target endpoint comparison context under governed consistency window
            </p>
          </div>
        </div>

        <div class="hidden sm:flex items-center gap-2 text-xs text-slate-500">
          <span class="w-2 h-2 rounded-full bg-blue-500"></span>
          <span>Consistent Read Boundary</span>
        </div>
      </div>

      <!-- 3-Column Source <-> Mode Visual <-> Target Grid -->
      <div class="grid grid-cols-1 md:grid-cols-11 gap-4 lg:gap-6 items-center">
        
        <!-- Source Endpoint Card (Cols 1-5) -->
        <div class="md:col-span-5 bg-slate-50/80 border border-slate-200/90 rounded-xl p-5 flex flex-col gap-3.5 shadow-2xs">
          
          <div class="flex items-start justify-between gap-3">
            <div class="flex flex-wrap items-center gap-2 min-w-0 flex-1">
              <span class="px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase tracking-wider bg-blue-100 text-blue-800 border border-blue-200 shrink-0">
                SOURCE
              </span>
              <span class="text-xs font-semibold text-slate-900 font-heading break-words">
                {{ store.source().provider }}
              </span>
            </div>
            @if (store.source().objectCount !== undefined && store.source().objectCount !== null) {
              <span class="text-xs text-slate-500 font-mono shrink-0 whitespace-nowrap">
                {{ store.source().objectCount }} objects
              </span>
            }
          </div>

          <div class="flex flex-col gap-1.5 pt-1">
            <div class="text-xs text-slate-500 font-sans">Instance / Identifier:</div>
            <div class="text-xs font-mono font-bold text-slate-900 break-all bg-white px-3 py-2 rounded-lg border border-slate-200/80">
              {{ store.source().label }}
            </div>
          </div>

          <div class="flex items-center gap-2 text-xs text-slate-500 pt-0.5 min-w-0">
            <app-lucide-icon name="server" [size]="13" class="text-slate-400 shrink-0" />
            <span class="font-mono text-[11px] text-slate-600 break-all" [title]="store.source().host">
              {{ store.source().host }}
            </span>
          </div>

        </div>

        <!-- Center: Canonical Comparison Mode Bridge (Cols 6) -->
        <div class="md:col-span-1 flex flex-col items-center justify-center py-2 md:py-0">
          
          <div class="relative flex md:flex-col items-center justify-center gap-2">
            <!-- Mode Node (Shows SYNC / ASYNC / UNKNOWN, NEVER Pass/Fail) -->
            <div
              [title]="'Canonical Comparison Mode: ' + store.comparisonMode()"
              class="w-14 h-14 rounded-full bg-white border-2 border-blue-500 text-blue-700 flex flex-col items-center justify-center shadow-xs">
              <app-lucide-icon name="refresh-cw" [size]="14" class="text-blue-600" />
              <span class="text-[9px] font-mono font-bold tracking-tight">
                {{ store.comparisonMode() }}
              </span>
            </div>
          </div>

        </div>

        <!-- Target Endpoint Card (Cols 7-11) -->
        <div class="md:col-span-5 bg-slate-50/80 border border-slate-200/90 rounded-xl p-5 flex flex-col gap-3.5 shadow-2xs">
          
          <div class="flex items-start justify-between gap-3">
            <div class="flex flex-wrap items-center gap-2 min-w-0 flex-1">
              <span class="px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase tracking-wider bg-purple-100 text-purple-800 border border-purple-200 shrink-0">
                TARGET
              </span>
              <span class="text-xs font-semibold text-slate-900 font-heading break-words">
                {{ store.target().provider }}
              </span>
            </div>
            @if (store.target().objectCount !== undefined && store.target().objectCount !== null) {
              <span class="text-xs text-slate-500 font-mono shrink-0 whitespace-nowrap">
                {{ store.target().objectCount }} objects
              </span>
            }
          </div>

          <div class="flex flex-col gap-1.5 pt-1">
            <div class="text-xs text-slate-500 font-sans">Instance / Identifier:</div>
            <div class="text-xs font-mono font-bold text-slate-900 break-all bg-white px-3 py-2 rounded-lg border border-slate-200/80">
              {{ store.target().label }}
            </div>
          </div>

          <div class="flex items-center gap-2 text-xs text-slate-500 pt-0.5 min-w-0">
            <app-lucide-icon name="database" [size]="13" class="text-slate-400 shrink-0" />
            <span class="font-mono text-[11px] text-slate-600 break-all" [title]="store.target().host">
              {{ store.target().host }}
            </span>
          </div>

        </div>

      </div>

      <!-- Bottom Topology Context Bar -->
      <div class="mt-5 p-3.5 rounded-lg bg-slate-50 border border-slate-200/80 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 text-xs text-slate-600">
        <div class="flex items-center gap-2">
          <app-lucide-icon name="info" [size]="14" class="text-slate-500 shrink-0" />
          <span>
            Temporal Model:
            <strong class="text-slate-800 font-medium">
              {{ store.temporalModel() === 'CONSISTENT_STATE' ? 'Consistent-State Validation' : store.temporalModel() === 'CONTINUOUS' ? 'Continuous Validation' : 'Unspecified Model' }}
            </strong>
          </span>
        </div>
        <div class="text-[11px] text-slate-500 font-sans">
          Comparison Mode (<strong class="font-mono text-slate-700">{{ store.comparisonMode() }}</strong>) indicates synchronization relationship semantics, decoupled from Validation #11 verdict.
        </div>
      </div>

    </section>
  `
})
export class ResultsSourceTargetProofComponent {
  readonly store = inject(ValidationResultsService);
}

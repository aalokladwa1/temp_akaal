import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ValidationWorkstationService } from '../validation-workstation.service';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';
import { CoverageRow } from '../validation-workstation.models';

@Component({
  selector: 'app-workstation-coverage-panel',
  standalone: true,
  imports: [CommonModule, LucideIconComponent],
  template: `
    <section class="bg-white border border-slate-200 rounded-xl p-6 shadow-2xs flex flex-col gap-5">
      
      <!-- Panel Header -->
      <div class="flex items-center justify-between border-b border-slate-100 pb-3 flex-wrap gap-2">
        <div class="flex items-center gap-2">
          <app-lucide-icon name="layers" [size]="16" class="text-blue-600" />
          <h2 class="text-sm font-bold text-slate-900 tracking-tight font-heading">
            Scope Coverage &amp; Finding Localization
          </h2>
        </div>
        <span class="text-[11px] text-slate-500">
          Decoupled Execution Progress &amp; Divergence Tiers
        </span>
      </div>

      <!-- Scope Coverage Matrix Table -->
      <div class="overflow-x-auto rounded-lg border border-slate-200">
        <table class="w-full text-left border-collapse text-xs">
          
          <!-- Column Headers -->
          <thead>
            <tr class="bg-slate-50/80 border-b border-slate-200 text-slate-500 text-[11px] uppercase tracking-wider font-semibold">
              <th class="py-3 px-4">Dimension</th>
              <th class="py-3 px-4 text-right">In Scope</th>
              <th class="py-3 px-4 text-right">Evaluated</th>
              <th class="py-3 px-4 text-right">Remaining</th>
              <th class="py-3 px-4 text-right text-rose-700">Differences Detected</th>
              <th class="py-3 px-4 text-right text-amber-700">Inconclusive</th>
            </tr>
          </thead>

          <!-- Table Body -->
          <tbody class="divide-y divide-slate-100">
            @for (row of store.state().coverage; track row.dimension) {
              <tr class="hover:bg-slate-50/50 transition-colors">
                
                <!-- Dimension Name -->
                <td class="py-3.5 px-4 font-bold text-slate-900 flex items-center gap-2">
                  <span class="w-2 h-2 rounded-sm bg-blue-600"></span>
                  <span>{{ row.dimension }}</span>
                </td>

                <!-- In Scope -->
                <td class="py-3.5 px-4 text-right font-mono font-medium text-slate-700">
                  {{ formatNumber(row.inScope) }}
                </td>

                <!-- Evaluated -->
                <td class="py-3.5 px-4 text-right font-mono font-bold text-blue-700">
                  {{ formatNumber(row.evaluated) }}
                </td>

                <!-- Remaining -->
                <td class="py-3.5 px-4 text-right font-mono text-slate-500">
                  {{ formatNumber(row.remaining) }}
                </td>

                <!-- Differences Detected -->
                <td class="py-3.5 px-4 text-right font-mono font-bold"
                    [class.text-rose-700]="row.differencesDetected && row.differencesDetected > 0"
                    [class.text-slate-400]="!row.differencesDetected || row.differencesDetected === 0">
                  {{ formatDiffNumber(row.differencesDetected) }}
                </td>

                <!-- Inconclusive -->
                <td class="py-3.5 px-4 text-right font-mono font-medium"
                    [class.text-amber-700]="row.inconclusive && row.inconclusive > 0"
                    [class.text-slate-400]="!row.inconclusive || row.inconclusive === 0">
                  {{ formatDiffNumber(row.inconclusive) }}
                </td>

              </tr>
            }
          </tbody>
        </table>
      </div>

      <!-- Semantic Execution Context Ribbon -->
      <div class="pt-2">
        <span class="text-[10px] font-bold text-slate-400 uppercase tracking-wider block mb-3">
          Semantic Execution Policy &amp; Rules
        </span>
        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          
          <div class="p-3 rounded-lg bg-slate-50/70 border border-slate-200/80 flex flex-col gap-1">
            <span class="text-[10px] font-semibold text-slate-400 uppercase">Sampling Strategy</span>
            <span class="text-xs font-bold text-slate-800">{{ store.state().semanticContext.samplingPolicy }}</span>
          </div>

          <div class="p-3 rounded-lg bg-slate-50/70 border border-slate-200/80 flex flex-col gap-1">
            <span class="text-[10px] font-semibold text-slate-400 uppercase">Divergence Tolerance</span>
            <span class="text-xs font-bold text-slate-800">{{ store.state().semanticContext.tolerance }}</span>
          </div>

          <div class="p-3 rounded-lg bg-slate-50/70 border border-slate-200/80 flex flex-col gap-1">
            <span class="text-[10px] font-semibold text-slate-400 uppercase">Worker Concurrency</span>
            <span class="text-xs font-bold text-slate-800">{{ store.state().semanticContext.concurrency }}</span>
          </div>

          <div class="p-3 rounded-lg bg-slate-50/70 border border-slate-200/80 flex flex-col gap-1">
            <span class="text-[10px] font-semibold text-slate-400 uppercase">Halt Condition</span>
            <span class="text-xs font-bold text-slate-800">{{ store.state().semanticContext.failureThreshold }}</span>
          </div>

        </div>
      </div>

    </section>
  `
})
export class WorkstationCoveragePanelComponent {
  readonly store = inject(ValidationWorkstationService);

  formatNumber(val: number | null): string {
    if (val === null || val === undefined) return '—';
    return val.toLocaleString();
  }

  formatDiffNumber(val: number | null): string {
    if (val === null || val === undefined) return '—';
    if (val === 0) return '0 (Clean)';
    return val.toLocaleString();
  }
}

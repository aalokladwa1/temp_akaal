import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ValidationResultsService } from '../validation-results.service';
import { LucideIconComponent } from '../../../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-results-unresolved-findings',
  standalone: true,
  imports: [CommonModule, LucideIconComponent],
  template: `
    <section class="bg-white border border-slate-200 rounded-xl p-6 sm:p-7 shadow-2xs">
      
      <!-- Section Header -->
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-5 mb-5 border-b border-slate-100">
        <div class="flex items-center gap-2.5">
          <div
            [ngClass]="store.unresolvedFindings() ? 'bg-rose-50 text-rose-700 border-rose-200' : 'bg-emerald-50 text-emerald-700 border-emerald-200'"
            class="w-8 h-8 rounded-lg border flex items-center justify-center">
            <app-lucide-icon [name]="store.unresolvedFindings() ? 'alert-triangle' : 'check-circle'" [size]="16" />
          </div>
          <div>
            <h2 class="text-sm font-bold text-slate-900 font-heading">
              Unresolved Findings Summary
            </h2>
            <p class="text-xs text-slate-500">
              Discrepancy reconciliation status (Validation #11 Discrepancy Truth)
            </p>
          </div>
        </div>

        @if (store.unresolvedFindings(); as findings) {
          <button
            type="button"
            (click)="store.navigateToDiscrepancies()"
            class="h-9 px-4 rounded-lg bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold flex items-center gap-2 cursor-pointer transition-colors shadow-2xs self-start sm:self-auto">
            <span>Investigate in Discrepancies Workbench</span>
            <app-lucide-icon name="arrow-up-right" [size]="14" />
          </button>
        }
      </div>

      <!-- Findings Content -->
      @if (store.unresolvedFindings(); as findings) {
        
        <div class="flex flex-col gap-5">
          
          <!-- Key Metrics Row -->
          <div class="grid grid-cols-1 sm:grid-cols-3 gap-4">
            
            <!-- Metric 1: Total Unresolved -->
            <div class="p-4.5 rounded-xl bg-rose-50/50 border border-rose-200/80 flex flex-col gap-1.5">
              <span class="text-xs font-medium text-rose-700 font-sans">Total Unresolved Findings</span>
              <div class="text-2xl font-bold font-mono text-rose-900 tracking-tight">
                {{ findings.totalCount | number }}
              </div>
              <span class="text-[11px] text-rose-600">Discrepant rows or partition mismatches</span>
            </div>

            <!-- Metric 2: Affected Objects -->
            <div class="p-4.5 rounded-xl bg-slate-50 border border-slate-200/80 flex flex-col gap-1.5">
              <span class="text-xs font-medium text-slate-600 font-sans">Affected Objects</span>
              <div class="text-2xl font-bold font-mono text-slate-900 tracking-tight">
                {{ findings.affectedObjectsCount }}
              </div>
              <span class="text-[11px] text-slate-500">Tables or views containing differences</span>
            </div>

            <!-- Metric 3: Finding Categories -->
            <div class="p-4.5 rounded-xl bg-slate-50 border border-slate-200/80 flex flex-col gap-1.5">
              <span class="text-xs font-medium text-slate-600 font-sans">Categorization</span>
              <div class="text-2xl font-bold font-mono text-slate-900 tracking-tight">
                {{ findings.affectedCategories.length }}
              </div>
              <span class="text-[11px] text-slate-500">Distinct discrepancy classifications</span>
            </div>

          </div>

          <!-- Affected Categories & Sample Objects Box -->
          <div class="p-5 rounded-xl bg-slate-50/80 border border-slate-200/80 flex flex-col gap-3.5">
            
            <div class="flex flex-col gap-2">
              <span class="text-xs font-bold text-slate-800 font-heading">Affected Categories:</span>
              <div class="flex flex-wrap gap-2">
                @for (cat of findings.affectedCategories; track cat) {
                  <span class="px-2.5 py-1 rounded-md bg-white border border-slate-200 text-xs font-medium text-slate-700 shadow-2xs">
                    {{ cat }}
                  </span>
                }
              </div>
            </div>

            @if (findings.sampleObjects && findings.sampleObjects.length > 0) {
              <div class="flex flex-col gap-2 pt-2 border-t border-slate-200/60">
                <span class="text-xs font-bold text-slate-800 font-heading">Sample Affected Entities:</span>
                <div class="flex flex-wrap gap-2">
                  @for (obj of findings.sampleObjects; track obj) {
                    <span class="px-2.5 py-1 rounded-md bg-white border border-slate-200 text-xs font-mono text-slate-800 shadow-2xs">
                      {{ obj }}
                    </span>
                  }
                </div>
              </div>
            }

          </div>

          <!-- Direct Navigation Prompt -->
          <div class="flex items-center justify-between p-4 rounded-lg bg-blue-50/50 border border-blue-200 text-xs text-blue-900">
            <div class="flex items-center gap-2">
              <app-lucide-icon name="info" [size]="15" class="text-blue-600 shrink-0" />
              <span>Full discrepancy drill-down, column-level diffs, and remediation proposals are managed in the Discrepancies workspace.</span>
            </div>
            <button
              type="button"
              (click)="store.navigateToDiscrepancies()"
              class="font-bold text-blue-700 hover:text-blue-900 hover:underline cursor-pointer shrink-0 ml-4">
              Open Discrepancies →
            </button>
          </div>

        </div>

      } @else {
        
        <!-- Clean State: Zero Unresolved Discrepancies -->
        <div class="p-6 rounded-xl bg-emerald-50/40 border border-emerald-200 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div class="flex items-center gap-3.5">
            <div class="w-10 h-10 rounded-lg bg-emerald-100 border border-emerald-200 flex items-center justify-center text-emerald-700 shrink-0">
              <app-lucide-icon name="badge-check" [size]="20" />
            </div>
            <div class="flex flex-col gap-0.5">
              <span class="text-sm font-bold text-emerald-950 font-heading">
                Zero Unresolved Discrepancies
              </span>
              <span class="text-xs text-emerald-800">
                Validation #11 confirmed complete parity across all in-scope tables, rows, and attributes.
              </span>
            </div>
          </div>

          <div class="text-xs font-mono font-bold text-emerald-900 bg-white px-3 py-1.5 rounded-md border border-emerald-200 shadow-2xs">
            0 UNRESOLVED
          </div>
        </div>

      }

    </section>
  `
})
export class ResultsUnresolvedFindingsComponent {
  readonly store = inject(ValidationResultsService);
}

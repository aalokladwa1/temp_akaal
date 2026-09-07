import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ValidationRepairService } from '../validation-repair.service';
import { LucideIconComponent } from '../../../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-repair-selected-scope',
  standalone: true,
  imports: [CommonModule, LucideIconComponent],
  template: `
    <section class="bg-white border border-slate-200/80 rounded-xl p-6 shadow-2xs flex flex-col gap-5">
      
      <!-- Section Header -->
      <div class="flex items-center justify-between flex-wrap gap-3 pb-4 border-b border-slate-100">
        <div class="flex items-center gap-2.5">
          <div class="w-7 h-7 rounded-md bg-purple-50 border border-purple-200 flex items-center justify-center text-purple-600 shrink-0">
            <app-lucide-icon name="filter" [size]="14"></app-lucide-icon>
          </div>
          <div>
            <h2 class="text-xs font-bold text-slate-900 uppercase tracking-wider font-heading">
              1. Selected Findings Scope ({{ store.selectedScope().totalSelectedFindings }} Findings)
            </h2>
            <p class="text-[11px] text-slate-500 mt-0.5">
              Differences originating from Discrepancies &amp; Reconciliation selected for remediation review
            </p>
          </div>
        </div>

        <div class="flex items-center gap-2">
          <span class="text-[11px] font-mono text-slate-400 bg-slate-50 border border-slate-200 px-2.5 py-1 rounded-md">
            Set: {{ store.selectedScope().selectionSetId }}
          </span>
        </div>
      </div>

      <!-- Scope Content Grid (3 Columns with Ample Room) -->
      <div class="grid grid-cols-1 md:grid-cols-3 gap-5">
        
        <!-- Objects in Scope -->
        <div class="p-5 rounded-xl bg-slate-50/80 border border-slate-200/80 flex flex-col gap-2.5 shadow-2xs">
          <div class="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-slate-600 font-heading">
            <app-lucide-icon name="table" [size]="14" class="text-slate-500"></app-lucide-icon>
            <span>Affected Objects</span>
          </div>
          <div class="flex flex-wrap gap-2 mt-1">
            @for (obj of store.selectedScope().selectedObjects; track obj) {
              <span class="px-3 py-1.5 rounded-lg bg-white border border-slate-200 text-xs font-mono font-bold text-slate-900 shadow-2xs break-all leading-normal" [title]="obj">
                {{ obj }}
              </span>
            } @empty {
              <span class="text-xs text-slate-400 italic">None selected</span>
            }
          </div>
        </div>

        <!-- Target Record Keys -->
        <div class="p-5 rounded-xl bg-slate-50/80 border border-slate-200/80 flex flex-col gap-2.5 shadow-2xs">
          <div class="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-slate-600 font-heading">
            <app-lucide-icon name="key" [size]="14" class="text-slate-500"></app-lucide-icon>
            <span>Record Identity Keys</span>
          </div>
          <div class="flex flex-wrap gap-2 mt-1">
            @for (key of store.selectedScope().affectedRecordKeys; track key) {
              <span class="px-3 py-1.5 rounded-lg bg-white border border-slate-200 text-xs font-mono font-medium text-slate-800 shadow-2xs break-all leading-normal" [title]="key">
                {{ key }}
              </span>
            } @empty {
              <span class="text-xs text-slate-400 italic">None selected</span>
            }
          </div>
        </div>

        <!-- Finding Categories -->
        <div class="p-5 rounded-xl bg-slate-50/80 border border-slate-200/80 flex flex-col gap-2.5 shadow-2xs">
          <div class="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-slate-600 font-heading">
            <app-lucide-icon name="file-diff" [size]="14" class="text-slate-500"></app-lucide-icon>
            <span>Discrepancy Categories</span>
          </div>
          <div class="flex flex-wrap gap-2 mt-1">
            @for (cat of store.selectedScope().findingCategories; track cat) {
              <span class="px-3 py-1.5 rounded-lg text-xs font-bold uppercase tracking-wider bg-rose-50 border border-rose-200 text-rose-700 flex items-center gap-2 shadow-2xs">
                <app-lucide-icon [name]="getCategoryIcon(cat)" [size]="13"></app-lucide-icon>
                <span>{{ formatCategory(cat) }}</span>
              </span>
            } @empty {
              <span class="text-xs text-slate-400 italic">None</span>
            }
          </div>
        </div>

      </div>

      <!-- Selection Policy Law Guard (Full Width Breathing Room) -->
      <div class="p-4.5 sm:p-5 rounded-xl bg-amber-50/70 border border-amber-200/80 flex items-start gap-3.5 text-xs text-amber-900 shadow-2xs">
        <div class="shrink-0 mt-0.5 text-amber-600">
          <app-lucide-icon name="shield-alert" [size]="18"></app-lucide-icon>
        </div>
        <div class="flex flex-col gap-1">
          <span class="font-bold uppercase tracking-wider text-xs text-amber-800 font-heading">
            Selection &ne; Eligibility Law
          </span>
          <p class="text-xs leading-relaxed text-amber-900/90 font-normal">
            A finding being selected does not grant repair eligibility. Target mutation requires canonical proposal compilation, risk evaluation, and governance authorization before dispatch.
          </p>
        </div>
      </div>

    </section>
  `
})
export class RepairSelectedScopeComponent {
  readonly store = inject(ValidationRepairService);

  formatCategory(cat: string): string {
    switch (cat) {
      case 'VALUE_DIFFERENCE': return 'Value Difference';
      case 'MISSING_ON_TARGET': return 'Missing on Target';
      case 'EXTRA_ON_TARGET': return 'Extra on Target';
      case 'STRUCTURAL_DIFFERENCE': return 'Schema Difference';
      case 'CARDINALITY_DIFFERENCE': return 'Cardinality Difference';
      default: return cat.replace(/_/g, ' ');
    }
  }

  getCategoryIcon(cat: string): string {
    switch (cat) {
      case 'VALUE_DIFFERENCE': return 'file-diff';
      case 'MISSING_ON_TARGET': return 'minus-square';
      case 'EXTRA_ON_TARGET': return 'plus-square';
      case 'STRUCTURAL_DIFFERENCE': return 'table-properties';
      case 'CARDINALITY_DIFFERENCE': return 'binary';
      default: return 'alert-circle';
    }
  }
}

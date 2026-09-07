import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ValidationDiscrepanciesService } from '../validation-discrepancies.service';
import { DiscrepancyItem, DiscrepancyCategory, DiscrepancyProofTier, ReconciliationState } from '../validation-discrepancies.models';
import { LucideIconComponent } from '../../../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-discrepancies-table',
  standalone: true,
  imports: [CommonModule, LucideIconComponent],
  template: `
    <div class="bg-white border border-slate-200/80 rounded-xl shadow-2xs flex flex-col flex-1 min-w-0 max-w-full overflow-hidden">
      
      <!-- Table Header Bar -->
      <div class="p-5 border-b border-slate-100 flex items-center justify-between flex-wrap gap-3">
        <div class="flex items-center gap-2.5">
          <div class="w-7 h-7 rounded-md bg-blue-50 border border-blue-200 flex items-center justify-center text-blue-600 shrink-0">
            <app-lucide-icon name="list-tree" [size]="14"></app-lucide-icon>
          </div>
          <h3 class="text-xs font-bold text-slate-900 uppercase tracking-wider font-heading">
            Discrepancy Findings ({{ store.filteredItems().length }} Displayed)
          </h3>
        </div>

        <!-- Filter context breadcrumb if object or partition selected -->
        @if (store.selectedObjectFilter()) {
          <div class="flex items-center gap-1.5 text-xs text-slate-600 bg-slate-50 border border-slate-200 px-3 py-1 rounded-lg">
            <span class="text-slate-400">Scoped to:</span>
            <span class="font-mono font-bold text-slate-900">{{ store.selectedObjectFilter() }}</span>
            @if (store.selectedPartitionFilter()) {
              <span class="text-slate-400">/</span>
              <span class="font-mono text-slate-700">{{ store.selectedPartitionFilter() }}</span>
            }
          </div>
        }
      </div>

      <!-- Table Viewport (Table-Local Scroll Viewport with Sticky Header) -->
      <div class="overflow-x-auto overflow-y-auto max-h-[380px] min-w-0 max-w-full relative">
        <table class="w-full text-left text-xs border-collapse">
          <thead class="sticky top-0 z-10 bg-slate-50 border-b border-slate-200 text-[10.5px] font-bold text-slate-500 uppercase tracking-wider shadow-2xs">
            <tr>
              <th class="py-3.5 px-4 w-12 text-center bg-slate-50">#</th>
              <th class="py-3.5 px-4.5 min-w-[190px] bg-slate-50">
                <div class="flex items-center gap-1.5">
                  <app-lucide-icon name="database" [size]="12" class="text-slate-400"></app-lucide-icon>
                  <span>Object / Scope</span>
                </div>
              </th>
              <th class="py-3.5 px-4.5 min-w-[190px] bg-slate-50">
                <div class="flex items-center gap-1.5">
                  <app-lucide-icon name="key" [size]="12" class="text-slate-400"></app-lucide-icon>
                  <span>Record Identity</span>
                </div>
              </th>
              <th class="py-3.5 px-4.5 min-w-[170px] bg-slate-50">
                <div class="flex items-center gap-1.5">
                  <app-lucide-icon name="file-diff" [size]="12" class="text-slate-400"></app-lucide-icon>
                  <span>Category</span>
                </div>
              </th>
              <th class="py-3.5 px-4.5 min-w-[150px] bg-slate-50">
                <div class="flex items-center gap-1.5">
                  <app-lucide-icon name="layers" [size]="12" class="text-slate-400"></app-lucide-icon>
                  <span>Proof Tier</span>
                </div>
              </th>
              <th class="py-3.5 px-4.5 min-w-[160px] text-right bg-slate-50">
                <div class="flex items-center justify-end gap-1.5">
                  <app-lucide-icon name="shield-check" [size]="12" class="text-slate-400"></app-lucide-icon>
                  <span>Reconciliation</span>
                </div>
              </th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-100">
            @for (item of store.filteredItems(); track item.id; let idx = $index) {
              <tr
                (click)="store.selectDiscrepancy(item.id)"
                (keydown.enter)="store.selectDiscrepancy(item.id)"
                tabindex="0"
                [class.bg-blue-50]="store.selectedDiscrepancyId() === item.id"
                [class.border-l-4]="store.selectedDiscrepancyId() === item.id"
                [class.border-l-blue-600]="store.selectedDiscrepancyId() === item.id"
                class="hover:bg-slate-50/80 cursor-pointer transition-colors focus:outline-none focus:bg-blue-50 group">
                
                <!-- Index -->
                <td class="py-3.5 px-4 text-center font-mono text-[11px] text-slate-400">
                  {{ idx + 1 }}
                </td>

                <!-- Object / Scope -->
                <td class="py-3.5 px-4.5 max-w-[220px]">
                  <div class="flex flex-col min-w-0">
                    <span class="font-mono font-bold text-slate-900 group-hover:text-blue-700 transition-colors truncate block" [title]="item.objectName">
                      {{ item.objectName }}
                    </span>
                    @if (item.partitionId) {
                      <span class="text-[11px] font-mono text-slate-500 truncate block mt-0.5" [title]="item.partitionId">
                        part: {{ item.partitionId }}
                      </span>
                    }
                  </div>
                </td>

                <!-- Record Key -->
                <td class="py-3.5 px-4.5 max-w-[200px] font-mono font-medium text-slate-800">
                  <span class="inline-block px-3 py-1.5 rounded-lg bg-slate-100 border border-slate-200 text-xs truncate max-w-full shadow-2xs" [title]="item.recordKey">
                    {{ item.recordKey }}
                  </span>
                </td>

                <!-- Category Badge -->
                <td class="py-3.5 px-4.5 min-w-[170px]">
                  <span [ngClass]="getCategoryBadgeClasses(item.category)"
                        class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold uppercase tracking-wider border shadow-2xs">
                    <app-lucide-icon [name]="getCategoryIcon(item.category)" [size]="12"></app-lucide-icon>
                    <span>{{ formatCategory(item.category) }}</span>
                  </span>
                </td>

                <!-- Proof Tier -->
                <td class="py-3.5 px-4.5 min-w-[150px] font-medium text-slate-700 text-xs">
                  {{ formatProofTier(item.proofTier) }}
                </td>

                <!-- Reconciliation State -->
                <td class="py-3.5 px-4.5 text-right min-w-[160px]">
                  <span [ngClass]="getReconciliationBadgeClasses(item.reconciliationState)"
                        class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold border shadow-2xs">
                    <app-lucide-icon [name]="getReconciliationIcon(item.reconciliationState)" [size]="12"></app-lucide-icon>
                    <span>{{ formatReconciliation(item.reconciliationState) }}</span>
                  </span>
                </td>

              </tr>
            } @empty {
              <tr>
                <td colspan="6" class="py-14 text-center text-slate-500">
                  <div class="flex flex-col items-center justify-center gap-2.5">
                    <div class="w-10 h-10 rounded-full bg-slate-100 flex items-center justify-center text-slate-400">
                      <app-lucide-icon name="search-x" [size]="20"></app-lucide-icon>
                    </div>
                    <span class="text-xs font-medium text-slate-600">No discrepancy findings match the active search/filter criteria.</span>
                    <button
                      type="button"
                      (click)="store.resetFilters()"
                      class="text-xs font-semibold text-blue-600 hover:text-blue-800 underline cursor-pointer mt-0.5">
                      Reset all filters
                    </button>
                  </div>
                </td>
              </tr>
            }
          </tbody>
        </table>
      </div>

      <!-- Scalable Pagination & Bounded Page Toolbar -->
      <div class="p-4 bg-slate-50/60 border-t border-slate-100 flex items-center justify-between text-xs text-slate-600 flex-wrap gap-4">
        
        <!-- Left: Record Bounded Range Display -->
        <div class="flex items-center gap-2">
          @if (store.summary().isLargeAggregate) {
            <span class="font-medium">
              Showing Bounded Page <span class="font-bold text-slate-900 font-mono">{{ store.state().pagination.currentPage }}</span> ({{ store.state().pagination.pageSize }} records)
              <span class="text-slate-400">·</span>
              Total Findings in Scope: <span class="font-bold font-mono text-slate-900">{{ store.summary().totalDiscrepanciesFormatted }}</span>
            </span>
          } @else {
            <span class="font-medium">
              Showing <span class="font-bold text-slate-900 font-mono">{{ store.filteredItems().length }}</span> of <span class="font-bold text-slate-900 font-mono">{{ store.summary().totalDiscrepanciesFormatted }}</span> total findings
            </span>
          }
        </div>

        <!-- Right: Pagination Buttons (Server-Backed Architecture Semantics) -->
        <div class="flex items-center gap-2">
          <button
            type="button"
            [disabled]="store.state().pagination.currentPage <= 1"
            (click)="store.setPage(store.state().pagination.currentPage - 1)"
            class="h-8 px-3.5 rounded-lg border border-slate-200 bg-white text-slate-700 hover:bg-slate-50 disabled:opacity-40 disabled:cursor-not-allowed text-xs font-semibold flex items-center gap-1.5 transition-colors cursor-pointer shadow-2xs">
            <app-lucide-icon name="chevron-left" [size]="13"></app-lucide-icon>
            <span>Previous</span>
          </button>

          <span class="px-3.5 py-1.5 font-mono text-xs font-semibold text-slate-800 bg-white border border-slate-200 rounded-lg shadow-2xs">
            Page {{ store.state().pagination.currentPage }}
          </span>

          <button
            type="button"
            [disabled]="store.summary().totalKnownPages !== null && store.state().pagination.currentPage >= store.summary().totalKnownPages!"
            (click)="store.setPage(store.state().pagination.currentPage + 1)"
            class="h-8 px-3.5 rounded-lg border border-slate-200 bg-white text-slate-700 hover:bg-slate-50 disabled:opacity-40 disabled:cursor-not-allowed text-xs font-semibold flex items-center gap-1.5 transition-colors cursor-pointer shadow-2xs">
            <span>Next</span>
            <app-lucide-icon name="chevron-right" [size]="13"></app-lucide-icon>
          </button>
        </div>

      </div>

    </div>
  `
})
export class DiscrepanciesTableComponent {
  readonly store = inject(ValidationDiscrepanciesService);

  getCategoryBadgeClasses(cat: DiscrepancyCategory): string {
    switch (cat) {
      case 'VALUE_DIFFERENCE':
        return 'bg-rose-50 border-rose-200 text-rose-700';
      case 'MISSING_ON_TARGET':
        return 'bg-amber-50 border-amber-200 text-amber-700';
      case 'EXTRA_ON_TARGET':
        return 'bg-purple-50 border-purple-200 text-purple-700';
      case 'STRUCTURAL_DIFFERENCE':
        return 'bg-orange-50 border-orange-200 text-orange-700';
      case 'CARDINALITY_DIFFERENCE':
        return 'bg-blue-50 border-blue-200 text-blue-700';
      case 'PARTITION_FINGERPRINT':
        return 'bg-indigo-50 border-indigo-200 text-indigo-700';
      case 'UNRESOLVED_CORRESPONDENCE':
        return 'bg-yellow-50 border-yellow-200 text-yellow-800';
      case 'INCONCLUSIVE':
        return 'bg-slate-50 border-slate-200 text-slate-700';
    }
  }

  getCategoryIcon(cat: DiscrepancyCategory): string {
    switch (cat) {
      case 'VALUE_DIFFERENCE': return 'file-diff';
      case 'MISSING_ON_TARGET': return 'minus-square';
      case 'EXTRA_ON_TARGET': return 'plus-square';
      case 'STRUCTURAL_DIFFERENCE': return 'table-properties';
      case 'CARDINALITY_DIFFERENCE': return 'binary';
      case 'PARTITION_FINGERPRINT': return 'git-branch';
      case 'UNRESOLVED_CORRESPONDENCE': return 'help-circle';
      case 'INCONCLUSIVE': return 'alert-circle';
    }
  }

  formatCategory(cat: DiscrepancyCategory): string {
    switch (cat) {
      case 'VALUE_DIFFERENCE': return 'Value Difference';
      case 'MISSING_ON_TARGET': return 'Missing on Target';
      case 'EXTRA_ON_TARGET': return 'Extra on Target';
      case 'STRUCTURAL_DIFFERENCE': return 'Schema Difference';
      case 'CARDINALITY_DIFFERENCE': return 'Cardinality Difference';
      case 'PARTITION_FINGERPRINT': return 'Fingerprint Difference';
      case 'UNRESOLVED_CORRESPONDENCE': return 'Unresolved Mapping';
      case 'INCONCLUSIVE': return 'Inconclusive';
    }
  }

  formatProofTier(tier: DiscrepancyProofTier): string {
    switch (tier) {
      case 'TIER_1_STRUCTURAL': return 'Tier 1 — Structural';
      case 'TIER_2_CARDINALITY': return 'Tier 2 — Cardinality';
      case 'TIER_3_PARTITION': return 'Tier 3 — Partition';
      case 'TIER_4_ATTRIBUTE': return 'Tier 4 — Attribute';
    }
  }

  getReconciliationBadgeClasses(state: ReconciliationState): string {
    switch (state) {
      case 'UNRESOLVED':
        return 'bg-rose-50 border-rose-200 text-rose-700';
      case 'CONFIRMED_DISCREPANCY':
        return 'bg-red-50 border-red-200 text-red-800';
      case 'EXPECTED_DIFFERENCE':
        return 'bg-blue-50 border-blue-200 text-blue-700';
      case 'EXPLAINED_BY_TRANSFORMATION':
        return 'bg-emerald-50 border-emerald-200 text-emerald-800';
      case 'EXCLUDED_BY_SCOPE':
        return 'bg-slate-100 border-slate-200 text-slate-700';
      case 'INCONCLUSIVE':
        return 'bg-amber-50 border-amber-200 text-amber-800';
    }
  }

  formatReconciliation(state: ReconciliationState): string {
    switch (state) {
      case 'UNRESOLVED': return 'Unresolved';
      case 'CONFIRMED_DISCREPANCY': return 'Confirmed Discrepancy';
      case 'EXPECTED_DIFFERENCE': return 'Expected Difference';
      case 'EXPLAINED_BY_TRANSFORMATION': return 'Explained by Transformation';
      case 'EXCLUDED_BY_SCOPE': return 'Excluded by Scope';
      case 'INCONCLUSIVE': return 'Inconclusive';
    }
  }

  getReconciliationIcon(state: ReconciliationState): string {
    switch (state) {
      case 'UNRESOLVED': return 'clock';
      case 'CONFIRMED_DISCREPANCY': return 'alert-triangle';
      case 'EXPECTED_DIFFERENCE': return 'check';
      case 'EXPLAINED_BY_TRANSFORMATION': return 'git-merge';
      case 'EXCLUDED_BY_SCOPE': return 'filter-x';
      case 'INCONCLUSIVE': return 'help-circle';
    }
  }
}

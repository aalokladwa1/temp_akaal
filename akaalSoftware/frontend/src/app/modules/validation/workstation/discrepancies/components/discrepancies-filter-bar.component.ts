import { Component, inject, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ValidationDiscrepanciesService } from '../validation-discrepancies.service';
import { DiscrepancyCategory, DiscrepancyProofTier, ReconciliationState } from '../validation-discrepancies.models';
import { LucideIconComponent } from '../../../../../shared/components/lucide-icon.component';
import { CustomSelectComponent, CustomSelectOption } from '../../../../../shared/components/custom-select.component';

@Component({
  selector: 'app-discrepancies-filter-bar',
  standalone: true,
  imports: [CommonModule, FormsModule, LucideIconComponent, CustomSelectComponent],
  template: `
    <section class="bg-white border border-slate-200/80 rounded-xl p-5 shadow-2xs flex flex-col gap-4">
      
      <!-- Top Row: Primary Search & Multi-Facet Filters -->
      <div class="flex items-center justify-between gap-4 flex-wrap">
        
        <!-- Left: Search Box -->
        <div class="relative flex-1 min-w-[280px] max-w-md">
          <app-lucide-icon name="search" [size]="15" class="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400"></app-lucide-icon>
          <input
            type="text"
            [ngModel]="store.searchQuery()"
            (ngModelChange)="store.setSearchQuery($event)"
            placeholder="Search objects, records, or attributes"
            class="w-full h-10 pl-10 pr-9 bg-slate-50 border border-slate-200 rounded-lg text-xs font-medium text-slate-800 placeholder-slate-400 focus:outline-none focus:border-blue-500 focus:bg-white transition-all shadow-2xs" />
          @if (store.searchQuery()) {
            <button
              type="button"
              (click)="store.setSearchQuery('')"
              class="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 cursor-pointer p-0.5">
              <app-lucide-icon name="x" [size]="14"></app-lucide-icon>
            </button>
          }
        </div>

        <!-- Right: Differences Only Toggle & Active Reset -->
        <div class="flex items-center gap-3 shrink-0">
          
          <!-- Differences Only Toggle Button -->
          <button
            type="button"
            (click)="store.toggleShowDifferencesOnly()"
            [class.bg-blue-50]="store.showDifferencesOnly()"
            [class.text-blue-700]="store.showDifferencesOnly()"
            [class.border-blue-300]="store.showDifferencesOnly()"
            class="h-10 px-4 text-xs font-semibold rounded-lg border border-slate-200 hover:border-slate-300 bg-white text-slate-700 flex items-center gap-2 transition-colors cursor-pointer shadow-2xs">
            <app-lucide-icon [name]="store.showDifferencesOnly() ? 'eye' : 'eye-off'" [size]="14"></app-lucide-icon>
            <span>{{ store.showDifferencesOnly() ? 'Differences Only' : 'Show All Attributes' }}</span>
          </button>

          <!-- Clear / Reset Filters Button -->
          @if (store.activeFiltersCount() > 0) {
            <button
              type="button"
              (click)="store.resetFilters()"
              class="h-10 px-3.5 text-xs font-semibold rounded-lg border border-rose-200 bg-rose-50 text-rose-700 hover:bg-rose-100 flex items-center gap-1.5 transition-colors cursor-pointer shadow-2xs">
              <app-lucide-icon name="filter-x" [size]="14"></app-lucide-icon>
              <span>Reset ({{ store.activeFiltersCount() }})</span>
            </button>
          }

        </div>

      </div>

      <!-- Bottom Row: Canonical Multi-Facet Dropdown Filters -->
      <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 pt-1 border-t border-slate-100">
        
        <!-- Filter 1: Finding Category -->
        <div class="flex flex-col gap-1.5">
          <label class="text-[11px] font-bold text-slate-500 uppercase tracking-wider">
            Finding Category
          </label>
          <app-custom-select
            [options]="categoryOptions"
            [value]="store.selectedCategoryFilter()"
            (valueChange)="onCategoryChange($event)"
            size="md">
          </app-custom-select>
        </div>

        <!-- Filter 2: Proof Tier -->
        <div class="flex flex-col gap-1.5">
          <label class="text-[11px] font-bold text-slate-500 uppercase tracking-wider">
            Proof Tier
          </label>
          <app-custom-select
            [options]="proofTierOptions"
            [value]="store.selectedProofTierFilter()"
            (valueChange)="onProofTierChange($event)"
            size="md">
          </app-custom-select>
        </div>

        <!-- Filter 3: Reconciliation State -->
        <div class="flex flex-col gap-1.5">
          <label class="text-[11px] font-bold text-slate-500 uppercase tracking-wider">
            Reconciliation State
          </label>
          <app-custom-select
            [options]="reconciliationOptions"
            [value]="store.selectedReconciliationFilter()"
            (valueChange)="onReconciliationChange($event)"
            size="md">
          </app-custom-select>
        </div>

        <!-- Filter 4: Scope Object -->
        <div class="flex flex-col gap-1.5">
          <label class="text-[11px] font-bold text-slate-500 uppercase tracking-wider">
            Scope Object
          </label>
          <app-custom-select
            [options]="objectOptions()"
            [value]="store.selectedObjectFilter() || 'ALL'"
            (valueChange)="onObjectChange($event)"
            size="md">
          </app-custom-select>
        </div>

      </div>

    </section>
  `
})
export class DiscrepanciesFilterBarComponent {
  readonly store = inject(ValidationDiscrepanciesService);

  readonly categoryOptions: CustomSelectOption[] = [
    { label: 'All Categories', value: 'ALL', icon: 'layers' },
    { label: 'Value difference', value: 'VALUE_DIFFERENCE', icon: 'file-diff' },
    { label: 'Missing on target', value: 'MISSING_ON_TARGET', icon: 'file-minus' },
    { label: 'Extra on target', value: 'EXTRA_ON_TARGET', icon: 'file-plus' },
    { label: 'Structural difference', value: 'STRUCTURAL_DIFFERENCE', icon: 'database' },
    { label: 'Cardinality difference', value: 'CARDINALITY_DIFFERENCE', icon: 'hash' },
    { label: 'Partition fingerprint', value: 'PARTITION_FINGERPRINT', icon: 'fingerprint' },
    { label: 'Unresolved correspondence', value: 'UNRESOLVED_CORRESPONDENCE', icon: 'git-branch' },
    { label: 'Inconclusive', value: 'INCONCLUSIVE', icon: 'help-circle' }
  ];

  readonly proofTierOptions: CustomSelectOption[] = [
    { label: 'All Proof Tiers', value: 'ALL', icon: 'shield' },
    { label: 'Tier 1 — Structural', value: 'TIER_1_STRUCTURAL', icon: 'layout-grid' },
    { label: 'Tier 2 — Cardinality', value: 'TIER_2_CARDINALITY', icon: 'list-ordered' },
    { label: 'Tier 3 — Partition', value: 'TIER_3_PARTITION', icon: 'binary' },
    { label: 'Tier 4 — Attribute', value: 'TIER_4_ATTRIBUTE', icon: 'file-text' }
  ];

  readonly reconciliationOptions: CustomSelectOption[] = [
    { label: 'All States', value: 'ALL', icon: 'check-circle-2' },
    { label: 'Unresolved', value: 'UNRESOLVED', icon: 'clock' },
    { label: 'Confirmed discrepancy', value: 'CONFIRMED_DISCREPANCY', icon: 'alert-triangle' },
    { label: 'Expected difference', value: 'EXPECTED_DIFFERENCE', icon: 'check' },
    { label: 'Explained by transformation', value: 'EXPLAINED_BY_TRANSFORMATION', icon: 'git-merge' },
    { label: 'Excluded by scope', value: 'EXCLUDED_BY_SCOPE', icon: 'filter-x' }
  ];

  readonly objectOptions = computed<CustomSelectOption[]>(() => {
    const objs = this.store.availableObjects();
    const opts: CustomSelectOption[] = [
      { label: 'All Objects', value: 'ALL', icon: 'table' }
    ];
    objs.forEach(o => {
      opts.push({ label: o, value: o, icon: 'table' });
    });
    return opts;
  });

  onCategoryChange(val: string): void {
    this.store.setCategoryFilter(val as DiscrepancyCategory | 'ALL');
  }

  onProofTierChange(val: string): void {
    this.store.setProofTierFilter(val as DiscrepancyProofTier | 'ALL');
  }

  onReconciliationChange(val: string): void {
    this.store.setReconciliationFilter(val as ReconciliationState | 'ALL');
  }

  onObjectChange(val: string): void {
    this.store.setObjectFilter(val === 'ALL' ? null : val);
  }
}

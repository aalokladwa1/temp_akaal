import { Component, inject, Optional } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HistoryHomeService } from '../history-home.service';
import { CustomSelectComponent } from '../../../../shared/components/custom-select.component';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-history-toolbar',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    CustomSelectComponent,
    LucideIconComponent
  ],
  template: `
    <div class="flex flex-col gap-3 pb-4 border-b border-slate-200">
      
      <!-- Top Row: Inventory Title, Total Count, Active Filters -->
      <div class="flex items-center justify-between flex-wrap gap-2">
        <div class="flex items-center gap-2.5">
          <span class="text-xs font-bold text-slate-900 uppercase tracking-wider font-heading">
            Historical Executions
          </span>
          <span class="px-2 py-0.5 rounded-md text-[11px] font-bold bg-slate-100 text-slate-700 border border-slate-200 font-mono">
            {{ hs.filteredHistoryItems().length }} of {{ hs.historyItems().length }}
          </span>
          @if (hs.isFiltered()) {
            <span class="px-2 py-0.5 rounded-md text-[10.5px] font-semibold bg-blue-50 text-blue-700 border border-blue-200">
              {{ hs.activeFilterCount() }} active {{ hs.activeFilterCount() === 1 ? 'filter' : 'filters' }}
            </span>
          }
        </div>

        <!-- Right: Sort Dropdown & Text-Led Clear Filters -->
        <div class="flex items-center gap-2 flex-wrap">
          <div class="w-56">
            <app-custom-select
              [options]="hs.sortOptions"
              [value]="hs.filters().sortBy"
              (valueChange)="onSortChange($event)"
              [size]="'sm'">
            </app-custom-select>
          </div>

          @if (hs.isFiltered()) {
            <button
              type="button"
              (click)="hs.clearFilters()"
              class="h-8 px-3 rounded-md bg-slate-100 hover:bg-slate-200 active:bg-slate-300 text-slate-700 text-xs font-semibold transition-colors cursor-pointer focus:outline-none focus:ring-2 focus:ring-slate-400">
              Clear filters
            </button>
          }
        </div>
      </div>

      <!-- Filter Controls Bar -->
      <div class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-2.5">
        
        <!-- 1. Search Query -->
        <div class="relative flex items-center col-span-1 sm:col-span-2 lg:col-span-2">
          <app-lucide-icon 
            name="search" 
            [size]="14"
            class="absolute left-3 text-slate-400 pointer-events-none z-10">
          </app-lucide-icon>
          <input
            type="text"
            [ngModel]="hs.filters().searchQuery"
            (ngModelChange)="hs.setSearchQuery($event)"
            placeholder="Search migration, ID, execution, provider, operator..."
            class="w-full h-8 pl-9 pr-7 rounded-md bg-white border border-slate-300 text-xs font-medium text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all shadow-2xs"
          />
          @if (hs.filters().searchQuery) {
            <button
              type="button"
              (click)="hs.setSearchQuery('')"
              class="absolute right-2.5 text-slate-400 hover:text-slate-700 cursor-pointer">
              <app-lucide-icon name="x" [size]="13"></app-lucide-icon>
            </button>
          }
        </div>

        <!-- 2. Project Filter -->
        <div>
          <app-custom-select
            [options]="hs.projectOptions()"
            [value]="hs.filters().project"
            (valueChange)="onProjectChange($event)"
            [size]="'sm'">
          </app-custom-select>
        </div>

        <!-- 3. Mode Filter (M1-M8) -->
        <div>
          <app-custom-select
            [options]="hs.modeOptions"
            [value]="hs.filters().mode"
            (valueChange)="onModeChange($event)"
            [size]="'sm'">
          </app-custom-select>
        </div>

        <!-- 4. Outcome Filter -->
        <div>
          <app-custom-select
            [options]="hs.outcomeOptions"
            [value]="hs.filters().outcome"
            (valueChange)="onOutcomeChange($event)"
            [size]="'sm'">
          </app-custom-select>
        </div>

        <!-- 5. Validation State Filter -->
        <div>
          <app-custom-select
            [options]="hs.validationOptions"
            [value]="hs.filters().validationState"
            (valueChange)="onValidationChange($event)"
            [size]="'sm'">
          </app-custom-select>
        </div>

      </div>

    </div>
  `
})
export class HistoryToolbarComponent {
  public hs: HistoryHomeService;

  constructor(@Optional() hs?: HistoryHomeService) {
    if (hs) {
      this.hs = hs;
    } else {
      try {
        this.hs = inject(HistoryHomeService);
      } catch {
        this.hs = new HistoryHomeService();
      }
    }
  }

  public onProjectChange(val: any): void {
    this.hs.setProjectFilter(val);
  }

  public onModeChange(val: any): void {
    this.hs.setModeFilter(val);
  }

  public onOutcomeChange(val: any): void {
    this.hs.setOutcomeFilter(val);
  }

  public onValidationChange(val: any): void {
    this.hs.setValidationFilter(val);
  }

  public onSortChange(val: any): void {
    this.hs.setSort(val);
  }
}

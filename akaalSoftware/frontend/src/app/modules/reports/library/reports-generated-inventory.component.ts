import { Component, Input, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ReportsService } from '../services/reports.service';
import { ReportItemDTO, ReportCategoryKey, formatReportText } from '../models/reports.models';
import { LucideIconComponent } from '../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-reports-generated-inventory',
  standalone: true,
  imports: [CommonModule, FormsModule, LucideIconComponent],
  template: `
    <div class="flex flex-col gap-5 w-full select-none">
      
      <!-- Scoped Header (if category scoped) -->
      @if (scopedCategoryKey) {
        <div class="flex items-center justify-between gap-4 pb-4 border-b border-slate-200">
          <div class="flex items-center gap-3">
            <button
              (click)="onClearCategoryScope()"
              class="h-8 px-3 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 font-medium text-xs inline-flex items-center gap-1.5 transition-colors cursor-pointer shadow-2xs">
              <app-lucide-icon name="arrow-left" [size]="14"></app-lucide-icon>
              <span>Back to Catalog</span>
            </button>
            <div class="flex flex-col">
              <h2 class="text-base font-bold text-slate-900 font-heading">
                {{ categoryDefinition?.label || scopedCategoryKey }} Reports
              </h2>
              <p class="text-xs text-slate-500">
                {{ categoryDefinition?.description }}
              </p>
            </div>
          </div>

          <div class="text-xs text-slate-500">
            <span class="font-bold text-slate-900">{{ scopedReportsCount }}</span> reports recorded in this domain
          </div>
        </div>
      }

      <!-- Search & Filters Toolbar -->
      <div class="flex items-center justify-between gap-4 flex-wrap bg-white p-3.5 border border-slate-200 rounded-xl shadow-2xs">
        
        <!-- Search Input -->
        <div class="relative flex-1 min-w-[240px] max-w-md">
          <span class="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400">
            <app-lucide-icon name="search" [size]="14"></app-lucide-icon>
          </span>
          <input
            type="text"
            [ngModel]="service.inventorySearchQuery()"
            (ngModelChange)="onSearchChange($event)"
            placeholder="Search by title, ID, or subject..."
            class="w-full h-8 pl-8 pr-3 text-xs rounded-lg border border-slate-200 bg-slate-50/50 text-slate-800 placeholder-slate-400 focus:outline-none focus:border-blue-500 focus:bg-white transition-colors"
          />
        </div>

        <!-- Filter Dropdowns -->
        <div class="flex items-center gap-3 flex-wrap">
          
          <!-- Category Filter (only if not scoped) -->
          @if (!scopedCategoryKey) {
            <div class="flex items-center gap-1.5 text-xs text-slate-500">
              <span class="font-medium">Category:</span>
              <select
                [ngModel]="service.inventoryCategoryFilter()"
                (ngModelChange)="onCategoryFilterChange($event)"
                class="h-8 px-2.5 rounded-lg border border-slate-200 bg-slate-50/50 text-xs font-medium text-slate-700 focus:outline-none focus:border-blue-500 cursor-pointer">
                <option value="ALL">All Categories (14)</option>
                @for (cat of service.categories; track cat.key) {
                  <option [value]="cat.key">{{ cat.label }}</option>
                }
              </select>
            </div>
          }

          <!-- Outcome Filter -->
          <div class="flex items-center gap-1.5 text-xs text-slate-500">
            <span class="font-medium">Outcome:</span>
            <select
              [ngModel]="service.inventoryOutcomeFilter()"
              (ngModelChange)="onOutcomeFilterChange($event)"
              class="h-8 px-2.5 rounded-lg border border-slate-200 bg-slate-50/50 text-xs font-medium text-slate-700 focus:outline-none focus:border-blue-500 cursor-pointer">
              <option value="ALL">All Outcomes</option>
              <option value="SATISFIED">Satisfied</option>
              <option value="CONVERGED">Converged</option>
              <option value="RECONCILED">Reconciled</option>
              <option value="DEFECTS_FOUND">Defects Found</option>
              <option value="IN_PROGRESS">In Progress</option>
              <option value="BLOCKED">Blocked</option>
            </select>
          </div>

          <!-- Sort Selector -->
          <div class="flex items-center gap-1.5 text-xs text-slate-500">
            <span class="font-medium">Sort:</span>
            <select
              [ngModel]="currentSortSelection"
              (ngModelChange)="onSortChange($event)"
              class="h-8 px-2.5 rounded-lg border border-slate-200 bg-slate-50/50 text-xs font-medium text-slate-700 focus:outline-none focus:border-blue-500 cursor-pointer">
              <option value="generated_at_desc">Newest First</option>
              <option value="generated_at_asc">Oldest First</option>
              <option value="title_asc">Title (A-Z)</option>
              <option value="category_asc">Category (A-Z)</option>
            </select>
          </div>

        </div>
      </div>

      <!-- Generated Reports Table -->
      <div class="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-2xs">
        <table class="w-full text-left border-collapse">
          <thead>
            <tr class="bg-slate-50/80 border-b border-slate-200 text-[11px] font-bold text-slate-500 uppercase tracking-wider">
              <th class="py-3 px-4">Report Details</th>
              @if (!scopedCategoryKey) {
                <th class="py-3 px-4">Category</th>
              }
              <th class="py-3 px-4">Subject Target</th>
              <th class="py-3 px-4">Generated Timestamp</th>
              <th class="py-3 px-4">Outcome</th>
              <th class="py-3 px-4 text-right">Actions</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-100 text-xs">
            @if (displayedReports.length === 0) {
              <tr>
                <td [attr.colspan]="scopedCategoryKey ? 5 : 6" class="py-12 text-center text-slate-400">
                  <div class="flex flex-col items-center justify-center gap-2">
                    <app-lucide-icon name="file-text" [size]="24"></app-lucide-icon>
                    <span class="font-medium">No reports matched your active filter or search query.</span>
                  </div>
                </td>
              </tr>
            }

            @for (report of displayedReports; track report.id) {
              <tr 
                (click)="onOpenReport(report.id)"
                class="hover:bg-slate-50/80 transition-colors group cursor-pointer">
                
                <!-- Report Title & ID -->
                <td class="py-3.5 px-4">
                  <div class="flex flex-col gap-0.5 max-w-md">
                    <span 
                      class="font-semibold text-slate-900 group-hover:text-blue-600 transition-colors line-clamp-1">
                      {{ report.title }}
                    </span>
                    <span class="font-mono text-[11px] text-slate-400">{{ report.id }}</span>
                  </div>
                </td>

                <!-- Category -->
                @if (!scopedCategoryKey) {
                  <td class="py-3.5 px-4 text-slate-700 font-medium">
                    {{ report.category_label }}
                  </td>
                }

                <!-- Subject Target -->
                <td class="py-3.5 px-4">
                  <div class="flex flex-col gap-0.5">
                    <span class="font-medium text-slate-800">{{ report.subject_name }}</span>
                    <span class="text-[10px] text-slate-400 uppercase tracking-wide">{{ report.subject_type }}</span>
                  </div>
                </td>

                <!-- Generated -->
                <td class="py-3.5 px-4 font-mono text-slate-500 text-[11px]">
                  {{ report.generated_at | date:'yyyy-MM-dd HH:mm:ss' }}
                </td>

                <!-- Outcome -->
                <td class="py-3.5 px-4">
                  @if (report.outcome) {
                    <span 
                      class="px-2 py-0.5 rounded text-[10px] font-bold"
                      [ngClass]="{
                        'bg-emerald-50 text-emerald-700 border border-emerald-200': report.outcome === 'SATISFIED' || report.outcome === 'CONVERGED' || report.outcome === 'RECONCILED',
                        'bg-amber-50 text-amber-700 border border-amber-200': report.outcome === 'DEFECTS_FOUND' || report.outcome === 'IN_PROGRESS',
                        'bg-rose-50 text-rose-700 border border-rose-200': report.outcome === 'BLOCKED',
                        'bg-slate-100 text-slate-600': report.outcome === 'NOT_APPLICABLE' || report.outcome === 'UNKNOWN'
                      }">
                      {{ report.outcome }}
                    </span>
                  } @else {
                    <span class="text-slate-400 font-mono text-[11px]">—</span>
                  }
                </td>

                <!-- Actions -->
                <td class="py-3.5 px-4 text-right">
                  <div class="inline-flex items-center gap-2">
                    <button
                      (click)="$event.stopPropagation(); onOpenReport(report.id)"
                      class="h-7 px-3 rounded-lg bg-blue-600 hover:bg-blue-700 text-white font-medium text-xs transition-colors cursor-pointer shadow-2xs">
                      View
                    </button>
                    <button
                      (click)="$event.stopPropagation(); onExport(report)"
                      class="h-7 px-2.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 font-medium text-xs transition-colors cursor-pointer shadow-2xs">
                      Export
                    </button>
                  </div>
                </td>

              </tr>
            }
          </tbody>
        </table>

        <!-- Pagination Controls -->
        <div class="p-4 border-t border-slate-200 bg-slate-50/50 flex items-center justify-between text-xs text-slate-600 flex-wrap gap-4">
          <div>
            Showing <strong class="text-slate-900">{{ displayedReports.length }}</strong> of <strong class="text-slate-900">{{ totalFilteredCount }}</strong> reports
          </div>

          <div class="flex items-center gap-2">
            <button
              [disabled]="service.inventoryPageIndex() <= 1"
              (click)="onPrevPage()"
              class="px-3 py-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 disabled:opacity-40 disabled:pointer-events-none text-slate-700 font-medium cursor-pointer shadow-2xs">
              Previous
            </button>
            <span class="px-2 font-mono text-slate-700">
              Page {{ service.inventoryPageIndex() }} of {{ service.totalInventoryPages() }}
            </span>
            <button
              [disabled]="service.inventoryPageIndex() >= service.totalInventoryPages()"
              (click)="onNextPage()"
              class="px-3 py-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 disabled:opacity-40 disabled:pointer-events-none text-slate-700 font-medium cursor-pointer shadow-2xs">
              Next
            </button>
          </div>
        </div>

      </div>

    </div>
  `
})
export class ReportsGeneratedInventoryComponent {
  @Input() public scopedCategoryKey: ReportCategoryKey | null = null;

  constructor(public service: ReportsService) {}

  public get categoryDefinition() {
    return this.service.getCategoryDefinition(this.scopedCategoryKey);
  }

  public get scopedReportsCount(): number {
    if (!this.scopedCategoryKey) return 0;
    return this.service.categoryScopedReports().length;
  }

  public get displayedReports(): ReportItemDTO[] {
    if (this.scopedCategoryKey) {
      // In category-scoped mode, filter on scoped list
      const q = this.service.inventorySearchQuery().toLowerCase().trim();
      const outcome = this.service.inventoryOutcomeFilter();
      let list = this.service.categoryScopedReports();
      if (outcome !== 'ALL') {
        list = list.filter(r => r.outcome === outcome);
      }
      if (q) {
        list = list.filter(r => 
          r.title.toLowerCase().includes(q) ||
          r.id.toLowerCase().includes(q) ||
          r.subject_name.toLowerCase().includes(q)
        );
      }
      return list;
    }
    return this.service.paginatedInventoryReports();
  }

  public get totalFilteredCount(): number {
    if (this.scopedCategoryKey) {
      return this.displayedReports.length;
    }
    return this.service.filteredInventoryReports().length;
  }

  public get currentSortSelection(): string {
    return `${this.service.inventorySortField()}_${this.service.inventorySortDirection()}`;
  }

  public onSearchChange(query: string): void {
    this.service.inventorySearchQuery.set(query);
    this.service.inventoryPageIndex.set(1);
  }

  public onCategoryFilterChange(category: string): void {
    this.service.inventoryCategoryFilter.set(category);
    this.service.inventoryPageIndex.set(1);
  }

  public onOutcomeFilterChange(outcome: string): void {
    this.service.inventoryOutcomeFilter.set(outcome);
    this.service.inventoryPageIndex.set(1);
  }

  public onSortChange(selection: string): void {
    const parts = selection.split('_');
    if (parts.length >= 2) {
      const dir = parts.pop() as 'asc' | 'desc';
      const field = parts.join('_') as 'generated_at' | 'title' | 'category';
      this.service.inventorySortField.set(field);
      this.service.inventorySortDirection.set(dir);
    }
  }

  public onPrevPage(): void {
    if (this.service.inventoryPageIndex() > 1) {
      this.service.inventoryPageIndex.update(p => p - 1);
    }
  }

  public onNextPage(): void {
    if (this.service.inventoryPageIndex() < this.service.totalInventoryPages()) {
      this.service.inventoryPageIndex.update(p => p + 1);
    }
  }

  public onOpenReport(reportId: string): void {
    this.service.openReportById(reportId);
  }

  public onExport(report: ReportItemDTO): void {
    this.service.openExportModal(report);
  }

  public onClearCategoryScope(): void {
    this.service.selectedCategory.set(null);
    this.service.selectLibraryView('CATALOG');
  }
}

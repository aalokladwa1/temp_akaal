import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink, ActivatedRoute } from '@angular/router';
import { ReportsService, LibraryViewMode } from './services/reports.service';
import { ReportCategoryKey } from './models/reports.models';
import { LucideIconComponent } from '../../shared/components/lucide-icon.component';
import { ReportsCatalogComponent } from './library/reports-catalog.component';
import { ReportsGeneratedInventoryComponent } from './library/reports-generated-inventory.component';
import { ReportDetailFrameComponent } from './library/report-detail/report-detail-frame.component';
import { ReportsExportModalComponent } from './library/reports-export-modal.component';

@Component({
  selector: 'app-reports-library',
  standalone: true,
  imports: [
    CommonModule, 
    RouterLink, 
    LucideIconComponent,
    ReportsCatalogComponent,
    ReportsGeneratedInventoryComponent,
    ReportDetailFrameComponent,
    ReportsExportModalComponent
  ],
  template: `
    <div class="flex flex-col gap-6 w-full max-w-[1680px] mx-auto font-sans pb-16 select-none animate-in fade-in duration-150">
      
      <!-- Top Header & Breadcrumb (when not in detail view) -->
      @if (!service.selectedReport()) {
        <div class="flex items-start justify-between gap-6 pb-5 border-b border-slate-200 flex-wrap">
          <div class="flex flex-col gap-1">
            <div class="flex items-center gap-2">
              <a routerLink="/reports" class="text-xs font-semibold text-slate-500 hover:text-slate-800 uppercase tracking-wider font-heading transition-colors">REPORTS</a>
              <span class="text-slate-300">•</span>
              <span class="text-xs font-medium text-slate-500">SPECIALIST WORKSPACE</span>
            </div>
            <h1 class="text-2xl font-bold text-slate-900 tracking-tight font-heading">Report Library</h1>
            <p class="text-sm font-medium text-slate-600">
              Comprehensive catalog, multi-category historical search, and multi-format export across all 14 technical domains.
            </p>
          </div>

          <div class="flex items-center gap-3 pt-1">
            <a
              routerLink="/reports"
              class="h-9 px-3.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 font-medium text-xs inline-flex items-center justify-center gap-2 cursor-pointer transition-colors shadow-2xs">
              <app-lucide-icon name="arrow-left" [size]="14"></app-lucide-icon>
              <span>Back to Reports Home</span>
            </a>
          </div>
        </div>

        <!-- Library Tabs (when not viewing a specific category subview) -->
        @if (!service.selectedCategory()) {
          <div class="flex items-center gap-6 border-b border-slate-200 -mt-2">
            <button
              (click)="onSelectTab('CATALOG')"
              class="pb-3 text-xs tracking-wide transition-colors cursor-pointer"
              [ngClass]="service.activeLibraryView() === 'CATALOG' ? 'border-b-2 border-blue-600 text-blue-600 font-bold' : 'text-slate-500 hover:text-slate-800 font-medium'">
              Catalog (14 Domains)
            </button>

            <button
              (click)="onSelectTab('INVENTORY')"
              class="pb-3 text-xs tracking-wide transition-colors cursor-pointer"
              [ngClass]="service.activeLibraryView() === 'INVENTORY' ? 'border-b-2 border-blue-600 text-blue-600 font-bold' : 'text-slate-500 hover:text-slate-800 font-medium'">
              All Generated Reports
            </button>
          </div>
        }
      }

      <!-- MAIN CONTENT SWITCH -->
      
      <!-- 1. Selected Report View -->
      @if (service.selectedReport()) {
        <app-report-detail-frame [report]="service.selectedReport()!"></app-report-detail-frame>
      }

      <!-- 2. Category Subview -->
      @else if (service.selectedCategory()) {
        <app-reports-generated-inventory [scopedCategoryKey]="service.selectedCategory()"></app-reports-generated-inventory>
      }

      <!-- 3. Catalog Tab -->
      @else if (service.activeLibraryView() === 'CATALOG') {
        <app-reports-catalog></app-reports-catalog>
      }

      <!-- 4. All Inventory Tab -->
      @else if (service.activeLibraryView() === 'INVENTORY') {
        <app-reports-generated-inventory></app-reports-generated-inventory>
      }

      <!-- Export Modal Mount -->
      <app-reports-export-modal></app-reports-export-modal>

    </div>
  `
})
export class ReportsLibraryComponent implements OnInit {
  constructor(
    public service: ReportsService,
    private route: ActivatedRoute
  ) {}

  public ngOnInit(): void {
    // Check for query params (e.g. ?reportId=... or ?category=...)
    this.route.queryParams.subscribe(params => {
      if (params['reportId']) {
        this.service.openReportById(params['reportId']);
      } else if (params['category']) {
        this.service.selectCategory(params['category'] as ReportCategoryKey);
      }
    });
  }

  public onSelectTab(view: LibraryViewMode): void {
    this.service.selectLibraryView(view);
  }
}

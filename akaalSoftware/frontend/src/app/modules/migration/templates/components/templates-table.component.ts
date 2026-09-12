import { Component, inject, Optional } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { TemplatesService } from '../templates.service';
import {
  TemplateItem,
  TemplateMigrationMode,
  TemplateLifecycle,
  TemplateScope,
  TEMPLATE_MODE_DESCRIPTORS,
  ModeDescriptor
} from '../templates.models';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';
import { CustomSelectComponent } from '../../../../shared/components/custom-select.component';

@Component({
  selector: 'app-templates-table',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    LucideIconComponent,
    CustomSelectComponent
  ],
  template: `
    <div class="p-6 rounded-2xl bg-white border border-slate-200 shadow-xs flex flex-col gap-5 select-none">
      
      <!-- =============================================================== -->
      <!-- 1. INTEGRATED OPERATIONAL TOOLBAR (Sibling Aligned)             -->
      <!-- =============================================================== -->
      <div class="flex items-center justify-between pb-4 border-b border-slate-200 flex-wrap gap-3">
        
        <!-- Left: Inventory Title & Count Badge -->
        <div class="flex items-center gap-2.5">
          <span class="text-xs font-bold text-slate-900 uppercase tracking-wider font-heading">Template Inventory</span>
          <span class="px-2 py-0.5 rounded-full text-[11px] font-semibold bg-slate-100 text-slate-700 border border-slate-200 font-mono">
            {{ ts.filteredTemplates().length }}
          </span>
        </div>

        <!-- Right: Search Input + GDS Filter Dropdowns + Clear Filters Action -->
        <div class="flex items-center gap-2.5 flex-wrap">
          
          <!-- Search Input with Absolutely Positioned Search Icon -->
          <div class="relative flex items-center w-64 sm:w-72">
            <app-lucide-icon 
              name="search" 
              [size]="14"
              class="absolute left-2.5 text-slate-400 pointer-events-none z-10">
            </app-lucide-icon>
            
            <input
              type="text"
              [ngModel]="ts.filters().searchQuery"
              (ngModelChange)="ts.setSearchQuery($event)"
              placeholder="Search templates..."
              class="w-full h-8 pl-8 pr-7 rounded-md bg-white border border-slate-300 text-xs font-medium text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all shadow-2xs"
            />

            @if (ts.filters().searchQuery) {
              <button
                type="button"
                (click)="ts.setSearchQuery('')"
                class="absolute right-2 text-slate-400 hover:text-slate-700 cursor-pointer">
                <app-lucide-icon name="x" [size]="13"></app-lucide-icon>
              </button>
            }
          </div>

          <!-- Migration Mode Filter Dropdown (M1-M7 only) -->
          <div class="w-48">
            <app-custom-select
              [options]="ts.modeOptions"
              [value]="ts.filters().mode"
              (valueChange)="onModeChange($event)"
              [size]="'sm'">
            </app-custom-select>
          </div>

          <!-- Applicability Filter Dropdown -->
          <div class="w-56">
            <app-custom-select
              [options]="ts.applicabilityOptions()"
              [value]="ts.filters().applicability"
              (valueChange)="onApplicabilityChange($event)"
              [size]="'sm'">
            </app-custom-select>
          </div>

          <!-- Sort Dropdown -->
          <div class="w-44">
            <app-custom-select
              [options]="ts.sortOptions"
              [value]="ts.filters().sortBy"
              (valueChange)="onSortChange($event)"
              [size]="'sm'">
            </app-custom-select>
          </div>

          <!-- Clear Filters Button (Text-Led, No Icon Inside Action Button) -->
          @if (ts.isFiltered()) {
            <button
              type="button"
              (click)="ts.clearFilters()"
              class="h-8 px-3 rounded-md bg-slate-100 hover:bg-slate-200 active:bg-slate-300 text-slate-700 text-xs font-semibold transition-colors cursor-pointer focus:outline-none focus:ring-2 focus:ring-slate-400">
              Clear filters
            </button>
          }

        </div>

      </div>

      <!-- =============================================================== -->
      <!-- 2. FOUR CORE COLUMNS TEMPLATE TABLE                             -->
      <!-- =============================================================== -->
      <div class="overflow-x-auto overflow-y-visible">
        <table class="w-full text-left border-collapse min-w-[850px]">
          <!-- Table Header -->
          <thead>
            <tr class="border-b border-slate-200 bg-slate-50/75 text-[11px] font-bold text-slate-600 uppercase tracking-wider select-none">
              
              <!-- Column 1: Template -->
              <th scope="col" class="py-3 px-4 font-bold min-w-[320px]">
                <button
                  type="button"
                  (click)="toggleSortName()"
                  class="flex items-center gap-1.5 text-slate-600 hover:text-slate-900 focus:outline-none font-bold cursor-pointer uppercase">
                  <span>Template</span>
                  <span class="text-[10px] font-mono text-slate-400" *ngIf="ts.filters().sortBy === 'name_asc'">▲</span>
                  <span class="text-[10px] font-mono text-slate-400" *ngIf="ts.filters().sortBy === 'name_desc'">▼</span>
                </button>
              </th>

              <!-- Column 2: Migration Use -->
              <th scope="col" class="py-3 px-4 font-bold min-w-[170px]">
                <span>Migration Use</span>
              </th>

              <!-- Column 3: Applicability -->
              <th scope="col" class="py-3 px-4 font-bold min-w-[200px]">
                <span>Applicability</span>
              </th>

              <!-- Column 4: Usage -->
              <th scope="col" class="py-3 px-4 font-bold min-w-[180px]">
                <button
                  type="button"
                  (click)="toggleSortUsage()"
                  class="flex items-center gap-1.5 text-slate-600 hover:text-slate-900 focus:outline-none font-bold cursor-pointer uppercase">
                  <span>Usage</span>
                  <span class="text-[10px] font-mono text-slate-400" *ngIf="ts.filters().sortBy === 'usage_desc'">▼</span>
                </button>
              </th>

            </tr>
          </thead>

          <!-- Table Body -->
          <tbody class="divide-y divide-slate-100 text-sm text-slate-700">
            @for (tmpl of ts.filteredTemplates(); track tmpl.id) {
              <tr
                class="hover:bg-slate-50/70 transition-colors group cursor-pointer"
                (click)="onRowClick(tmpl)">
                
                <!-- Column 1: Template (Clean Name Only) -->
                <td class="py-3.5 px-4 align-middle">
                  <span class="font-semibold text-slate-900 group-hover:text-blue-600 transition-colors text-sm truncate">
                    {{ tmpl.name }}
                  </span>
                </td>

                <!-- Column 2: Migration Use (Only Name, No MN) -->
                <td class="py-3.5 px-4 align-middle whitespace-nowrap">
                  <span class="inline-flex items-center px-2.5 py-1 rounded-md text-xs font-semibold bg-slate-100 text-slate-800 border border-slate-200">
                    {{ getModeDescriptor(tmpl.mode).label }}
                  </span>
                </td>

                <!-- Column 3: Applicability (Source -> Target Clean Text) -->
                <td class="py-3.5 px-4 align-middle whitespace-nowrap">
                  <div class="text-xs font-semibold text-slate-800 flex items-center gap-1.5">
                    <span>{{ tmpl.applicability.sourceProviderName }}</span>
                    <span class="text-slate-400 font-normal">→</span>
                    <span>{{ tmpl.applicability.targetProviderName }}</span>
                  </div>
                </td>

                <!-- Column 4: Usage Context -->
                <td class="py-3.5 px-4 align-middle whitespace-nowrap">
                  @if (!tmpl.usage.isUsageKnown) {
                    <span class="text-xs text-slate-500 italic">
                      Usage unavailable
                    </span>
                  } @else if (tmpl.usage.isUnused) {
                    <span class="inline-flex items-center px-2 py-0.5 rounded-md text-[11px] font-medium bg-slate-100 text-slate-600 border border-slate-200">
                      Unused
                    </span>
                  } @else {
                    <div class="text-xs font-medium text-slate-800">
                      <strong class="font-mono font-bold text-slate-900">{{ tmpl.usage.migrationCount }}</strong> {{ tmpl.usage.migrationCount === 1 ? 'migration' : 'migrations' }}
                      <span class="text-slate-300 mx-1">•</span>
                      <strong class="font-mono font-bold text-slate-900">{{ tmpl.usage.referencedProjectCount }}</strong> {{ tmpl.usage.referencedProjectCount === 1 ? 'project' : 'projects' }}
                    </div>
                  }
                </td>

              </tr>
            }
          </tbody>
        </table>
      </div>

    </div>
  `
})
export class TemplatesTableComponent {
  public ts: TemplatesService;
  private router: Router | null;

  constructor(
    @Optional() ts?: TemplatesService,
    @Optional() router?: Router
  ) {
    if (ts) {
      this.ts = ts;
    } else {
      try {
        this.ts = inject(TemplatesService);
      } catch {
        this.ts = new TemplatesService();
      }
    }

    if (router) {
      this.router = router;
    } else {
      try {
        this.router = inject(Router);
      } catch {
        this.router = null;
      }
    }
  }

  public onModeChange(val: any): void {
    this.ts.setModeFilter(val);
  }

  public onApplicabilityChange(val: any): void {
    this.ts.setApplicabilityFilter(val);
  }

  public onSortChange(val: any): void {
    this.ts.setSort(val);
  }

  public toggleSortName(): void {
    const curr = this.ts.filters().sortBy;
    this.ts.setSort(curr === 'name_asc' ? 'name_desc' : 'name_asc');
  }

  public toggleSortUsage(): void {
    this.ts.setSort('usage_desc');
  }

  public onRowClick(tmpl: TemplateItem): void {
    const isMigrationPrefix = this.router ? this.router.url.startsWith('/migration') : true;
    const path = isMigrationPrefix
      ? `/migration/templates/${tmpl.id}`
      : `/templates/${tmpl.id}`;
    this.router?.navigate([path]);
  }

  public getModeDescriptor(mode: TemplateMigrationMode): ModeDescriptor {
    return TEMPLATE_MODE_DESCRIPTORS[mode];
  }

  public formatScope(scope: TemplateScope): string {
    switch (scope) {
      case 'ORGANIZATION':
        return 'Organization';
      case 'WORKSPACE':
        return 'Workspace';
      case 'PROJECT':
        return 'Project';
      default:
        return scope;
    }
  }

  public getLifecycleBadgeClass(lifecycle: TemplateLifecycle): string {
    switch (lifecycle) {
      case 'DRAFT':
        return 'px-1.5 py-0.5 rounded text-[10px] font-semibold bg-amber-50 text-amber-700 border border-amber-200';
      case 'DEPRECATED':
        return 'px-1.5 py-0.5 rounded text-[10px] font-semibold bg-rose-50 text-rose-700 border border-rose-200';
      case 'ARCHIVED':
        return 'px-1.5 py-0.5 rounded text-[10px] font-semibold bg-slate-100 text-slate-600 border border-slate-200';
      default:
        return 'px-1.5 py-0.5 rounded text-[10px] font-semibold bg-slate-100 text-slate-700 border border-slate-200';
    }
  }
}

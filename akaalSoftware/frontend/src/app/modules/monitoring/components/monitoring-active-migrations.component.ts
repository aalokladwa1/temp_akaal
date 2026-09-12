import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink, Router } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { MonitoringService } from '../services/monitoring.service';
import { ActiveMigrationOperationalItem, CANONICAL_MODES, CanonicalMigrationMode } from '../models/monitoring.models';
import { LucideIconComponent } from '../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-monitoring-active-migrations',
  standalone: true,
  imports: [CommonModule, RouterLink, FormsModule, LucideIconComponent],
  template: `
    <!-- Active Migrations (Section 4 - Curated Operational View) -->
    <div class="p-6 rounded-2xl bg-white border border-slate-200 shadow-2xs flex flex-col gap-4 select-none">
      
      <!-- Toolbar: Title, Count, Search -->
      <div class="flex items-center justify-between pb-3 border-b border-slate-200 flex-wrap gap-3">
        <div class="flex items-center gap-2.5">
          <app-lucide-icon name="arrow-left-right" [size]="16" class="text-blue-600"></app-lucide-icon>
          <span class="text-xs font-bold text-slate-900 uppercase tracking-wider font-heading">Active Migrations</span>
          <span class="px-2 py-0.5 rounded-md text-[11px] font-semibold bg-blue-50 text-blue-700 border border-blue-200">
            {{ ms.filteredActiveMigrations().length }}
          </span>
        </div>

        <!-- Search Input with Clear Button -->
        <div class="relative w-64 flex items-center">
          <app-lucide-icon 
            name="search" 
            [size]="14"
            class="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none">
          </app-lucide-icon>
          <input
            type="text"
            [ngModel]="ms.migrationSearchQuery()"
            (ngModelChange)="ms.migrationSearchQuery.set($event)"
            placeholder="Search active migrations..."
            class="w-full h-8 pl-9 pr-7 bg-white border border-slate-200 focus:border-blue-600 rounded-lg text-xs font-medium text-slate-900 focus:outline-none transition-all placeholder:text-slate-400 shadow-2xs"
          />
          @if (ms.migrationSearchQuery()) {
            <button 
              type="button" 
              (click)="ms.migrationSearchQuery.set('')" 
              class="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 text-xs font-bold cursor-pointer">
              &times;
            </button>
          }
        </div>
      </div>

      <!-- Content: Active Migrations Table or Calm Empty State -->
      @if (ms.filteredActiveMigrations().length === 0) {
        <div class="py-10 flex flex-col items-center justify-center text-center gap-1.5 text-slate-500">
          <app-lucide-icon name="database" [size]="28" class="text-slate-300"></app-lucide-icon>
          <span class="text-xs font-semibold text-slate-700">No active migrations match criteria</span>
          <p class="text-xs text-slate-500 font-medium">
            {{ ms.migrationSearchQuery() ? 'Try adjusting your search query.' : 'There are currently no active migration workloads running.' }}
          </p>
        </div>
      } @else {
        <div class="overflow-x-auto">
          <table class="w-full text-left border-collapse table-fixed">
            <thead>
              <tr class="bg-slate-50/80 border-b border-slate-200 text-[10px] font-bold text-slate-500 uppercase tracking-wider">
                <th class="py-3 px-4 w-[26%]">Migration</th>
                <th class="py-3 px-4 w-[24%]">Current Stage</th>
                <th class="py-3 px-4 w-[16%]">Mode</th>
                <th class="py-3 px-4 w-[20%]">Progress</th>
                <th class="py-3 px-4 w-[10%]">Health</th>
                <th class="py-3 px-3 w-[4%] text-right"></th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-100 text-xs">
              @for (m of ms.filteredActiveMigrations(); track m.id) {
                <tr 
                  (click)="navigateTo(m.deep_link_route)"
                  class="hover:bg-blue-50/40 transition-colors cursor-pointer group h-14 select-none">
                  
                  <!-- 1. Migration Name -->
                  <td class="py-3 px-4 min-w-0">
                    <span class="font-semibold text-slate-900 group-hover:text-blue-600 transition-colors truncate text-xs block">
                      {{ m.name }}
                    </span>
                  </td>

                  <!-- 2. Current Stage (Clean, No Underscores) -->
                  <td class="py-3 px-4 min-w-0">
                    <span class="text-xs font-medium text-slate-600 truncate block">
                      {{ ms.formatLabel(m.current_stage) }}
                    </span>
                  </td>

                  <!-- 3. Canonical Mode Label (Clean Name Only, No M1/M2 Tag) -->
                  <td class="py-3 px-4 whitespace-nowrap">
                    <span class="inline-flex items-center px-2.5 py-0.5 rounded-md bg-slate-100 text-slate-800 border border-slate-200 text-[11px] font-semibold">
                      {{ getModeInfo(m.mode).label }}
                    </span>
                  </td>

                  <!-- 4. Progress (Inline Bar with x% / Live) -->
                  <td class="py-3 px-4 min-w-0">
                    <div class="flex items-center gap-3 w-full max-w-[180px]">
                      <div class="flex-1 bg-slate-100 rounded-full h-1.5 overflow-hidden">
                        @if (m.progress_percent !== null && m.progress_percent !== undefined) {
                          <div class="bg-blue-600 h-1.5 rounded-full transition-all duration-300" [style.width.%]="m.progress_percent"></div>
                        } @else {
                          <div class="bg-blue-600 h-1.5 rounded-full w-2/3 animate-pulse"></div>
                        }
                      </div>
                      <span class="text-xs font-mono font-bold text-slate-800 shrink-0 tabular-nums">
                        {{ m.progress_percent !== null && m.progress_percent !== undefined ? m.progress_percent + '%' : 'Continuous' }}
                      </span>
                    </div>
                  </td>

                  <!-- 5. Health Status (Circular Dot Badge) -->
                  <td class="py-3 px-4 whitespace-nowrap">
                    @if (m.health === 'HEALTHY') {
                      <span class="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-md text-[11px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
                        <span class="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
                        <span>Healthy</span>
                      </span>
                    } @else if (m.health === 'DEGRADED') {
                      <span class="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-md text-[11px] font-semibold bg-amber-50 text-amber-700 border border-amber-200">
                        <span class="w-1.5 h-1.5 rounded-full bg-amber-500"></span>
                        <span>Degraded</span>
                      </span>
                    } @else if (m.health === 'UNHEALTHY') {
                      <span class="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-md text-[11px] font-semibold bg-rose-50 text-rose-700 border border-rose-200">
                        <span class="w-1.5 h-1.5 rounded-full bg-rose-500"></span>
                        <span>Unhealthy</span>
                      </span>
                    } @else {
                      <span class="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-md text-[11px] font-semibold bg-slate-100 text-slate-700 border border-slate-200">
                        <span class="w-1.5 h-1.5 rounded-full bg-slate-400"></span>
                        <span>Unknown</span>
                      </span>
                    }
                  </td>

                  <!-- 6. Row Action Drill-in -->
                  <td class="py-3 px-3 text-right whitespace-nowrap" (click)="$event.stopPropagation()">
                    <a
                      [routerLink]="m.deep_link_route"
                      class="w-7 h-7 inline-flex items-center justify-center rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-slate-600 hover:text-blue-600 transition-colors shadow-2xs cursor-pointer"
                      title="Inspect Cockpit">
                      <app-lucide-icon name="chevron-right" [size]="14"></app-lucide-icon>
                    </a>
                  </td>

                </tr>
              }
            </tbody>
          </table>
        </div>
      }

    </div>
  `
})
export class MonitoringActiveMigrationsComponent {
  public ms = inject(MonitoringService);
  private router = inject(Router);

  public getModeInfo(mode: CanonicalMigrationMode) {
    return CANONICAL_MODES[mode] || { code: mode, tag: mode, label: mode, shortDescription: '' };
  }

  public navigateTo(route: string): void {
    if (route) {
      this.router.navigateByUrl(route);
    }
  }
}

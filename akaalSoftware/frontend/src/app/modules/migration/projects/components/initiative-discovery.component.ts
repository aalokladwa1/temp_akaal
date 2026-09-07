import { Component, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { ProjectsService } from '../projects.service';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';
import { ProjectsStateFallbackComponent } from './projects-state-fallback.component';

@Component({
  selector: 'app-initiative-discovery',
  standalone: true,
  imports: [CommonModule, RouterLink, FormsModule, LucideIconComponent, ProjectsStateFallbackComponent],
  template: `
    <div class="flex flex-col gap-4">
      
      <!-- Toolbar: Search, Status Filter, Reset (Rectangular Framed GDS Buttons) -->
      <div class="p-4 sm:p-4.5 rounded-xl bg-white border border-slate-200 shadow-xs flex items-center justify-between gap-4 flex-wrap">
        
        <!-- Search Input with Pure Inline Style Overlay -->
        <div style="position: relative; display: flex; align-items: center; width: 280px; max-width: 100%;">
          <app-lucide-icon
            name="search"
            [size]="14"
            style="position: absolute; left: 11px; top: 50%; transform: translateY(-50%); width: 14px; height: 14px; color: #94a3b8; pointer-events: none; z-index: 2;">
          </app-lucide-icon>
          
          <input
            type="text"
            [ngModel]="ps.initiativeFilters().searchQuery"
            (ngModelChange)="ps.setInitiativeSearch($event)"
            placeholder="Search initiatives by name, key, objective..."
            style="width: 100%; height: 36px; padding-left: 36px !important; padding-right: 28px; font-size: 12px; background-color: #ffffff; border: 1px solid #e2e8f0; border-radius: 6px; outline: none; color: #0f172a;"
          />

          @if (ps.initiativeFilters().searchQuery) {
            <button
              type="button"
              (click)="ps.setInitiativeSearch('')"
              class="w-5 h-5 rounded-md hover:bg-slate-100 flex items-center justify-center text-slate-400 hover:text-slate-600 transition-colors cursor-pointer"
              style="position: absolute; right: 8px; top: 50%; transform: translateY(-50%);">
              <app-lucide-icon name="x" [size]="12"></app-lucide-icon>
            </button>
          }
        </div>

        <!-- Filter Dropdowns & Sorter -->
        <div class="flex items-center gap-2.5 flex-wrap">
          
          <!-- Status Filter Popover (Rectangular Framed rounded-md) -->
          <div class="relative" (click)="$event.stopPropagation()">
            <button
              type="button"
              (click)="toggleStatusDropdown()"
              class="h-9 px-3.5 text-xs text-slate-700 border border-slate-200 rounded-md bg-white hover:bg-slate-50 flex items-center gap-2 cursor-pointer select-none transition-colors shadow-2xs"
              [class.bg-blue-50]="isStatusOpen()"
              [class.border-blue-300]="isStatusOpen()">
              <app-lucide-icon name="filter" [size]="13" class="text-slate-500"></app-lucide-icon>
              <span>Status: <strong>{{ ps.initiativeFilters().statusFilter === 'ALL' ? 'All States' : ps.initiativeFilters().statusFilter }}</strong></span>
              <app-lucide-icon name="chevron-down" [size]="12" class="text-slate-400"></app-lucide-icon>
            </button>

            @if (isStatusOpen()) {
              <div class="absolute right-0 mt-1.5 w-44 rounded-lg bg-white border border-slate-200 shadow-xl p-1 flex flex-col gap-0.5 z-30 animate-in fade-in zoom-in-95 duration-100">
                <button
                  type="button"
                  (click)="selectStatus('ALL')"
                  class="w-full text-left px-2.5 py-1.5 rounded-md text-xs font-medium text-slate-700 hover:bg-slate-50 flex items-center justify-between cursor-pointer"
                  [class.bg-blue-50]="ps.initiativeFilters().statusFilter === 'ALL'"
                  [class.text-blue-700]="ps.initiativeFilters().statusFilter === 'ALL'">
                  <span>All States</span>
                  @if (ps.initiativeFilters().statusFilter === 'ALL') {
                    <app-lucide-icon name="check" [size]="13" class="text-blue-600"></app-lucide-icon>
                  }
                </button>
                @for (status of ps.availableInitiativeStatusOptions(); track status) {
                  <button
                    type="button"
                    (click)="selectStatus(status)"
                    class="w-full text-left px-2.5 py-1.5 rounded-md text-xs font-medium text-slate-700 hover:bg-slate-50 flex items-center justify-between cursor-pointer"
                    [class.bg-blue-50]="ps.initiativeFilters().statusFilter === status"
                    [class.text-blue-700]="ps.initiativeFilters().statusFilter === status">
                    <span>{{ status }}</span>
                    @if (ps.initiativeFilters().statusFilter === status) {
                      <app-lucide-icon name="check" [size]="13" class="text-blue-600"></app-lucide-icon>
                    }
                  </button>
                }
              </div>
            }
          </div>

          <!-- Sort Button (Rectangular Framed rounded-md) -->
          <button
            type="button"
            (click)="toggleSort()"
            class="h-9 px-3.5 text-xs text-slate-700 border border-slate-200 rounded-md bg-white hover:bg-slate-50 flex items-center gap-1.5 cursor-pointer shadow-2xs transition-colors"
            title="Toggle sort direction">
            <app-lucide-icon [name]="ps.initiativeFilters().sortDirection === 'ASC' ? 'arrow-up-narrow-wide' : 'arrow-down-wide-narrow'" [size]="14" class="text-slate-500"></app-lucide-icon>
            <span>Sort: <strong>{{ ps.initiativeFilters().sortBy === 'RECENT' ? 'Recent' : (ps.initiativeFilters().sortBy === 'NAME' ? 'Name' : 'Projects') }}</strong></span>
          </button>

          <!-- Reset All Filters -->
          @if (ps.initiativeFilters().searchQuery || ps.initiativeFilters().statusFilter !== 'ALL') {
            <button
              type="button"
              (click)="ps.clearInitiativeFilters()"
              class="h-9 px-3 text-xs text-rose-600 hover:text-rose-800 bg-rose-50 hover:bg-rose-100/70 border border-rose-200/80 rounded-md flex items-center gap-1 cursor-pointer transition-colors font-semibold">
              <app-lucide-icon name="x" [size]="12"></app-lucide-icon>
              <span>Reset</span>
            </button>
          }

        </div>

      </div>

      <!-- State Handling: Non-Ready States -->
      @if (ps.isUnavailable() || ps.isUnauthorized() || ps.isError()) {
        <app-projects-state-fallback
          [state]="ps.initiativesAvailability()"
          entityName="initiatives"
          [customErrorMessage]="ps.errorMessage()"
          (retry)="ps.retryConnection()">
        </app-projects-state-fallback>
      } @else if (ps.filteredInitiatives().length === 0) {
        <app-projects-state-fallback
          [state]="'EMPTY'"
          entityName="initiatives"
          (retry)="ps.retryConnection()">
        </app-projects-state-fallback>
      } @else {
        <!-- Scalable Enterprise Table for Initiatives (Associated Projects Column Removed) -->
        <div class="rounded-xl bg-white border border-slate-200 shadow-xs overflow-hidden">
          <div class="overflow-x-auto">
            <table class="w-full text-left border-collapse table-fixed">
              <thead>
                <tr class="bg-slate-100/90 text-[10px] font-bold uppercase tracking-wider text-slate-600 border-b border-slate-200 select-none">
                  <th class="py-3.5 px-5 w-[56%]">Initiative</th>
                  <th class="py-3.5 px-5 w-[20%]">Status</th>
                  <th class="py-3.5 px-5 w-[20%]">Last Activity</th>
                  <th class="py-3.5 px-4 w-[4%] text-right"></th>
                </tr>
              </thead>
              <tbody class="divide-y divide-slate-100 text-xs">
                @for (init of ps.filteredInitiatives(); track init.id; let i = $index) {
                  <tr
                    [routerLink]="['/migration/initiatives', init.id]"
                    class="hover:bg-blue-50/50 even:bg-slate-50/50 transition-colors cursor-pointer group select-none">
                    
                    <!-- 1. Initiative Key, Name & Objective -->
                    <td class="py-4 px-5">
                      <div class="flex flex-col gap-1.5 min-w-0">
                        <div class="flex items-center gap-2.5">
                          <span class="px-2.5 py-0.5 rounded-md text-[10px] font-bold font-mono bg-indigo-50 text-indigo-700 border border-indigo-200/80 shrink-0">
                            {{ init.key }}
                          </span>
                          <span class="font-bold text-slate-900 group-hover:text-blue-700 transition-colors truncate">
                            {{ init.name }}
                          </span>
                        </div>
                        @if (init.objective) {
                          <p class="text-[11.5px] text-slate-500 font-normal leading-relaxed line-clamp-1">
                            {{ init.objective }}
                          </p>
                        }
                      </div>
                    </td>

                    <!-- 2. Status Badge -->
                    <td class="py-4 px-5">
                      <span
                        class="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-md text-[11px] font-semibold border select-none"
                        [class.bg-emerald-50]="init.status === 'ACTIVE'"
                        [class.text-emerald-700]="init.status === 'ACTIVE'"
                        [class.border-emerald-200]="init.status === 'ACTIVE'"
                        [class.bg-blue-50]="init.status === 'PLANNING'"
                        [class.text-blue-700]="init.status === 'PLANNING'"
                        [class.border-blue-200]="init.status === 'PLANNING'"
                        [class.bg-slate-100]="init.status !== 'ACTIVE' && init.status !== 'PLANNING'"
                        [class.text-slate-700]="init.status !== 'ACTIVE' && init.status !== 'PLANNING'"
                        [class.border-slate-200]="init.status !== 'ACTIVE' && init.status !== 'PLANNING'">
                        <span
                          class="w-1.5 h-1.5 rounded-xs"
                          [class.bg-emerald-500]="init.status === 'ACTIVE'"
                          [class.bg-blue-500]="init.status === 'PLANNING'"
                          [class.bg-slate-400]="init.status === 'ARCHIVED'">
                        </span>
                        <span>{{ init.status || 'Active' }}</span>
                      </span>
                    </td>

                    <!-- 3. Last Activity Timestamp -->
                    <td class="py-4 px-5">
                      <div class="flex flex-col gap-0.5 text-xs text-slate-500 font-medium">
                        <span class="tabular-nums">{{ init.lastActivityAt ? (init.lastActivityAt | date:'MMM d, yyyy') : 'Recently' }}</span>
                        @if (init.lastActivityAt) {
                          <span class="text-[10.5px] text-slate-400 font-mono">{{ init.lastActivityAt | date:'HH:mm UTC' }}</span>
                        }
                      </div>
                    </td>

                    <!-- 4. Action Arrow -->
                    <td class="py-4 px-4 text-right">
                      <app-lucide-icon
                        name="chevron-right"
                        [size]="15"
                        class="text-slate-400 group-hover:text-blue-600 group-hover:translate-x-0.5 transition-all inline-block">
                      </app-lucide-icon>
                    </td>

                  </tr>
                }
              </tbody>
            </table>
          </div>
        </div>
      }

    </div>
  `
})
export class InitiativeDiscoveryComponent {
  public ps = inject(ProjectsService);

  public isStatusOpen = signal<boolean>(false);

  public toggleStatusDropdown(): void {
    this.isStatusOpen.update(v => !v);
  }

  public selectStatus(status: string): void {
    this.ps.setInitiativeStatusFilter(status);
    this.isStatusOpen.set(false);
  }

  public toggleSort(): void {
    const current = this.ps.initiativeFilters().sortBy;
    if (current === 'RECENT') {
      this.ps.setInitiativeSort('NAME');
    } else if (current === 'NAME') {
      this.ps.setInitiativeSort('PROJECTS');
    } else {
      this.ps.setInitiativeSort('RECENT');
    }
  }
}

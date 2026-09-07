import { Component, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { ProjectsService } from '../projects.service';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';
import { ProjectsStateFallbackComponent } from './projects-state-fallback.component';

@Component({
  selector: 'app-project-discovery',
  standalone: true,
  imports: [CommonModule, RouterLink, FormsModule, LucideIconComponent, ProjectsStateFallbackComponent],
  template: `
    <div class="flex flex-col gap-4">
      
      <!-- Toolbar: Search, Status Filter, Initiative Filter, Reset (Rectangular Framed rounded-md) -->
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
            [ngModel]="ps.projectFilters().searchQuery"
            (ngModelChange)="ps.setProjectSearch($event)"
            placeholder="Search projects by name, key, initiative..."
            style="width: 100%; height: 36px; padding-left: 36px !important; padding-right: 28px; font-size: 12px; background-color: #ffffff; border: 1px solid #e2e8f0; border-radius: 6px; outline: none; color: #0f172a;"
          />

          @if (ps.projectFilters().searchQuery) {
            <button
              type="button"
              (click)="ps.setProjectSearch('')"
              class="w-5 h-5 rounded-md hover:bg-slate-100 flex items-center justify-center text-slate-400 hover:text-slate-600 transition-colors cursor-pointer"
              style="position: absolute; right: 8px; top: 50%; transform: translateY(-50%);">
              <app-lucide-icon name="x" [size]="12"></app-lucide-icon>
            </button>
          }
        </div>

        <!-- Filter Dropdowns & Sorter -->
        <div class="flex items-center gap-2.5 flex-wrap">
          
          <!-- 1. Status Filter Popover (Rectangular Framed rounded-md) -->
          <div class="relative" (click)="$event.stopPropagation()">
            <button
              type="button"
              (click)="toggleStatusDropdown()"
              class="h-9 px-3.5 text-xs text-slate-700 border border-slate-200 rounded-md bg-white hover:bg-slate-50 flex items-center gap-2 cursor-pointer select-none transition-colors shadow-2xs"
              [class.bg-blue-50]="isStatusOpen()"
              [class.border-blue-300]="isStatusOpen()">
              <app-lucide-icon name="filter" [size]="13" class="text-slate-500"></app-lucide-icon>
              <span>Status: <strong>{{ ps.projectFilters().statusFilter === 'ALL' ? 'All States' : ps.projectFilters().statusFilter }}</strong></span>
              <app-lucide-icon name="chevron-down" [size]="12" class="text-slate-400"></app-lucide-icon>
            </button>

            @if (isStatusOpen()) {
              <div class="absolute right-0 mt-1.5 w-44 rounded-lg bg-white border border-slate-200 shadow-xl p-1 flex flex-col gap-0.5 z-30 animate-in fade-in zoom-in-95 duration-100">
                <button
                  type="button"
                  (click)="selectStatus('ALL')"
                  class="w-full text-left px-2.5 py-1.5 rounded-md text-xs font-medium text-slate-700 hover:bg-slate-50 flex items-center justify-between cursor-pointer"
                  [class.bg-blue-50]="ps.projectFilters().statusFilter === 'ALL'"
                  [class.text-blue-700]="ps.projectFilters().statusFilter === 'ALL'">
                  <span>All States</span>
                  @if (ps.projectFilters().statusFilter === 'ALL') {
                    <app-lucide-icon name="check" [size]="13" class="text-blue-600"></app-lucide-icon>
                  }
                </button>
                @for (status of ps.availableProjectStatusOptions(); track status) {
                  <button
                    type="button"
                    (click)="selectStatus(status)"
                    class="w-full text-left px-2.5 py-1.5 rounded-md text-xs font-medium text-slate-700 hover:bg-slate-50 flex items-center justify-between cursor-pointer"
                    [class.bg-blue-50]="ps.projectFilters().statusFilter === status"
                    [class.text-blue-700]="ps.projectFilters().statusFilter === status">
                    <span>{{ status }}</span>
                    @if (ps.projectFilters().statusFilter === status) {
                      <app-lucide-icon name="check" [size]="13" class="text-blue-600"></app-lucide-icon>
                    }
                  </button>
                }
              </div>
            }
          </div>

          <!-- 2. Initiative Scoping Filter Popover (Rectangular Framed rounded-md) -->
          <div class="relative" (click)="$event.stopPropagation()">
            <button
              type="button"
              (click)="toggleInitiativeDropdown()"
              class="h-9 px-3.5 text-xs text-slate-700 border border-slate-200 rounded-md bg-white hover:bg-slate-50 flex items-center gap-2 cursor-pointer select-none transition-colors shadow-2xs"
              [class.bg-blue-50]="isInitiativeOpen()"
              [class.border-blue-300]="isInitiativeOpen()">
              <app-lucide-icon name="target" [size]="13" class="text-slate-500"></app-lucide-icon>
              <span>Initiative: <strong>{{ selectedInitiativeLabel() }}</strong></span>
              <app-lucide-icon name="chevron-down" [size]="12" class="text-slate-400"></app-lucide-icon>
            </button>

            @if (isInitiativeOpen()) {
              <div class="absolute right-0 mt-1.5 w-64 rounded-lg bg-white border border-slate-200 shadow-xl p-1 flex flex-col gap-0.5 z-30 animate-in fade-in zoom-in-95 duration-100 max-h-60 overflow-y-auto">
                <button
                  type="button"
                  (click)="selectInitiative('ALL')"
                  class="w-full text-left px-2.5 py-1.5 rounded-md text-xs font-medium text-slate-700 hover:bg-slate-50 flex items-center justify-between cursor-pointer"
                  [class.bg-blue-50]="ps.projectFilters().initiativeFilter === 'ALL'"
                  [class.text-blue-700]="ps.projectFilters().initiativeFilter === 'ALL'">
                  <span>All Initiatives</span>
                  @if (ps.projectFilters().initiativeFilter === 'ALL') {
                    <app-lucide-icon name="check" [size]="13" class="text-blue-600"></app-lucide-icon>
                  }
                </button>
                @for (init of ps.availableInitiativeOptions(); track init.id) {
                  <button
                    type="button"
                    (click)="selectInitiative(init.id)"
                    class="w-full text-left px-2.5 py-1.5 rounded-md text-xs font-medium text-slate-700 hover:bg-slate-50 flex items-center justify-between cursor-pointer"
                    [class.bg-blue-50]="ps.projectFilters().initiativeFilter === init.id"
                    [class.text-blue-700]="ps.projectFilters().initiativeFilter === init.id">
                    <span class="truncate">{{ init.name }}</span>
                    @if (ps.projectFilters().initiativeFilter === init.id) {
                      <app-lucide-icon name="check" [size]="13" class="text-blue-600 shrink-0"></app-lucide-icon>
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
            <app-lucide-icon [name]="ps.projectFilters().sortDirection === 'ASC' ? 'arrow-up-narrow-wide' : 'arrow-down-wide-narrow'" [size]="14" class="text-slate-500"></app-lucide-icon>
            <span>Sort: <strong>{{ ps.projectFilters().sortBy === 'RECENT' ? 'Recent' : (ps.projectFilters().sortBy === 'NAME' ? 'Name' : 'Status') }}</strong></span>
          </button>

          <!-- Reset All Filters -->
          @if (ps.projectFilters().searchQuery || ps.projectFilters().statusFilter !== 'ALL' || ps.projectFilters().initiativeFilter !== 'ALL') {
            <button
              type="button"
              (click)="ps.clearProjectFilters()"
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
          [state]="ps.projectsAvailability()"
          entityName="projects"
          [customErrorMessage]="ps.errorMessage()"
          (retry)="ps.retryConnection()">
        </app-projects-state-fallback>
      } @else if (ps.filteredProjects().length === 0) {
        <app-projects-state-fallback
          [state]="'EMPTY'"
          entityName="projects"
          (retry)="ps.retryConnection()">
        </app-projects-state-fallback>
      } @else {
        <!-- High-Precision Enterprise Projects Table -->
        <div class="rounded-xl bg-white border border-slate-200 shadow-xs overflow-hidden">
          <div class="overflow-x-auto">
            <table class="w-full text-left border-collapse table-fixed">
              <thead>
                <tr class="bg-slate-100/90 text-[10px] font-bold uppercase tracking-wider text-slate-600 border-b border-slate-200 select-none">
                  <th class="py-3.5 px-5 w-[36%]">Project</th>
                  <th class="py-3.5 px-5 w-[22%]">Initiative</th>
                  <th class="py-3.5 px-5 w-[14%]">Status</th>
                  <th class="py-3.5 px-5 w-[14%]">Workloads</th>
                  <th class="py-3.5 px-5 w-[10%]">Last Activity</th>
                  <th class="py-3.5 px-4 w-[4%] text-right"></th>
                </tr>
              </thead>
              <tbody class="divide-y divide-slate-100 text-xs">
                @for (p of ps.filteredProjects(); track p.id; let i = $index) {
                  <tr
                    [routerLink]="['/migration/projects', p.id]"
                    class="hover:bg-blue-50/50 even:bg-slate-50/50 transition-colors cursor-pointer group select-none">
                    
                    <!-- 1. Project Key, Name & Description -->
                    <td class="py-4 px-5">
                      <div class="flex flex-col gap-1 min-w-0">
                        <div class="flex items-center gap-2">
                          <span class="px-2 py-0.5 rounded-md text-[10px] font-bold font-mono bg-blue-50 text-blue-700 border border-blue-200/80 shrink-0">
                            {{ p.key }}
                          </span>
                          <span class="font-bold text-slate-900 group-hover:text-blue-700 transition-colors truncate">
                            {{ p.name }}
                          </span>
                        </div>
                        @if (p.description) {
                          <p class="text-[11.5px] text-slate-500 font-normal leading-relaxed line-clamp-1">
                            {{ p.description }}
                          </p>
                        }
                      </div>
                    </td>

                    <!-- 2. Initiative Association -->
                    <td class="py-4 px-5">
                      @if (p.initiativeName) {
                        <div class="flex items-center gap-1.5">
                          <app-lucide-icon name="target" [size]="13" class="text-indigo-600 shrink-0"></app-lucide-icon>
                          <span class="text-xs font-semibold text-slate-700 truncate" [title]="p.initiativeName">
                            {{ p.initiativeName }}
                          </span>
                        </div>
                      } @else {
                        <span class="text-slate-400 font-medium text-xs">&mdash;</span>
                      }
                    </td>

                    <!-- 3. Status Badge -->
                    <td class="py-4 px-5">
                      <span
                        class="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-md text-[11px] font-semibold border select-none"
                        [class.bg-emerald-50]="p.status === 'ACTIVE'"
                        [class.text-emerald-700]="p.status === 'ACTIVE'"
                        [class.border-emerald-200]="p.status === 'ACTIVE'"
                        [class.bg-blue-50]="p.status === 'PLANNING'"
                        [class.text-blue-700]="p.status === 'PLANNING'"
                        [class.border-blue-200]="p.status === 'PLANNING'"
                        [class.bg-slate-100]="p.status !== 'ACTIVE' && p.status !== 'PLANNING'"
                        [class.text-slate-700]="p.status !== 'ACTIVE' && p.status !== 'PLANNING'"
                        [class.border-slate-200]="p.status !== 'ACTIVE' && p.status !== 'PLANNING'">
                        <span
                          class="w-1.5 h-1.5 rounded-xs"
                          [class.bg-emerald-500]="p.status === 'ACTIVE'"
                          [class.bg-blue-500]="p.status === 'PLANNING'"
                          [class.bg-slate-400]="p.status !== 'ACTIVE' && p.status !== 'PLANNING'">
                        </span>
                        <span>{{ p.status || 'Active' }}</span>
                      </span>
                    </td>

                    <!-- 4. Workloads / Migrations Count -->
                    <td class="py-4 px-5">
                      <div class="flex flex-col gap-0.5 text-xs text-slate-700 font-medium">
                        @if (p.migrationCount !== null && p.migrationCount !== undefined) {
                          <span class="tabular-nums font-semibold text-slate-800">
                            {{ p.migrationCount }} migrations
                          </span>
                          @if (p.validationCount !== null && p.validationCount !== undefined && p.validationCount > 0) {
                            <span class="text-[11px] text-slate-500 tabular-nums">
                              {{ p.validationCount }} validations
                            </span>
                          }
                        } @else {
                          <span class="text-slate-400">&mdash;</span>
                        }
                      </div>
                    </td>

                    <!-- 5. Last Activity Timestamp -->
                    <td class="py-4 px-5">
                      <div class="flex flex-col gap-0.5 text-xs text-slate-500 font-medium">
                        <span class="tabular-nums">{{ p.lastActivityAt ? (p.lastActivityAt | date:'MMM d, yyyy') : 'Recently' }}</span>
                        @if (p.lastActivityAt) {
                          <span class="text-[10.5px] text-slate-400 font-mono">{{ p.lastActivityAt | date:'HH:mm UTC' }}</span>
                        }
                      </div>
                    </td>

                    <!-- 6. Action Arrow -->
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
export class ProjectDiscoveryComponent {
  public ps = inject(ProjectsService);

  public isStatusOpen = signal<boolean>(false);
  public isInitiativeOpen = signal<boolean>(false);

  public toggleStatusDropdown(): void {
    const next = !this.isStatusOpen();
    this.closeDropdowns();
    this.isStatusOpen.set(next);
  }

  public toggleInitiativeDropdown(): void {
    const next = !this.isInitiativeOpen();
    this.closeDropdowns();
    this.isInitiativeOpen.set(next);
  }

  public closeDropdowns(): void {
    this.isStatusOpen.set(false);
    this.isInitiativeOpen.set(false);
  }

  public selectStatus(status: string): void {
    this.ps.setProjectStatusFilter(status);
    this.isStatusOpen.set(false);
  }

  public selectInitiative(initiativeId: string): void {
    this.ps.setProjectInitiativeFilter(initiativeId);
    this.isInitiativeOpen.set(false);
  }

  public selectedInitiativeLabel(): string {
    const filter = this.ps.projectFilters().initiativeFilter;
    if (filter === 'ALL') return 'All Initiatives';
    const found = this.ps.availableInitiativeOptions().find(o => o.id === filter);
    return found ? found.name : filter;
  }

  public toggleSort(): void {
    const current = this.ps.projectFilters().sortBy;
    if (current === 'RECENT') {
      this.ps.setProjectSort('NAME');
    } else if (current === 'NAME') {
      this.ps.setProjectSort('STATUS');
    } else {
      this.ps.setProjectSort('RECENT');
    }
  }
}

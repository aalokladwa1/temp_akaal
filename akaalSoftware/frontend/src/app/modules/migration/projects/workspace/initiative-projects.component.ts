import { Component, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { ProjectsService } from '../projects.service';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';
import { ProjectDiscoveryItem } from '../projects.models';

@Component({
  selector: 'app-initiative-projects',
  standalone: true,
  imports: [CommonModule, RouterLink, FormsModule, LucideIconComponent],
  template: `
    <div class="flex flex-col gap-4">
      
      <!-- Toolbar: Search, Status Filter, Sorter, Add Projects Button -->
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
            placeholder="Search projects in initiative..."
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

        <!-- Right Controls: Status Filter, Sorter, Add Projects Action -->
        <div class="flex items-center gap-2.5 flex-wrap">
          
          <!-- Status Filter Dropdown -->
          <div class="relative" (click)="$event.stopPropagation()">
            <button
              type="button"
              (click)="isStatusOpen.set(!isStatusOpen())"
              class="h-9 px-3.5 text-xs text-slate-700 border border-slate-200 rounded-md bg-white hover:bg-slate-50 flex items-center gap-2 cursor-pointer select-none transition-colors shadow-2xs"
              [class.bg-blue-50]="isStatusOpen()"
              [class.border-blue-300]="isStatusOpen()">
              <app-lucide-icon name="filter" [size]="13" class="text-slate-500"></app-lucide-icon>
              <span>Status: <strong>{{ ps.projectFilters().statusFilter === 'ALL' ? 'All States' : ps.projectFilters().statusFilter }}</strong></span>
              <app-lucide-icon name="chevron-down" [size]="12" class="text-slate-400"></app-lucide-icon>
            </button>

            @if (isStatusOpen()) {
              <div class="absolute right-0 mt-1.5 w-44 rounded-md bg-white border border-slate-200 shadow-xl p-1 flex flex-col gap-0.5 z-30 animate-in fade-in zoom-in-95 duration-100">
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

          <!-- Sort Button -->
          <button
            type="button"
            (click)="toggleSort()"
            class="h-9 px-3.5 text-xs text-slate-700 border border-slate-200 rounded-md bg-white hover:bg-slate-50 flex items-center gap-1.5 cursor-pointer shadow-2xs transition-colors"
            title="Toggle sort direction">
            <app-lucide-icon [name]="ps.projectFilters().sortDirection === 'ASC' ? 'arrow-up-narrow-wide' : 'arrow-down-wide-narrow'" [size]="14" class="text-slate-500"></app-lucide-icon>
            <span>Sort: <strong>{{ ps.projectFilters().sortBy === 'RECENT' ? 'Recent' : 'Name' }}</strong></span>
          </button>

          <!-- Add Projects Button -->
          <button
            type="button"
            (click)="openAddModal()"
            class="h-9 px-3.5 rounded-md bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold inline-flex items-center justify-center cursor-pointer shadow-2xs transition-colors">
            Add Projects
          </button>

        </div>

      </div>

      <!-- Projects Table or Empty State -->
      @if (ps.filteredActiveInitiativeProjects().length === 0) {
        <div class="p-12 rounded-xl bg-white border border-slate-200 shadow-xs flex flex-col items-center justify-center text-center gap-3">
          <div class="w-12 h-12 rounded-lg bg-slate-50 border border-slate-200 flex items-center justify-center text-slate-400">
            <app-lucide-icon name="folder-kanban" [size]="24"></app-lucide-icon>
          </div>
          <div class="flex flex-col gap-1">
            <span class="text-sm font-bold text-slate-800">No Projects Found</span>
            <p class="text-xs text-slate-500 max-w-sm">
              {{ ps.projectFilters().searchQuery || ps.projectFilters().statusFilter !== 'ALL' ? 'No projects match your filter criteria.' : 'Associate existing database migration projects to track them in this initiative.' }}
            </p>
          </div>
          <button
            type="button"
            (click)="openAddModal()"
            class="mt-2 h-9 px-4 rounded-md bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold inline-flex items-center justify-center cursor-pointer shadow-2xs transition-colors">
            Associate Projects
          </button>
        </div>
      } @else {
        <div class="rounded-xl bg-white border border-slate-200 shadow-xs overflow-hidden">
          <div class="overflow-x-auto">
            <table class="w-full text-left border-collapse table-fixed">
              <thead>
                <tr class="bg-slate-100/90 text-[10px] font-bold uppercase tracking-wider text-slate-600 border-b border-slate-200 select-none">
                  <th class="py-3.5 px-5 w-[40%]">Project</th>
                  <th class="py-3.5 px-5 w-[18%]">Status</th>
                  <th class="py-3.5 px-5 w-[18%]">Workloads</th>
                  <th class="py-3.5 px-5 w-[14%]">Last Activity</th>
                  <th class="py-3.5 px-4 w-[10%] text-right">Actions</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-slate-100 text-xs">
                @for (p of ps.filteredActiveInitiativeProjects(); track p.id) {
                  <tr class="hover:bg-blue-50/50 even:bg-slate-50/50 transition-colors select-none group">
                    
                    <!-- Project Key & Name -->
                    <td class="py-4 px-5">
                      <div class="flex flex-col gap-1 min-w-0">
                        <div class="flex items-center gap-2">
                          <span class="px-2 py-0.5 rounded-md text-[10px] font-bold font-mono bg-blue-50 text-blue-700 border border-blue-200/80 shrink-0">
                            {{ p.key }}
                          </span>
                          <a
                            [routerLink]="['/migration/projects', p.id]"
                            class="font-bold text-slate-900 group-hover:text-blue-700 transition-colors truncate">
                            {{ p.name }}
                          </a>
                        </div>
                        @if (p.description) {
                          <p class="text-[11.5px] text-slate-500 font-normal line-clamp-1">
                            {{ p.description }}
                          </p>
                        }
                      </div>
                    </td>

                    <!-- Status -->
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

                    <!-- Workloads -->
                    <td class="py-4 px-5">
                      <div class="flex flex-col gap-0.5 text-xs text-slate-700 font-medium">
                        <span class="tabular-nums font-semibold text-slate-800">
                          {{ p.migrationCount || 0 }} migrations
                        </span>
                        <span class="text-[11px] text-slate-500 tabular-nums">
                          {{ p.validationCount || 0 }} validations
                        </span>
                      </div>
                    </td>

                    <!-- Last Activity -->
                    <td class="py-4 px-5">
                      <div class="flex flex-col gap-0.5 text-xs text-slate-500 font-medium">
                        <span class="tabular-nums">{{ p.lastActivityAt ? (p.lastActivityAt | date:'MMM d, yyyy') : 'Recently' }}</span>
                        @if (p.lastActivityAt) {
                          <span class="text-[10.5px] text-slate-400 font-mono">{{ p.lastActivityAt | date:'HH:mm UTC' }}</span>
                        }
                      </div>
                    </td>

                    <!-- Actions -->
                    <td class="py-4 px-4 text-right whitespace-nowrap">
                      <button
                        type="button"
                        (click)="openRemoveModal(p)"
                        class="h-8 px-3 rounded-md text-xs font-medium text-slate-600 hover:text-rose-700 hover:bg-rose-50 border border-slate-200 hover:border-rose-200 transition-colors cursor-pointer shadow-2xs"
                        title="Remove project from this initiative">
                        Remove
                      </button>
                    </td>

                  </tr>
                }
              </tbody>
            </table>
          </div>
        </div>
      }

      <!-- =============================================================== -->
      <!-- MODAL 1: ADD PROJECTS MODAL                                     -->
      <!-- =============================================================== -->
      @if (isAddModalOpen()) {
        <div
          class="fixed inset-0 z-50 bg-slate-900/40 backdrop-blur-xs flex items-center justify-center p-4 animate-in fade-in duration-150"
          (click)="closeAddModal()">
          <div
            class="w-full max-w-xl bg-white border border-slate-200 rounded-xl shadow-2xl p-6 flex flex-col gap-4 max-h-[85vh] overflow-hidden"
            (click)="$event.stopPropagation()">
            
            <div class="flex items-center justify-between pb-3 border-b border-slate-100">
              <div class="flex items-center gap-2.5">
                <app-lucide-icon name="folder-plus" [size]="18" class="text-blue-600"></app-lucide-icon>
                <h3 class="text-base font-bold text-slate-900 font-heading">Add Projects to Initiative</h3>
              </div>
              <button type="button" (click)="closeAddModal()" class="p-1 text-slate-400 hover:text-slate-700 rounded-md hover:bg-slate-100 cursor-pointer">
                <app-lucide-icon name="x" [size]="16"></app-lucide-icon>
              </button>
            </div>

            <p class="text-xs text-slate-600 leading-relaxed">
              Select existing migration projects from the active workspace to associate with <strong>{{ ps.activeInitiative()?.name }}</strong>:
            </p>

            <!-- Modal Search Input -->
            <div style="position: relative; display: flex; align-items: center; width: 100%;">
              <app-lucide-icon
                name="search"
                [size]="14"
                style="position: absolute; left: 11px; top: 50%; transform: translateY(-50%); width: 14px; height: 14px; color: #94a3b8; pointer-events: none; z-index: 2;">
              </app-lucide-icon>
              <input
                type="text"
                [(ngModel)]="addModalSearch"
                placeholder="Filter available projects..."
                style="width: 100%; height: 36px; padding-left: 36px !important; padding-right: 28px; font-size: 12px; background-color: #ffffff; border: 1px solid #e2e8f0; border-radius: 6px; outline: none; color: #0f172a;"
              />
            </div>

            <!-- Available Projects List -->
            <div class="flex flex-col gap-1 max-h-60 overflow-y-auto divide-y divide-slate-100 border border-slate-200 rounded-lg p-1">
              @for (p of filteredModalAvailableProjects(); track p.id) {
                <div
                  (click)="toggleAddSelection(p.id)"
                  class="p-2.5 flex items-center justify-between gap-3 hover:bg-slate-50 rounded-md cursor-pointer transition-colors"
                  [class.bg-blue-50]="selectedToAdd().includes(p.id)">
                  <div class="flex items-center gap-3 min-w-0">
                    <div
                      class="w-4.5 h-4.5 rounded border flex items-center justify-center transition-all shrink-0"
                      [class.bg-blue-600]="selectedToAdd().includes(p.id)"
                      [class.border-blue-600]="selectedToAdd().includes(p.id)"
                      [class.border-slate-300]="!selectedToAdd().includes(p.id)">
                      @if (selectedToAdd().includes(p.id)) {
                        <app-lucide-icon name="check" [size]="11" class="text-white"></app-lucide-icon>
                      }
                    </div>
                    <div class="flex flex-col min-w-0">
                      <div class="flex items-center gap-2">
                        <span class="font-mono text-[10px] font-bold text-blue-600 bg-blue-50 px-1.5 py-0.5 rounded border border-blue-100">{{ p.key }}</span>
                        <span class="font-semibold text-slate-900 text-xs truncate">{{ p.name }}</span>
                      </div>
                      @if (p.initiativeName) {
                        <span class="text-[10.5px] text-slate-500">Currently attached to: {{ p.initiativeName }}</span>
                      }
                    </div>
                  </div>
                  <span class="text-[11px] text-slate-500 font-medium tabular-nums">{{ p.migrationCount || 0 }} migrations</span>
                </div>
              }
              @if (filteredModalAvailableProjects().length === 0) {
                <div class="py-6 text-center text-xs text-slate-400">No available projects found</div>
              }
            </div>

            <div class="pt-3 border-t border-slate-100 flex items-center justify-between">
              <span class="text-xs font-semibold text-slate-600">
                {{ selectedToAdd().length }} project{{ selectedToAdd().length === 1 ? '' : 's' }} selected
              </span>
              <div class="flex items-center gap-2">
                <button
                  type="button"
                  (click)="closeAddModal()"
                  class="h-8.5 px-3 rounded-md border border-slate-200 text-xs font-medium text-slate-700 hover:bg-slate-50 cursor-pointer transition-colors shadow-2xs">
                  Cancel
                </button>
                <button
                  type="button"
                  (click)="confirmAddProjects()"
                  [disabled]="selectedToAdd().length === 0"
                  class="h-8.5 px-4 rounded-md bg-blue-600 hover:bg-blue-700 disabled:opacity-40 disabled:cursor-not-allowed text-white text-xs font-semibold cursor-pointer transition-colors shadow-2xs">
                  Add Selected
                </button>
              </div>
            </div>

          </div>
        </div>
      }

      <!-- =============================================================== -->
      <!-- MODAL 2: REMOVE PROJECT CONFIRMATION MODAL                      -->
      <!-- =============================================================== -->
      @if (projectToRemove(); as p) {
        <div
          class="fixed inset-0 z-50 bg-slate-900/40 backdrop-blur-xs flex items-center justify-center p-4 animate-in fade-in duration-150"
          (click)="projectToRemove.set(null)">
          <div
            class="w-full max-w-md bg-white border border-slate-200 rounded-xl shadow-2xl p-6 flex flex-col gap-4"
            (click)="$event.stopPropagation()">
            
            <div class="flex items-center gap-3 text-amber-600">
              <div class="w-10 h-10 rounded-lg bg-amber-50 border border-amber-200 flex items-center justify-center shrink-0">
                <app-lucide-icon name="alert-triangle" [size]="20"></app-lucide-icon>
              </div>
              <div class="flex flex-col">
                <h3 class="text-base font-bold text-slate-900 font-heading">Remove from Initiative</h3>
                <span class="text-[11px] text-slate-500 font-semibold">Portfolio Scope Adjustment</span>
              </div>
            </div>

            <p class="text-xs text-slate-700 leading-relaxed">
              Remove <strong>{{ p.name }}</strong> (<code>{{ p.key }}</code>) from this initiative? The project and its migration workloads will remain intact as standalone entities.
            </p>

            <div class="pt-3 border-t border-slate-100 flex justify-end gap-2.5">
              <button
                type="button"
                (click)="projectToRemove.set(null)"
                class="h-8.5 px-3 text-xs font-medium text-slate-700 border border-slate-200 rounded-md hover:bg-slate-50 transition-colors cursor-pointer shadow-2xs">
                Cancel
              </button>
              <button
                type="button"
                (click)="confirmRemoveProject(p.id)"
                class="h-8.5 px-4 text-xs font-semibold rounded-md bg-rose-600 hover:bg-rose-700 text-white shadow-2xs transition-colors cursor-pointer">
                Remove from Initiative
              </button>
            </div>

          </div>
        </div>
      }

    </div>
  `
})
export class InitiativeProjectsComponent {
  public ps = inject(ProjectsService);

  public isStatusOpen = signal<boolean>(false);
  public isAddModalOpen = signal<boolean>(false);
  public addModalSearch = '';
  public selectedToAdd = signal<string[]>([]);
  public projectToRemove = signal<ProjectDiscoveryItem | null>(null);

  public selectStatus(status: string): void {
    this.ps.setProjectStatusFilter(status);
    this.isStatusOpen.set(false);
  }

  public toggleSort(): void {
    const current = this.ps.projectFilters().sortBy;
    this.ps.setProjectSort(current === 'RECENT' ? 'NAME' : 'RECENT');
  }

  public openAddModal(): void {
    this.addModalSearch = '';
    this.selectedToAdd.set([]);
    this.isAddModalOpen.set(true);
  }

  public closeAddModal(): void {
    this.isAddModalOpen.set(false);
    this.selectedToAdd.set([]);
  }

  public toggleAddSelection(projectId: string): void {
    this.selectedToAdd.update(list =>
      list.includes(projectId) ? list.filter(id => id !== projectId) : [...list, projectId]
    );
  }

  public confirmAddProjects(): void {
    const active = this.ps.activeInitiative();
    if (active && this.selectedToAdd().length > 0) {
      this.ps.addProjectsToInitiative(active.id, this.selectedToAdd());
    }
    this.closeAddModal();
  }

  public openRemoveModal(project: ProjectDiscoveryItem): void {
    this.projectToRemove.set(project);
  }

  public confirmRemoveProject(projectId: string): void {
    const active = this.ps.activeInitiative();
    if (active) {
      this.ps.removeProjectFromInitiative(active.id, projectId);
    }
    this.projectToRemove.set(null);
  }

  public filteredModalAvailableProjects(): ProjectDiscoveryItem[] {
    const list = this.ps.availableProjectsForAssociation();
    const q = this.addModalSearch.trim().toLowerCase();
    if (!q) return list;
    return list.filter(p =>
      p.name.toLowerCase().includes(q) ||
      p.key.toLowerCase().includes(q)
    );
  }
}

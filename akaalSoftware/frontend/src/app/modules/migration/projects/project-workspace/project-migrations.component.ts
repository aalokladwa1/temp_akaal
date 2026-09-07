import { Component, inject, signal, HostListener } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink, Router } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { ProjectsService } from '../projects.service';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';
import { ProjectsStateFallbackComponent } from '../components/projects-state-fallback.component';
import { ProjectMigrationItem } from '../projects.models';

interface StateOption {
  label: string;
  value: string;
}

interface ModeOption {
  label: string;
  value: string;
}

@Component({
  selector: 'app-project-migrations',
  standalone: true,
  imports: [
    CommonModule,
    RouterLink,
    FormsModule,
    LucideIconComponent,
    ProjectsStateFallbackComponent
  ],
  template: `
    <div class="flex flex-col gap-6 select-none animate-in fade-in duration-150">
      
      <!-- Non-Ready State Fallback -->
      @if (ps.projectMigrationsAvailability() === 'UNAVAILABLE' || ps.projectMigrationsAvailability() === 'NOT_CONNECTED') {
        <app-projects-state-fallback
          [state]="ps.projectMigrationsAvailability()"
          entityName="migrations"
          [customErrorMessage]="ps.errorMessage() || 'Migration authority is currently unreachable or disconnected in this project context.'"
          (retry)="ps.retryConnection()">
        </app-projects-state-fallback>
      } @else if (ps.projectMigrationsAvailability() === 'UNAUTHORIZED') {
        <app-projects-state-fallback
          [state]="'UNAUTHORIZED'"
          entityName="migrations"
          customErrorMessage="You do not have operator authorization to inspect migration pipelines in this project boundary."
          (retry)="ps.retryConnection()">
        </app-projects-state-fallback>
      } @else if (ps.projectMigrationsAvailability() === 'ERROR') {
        <app-projects-state-fallback
          [state]="'ERROR'"
          entityName="migrations"
          [customErrorMessage]="ps.errorMessage() || 'Failed to load project migration inventory.'"
          (retry)="ps.retryConnection()">
        </app-projects-state-fallback>
      } @else {
        
        <!-- Main Migrations Workload Card -->
        <div class="p-6 sm:p-7 rounded-xl bg-white border border-slate-200 shadow-xs flex flex-col gap-5">
          
          <!-- Header Section: Title, Subtitle & Primary Text Action Button -->
          <div class="flex items-start justify-between pb-4 border-b border-slate-200 flex-wrap gap-4">
            <div class="flex flex-col gap-1 max-w-3xl">
              <div class="flex items-center gap-2.5">
                <h2 class="text-base font-bold text-slate-900 font-heading">
                  Migrations
                </h2>
                @if (ps.activeProjectMigrations().length > 0) {
                  <span class="px-2.5 py-0.5 rounded-md text-[11px] font-semibold bg-slate-100 text-slate-700 border border-slate-200 tabular-nums">
                    {{ ps.activeProjectMigrations().length }}
                  </span>
                }
              </div>
              <p class="text-xs text-slate-600 font-normal">
                Migration pipelines and execution workloads governed within this project boundary.
              </p>
            </div>

            <!-- Primary Action: New Migration (Text Only, No Lucide Icon, Restrained Rectangular) -->
            @if (ps.activeProject(); as proj) {
              <a
                routerLink="/migration/create"
                [queryParams]="{ projectId: proj.id }"
                class="h-8 px-3.5 rounded-md bg-blue-600 hover:bg-blue-700 active:bg-blue-800 text-white text-xs font-semibold transition-colors inline-flex items-center justify-center cursor-pointer shadow-2xs">
                New Migration
              </a>
            }
          </div>

          <!-- Controls Bar: Search, State Filter, Mode Filter & Reset -->
          <div class="flex items-center justify-between gap-3 flex-wrap">
            
            <!-- Search Box (Increased 40px Height & Clean Rectangular Framing) -->
            <div class="relative flex-1 min-w-[240px] max-w-md">
              <app-lucide-icon
                name="search"
                [size]="14"
                class="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none">
              </app-lucide-icon>
              <input
                type="text"
                [ngModel]="ps.migrationFilters().searchQuery"
                (ngModelChange)="ps.setMigrationSearch($event)"
                placeholder="Search migrations by name, key, source, target..."
                class="w-full h-9 pl-9 pr-8 rounded-md bg-slate-50 hover:bg-slate-100/70 focus:bg-white border border-slate-300 text-xs font-medium text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all shadow-2xs"
              />
              @if (ps.migrationFilters().searchQuery) {
                <button
                  type="button"
                  (click)="ps.setMigrationSearch('')"
                  class="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 text-xs font-bold cursor-pointer">
                  &times;
                </button>
              }
            </div>

            <!-- Filter Dropdowns Group -->
            <div class="flex items-center gap-2.5 flex-wrap">
              
              <!-- State Filter Dropdown -->
              <div class="relative" (click)="$event.stopPropagation()">
                <button
                  type="button"
                  (click)="toggleDropdown('state', $event)"
                  class="h-8 px-2.5 rounded-md bg-white hover:bg-slate-50 border border-slate-300 flex items-center justify-between gap-2 text-xs font-semibold text-slate-700 cursor-pointer shadow-2xs focus:outline-none focus:ring-1 focus:ring-blue-500"
                  [class.bg-blue-50]="openDropdown() === 'state'"
                  [class.border-blue-400]="openDropdown() === 'state'">
                  <span>{{ getStateFilterLabel() }}</span>
                  <app-lucide-icon name="chevron-down" [size]="12" class="text-slate-400 shrink-0"></app-lucide-icon>
                </button>

                @if (openDropdown() === 'state') {
                  <div class="absolute right-0 top-full mt-1 w-44 rounded-lg bg-white border border-slate-200 shadow-xl p-1 flex flex-col gap-0.5 z-50 animate-in fade-in zoom-in-95 duration-100">
                    @for (opt of stateOptions; track opt.value) {
                      <button
                        type="button"
                        (click)="selectStateFilter(opt.value)"
                        class="w-full text-left px-2.5 py-1.5 rounded-md text-xs font-medium text-slate-700 hover:text-slate-900 hover:bg-slate-50 transition-colors flex items-center justify-between cursor-pointer"
                        [class.bg-blue-50]="ps.migrationFilters().stateFilter === opt.value"
                        [class.text-blue-700]="ps.migrationFilters().stateFilter === opt.value">
                        <span>{{ opt.label }}</span>
                        @if (ps.migrationFilters().stateFilter === opt.value) {
                          <app-lucide-icon name="check" [size]="13" class="text-blue-600 shrink-0"></app-lucide-icon>
                        }
                      </button>
                    }
                  </div>
                }
              </div>

              <!-- Mode Filter Dropdown -->
              <div class="relative" (click)="$event.stopPropagation()">
                <button
                  type="button"
                  (click)="toggleDropdown('mode', $event)"
                  class="h-8 px-2.5 rounded-md bg-white hover:bg-slate-50 border border-slate-300 flex items-center justify-between gap-2 text-xs font-semibold text-slate-700 cursor-pointer shadow-2xs focus:outline-none focus:ring-1 focus:ring-blue-500"
                  [class.bg-blue-50]="openDropdown() === 'mode'"
                  [class.border-blue-400]="openDropdown() === 'mode'">
                  <span>{{ getModeFilterLabel() }}</span>
                  <app-lucide-icon name="chevron-down" [size]="12" class="text-slate-400 shrink-0"></app-lucide-icon>
                </button>

                @if (openDropdown() === 'mode') {
                  <div class="absolute right-0 top-full mt-1 w-44 rounded-lg bg-white border border-slate-200 shadow-xl p-1 flex flex-col gap-0.5 z-50 animate-in fade-in zoom-in-95 duration-100">
                    @for (opt of modeOptions; track opt.value) {
                      <button
                        type="button"
                        (click)="selectModeFilter(opt.value)"
                        class="w-full text-left px-2.5 py-1.5 rounded-md text-xs font-medium text-slate-700 hover:text-slate-900 hover:bg-slate-50 transition-colors flex items-center justify-between cursor-pointer"
                        [class.bg-blue-50]="ps.migrationFilters().modeFilter === opt.value"
                        [class.text-blue-700]="ps.migrationFilters().modeFilter === opt.value">
                        <span>{{ opt.label }}</span>
                        @if (ps.migrationFilters().modeFilter === opt.value) {
                          <app-lucide-icon name="check" [size]="13" class="text-blue-600 shrink-0"></app-lucide-icon>
                        }
                      </button>
                    }
                  </div>
                }
              </div>

              <!-- Clear Filters (if active) -->
              @if (isFilterActive()) {
                <button
                  type="button"
                  (click)="ps.clearMigrationFilters()"
                  class="h-8 px-2.5 rounded-md bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold transition-colors cursor-pointer">
                  Clear Filters
                </button>
              }

            </div>

          </div>

          <!-- Active Filter Banner (if filtered) -->
          @if (isFilterActive()) {
            <div class="flex items-center justify-between p-2.5 rounded-lg bg-blue-50/80 border border-blue-200 text-xs text-blue-900">
              <div class="flex items-center gap-2">
                <app-lucide-icon name="filter" [size]="13" class="text-blue-600"></app-lucide-icon>
                <span>Showing filtered results ({{ ps.filteredActiveProjectMigrations().length }} matching)</span>
              </div>
              <button
                type="button"
                (click)="ps.clearMigrationFilters()"
                class="text-blue-700 hover:text-blue-900 font-bold px-2 py-0.5 rounded hover:bg-blue-100 cursor-pointer">
                Reset Filters
              </button>
            </div>
          }

          <!-- Migrations Data Table or Empty State -->
          @if (ps.filteredActiveProjectMigrations().length === 0) {
            
            <div class="py-14 rounded-xl border border-slate-200/80 bg-slate-50/50 flex flex-col items-center justify-center text-center gap-3">
              <div class="w-12 h-12 rounded-lg bg-white border border-slate-200 flex items-center justify-center text-slate-400 shadow-2xs">
                <app-lucide-icon name="arrow-left-right" [size]="24"></app-lucide-icon>
              </div>
              <div class="flex flex-col gap-1 max-w-md">
                <h3 class="text-sm font-bold text-slate-800">
                  {{ isFilterActive() ? 'No migrations match your filter criteria' : 'No migrations in this Project' }}
                </h3>
                <p class="text-xs text-slate-500 font-normal">
                  {{ isFilterActive() ? 'Try clearing your search terms or resetting the status and mode filters.' : 'Create a migration pipeline to begin planning data movement within this project context.' }}
                </p>
              </div>
              <div class="pt-2">
                @if (isFilterActive()) {
                  <button
                    type="button"
                    (click)="ps.clearMigrationFilters()"
                    class="h-8 px-3.5 rounded-md bg-white hover:bg-slate-50 text-slate-700 border border-slate-300 text-xs font-semibold shadow-2xs transition-colors cursor-pointer">
                    Reset All Filters
                  </button>
                } @else {
                  @if (ps.activeProject(); as proj) {
                    <a
                      routerLink="/migration/create"
                      [queryParams]="{ projectId: proj.id }"
                      class="h-8 px-3.5 rounded-md bg-blue-600 hover:bg-blue-700 active:bg-blue-800 text-white text-xs font-semibold shadow-2xs transition-colors inline-flex items-center justify-center cursor-pointer">
                      New Migration
                    </a>
                  }
                }
              </div>
            </div>

          } @else {

            <!-- High-Precision Responsive Data Table with Zebra Rows -->
            <div class="overflow-x-auto rounded-xl border border-slate-200/80">
              <table class="w-full text-left border-collapse table-fixed">
                <thead>
                  <tr class="bg-slate-50 text-[10px] font-bold uppercase tracking-wider text-slate-600 border-b border-slate-200 select-none">
                    <th class="py-3 px-4 w-[28%]">Migration Pipeline</th>
                    <th class="py-3 px-4 w-[22%]">Source &rarr; Target Route</th>
                    <th class="py-3 px-4 w-[14%]">Execution Mode</th>
                    <th class="py-3 px-4 w-[14%]">Lifecycle State</th>
                    <th class="py-3 px-4 w-[12%]">Last Activity</th>
                    <th class="py-3 px-4 w-[10%] text-right">Actions</th>
                  </tr>
                </thead>
                <tbody class="divide-y divide-slate-100 text-xs">
                  @for (m of ps.filteredActiveProjectMigrations(); track m.id) {
                    <tr
                      (click)="navigateToMigration(m.id)"
                      class="hover:bg-blue-50/50 even:bg-slate-50/50 transition-colors cursor-pointer group select-none">
                      
                      <!-- 1. Pipeline Name & Key -->
                      <td class="py-3.5 px-4">
                        <div class="flex items-center gap-2.5 min-w-0">
                          <span class="px-2 py-0.5 rounded-md text-[10px] font-bold font-mono bg-blue-50 text-blue-700 border border-blue-200/80 shrink-0">
                            {{ m.key }}
                          </span>
                          <div class="flex flex-col min-w-0">
                            <span class="font-bold text-slate-900 group-hover:text-blue-700 transition-colors truncate">
                              {{ m.name }}
                            </span>
                            <span class="text-[11px] text-slate-500 truncate">
                              {{ m.currentPhase || 'Active' }}
                            </span>
                          </div>
                        </div>
                      </td>

                      <!-- 2. Source -> Target Route -->
                      <td class="py-3.5 px-4">
                        <div class="flex items-center gap-1.5 text-xs text-slate-700 font-medium truncate">
                          <span class="font-bold text-slate-800 truncate">{{ m.sourceProvider }}</span>
                          <span class="text-slate-400 font-normal shrink-0">&rarr;</span>
                          <span class="font-bold text-slate-800 truncate">{{ m.targetProvider }}</span>
                        </div>
                      </td>

                      <!-- 3. Execution Mode -->
                      <td class="py-3.5 px-4">
                        <span class="px-2 py-0.5 rounded-md text-[10.5px] font-semibold bg-slate-100 text-slate-700 border border-slate-200">
                          {{ getModeDisplayLabel(m.mode) }}
                        </span>
                      </td>

                      <!-- 4. Lifecycle State Badge -->
                      <td class="py-3.5 px-4">
                        <span
                          class="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-md text-[10.5px] font-semibold border select-none"
                          [class.bg-emerald-50]="m.lifecycleState === 'COMPLETED'"
                          [class.text-emerald-700]="m.lifecycleState === 'COMPLETED'"
                          [class.border-emerald-200]="m.lifecycleState === 'COMPLETED'"
                          [class.bg-blue-50]="m.lifecycleState === 'RUNNING'"
                          [class.text-blue-700]="m.lifecycleState === 'RUNNING'"
                          [class.border-blue-200]="m.lifecycleState === 'RUNNING'"
                          [class.bg-amber-50]="m.lifecycleState === 'ATTENTION'"
                          [class.text-amber-800]="m.lifecycleState === 'ATTENTION'"
                          [class.border-amber-300]="m.lifecycleState === 'ATTENTION'"
                          [class.bg-slate-100]="m.lifecycleState === 'PLANNING' || m.lifecycleState === 'PAUSED'"
                          [class.text-slate-700]="m.lifecycleState === 'PLANNING' || m.lifecycleState === 'PAUSED'"
                          [class.border-slate-200]="m.lifecycleState === 'PLANNING' || m.lifecycleState === 'PAUSED'">
                          <span
                            class="w-1.5 h-1.5 rounded-xs"
                            [class.bg-emerald-500]="m.lifecycleState === 'COMPLETED'"
                            [class.bg-blue-500]="m.lifecycleState === 'RUNNING'"
                            [class.bg-amber-500]="m.lifecycleState === 'ATTENTION'"
                            [class.bg-slate-400]="m.lifecycleState === 'PLANNING' || m.lifecycleState === 'PAUSED'">
                          </span>
                          <span>{{ m.lifecycleState }}</span>
                        </span>
                      </td>

                      <!-- 5. Last Activity Timestamp -->
                      <td class="py-3.5 px-4 text-slate-600 font-medium whitespace-nowrap">
                        <span class="text-xs tabular-nums font-mono">
                          {{ m.lastActivityAt | date:'MMM d, HH:mm' }}
                        </span>
                      </td>

                      <!-- 6. Actions (Move Migration) -->
                      <td class="py-3.5 px-4 text-right" (click)="$event.stopPropagation()">
                        <button
                          type="button"
                          (click)="ps.openMoveMigrationModal(m)"
                          class="h-7 px-2.5 rounded-md border border-slate-200 hover:border-slate-300 bg-white hover:bg-slate-50 text-slate-700 text-[11px] font-semibold transition-colors cursor-pointer shadow-2xs"
                          title="Reassign migration to another project within workspace">
                          Move
                        </button>
                      </td>

                    </tr>
                  }
                </tbody>
              </table>
            </div>

          }

        </div>

      }

      <!-- Move Migration Governed Modal Overlay -->
      @if (ps.moveMigrationModalItem(); as targetMig) {
        <div
          role="dialog"
          aria-modal="true"
          class="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-4 animate-in fade-in duration-100"
          (click)="ps.closeMoveMigrationModal()">
          <div
            class="w-full max-w-lg rounded-xl bg-white border border-slate-200 p-6 flex flex-col gap-4 shadow-xl"
            (click)="$event.stopPropagation()">
            
            <!-- Modal Header -->
            <div class="flex items-start justify-between pb-3 border-b border-slate-200">
              <div class="flex flex-col gap-0.5">
                <h3 class="text-sm font-bold text-slate-900 font-heading">
                  Move Migration Pipeline
                </h3>
                <span class="text-xs text-slate-500 font-medium">
                  Governed Project Reassignment
                </span>
              </div>
              <button
                type="button"
                (click)="ps.closeMoveMigrationModal()"
                class="text-slate-400 hover:text-slate-600 text-sm font-bold cursor-pointer">
                &times;
              </button>
            </div>

            <!-- Migration Detail Card -->
            <div class="p-3 rounded-lg bg-slate-50 border border-slate-200 flex flex-col gap-2 text-xs">
              <div class="flex items-center justify-between">
                <div class="flex items-center gap-2">
                  <span class="px-2 py-0.5 rounded-md text-[10px] font-bold font-mono bg-blue-50 text-blue-700 border border-blue-200">
                    {{ targetMig.key }}
                  </span>
                  <span class="font-bold text-slate-900">{{ targetMig.name }}</span>
                </div>
                <span class="px-2 py-0.5 rounded-md text-[10px] font-semibold bg-white border border-slate-200 text-slate-700">
                  {{ targetMig.mode }}
                </span>
              </div>
              <div class="flex items-center justify-between text-[11px] text-slate-600 border-t border-slate-200/60 pt-1.5">
                <span>Current Project: <strong class="text-slate-800">{{ ps.activeProject()?.name || targetMig.projectId }}</strong></span>
                <span>State: <strong class="text-slate-800">{{ targetMig.lifecycleState }}</strong></span>
              </div>
            </div>

            <!-- Condition 1: Active Execution Lock Banner -->
            @if (targetMig.lifecycleState === 'RUNNING' || targetMig.lifecycleState === 'ATTENTION') {
              <div class="p-3 rounded-lg bg-amber-50 border border-amber-200 text-amber-900 flex flex-col gap-1 text-xs">
                <span class="font-bold flex items-center gap-1.5">
                  Active Execution In Progress
                </span>
                <p class="text-[11px] text-amber-800 font-normal leading-relaxed">
                  Reassigning an active or attention-required pipeline is prohibited while worker execution is active to prevent runtime desynchronization. Complete or pause the migration before moving.
                </p>
              </div>
            } @else if (ps.availableDestinationProjects().length === 0) {
              <!-- Condition 2: No Available Destination Projects -->
              <div class="p-3 rounded-lg bg-slate-100 border border-slate-200 text-slate-800 flex flex-col gap-1 text-xs">
                <span class="font-bold">No Destination Projects Available</span>
                <p class="text-[11px] text-slate-600 font-normal leading-relaxed">
                  There are no other active projects in the current workspace. To reassign this migration, create a target project first.
                </p>
              </div>
            } @else {
              <!-- Condition 3: Select Destination Project Dropdown -->
              <div class="flex flex-col gap-1.5">
                <label class="text-xs font-bold text-slate-800">
                  Destination Project <span class="text-rose-500">*</span>
                </label>
                <div class="relative">
                  <select
                    [ngModel]="ps.selectedDestinationProjectId()"
                    (ngModelChange)="ps.setSelectedDestinationProjectId($event)"
                    class="w-full h-9 px-3 rounded-md bg-white border border-slate-300 text-xs font-medium text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 cursor-pointer">
                    @for (proj of ps.availableDestinationProjects(); track proj.id) {
                      <option [value]="proj.id">
                        {{ proj.name }} ({{ proj.key }}){{ proj.initiativeName ? ' — Initiative: ' + proj.initiativeName : ' — Standalone' }}
                      </option>
                    }
                  </select>
                </div>
                <span class="text-[11px] text-slate-500 font-normal">
                  Target project must reside within the current workspace boundary. Cross-workspace movement is prohibited.
                </span>
              </div>

              <div class="p-3 rounded-lg bg-blue-50/70 border border-blue-200 text-blue-900 text-xs flex flex-col gap-1">
                <span class="font-bold">Governed Portfolio Action</span>
                <p class="text-[11px] text-blue-800 font-normal leading-relaxed">
                  Moving this migration updates its project oversight, access inheritance, and telemetry aggregation within this workspace.
                </p>
              </div>
            }

            <!-- Modal Actions -->
            <div class="flex items-center justify-end gap-2.5 pt-3 border-t border-slate-200">
              <button
                type="button"
                (click)="ps.closeMoveMigrationModal()"
                class="h-8 px-3 text-xs font-medium text-slate-700 border border-slate-300 rounded-md bg-white hover:bg-slate-50 transition-colors cursor-pointer">
                Cancel
              </button>

              <button
                type="button"
                (click)="ps.submitMoveMigrationIntent()"
                [disabled]="targetMig.lifecycleState === 'RUNNING' || targetMig.lifecycleState === 'ATTENTION' || ps.availableDestinationProjects().length === 0 || !ps.selectedDestinationProjectId()"
                class="h-8 px-4 text-xs font-semibold rounded-md bg-blue-600 hover:bg-blue-700 text-white disabled:opacity-40 disabled:pointer-events-none transition-colors cursor-pointer shadow-2xs">
                Move Migration
              </button>
            </div>

          </div>
        </div>
      }

    </div>
  `
})
export class ProjectMigrationsComponent {
  public ps = inject(ProjectsService);
  private router = inject(Router);

  public openDropdown = signal<'state' | 'mode' | null>(null);

  public stateOptions: StateOption[] = [
    { label: 'All States', value: 'ALL' },
    { label: 'Running', value: 'RUNNING' },
    { label: 'Needs Attention', value: 'ATTENTION' },
    { label: 'Completed', value: 'COMPLETED' },
    { label: 'Planning', value: 'PLANNING' },
    { label: 'Paused', value: 'PAUSED' }
  ];

  public modeOptions: ModeOption[] = [
    { label: 'All Modes', value: 'ALL' },
    { label: 'Online CDC', value: 'ONLINE_CDC' },
    { label: 'Offline Bulk', value: 'OFFLINE_BULK' },
    { label: 'Dual-Run Sync', value: 'DUAL_RUN' },
    { label: 'Schema Only', value: 'SCHEMA_ONLY' }
  ];

  @HostListener('document:click')
  public onDocumentClick(): void {
    this.openDropdown.set(null);
  }

  public toggleDropdown(dropdown: 'state' | 'mode', event: Event): void {
    event.stopPropagation();
    if (this.openDropdown() === dropdown) {
      this.openDropdown.set(null);
    } else {
      this.openDropdown.set(dropdown);
    }
  }

  public selectStateFilter(value: string): void {
    this.ps.setMigrationStateFilter(value);
    this.openDropdown.set(null);
  }

  public selectModeFilter(value: string): void {
    this.ps.setMigrationModeFilter(value);
    this.openDropdown.set(null);
  }

  public getStateFilterLabel(): string {
    const val = this.ps.migrationFilters().stateFilter;
    const found = this.stateOptions.find(o => o.value === val);
    return found ? found.label : 'All States';
  }

  public getModeFilterLabel(): string {
    const val = this.ps.migrationFilters().modeFilter;
    const found = this.modeOptions.find(o => o.value === val);
    return found ? found.label : 'All Modes';
  }

  public getModeDisplayLabel(mode: string): string {
    switch (mode) {
      case 'ONLINE_CDC': return 'Online CDC';
      case 'OFFLINE_BULK': return 'Offline Bulk';
      case 'DUAL_RUN': return 'Dual-Run Sync';
      case 'SCHEMA_ONLY': return 'Schema Only';
      default: return mode;
    }
  }

  public isFilterActive(): boolean {
    const f = this.ps.migrationFilters();
    return !!f.searchQuery || f.stateFilter !== 'ALL' || f.modeFilter !== 'ALL';
  }

  public navigateToMigration(id: string): void {
    this.router.navigate(['/migration/cockpit', id]);
  }
}

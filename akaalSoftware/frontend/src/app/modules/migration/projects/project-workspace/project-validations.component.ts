import { Component, inject, signal, HostListener } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink, Router } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { ProjectsService } from '../projects.service';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';
import { ProjectsStateFallbackComponent } from '../components/projects-state-fallback.component';
import { ProjectValidationItem } from '../projects.models';

interface StateOption {
  label: string;
  value: string;
}

interface StrategyOption {
  label: string;
  value: string;
}

@Component({
  selector: 'app-project-validations',
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
      @if (ps.projectValidationsAvailability() === 'UNAVAILABLE' || ps.projectValidationsAvailability() === 'NOT_CONNECTED') {
        <app-projects-state-fallback
          [state]="ps.projectValidationsAvailability()"
          entityName="validations"
          [customErrorMessage]="ps.errorMessage() || 'Validation authority (#11) is currently unreachable or disconnected in this project context.'"
          (retry)="ps.retryConnection()">
        </app-projects-state-fallback>
      } @else if (ps.projectValidationsAvailability() === 'UNAUTHORIZED') {
        <app-projects-state-fallback
          [state]="'UNAUTHORIZED'"
          entityName="validations"
          customErrorMessage="You do not have operator authorization to inspect validation missions in this project boundary."
          (retry)="ps.retryConnection()">
        </app-projects-state-fallback>
      } @else if (ps.projectValidationsAvailability() === 'ERROR') {
        <app-projects-state-fallback
          [state]="'ERROR'"
          entityName="validations"
          [customErrorMessage]="ps.errorMessage() || 'Failed to load project validation inventory.'"
          (retry)="ps.retryConnection()">
        </app-projects-state-fallback>
      } @else {
        
        <!-- Main Validations Workload Card -->
        <div class="p-6 sm:p-7 rounded-xl bg-white border border-slate-200 shadow-xs flex flex-col gap-5">
          
          <!-- Header Section: Title, Subtitle & Primary Text Action Button -->
          <div class="flex items-start justify-between pb-4 border-b border-slate-200 flex-wrap gap-4">
            <div class="flex flex-col gap-1 max-w-3xl">
              <div class="flex items-center gap-2.5">
                <h2 class="text-base font-bold text-slate-900 font-heading">
                  Validations
                </h2>
                @if (ps.activeProjectValidations().length > 0) {
                  <span class="px-2.5 py-0.5 rounded-md text-[11px] font-semibold bg-slate-100 text-slate-700 border border-slate-200 tabular-nums">
                    {{ ps.activeProjectValidations().length }}
                  </span>
                }
              </div>
              <p class="text-xs text-slate-600 font-normal">
                Verification missions, schema audits, and data parity assertions associated with this project boundary.
              </p>
            </div>

            <!-- Primary Action: Create Validation (Text Only, No Lucide Icon, Restrained Rectangular) -->
            @if (ps.activeProject(); as proj) {
              <a
                routerLink="/migration/validation/new"
                [queryParams]="{ projectId: proj.id }"
                class="h-8 px-3.5 rounded-md bg-blue-600 hover:bg-blue-700 active:bg-blue-800 text-white text-xs font-semibold transition-colors inline-flex items-center justify-center cursor-pointer shadow-2xs">
                Create Validation
              </a>
            }
          </div>

          <!-- Controls Bar: Search, Outcome/State Filter, Strategy Filter & Reset -->
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
                [ngModel]="ps.validationFilters().searchQuery"
                (ngModelChange)="ps.setValidationSearch($event)"
                placeholder="Search validations by name, scope, source, target..."
                class="w-full h-9 pl-9 pr-8 rounded-md bg-slate-50 hover:bg-slate-100/70 focus:bg-white border border-slate-300 text-xs font-medium text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all shadow-2xs"
              />
              @if (ps.validationFilters().searchQuery) {
                <button
                  type="button"
                  (click)="ps.setValidationSearch('')"
                  class="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 text-xs font-bold cursor-pointer">
                  &times;
                </button>
              }
            </div>

            <!-- Filter Dropdowns Group -->
            <div class="flex items-center gap-2.5 flex-wrap">
              
              <!-- State / Outcome Filter Dropdown -->
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
                  <div class="absolute right-0 top-full mt-1 w-48 rounded-lg bg-white border border-slate-200 shadow-xl p-1 flex flex-col gap-0.5 z-50 animate-in fade-in zoom-in-95 duration-100">
                    @for (opt of stateOptions; track opt.value) {
                      <button
                        type="button"
                        (click)="selectStateFilter(opt.value)"
                        class="w-full text-left px-2.5 py-1.5 rounded-md text-xs font-medium text-slate-700 hover:text-slate-900 hover:bg-slate-50 transition-colors flex items-center justify-between cursor-pointer"
                        [class.bg-blue-50]="ps.validationFilters().stateFilter === opt.value"
                        [class.text-blue-700]="ps.validationFilters().stateFilter === opt.value">
                        <span>{{ opt.label }}</span>
                        @if (ps.validationFilters().stateFilter === opt.value) {
                          <app-lucide-icon name="check" [size]="13" class="text-blue-600 shrink-0"></app-lucide-icon>
                        }
                      </button>
                    }
                  </div>
                }
              </div>

              <!-- Strategy Filter Dropdown -->
              <div class="relative" (click)="$event.stopPropagation()">
                <button
                  type="button"
                  (click)="toggleDropdown('strategy', $event)"
                  class="h-8 px-2.5 rounded-md bg-white hover:bg-slate-50 border border-slate-300 flex items-center justify-between gap-2 text-xs font-semibold text-slate-700 cursor-pointer shadow-2xs focus:outline-none focus:ring-1 focus:ring-blue-500"
                  [class.bg-blue-50]="openDropdown() === 'strategy'"
                  [class.border-blue-400]="openDropdown() === 'strategy'">
                  <span>{{ getStrategyFilterLabel() }}</span>
                  <app-lucide-icon name="chevron-down" [size]="12" class="text-slate-400 shrink-0"></app-lucide-icon>
                </button>

                @if (openDropdown() === 'strategy') {
                  <div class="absolute right-0 top-full mt-1 w-52 rounded-lg bg-white border border-slate-200 shadow-xl p-1 flex flex-col gap-0.5 z-50 animate-in fade-in zoom-in-95 duration-100">
                    @for (opt of strategyOptions; track opt.value) {
                      <button
                        type="button"
                        (click)="selectStrategyFilter(opt.value)"
                        class="w-full text-left px-2.5 py-1.5 rounded-md text-xs font-medium text-slate-700 hover:text-slate-900 hover:bg-slate-50 transition-colors flex items-center justify-between cursor-pointer"
                        [class.bg-blue-50]="ps.validationFilters().strategyFilter === opt.value"
                        [class.text-blue-700]="ps.validationFilters().strategyFilter === opt.value">
                        <span>{{ opt.label }}</span>
                        @if (ps.validationFilters().strategyFilter === opt.value) {
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
                  (click)="ps.clearValidationFilters()"
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
                <span>Showing filtered validation missions ({{ ps.filteredActiveProjectValidations().length }} matching)</span>
              </div>
              <button
                type="button"
                (click)="ps.clearValidationFilters()"
                class="text-blue-700 hover:text-blue-900 font-bold px-2 py-0.5 rounded hover:bg-blue-100 cursor-pointer">
                Reset Filters
              </button>
            </div>
          }

          <!-- Validations Data Table or Empty State -->
          @if (ps.filteredActiveProjectValidations().length === 0) {
            
            <div class="py-14 rounded-xl border border-slate-200/80 bg-slate-50/50 flex flex-col items-center justify-center text-center gap-3">
              <div class="w-12 h-12 rounded-lg bg-white border border-slate-200 flex items-center justify-center text-slate-400 shadow-2xs">
                <app-lucide-icon name="check-circle-2" [size]="24"></app-lucide-icon>
              </div>
              <div class="flex flex-col gap-1 max-w-md">
                <h3 class="text-sm font-bold text-slate-800">
                  {{ isFilterActive() ? 'No validation missions match your filter criteria' : 'No Validation Missions in this Project' }}
                </h3>
                <p class="text-xs text-slate-500 font-normal">
                  {{ isFilterActive() ? 'Try clearing your search terms or resetting the state and strategy filters.' : 'Create a Validation Mission to verify schema parity, row cardinality, or full attribute integrity.' }}
                </p>
              </div>
              <div class="pt-2">
                @if (isFilterActive()) {
                  <button
                    type="button"
                    (click)="ps.clearValidationFilters()"
                    class="h-8 px-3.5 rounded-md bg-white hover:bg-slate-50 text-slate-700 border border-slate-300 text-xs font-semibold shadow-2xs transition-colors cursor-pointer">
                    Reset All Filters
                  </button>
                } @else {
                  @if (ps.activeProject(); as proj) {
                    <a
                      routerLink="/migration/validation/new"
                      [queryParams]="{ projectId: proj.id }"
                      class="h-8 px-3.5 rounded-md bg-blue-600 hover:bg-blue-700 active:bg-blue-800 text-white text-xs font-semibold shadow-2xs transition-colors inline-flex items-center justify-center cursor-pointer">
                      Create Validation
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
                    <th class="py-3 px-4 w-[34%]">Validation Mission &amp; Scope</th>
                    <th class="py-3 px-4 w-[22%]">Route</th>
                    <th class="py-3 px-4 w-[16%]">Strategy</th>
                    <th class="py-3 px-4 w-[16%]">Outcome / State</th>
                    <th class="py-3 px-4 w-[12%]">Last Run</th>
                  </tr>
                </thead>
                <tbody class="divide-y divide-slate-100 text-xs">
                  @for (v of ps.filteredActiveProjectValidations(); track v.id) {
                    <tr
                      (click)="navigateToValidation(v.id)"
                      class="hover:bg-blue-50/50 even:bg-slate-50/50 transition-colors cursor-pointer group select-none">
                      
                      <!-- 1. Mission Name, Key & Scope -->
                      <td class="py-3.5 px-4">
                        <div class="flex items-center gap-2.5 min-w-0">
                          <span class="px-2 py-0.5 rounded-md text-[10px] font-bold font-mono bg-emerald-50 text-emerald-700 border border-emerald-200/80 shrink-0">
                            {{ v.key }}
                          </span>
                          <div class="flex flex-col min-w-0">
                            <span class="font-bold text-slate-900 group-hover:text-blue-700 transition-colors truncate">
                              {{ v.name }}
                            </span>
                            <span class="text-[11px] text-slate-500 font-mono truncate">
                              {{ v.scopeName }}
                            </span>
                          </div>
                        </div>
                      </td>

                      <!-- 2. Source -> Target Route -->
                      <td class="py-3.5 px-4">
                        <div class="flex items-center gap-1.5 text-xs text-slate-700 font-medium truncate">
                          <span class="font-bold text-slate-800 truncate">{{ v.sourceProvider }}</span>
                          <span class="text-slate-400 font-normal shrink-0">&rarr;</span>
                          <span class="font-bold text-slate-800 truncate">{{ v.targetProvider }}</span>
                        </div>
                      </td>

                      <!-- 3. Strategy Tag -->
                      <td class="py-3.5 px-4">
                        <span class="px-2 py-0.5 rounded-md text-[10.5px] font-semibold bg-slate-100 text-slate-700 border border-slate-200">
                          {{ v.strategy }}
                        </span>
                      </td>

                      <!-- 4. Outcome / Canonical State Badge -->
                      <td class="py-3.5 px-4">
                        <span
                          class="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-md text-[10.5px] font-semibold border select-none"
                          [class.bg-emerald-50]="v.outcome === 'Validated' || v.state === 'COMPLETED'"
                          [class.text-emerald-700]="v.outcome === 'Validated' || v.state === 'COMPLETED'"
                          [class.border-emerald-200]="v.outcome === 'Validated' || v.state === 'COMPLETED'"
                          [class.bg-amber-50]="v.outcome === 'Discrepancies Found' || v.state === 'ATTENTION'"
                          [class.text-amber-800]="v.outcome === 'Discrepancies Found' || v.state === 'ATTENTION'"
                          [class.border-amber-300]="v.outcome === 'Discrepancies Found' || v.state === 'ATTENTION'"
                          [class.bg-blue-50]="v.state === 'RUNNING'"
                          [class.text-blue-700]="v.state === 'RUNNING'"
                          [class.border-blue-200]="v.state === 'RUNNING'"
                          [class.bg-slate-100]="v.state === 'SCHEDULED'"
                          [class.text-slate-700]="v.state === 'SCHEDULED'"
                          [class.border-slate-200]="v.state === 'SCHEDULED'">
                          <span
                            class="w-1.5 h-1.5 rounded-xs"
                            [class.bg-emerald-500]="v.outcome === 'Validated' || v.state === 'COMPLETED'"
                            [class.bg-amber-500]="v.outcome === 'Discrepancies Found' || v.state === 'ATTENTION'"
                            [class.bg-blue-500]="v.state === 'RUNNING'"
                            [class.bg-slate-400]="v.state === 'SCHEDULED'">
                          </span>
                          <span>{{ v.outcome || v.state }}</span>
                        </span>
                      </td>

                      <!-- 5. Last Run Timestamp -->
                      <td class="py-3.5 px-4 text-slate-600 font-medium whitespace-nowrap">
                        <span class="text-xs tabular-nums font-mono">
                          {{ v.lastRunAt ? (v.lastRunAt | date:'MMM d, HH:mm') : (v.nextRunAt ? ('Sched: ' + (v.nextRunAt | date:'MMM d')) : '&mdash;') }}
                        </span>
                      </td>

                    </tr>
                  }
                </tbody>
              </table>
            </div>

          }

        </div>

      }

    </div>
  `
})
export class ProjectValidationsComponent {
  public ps = inject(ProjectsService);
  private router = inject(Router);

  public openDropdown = signal<'state' | 'strategy' | null>(null);

  public stateOptions: StateOption[] = [
    { label: 'All Outcomes', value: 'ALL' },
    { label: 'Validated', value: 'Validated' },
    { label: 'Discrepancies Found', value: 'Discrepancies Found' },
    { label: 'Running', value: 'RUNNING' },
    { label: 'Scheduled', value: 'SCHEDULED' }
  ];

  public strategyOptions: StrategyOption[] = [
    { label: 'All Strategies', value: 'ALL' },
    { label: 'Structural', value: 'Structural' },
    { label: 'Cardinality', value: 'Cardinality' },
    { label: 'Partition Fingerprint', value: 'Partition Fingerprint' },
    { label: 'Complete Attribute', value: 'Complete Attribute' }
  ];

  @HostListener('document:click')
  public onDocumentClick(): void {
    this.openDropdown.set(null);
  }

  public toggleDropdown(dropdown: 'state' | 'strategy', event: Event): void {
    event.stopPropagation();
    if (this.openDropdown() === dropdown) {
      this.openDropdown.set(null);
    } else {
      this.openDropdown.set(dropdown);
    }
  }

  public selectStateFilter(value: string): void {
    this.ps.setValidationStateFilter(value);
    this.openDropdown.set(null);
  }

  public selectStrategyFilter(value: string): void {
    this.ps.setValidationStrategyFilter(value);
    this.openDropdown.set(null);
  }

  public getStateFilterLabel(): string {
    const val = this.ps.validationFilters().stateFilter;
    const found = this.stateOptions.find(o => o.value === val);
    return found ? found.label : 'All Outcomes';
  }

  public getStrategyFilterLabel(): string {
    const val = this.ps.validationFilters().strategyFilter;
    const found = this.strategyOptions.find(o => o.value === val);
    return found ? found.label : 'All Strategies';
  }

  public isFilterActive(): boolean {
    const f = this.ps.validationFilters();
    return !!f.searchQuery || f.stateFilter !== 'ALL' || f.strategyFilter !== 'ALL';
  }

  public navigateToValidation(id: string): void {
    this.router.navigate(['/migration/validation/val-mission-11']);
  }
}

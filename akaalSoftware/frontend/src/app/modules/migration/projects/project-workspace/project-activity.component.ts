import { Component, inject, signal, HostListener } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink, Router } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { ProjectsService } from '../projects.service';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';
import { ProjectsStateFallbackComponent } from '../components/projects-state-fallback.component';
import { ProjectActivityItem, ProjectActivityCategory } from '../projects.models';

interface CategoryOption {
  label: string;
  value: ProjectActivityCategory;
}

@Component({
  selector: 'app-project-activity',
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
      @if (ps.projectActivityAvailability() === 'UNAVAILABLE' || ps.projectActivityAvailability() === 'NOT_CONNECTED') {
        <app-projects-state-fallback
          [state]="ps.projectActivityAvailability()"
          entityName="activity"
          [customErrorMessage]="ps.errorMessage() || 'Activity stream is currently unreachable or disconnected in this project context.'"
          (retry)="ps.retryConnection()">
        </app-projects-state-fallback>
      } @else if (ps.projectActivityAvailability() === 'UNAUTHORIZED') {
        <app-projects-state-fallback
          [state]="'UNAUTHORIZED'"
          entityName="activity"
          customErrorMessage="You do not have operator authorization to inspect the activity stream in this project boundary."
          (retry)="ps.retryConnection()">
        </app-projects-state-fallback>
      } @else if (ps.projectActivityAvailability() === 'ERROR') {
        <app-projects-state-fallback
          [state]="'ERROR'"
          entityName="activity"
          [customErrorMessage]="ps.errorMessage() || 'Failed to load project activity stream.'"
          (retry)="ps.retryConnection()">
        </app-projects-state-fallback>
      } @else {
        
        <!-- Main Activity Card -->
        <div class="p-6 sm:p-7 rounded-xl bg-white border border-slate-200 shadow-xs flex flex-col gap-5">
          
          <!-- Header Section: Title & Scope Summary -->
          <div class="flex items-start justify-between pb-4 border-b border-slate-200 flex-wrap gap-4">
            <div class="flex flex-col gap-1 max-w-3xl">
              <div class="flex items-center gap-2.5">
                <h2 class="text-base font-bold text-slate-900 font-heading">
                  Project Activity
                </h2>
                @if (ps.activeProjectDetailedActivities().length > 0) {
                  <span class="px-2.5 py-0.5 rounded-md text-[11px] font-semibold bg-slate-100 text-slate-700 border border-slate-200 tabular-nums">
                    {{ ps.activeProjectDetailedActivities().length }}
                  </span>
                }
              </div>
              <p class="text-xs text-slate-600 font-normal">
                Chronological operator context regarding pipeline lifecycles, validation milestones, resource intents, and governance events.
              </p>
            </div>

            <!-- Inherited Context Chip -->
            <div class="flex items-center gap-2 text-xs text-slate-500 font-medium bg-slate-50 px-3 py-1.5 rounded-lg border border-slate-200 shrink-0">
              <app-lucide-icon name="activity" [size]="14" class="text-blue-600"></app-lucide-icon>
              <span>Operator Event Context</span>
            </div>
          </div>

          <!-- Boundary Clarification Banner (Activity != Audit) -->
          <div class="p-3.5 rounded-lg bg-blue-50/70 border border-blue-200 text-blue-950 flex items-start gap-3">
            <app-lucide-icon name="info" [size]="16" class="text-blue-600 shrink-0 mt-0.5"></app-lucide-icon>
            <div class="flex flex-col gap-0.5 text-xs">
              <span class="font-bold text-blue-900">Activity &ne; Forensic Audit</span>
              <p class="text-blue-800 text-[11px] leading-relaxed">
                Project Activity provides contextual operator telemetry for everyday operations. Formal, immutable compliance records and non-repudiable audit evidence are managed independently in the Security &amp; Audit domain.
              </p>
            </div>
          </div>

          <!-- Controls Bar: Search, Category Filter & Reset -->
          <div class="flex items-center justify-between gap-3 flex-wrap">
            
            <!-- Search Box -->
            <div class="relative flex-1 min-w-[240px] max-w-md">
              <app-lucide-icon
                name="search"
                [size]="14"
                class="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none">
              </app-lucide-icon>
              <input
                type="text"
                [ngModel]="ps.activityFilters().searchQuery"
                (ngModelChange)="ps.setActivitySearch($event)"
                placeholder="Search activity by title, description, actor, or subject..."
                class="w-full h-9 pl-9 pr-8 rounded-md bg-slate-50 hover:bg-slate-100/70 focus:bg-white border border-slate-300 text-xs font-medium text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all shadow-2xs"
              />
              @if (ps.activityFilters().searchQuery) {
                <button
                  type="button"
                  (click)="ps.setActivitySearch('')"
                  class="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 text-xs font-bold cursor-pointer">
                  &times;
                </button>
              }
            </div>

            <!-- Filter Dropdowns Group -->
            <div class="flex items-center gap-2.5 flex-wrap">
              
              <!-- Category Filter Dropdown -->
              <div class="relative" (click)="$event.stopPropagation()">
                <button
                  type="button"
                  (click)="toggleDropdown('category', $event)"
                  class="h-8 px-2.5 rounded-md bg-white hover:bg-slate-50 border border-slate-300 flex items-center justify-between gap-2 text-xs font-semibold text-slate-700 cursor-pointer shadow-2xs focus:outline-none focus:ring-1 focus:ring-blue-500"
                  [class.bg-blue-50]="openDropdown() === 'category'"
                  [class.border-blue-400]="openDropdown() === 'category'">
                  <span>{{ getCategoryFilterLabel() }}</span>
                  <app-lucide-icon name="chevron-down" [size]="12" class="text-slate-400 shrink-0"></app-lucide-icon>
                </button>

                @if (openDropdown() === 'category') {
                  <div class="absolute right-0 top-full mt-1 w-44 rounded-lg bg-white border border-slate-200 shadow-xl p-1 flex flex-col gap-0.5 z-50 animate-in fade-in zoom-in-95 duration-100">
                    @for (opt of categoryOptions; track opt.value) {
                      <button
                        type="button"
                        (click)="selectCategoryFilter(opt.value)"
                        class="w-full text-left px-2.5 py-1.5 rounded-md text-xs font-medium text-slate-700 hover:text-slate-900 hover:bg-slate-50 transition-colors flex items-center justify-between cursor-pointer"
                        [class.bg-blue-50]="ps.activityFilters().categoryFilter === opt.value"
                        [class.text-blue-700]="ps.activityFilters().categoryFilter === opt.value">
                        <span>{{ opt.label }}</span>
                        @if (ps.activityFilters().categoryFilter === opt.value) {
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
                  (click)="ps.clearActivityFilters()"
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
                <span>Showing filtered events ({{ ps.filteredActiveProjectActivities().length }} matching)</span>
              </div>
              <button
                type="button"
                (click)="ps.clearActivityFilters()"
                class="text-blue-700 hover:text-blue-900 font-bold px-2 py-0.5 rounded hover:bg-blue-100 cursor-pointer">
                Reset Filters
              </button>
            </div>
          }

          <!-- Activity List or Empty State -->
          @if (ps.filteredActiveProjectActivities().length === 0) {
            
            <div class="py-14 rounded-xl border border-slate-200/80 bg-slate-50/50 flex flex-col items-center justify-center text-center gap-3">
              <div class="w-12 h-12 rounded-lg bg-white border border-slate-200 flex items-center justify-center text-slate-400 shadow-2xs">
                <app-lucide-icon name="activity" [size]="24"></app-lucide-icon>
              </div>
              <div class="flex flex-col gap-1 max-w-md">
                <h3 class="text-sm font-bold text-slate-800">
                  {{ isFilterActive() ? 'No events match your filter criteria' : 'No Activity in this Project' }}
                </h3>
                <p class="text-xs text-slate-500 font-normal">
                  {{ isFilterActive() ? 'Try clearing your search terms or resetting the category filter.' : 'Operational events will appear as migration pipelines, validations, and resource associations are exercised.' }}
                </p>
              </div>
              <div class="pt-2">
                @if (isFilterActive()) {
                  <button
                    type="button"
                    (click)="ps.clearActivityFilters()"
                    class="h-8 px-3.5 rounded-md bg-white hover:bg-slate-50 text-slate-700 border border-slate-300 text-xs font-semibold shadow-2xs transition-colors cursor-pointer">
                    Reset All Filters
                  </button>
                }
              </div>
            </div>

          } @else {

            <!-- Chronological Event Stream Table -->
            <div class="overflow-x-auto rounded-xl border border-slate-200/80">
              <table class="w-full text-left border-collapse table-fixed">
                <thead>
                  <tr class="bg-slate-50 text-[10px] font-bold uppercase tracking-wider text-slate-600 border-b border-slate-200 select-none">
                    <th class="py-3 px-4 w-[16%]">Timestamp</th>
                    <th class="py-3 px-4 w-[14%]">Category</th>
                    <th class="py-3 px-4 w-[42%]">Event Description</th>
                    <th class="py-3 px-4 w-[16%]">Initiator / Actor</th>
                    <th class="py-3 px-3 w-[12%] text-right">Action</th>
                  </tr>
                </thead>
                <tbody class="divide-y divide-slate-100 text-xs">
                  @for (act of ps.filteredActiveProjectActivities(); track act.id) {
                    <tr class="hover:bg-blue-50/50 even:bg-slate-50/50 transition-colors select-none">
                      
                      <!-- 1. Timestamp -->
                      <td class="py-3.5 px-4 text-slate-600 font-mono text-[11px] whitespace-nowrap">
                        {{ act.occurredAt | date:'MMM d, HH:mm' }}
                      </td>

                      <!-- 2. Category Badge -->
                      <td class="py-3.5 px-4">
                        <span
                          class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md text-[10.5px] font-semibold border select-none"
                          [class.bg-blue-50]="act.category === 'MIGRATION'"
                          [class.text-blue-700]="act.category === 'MIGRATION'"
                          [class.border-blue-200]="act.category === 'MIGRATION'"
                          [class.bg-emerald-50]="act.category === 'VALIDATION'"
                          [class.text-emerald-700]="act.category === 'VALIDATION'"
                          [class.border-emerald-200]="act.category === 'VALIDATION'"
                          [class.bg-amber-50]="act.category === 'GOVERNANCE'"
                          [class.text-amber-800]="act.category === 'GOVERNANCE'"
                          [class.border-amber-200]="act.category === 'GOVERNANCE'"
                          [class.bg-purple-50]="act.category === 'ACCESS'"
                          [class.text-purple-700]="act.category === 'ACCESS'"
                          [class.border-purple-200]="act.category === 'ACCESS'"
                          [class.bg-slate-100]="act.category === 'METADATA' || act.category === 'RESOURCE' || act.category === 'SYSTEM'"
                          [class.text-slate-700]="act.category === 'METADATA' || act.category === 'RESOURCE' || act.category === 'SYSTEM'"
                          [class.border-slate-200]="act.category === 'METADATA' || act.category === 'RESOURCE' || act.category === 'SYSTEM'">
                          <span>{{ act.category }}</span>
                        </span>
                      </td>

                      <!-- 3. Event Title & Narrative -->
                      <td class="py-3.5 px-4">
                        <div class="flex flex-col min-w-0">
                          <span class="font-bold text-slate-900 truncate">{{ act.title }}</span>
                          <span class="text-[11px] text-slate-500 line-clamp-1">{{ act.description }}</span>
                        </div>
                      </td>

                      <!-- 4. Actor / Initiator -->
                      <td class="py-3.5 px-4">
                        <div class="flex items-center gap-1.5 text-xs text-slate-700 font-medium truncate">
                          <span class="truncate">{{ act.actorName }}</span>
                          @if (act.actorType === 'SERVICE_ACCOUNT' || act.actorType === 'SYSTEM') {
                            <span class="px-1 py-0.2 rounded text-[9px] font-mono font-bold bg-slate-100 text-slate-500 border border-slate-200 shrink-0">SYS</span>
                          }
                        </div>
                      </td>

                      <!-- 5. Navigation / Context Action (Text Only, No Icon) -->
                      <td class="py-3.5 px-3 text-right whitespace-nowrap">
                        @if (act.actionRoute) {
                          <a
                            [routerLink]="act.actionRoute"
                            class="h-7.5 px-2.5 rounded-md text-xs font-semibold text-slate-700 hover:text-blue-700 hover:bg-slate-100 border border-slate-200 transition-colors inline-flex items-center justify-center cursor-pointer shadow-2xs">
                            {{ act.actionType === 'REVIEW' ? 'Review Finding' : 'View Pipeline' }}
                          </a>
                        } @else {
                          <span class="text-xs text-slate-400 font-medium">&mdash;</span>
                        }
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
export class ProjectActivityComponent {
  public ps = inject(ProjectsService);
  private router = inject(Router);

  public openDropdown = signal<'category' | null>(null);

  public categoryOptions: CategoryOption[] = [
    { label: 'All Categories', value: 'ALL' },
    { label: 'Migration', value: 'MIGRATION' },
    { label: 'Validation', value: 'VALIDATION' },
    { label: 'Governance', value: 'GOVERNANCE' },
    { label: 'Access', value: 'ACCESS' },
    { label: 'Resource', value: 'RESOURCE' },
    { label: 'Metadata', value: 'METADATA' }
  ];

  @HostListener('document:click')
  public onDocumentClick(): void {
    this.openDropdown.set(null);
  }

  public toggleDropdown(dropdown: 'category', event: Event): void {
    event.stopPropagation();
    if (this.openDropdown() === dropdown) {
      this.openDropdown.set(null);
    } else {
      this.openDropdown.set(dropdown);
    }
  }

  public selectCategoryFilter(value: ProjectActivityCategory): void {
    this.ps.setActivityCategory(value);
    this.openDropdown.set(null);
  }

  public getCategoryFilterLabel(): string {
    const val = this.ps.activityFilters().categoryFilter;
    const found = this.categoryOptions.find(o => o.value === val);
    return found ? found.label : 'All Categories';
  }

  public isFilterActive(): boolean {
    const f = this.ps.activityFilters();
    return !!f.searchQuery || f.categoryFilter !== 'ALL';
  }
}

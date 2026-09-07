import { Component, inject, signal, HostListener } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink, Router } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { ProjectsService } from '../projects.service';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';
import { ProjectsStateFallbackComponent } from '../components/projects-state-fallback.component';
import { ProjectGovernanceItem } from '../projects.models';

interface CategoryOption {
  label: string;
  value: string;
}

interface StatusOption {
  label: string;
  value: string;
}

@Component({
  selector: 'app-project-governance',
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
      @if (ps.projectGovernanceAvailability() === 'UNAVAILABLE' || ps.projectGovernanceAvailability() === 'NOT_CONNECTED') {
        <app-projects-state-fallback
          [state]="ps.projectGovernanceAvailability()"
          entityName="governance"
          [customErrorMessage]="ps.errorMessage() || 'Governance & approval authority is currently unreachable or disconnected in this project context.'"
          (retry)="ps.retryConnection()">
        </app-projects-state-fallback>
      } @else if (ps.projectGovernanceAvailability() === 'UNAUTHORIZED') {
        <app-projects-state-fallback
          [state]="'UNAUTHORIZED'"
          entityName="governance"
          customErrorMessage="You do not have operator authorization to inspect governance gates and policies in this project boundary."
          (retry)="ps.retryConnection()">
        </app-projects-state-fallback>
      } @else if (ps.projectGovernanceAvailability() === 'ERROR') {
        <app-projects-state-fallback
          [state]="'ERROR'"
          entityName="governance"
          [customErrorMessage]="ps.errorMessage() || 'Failed to load project governance ledger.'"
          (retry)="ps.retryConnection()">
        </app-projects-state-fallback>
      } @else {
        
        <!-- Main Governance Card -->
        <div class="p-6 sm:p-7 rounded-xl bg-white border border-slate-200 shadow-xs flex flex-col gap-6">
          
          <!-- Header Section: Title & Subtitle -->
          <div class="flex items-start justify-between pb-4 border-b border-slate-200 flex-wrap gap-4">
            <div class="flex flex-col gap-1 max-w-3xl">
              <div class="flex items-center gap-2.5">
                <h2 class="text-base font-bold text-slate-900 font-heading">
                  Project Governance &amp; Controls
                </h2>
                @if (ps.activeProjectGovernance().length > 0) {
                  <span class="px-2.5 py-0.5 rounded-md text-[11px] font-semibold bg-slate-100 text-slate-700 border border-slate-200 tabular-nums">
                    {{ ps.activeProjectGovernance().length }}
                  </span>
                }
              </div>
              <p class="text-xs text-slate-600 font-normal">
                Protected operation approvals, mandatory validation gates, policy requirements, and authorized exception waivers.
              </p>
            </div>

            <!-- Inherited Context Chip -->
            <div class="flex items-center gap-2 text-xs text-slate-500 font-medium bg-slate-50 px-3 py-1.5 rounded-lg border border-slate-200 shrink-0">
              <app-lucide-icon name="scale" [size]="14" class="text-slate-500"></app-lucide-icon>
              <span>Governed Scope Context</span>
            </div>
          </div>

          <!-- Enterprise Law Banner (Governance != Approval Authority) -->
          <div class="p-3.5 rounded-lg bg-amber-50/80 border border-amber-200 text-amber-950 flex items-start gap-3">
            <app-lucide-icon name="shield-alert" [size]="16" class="text-amber-600 shrink-0 mt-0.5"></app-lucide-icon>
            <div class="flex flex-col gap-0.5 text-xs">
              <span class="font-bold text-amber-900">Governance Context &ne; Universal Approval Authority</span>
              <p class="text-amber-800 text-[11px] leading-relaxed">
                Project Governance surfaces operational approval gates and policies governed by enterprise rule engines. Project membership does not grant automatic approval authority; multi-party quorum is verified per protected operation.
              </p>
            </div>
          </div>

          <!-- Section 1: Pending Approvals (Rendered if pending items exist) -->
          @if (ps.activeProjectPendingApprovals().length > 0) {
            <div class="p-4 rounded-xl bg-amber-50/50 border border-amber-200/80 flex flex-col gap-3">
              <div class="flex items-center justify-between">
                <div class="flex items-center gap-2">
                  <app-lucide-icon name="alert-triangle" [size]="15" class="text-amber-600"></app-lucide-icon>
                  <h3 class="text-xs font-bold text-amber-950 uppercase tracking-wide">
                    Requires Attention: Pending Multi-Party Signoff ({{ ps.activeProjectPendingApprovals().length }})
                  </h3>
                </div>
              </div>

              <div class="divide-y divide-amber-200/60">
                @for (appr of ps.activeProjectPendingApprovals(); track appr.id) {
                  <div class="py-3 first:pt-1 last:pb-1 flex items-center justify-between gap-4 flex-wrap">
                    <div class="flex flex-col gap-1 max-w-2xl">
                      <div class="flex items-center gap-2">
                        <span class="font-bold text-slate-900 text-xs">{{ appr.title }}</span>
                        <span class="px-2 py-0.2 rounded text-[10px] font-bold font-mono bg-amber-100 text-amber-800 border border-amber-300">
                          {{ appr.protectedOperation }}
                        </span>
                      </div>
                      <p class="text-xs text-slate-600 font-normal leading-relaxed">{{ appr.description }}</p>
                      @if (appr.policyReference) {
                        <span class="text-[10.5px] text-slate-500 font-medium italic">{{ appr.policyReference }}</span>
                      }
                    </div>

                    <!-- Action: Review Approval (Text Only, No Icon, Restrained Rectangular) -->
                    <a
                      [routerLink]="appr.actionRoute || '/migration/cockpit/mig-cb-01'"
                      class="h-8 px-3.5 rounded-md bg-amber-600 hover:bg-amber-700 active:bg-amber-800 text-white text-xs font-semibold shadow-2xs transition-colors inline-flex items-center justify-center cursor-pointer shrink-0">
                      Review Approval
                    </a>
                  </div>
                }
              </div>
            </div>
          }

          <!-- Controls Bar: Search, Category Filter, Status Filter & Reset -->
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
                [ngModel]="ps.governanceFilters().searchQuery"
                (ngModelChange)="ps.setGovernanceSearch($event)"
                placeholder="Search governance items by title, policy, or operation..."
                class="w-full h-9 pl-9 pr-8 rounded-md bg-slate-50 hover:bg-slate-100/70 focus:bg-white border border-slate-300 text-xs font-medium text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all shadow-2xs"
              />
              @if (ps.governanceFilters().searchQuery) {
                <button
                  type="button"
                  (click)="ps.setGovernanceSearch('')"
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
                  <div class="absolute right-0 top-full mt-1 w-48 rounded-lg bg-white border border-slate-200 shadow-xl p-1 flex flex-col gap-0.5 z-50 animate-in fade-in zoom-in-95 duration-100">
                    @for (opt of categoryOptions; track opt.value) {
                      <button
                        type="button"
                        (click)="selectCategoryFilter(opt.value)"
                        class="w-full text-left px-2.5 py-1.5 rounded-md text-xs font-medium text-slate-700 hover:text-slate-900 hover:bg-slate-50 transition-colors flex items-center justify-between cursor-pointer"
                        [class.bg-blue-50]="ps.governanceFilters().categoryFilter === opt.value"
                        [class.text-blue-700]="ps.governanceFilters().categoryFilter === opt.value">
                        <span>{{ opt.label }}</span>
                        @if (ps.governanceFilters().categoryFilter === opt.value) {
                          <app-lucide-icon name="check" [size]="13" class="text-blue-600 shrink-0"></app-lucide-icon>
                        }
                      </button>
                    }
                  </div>
                }
              </div>

              <!-- Status Filter Dropdown -->
              <div class="relative" (click)="$event.stopPropagation()">
                <button
                  type="button"
                  (click)="toggleDropdown('status', $event)"
                  class="h-8 px-2.5 rounded-md bg-white hover:bg-slate-50 border border-slate-300 flex items-center justify-between gap-2 text-xs font-semibold text-slate-700 cursor-pointer shadow-2xs focus:outline-none focus:ring-1 focus:ring-blue-500"
                  [class.bg-blue-50]="openDropdown() === 'status'"
                  [class.border-blue-400]="openDropdown() === 'status'">
                  <span>{{ getStatusFilterLabel() }}</span>
                  <app-lucide-icon name="chevron-down" [size]="12" class="text-slate-400 shrink-0"></app-lucide-icon>
                </button>

                @if (openDropdown() === 'status') {
                  <div class="absolute right-0 top-full mt-1 w-44 rounded-lg bg-white border border-slate-200 shadow-xl p-1 flex flex-col gap-0.5 z-50 animate-in fade-in zoom-in-95 duration-100">
                    @for (opt of statusOptions; track opt.value) {
                      <button
                        type="button"
                        (click)="selectStatusFilter(opt.value)"
                        class="w-full text-left px-2.5 py-1.5 rounded-md text-xs font-medium text-slate-700 hover:text-slate-900 hover:bg-slate-50 transition-colors flex items-center justify-between cursor-pointer"
                        [class.bg-blue-50]="ps.governanceFilters().statusFilter === opt.value"
                        [class.text-blue-700]="ps.governanceFilters().statusFilter === opt.value">
                        <span>{{ opt.label }}</span>
                        @if (ps.governanceFilters().statusFilter === opt.value) {
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
                  (click)="ps.clearGovernanceFilters()"
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
                <span>Showing filtered governance items ({{ ps.filteredActiveProjectGovernance().length }} matching)</span>
              </div>
              <button
                type="button"
                (click)="ps.clearGovernanceFilters()"
                class="text-blue-700 hover:text-blue-900 font-bold px-2 py-0.5 rounded hover:bg-blue-100 cursor-pointer">
                Reset Filters
              </button>
            </div>
          }

          <!-- Governance Table or Empty State -->
          @if (ps.filteredActiveProjectGovernance().length === 0) {
            
            <div class="py-14 rounded-xl border border-slate-200/80 bg-slate-50/50 flex flex-col items-center justify-center text-center gap-3">
              <div class="w-12 h-12 rounded-lg bg-white border border-slate-200 flex items-center justify-center text-slate-400 shadow-2xs">
                <app-lucide-icon name="scale" [size]="24"></app-lucide-icon>
              </div>
              <div class="flex flex-col gap-1 max-w-md">
                <h3 class="text-sm font-bold text-slate-800">
                  {{ isFilterActive() ? 'No governance records match your filter criteria' : 'No Governance Policies Active' }}
                </h3>
                <p class="text-xs text-slate-500 font-normal">
                  {{ isFilterActive() ? 'Try clearing your search terms or resetting category and status filters.' : 'Governance gates and policy requirements will appear as pipelines and validation missions are configured.' }}
                </p>
              </div>
              <div class="pt-2">
                @if (isFilterActive()) {
                  <button
                    type="button"
                    (click)="ps.clearGovernanceFilters()"
                    class="h-8 px-3.5 rounded-md bg-white hover:bg-slate-50 text-slate-700 border border-slate-300 text-xs font-semibold shadow-2xs transition-colors cursor-pointer">
                    Reset All Filters
                  </button>
                }
              </div>
            </div>

          } @else {

            <!-- High-Precision Responsive Data Table with Zebra Rows -->
            <div class="overflow-x-auto rounded-xl border border-slate-200/80">
              <table class="w-full text-left border-collapse table-fixed">
                <thead>
                  <tr class="bg-slate-50 text-[10px] font-bold uppercase tracking-wider text-slate-600 border-b border-slate-200 select-none">
                    <th class="py-3 px-4 w-[34%]">Governance Requirement / Item</th>
                    <th class="py-3 px-4 w-[20%]">Protected Operation</th>
                    <th class="py-3 px-4 w-[16%]">Category</th>
                    <th class="py-3 px-4 w-[16%]">Status</th>
                    <th class="py-3 px-3 w-[14%] text-right">Context</th>
                  </tr>
                </thead>
                <tbody class="divide-y divide-slate-100 text-xs">
                  @for (gov of ps.filteredActiveProjectGovernance(); track gov.id) {
                    <tr class="hover:bg-blue-50/50 even:bg-slate-50/50 transition-colors select-none">
                      
                      <!-- 1. Title, Description & Policy Reference -->
                      <td class="py-3.5 px-4">
                        <div class="flex flex-col min-w-0">
                          <span class="font-bold text-slate-900 truncate">{{ gov.title }}</span>
                          <span class="text-[11px] text-slate-500 line-clamp-1">{{ gov.description }}</span>
                          @if (gov.policyReference) {
                            <span class="text-[10px] font-mono text-slate-400 mt-0.5 truncate">{{ gov.policyReference }}</span>
                          }
                        </div>
                      </td>

                      <!-- 2. Protected Operation -->
                      <td class="py-3.5 px-4">
                        <span class="px-2 py-0.5 rounded-md text-[10.5px] font-mono font-semibold bg-slate-100 text-slate-700 border border-slate-200 truncate block">
                          {{ gov.protectedOperation }}
                        </span>
                      </td>

                      <!-- 3. Category -->
                      <td class="py-3.5 px-4">
                        <span class="px-2 py-0.5 rounded-md text-[10.5px] font-semibold bg-slate-100 text-slate-700 border border-slate-200">
                          {{ getCategoryDisplayLabel(gov.category) }}
                        </span>
                      </td>

                      <!-- 4. Status Badge -->
                      <td class="py-3.5 px-4">
                        <span
                          class="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-md text-[10.5px] font-semibold border select-none"
                          [class.bg-amber-50]="gov.status === 'PENDING'"
                          [class.text-amber-800]="gov.status === 'PENDING'"
                          [class.border-amber-300]="gov.status === 'PENDING'"
                          [class.bg-emerald-50]="gov.status === 'APPROVED' || gov.status === 'ACTIVE'"
                          [class.text-emerald-700]="gov.status === 'APPROVED' || gov.status === 'ACTIVE'"
                          [class.border-emerald-200]="gov.status === 'APPROVED' || gov.status === 'ACTIVE'"
                          [class.bg-blue-50]="gov.status === 'WAIVED'"
                          [class.text-blue-700]="gov.status === 'WAIVED'"
                          [class.border-blue-200]="gov.status === 'WAIVED'"
                          [class.bg-rose-50]="gov.status === 'REJECTED'"
                          [class.text-rose-700]="gov.status === 'REJECTED'"
                          [class.border-rose-200]="gov.status === 'REJECTED'">
                          <span
                            class="w-1.5 h-1.5 rounded-xs"
                            [class.bg-amber-500]="gov.status === 'PENDING'"
                            [class.bg-emerald-500]="gov.status === 'APPROVED' || gov.status === 'ACTIVE'"
                            [class.bg-blue-500]="gov.status === 'WAIVED'"
                            [class.bg-rose-500]="gov.status === 'REJECTED'">
                          </span>
                          <span>{{ gov.status }}</span>
                        </span>
                      </td>

                      <!-- 5. Context Action (Text Only, No Icon) -->
                      <td class="py-3.5 px-3 text-right whitespace-nowrap">
                        @if (gov.category === 'PENDING_APPROVAL') {
                          <a
                            [routerLink]="gov.actionRoute || '/migration/cockpit/mig-cb-01'"
                            class="h-7.5 px-2.5 rounded-md text-xs font-semibold text-amber-700 hover:text-amber-800 hover:bg-amber-50 border border-amber-200 transition-colors inline-flex items-center justify-center cursor-pointer shadow-2xs">
                            Review Gate
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
export class ProjectGovernanceComponent {
  public ps = inject(ProjectsService);

  public openDropdown = signal<'category' | 'status' | null>(null);

  public categoryOptions: CategoryOption[] = [
    { label: 'All Categories', value: 'ALL' },
    { label: 'Pending Approvals', value: 'PENDING_APPROVAL' },
    { label: 'Policy Requirements', value: 'POLICY_REQUIREMENT' },
    { label: 'Resolved Decisions', value: 'RESOLVED_DECISION' },
    { label: 'Exceptions / Waivers', value: 'EXCEPTION_WAIVER' }
  ];

  public statusOptions: StatusOption[] = [
    { label: 'All Statuses', value: 'ALL' },
    { label: 'Pending', value: 'PENDING' },
    { label: 'Active', value: 'ACTIVE' },
    { label: 'Approved', value: 'APPROVED' },
    { label: 'Waived', value: 'WAIVED' },
    { label: 'Rejected', value: 'REJECTED' }
  ];

  @HostListener('document:click')
  public onDocumentClick(): void {
    this.openDropdown.set(null);
  }

  public toggleDropdown(dropdown: 'category' | 'status', event: Event): void {
    event.stopPropagation();
    if (this.openDropdown() === dropdown) {
      this.openDropdown.set(null);
    } else {
      this.openDropdown.set(dropdown);
    }
  }

  public selectCategoryFilter(value: string): void {
    this.ps.setGovernanceCategoryFilter(value);
    this.openDropdown.set(null);
  }

  public selectStatusFilter(value: string): void {
    this.ps.setGovernanceStatusFilter(value);
    this.openDropdown.set(null);
  }

  public getCategoryFilterLabel(): string {
    const val = this.ps.governanceFilters().categoryFilter;
    const found = this.categoryOptions.find(o => o.value === val);
    return found ? found.label : 'All Categories';
  }

  public getStatusFilterLabel(): string {
    const val = this.ps.governanceFilters().statusFilter;
    const found = this.statusOptions.find(o => o.value === val);
    return found ? found.label : 'All Statuses';
  }

  public getCategoryDisplayLabel(cat: string): string {
    switch (cat) {
      case 'PENDING_APPROVAL': return 'Pending Approval';
      case 'POLICY_REQUIREMENT': return 'Policy Requirement';
      case 'RESOLVED_DECISION': return 'Resolved Decision';
      case 'EXCEPTION_WAIVER': return 'Exception Waiver';
      default: return cat;
    }
  }

  public isFilterActive(): boolean {
    const f = this.ps.governanceFilters();
    return !!f.searchQuery || f.categoryFilter !== 'ALL' || f.statusFilter !== 'ALL';
  }
}

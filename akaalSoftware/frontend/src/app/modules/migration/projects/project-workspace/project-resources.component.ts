import { Component, inject, signal, HostListener } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ProjectsService } from '../projects.service';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';
import { ProjectsStateFallbackComponent } from '../components/projects-state-fallback.component';
import { ProjectResourceItem, ProjectResourceAvailabilityState } from '../projects.models';

interface CategoryOption {
  label: string;
  value: string;
}

interface AssociationOption {
  label: string;
  value: 'ALL' | 'BOUND' | 'AVAILABLE';
}

interface AvailabilityOption {
  label: string;
  value: string;
}

@Component({
  selector: 'app-project-resources',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    LucideIconComponent,
    ProjectsStateFallbackComponent
  ],
  template: `
    <div class="flex flex-col gap-6 select-none animate-in fade-in duration-150">
      
      <!-- Non-Ready State Fallback -->
      @if (ps.projectResourcesAvailability() === 'UNAVAILABLE' || ps.projectResourcesAvailability() === 'NOT_CONNECTED') {
        <app-projects-state-fallback
          [state]="ps.projectResourcesAvailability()"
          entityName="resources"
          [customErrorMessage]="ps.errorMessage() || 'Connection authority is currently unreachable or disconnected in this project context.'"
          (retry)="ps.retryConnection()">
        </app-projects-state-fallback>
      } @else if (ps.projectResourcesAvailability() === 'UNAUTHORIZED') {
        <app-projects-state-fallback
          [state]="'UNAUTHORIZED'"
          entityName="resources"
          customErrorMessage="You do not have authorization to inspect connection resources in this project boundary."
          (retry)="ps.retryConnection()">
        </app-projects-state-fallback>
      } @else if (ps.projectResourcesAvailability() === 'ERROR') {
        <app-projects-state-fallback
          [state]="'ERROR'"
          entityName="resources"
          [customErrorMessage]="ps.errorMessage() || 'Failed to load project resource inventory.'"
          (retry)="ps.retryConnection()">
        </app-projects-state-fallback>
      } @else {
        
        <!-- Main Resources Card -->
        <div class="p-6 sm:p-7 rounded-xl bg-white border border-slate-200 shadow-xs flex flex-col gap-5">
          
          <!-- Header Section: Title, Subtitle & Inherited Context Badge -->
          <div class="flex items-start justify-between pb-4 border-b border-slate-200 flex-wrap gap-4">
            <div class="flex flex-col gap-1 max-w-3xl">
              <div class="flex items-center gap-2.5">
                <h2 class="text-base font-bold text-slate-900 font-heading">
                  Project Resources
                </h2>
                @if (ps.activeProjectResources().length > 0) {
                  <span class="px-2.5 py-0.5 rounded-md text-[11px] font-semibold bg-slate-100 text-slate-700 border border-slate-200 tabular-nums">
                    {{ ps.activeProjectResources().length }}
                  </span>
                }
              </div>
              <p class="text-xs text-slate-600 font-normal">
                Database connection profiles, event streams, and storage endpoints visible and associated within this project boundary.
              </p>
            </div>

            <!-- Shell Authority Badge -->
            <div class="flex items-center gap-2 text-xs text-slate-500 font-medium bg-slate-50 px-3 py-1.5 rounded-lg border border-slate-200 shrink-0">
              <app-lucide-icon name="server" [size]="14" class="text-slate-500"></app-lucide-icon>
              <span>{{ ps.cs.selectedEnvironment()?.name || 'Production' }}</span>
              <span class="text-slate-300">&bull;</span>
              <span>{{ ps.cs.selectedWorkspace()?.name || 'Workspace' }}</span>
            </div>
          </div>

          <!-- Enterprise Security Disclaimer Banner (Required by Law 35) -->
          <div class="p-3.5 rounded-lg bg-amber-50/80 border border-amber-200 text-amber-950 flex items-start gap-3">
            <app-lucide-icon name="shield-alert" [size]="16" class="text-amber-600 shrink-0 mt-0.5"></app-lucide-icon>
            <div class="flex flex-col gap-0.5 text-xs">
              <span class="font-bold text-amber-900">Resource Visibility &#8800; Resource Use Authorization</span>
              <p class="text-amber-800 text-[11px] leading-relaxed">
                Associating a connection profile declares operational intent within this project boundary. Database secrets, credentials, and encryption keys remain sealed in enterprise vaults and are validated per migration run with cryptographic verification.
              </p>
            </div>
          </div>

          <!-- Controls Bar: Search, Category Filter, Association Filter & Reset -->
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
                [ngModel]="ps.resourceFilters().searchQuery"
                (ngModelChange)="ps.setResourceSearch($event)"
                placeholder="Search resources by name, host, provider, capability..."
                class="w-full h-9 pl-9 pr-8 rounded-md bg-slate-50 hover:bg-slate-100/70 focus:bg-white border border-slate-300 text-xs font-medium text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all shadow-2xs"
              />
              @if (ps.resourceFilters().searchQuery) {
                <button
                  type="button"
                  (click)="ps.setResourceSearch('')"
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
                        [class.bg-blue-50]="ps.resourceFilters().categoryFilter === opt.value"
                        [class.text-blue-700]="ps.resourceFilters().categoryFilter === opt.value">
                        <span>{{ opt.label }}</span>
                        @if (ps.resourceFilters().categoryFilter === opt.value) {
                          <app-lucide-icon name="check" [size]="13" class="text-blue-600 shrink-0"></app-lucide-icon>
                        }
                      </button>
                    }
                  </div>
                }
              </div>

              <!-- Association Filter Dropdown -->
              <div class="relative" (click)="$event.stopPropagation()">
                <button
                  type="button"
                  (click)="toggleDropdown('association', $event)"
                  class="h-8 px-2.5 rounded-md bg-white hover:bg-slate-50 border border-slate-300 flex items-center justify-between gap-2 text-xs font-semibold text-slate-700 cursor-pointer shadow-2xs focus:outline-none focus:ring-1 focus:ring-blue-500"
                  [class.bg-blue-50]="openDropdown() === 'association'"
                  [class.border-blue-400]="openDropdown() === 'association'">
                  <span>{{ getAssociationFilterLabel() }}</span>
                  <app-lucide-icon name="chevron-down" [size]="12" class="text-slate-400 shrink-0"></app-lucide-icon>
                </button>

                @if (openDropdown() === 'association') {
                  <div class="absolute right-0 top-full mt-1 w-48 rounded-lg bg-white border border-slate-200 shadow-xl p-1 flex flex-col gap-0.5 z-50 animate-in fade-in zoom-in-95 duration-100">
                    @for (opt of associationOptions; track opt.value) {
                      <button
                        type="button"
                        (click)="selectAssociationFilter(opt.value)"
                        class="w-full text-left px-2.5 py-1.5 rounded-md text-xs font-medium text-slate-700 hover:text-slate-900 hover:bg-slate-50 transition-colors flex items-center justify-between cursor-pointer"
                        [class.bg-blue-50]="ps.resourceFilters().associationFilter === opt.value"
                        [class.text-blue-700]="ps.resourceFilters().associationFilter === opt.value">
                        <span>{{ opt.label }}</span>
                        @if (ps.resourceFilters().associationFilter === opt.value) {
                          <app-lucide-icon name="check" [size]="13" class="text-blue-600 shrink-0"></app-lucide-icon>
                        }
                      </button>
                    }
                  </div>
                }
              </div>

              <!-- Availability Filter Dropdown -->
              <div class="relative" (click)="$event.stopPropagation()">
                <button
                  type="button"
                  (click)="toggleDropdown('availability', $event)"
                  class="h-8 px-2.5 rounded-md bg-white hover:bg-slate-50 border border-slate-300 flex items-center justify-between gap-2 text-xs font-semibold text-slate-700 cursor-pointer shadow-2xs focus:outline-none focus:ring-1 focus:ring-blue-500"
                  [class.bg-blue-50]="openDropdown() === 'availability'"
                  [class.border-blue-400]="openDropdown() === 'availability'">
                  <span>{{ getAvailabilityFilterLabel() }}</span>
                  <app-lucide-icon name="chevron-down" [size]="12" class="text-slate-400 shrink-0"></app-lucide-icon>
                </button>

                @if (openDropdown() === 'availability') {
                  <div class="absolute right-0 top-full mt-1 w-48 rounded-lg bg-white border border-slate-200 shadow-xl p-1 flex flex-col gap-0.5 z-50 animate-in fade-in zoom-in-95 duration-100">
                    @for (opt of availabilityOptions; track opt.value) {
                      <button
                        type="button"
                        (click)="selectAvailabilityFilter(opt.value)"
                        class="w-full text-left px-2.5 py-1.5 rounded-md text-xs font-medium text-slate-700 hover:text-slate-900 hover:bg-slate-50 transition-colors flex items-center justify-between cursor-pointer"
                        [class.bg-blue-50]="ps.resourceFilters().availabilityFilter === opt.value"
                        [class.text-blue-700]="ps.resourceFilters().availabilityFilter === opt.value">
                        <span>{{ opt.label }}</span>
                        @if (ps.resourceFilters().availabilityFilter === opt.value) {
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
                  (click)="ps.clearResourceFilters()"
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
                <span>Showing filtered resources ({{ ps.filteredActiveProjectResources().length }} matching)</span>
              </div>
              <button
                type="button"
                (click)="ps.clearResourceFilters()"
                class="text-blue-700 hover:text-blue-900 font-bold px-2 py-0.5 rounded hover:bg-blue-100 cursor-pointer">
                Reset Filters
              </button>
            </div>
          }

          <!-- Resources Data Table or Empty State -->
          @if (ps.filteredActiveProjectResources().length === 0) {
            
            <div class="py-14 rounded-xl border border-slate-200/80 bg-slate-50/50 flex flex-col items-center justify-center text-center gap-3">
              <div class="w-12 h-12 rounded-lg bg-white border border-slate-200 flex items-center justify-center text-slate-400 shadow-2xs">
                <app-lucide-icon name="database" [size]="24"></app-lucide-icon>
              </div>
              <div class="flex flex-col gap-1 max-w-md">
                <h3 class="text-sm font-bold text-slate-800">
                  {{ isFilterActive() ? 'No resources match your filter criteria' : 'No Resources Available in Current Context' }}
                </h3>
                <p class="text-xs text-slate-500 font-normal">
                  {{ isFilterActive() ? 'Try clearing your search terms or resetting the category and association filters.' : 'Ensure connection profiles have been registered in the workspace inventory.' }}
                </p>
              </div>
              <div class="pt-2">
                @if (isFilterActive()) {
                  <button
                    type="button"
                    (click)="ps.clearResourceFilters()"
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
                    <th class="py-3 px-4 w-[30%]">Resource Connection Profile</th>
                    <th class="py-3 px-4 w-[24%]">Endpoint Host / Schema</th>
                    <th class="py-3 px-4 w-[16%]">Category</th>
                    <th class="py-3 px-4 w-[16%]">Association Status</th>
                    <th class="py-3 px-3 w-[14%] text-right">Action</th>
                  </tr>
                </thead>
                <tbody class="divide-y divide-slate-100 text-xs">
                  @for (r of ps.filteredActiveProjectResources(); track r.id) {
                    <tr
                      class="hover:bg-blue-50/50 even:bg-slate-50/50 transition-colors select-none">
                      
                      <!-- 1. Resource Name & Provider Badge -->
                      <td class="py-3.5 px-4">
                        <div class="flex items-center gap-2.5 min-w-0">
                          <span class="px-2 py-0.5 rounded-md text-[10px] font-bold font-mono bg-slate-100 text-slate-700 border border-slate-200 shrink-0">
                            {{ r.provider }}
                          </span>
                          <div class="flex flex-col min-w-0">
                            <span class="font-bold text-slate-900 truncate">
                              {{ r.connectionName }}
                            </span>
                            @if (r.capabilityText) {
                              <span class="text-[10.5px] text-slate-500 truncate">
                                {{ r.capabilityText }}
                              </span>
                            }
                          </div>
                        </div>
                      </td>

                      <!-- 2. Host / Endpoint -->
                      <td class="py-3.5 px-4 font-mono text-[11px] text-slate-600 truncate">
                        {{ r.host || '&mdash;' }}
                      </td>

                      <!-- 3. Category Badge -->
                      <td class="py-3.5 px-4">
                        <span class="px-2 py-0.5 rounded-md text-[10.5px] font-semibold bg-slate-100 text-slate-700 border border-slate-200 uppercase">
                          {{ r.category }}
                        </span>
                      </td>

                      <!-- 4. Association Status -->
                      <td class="py-3.5 px-4">
                        @if (r.isBoundToProject) {
                          <span class="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-md text-[10.5px] font-semibold bg-blue-50 text-blue-700 border border-blue-200">
                            <span class="w-1.5 h-1.5 rounded-xs bg-blue-600"></span>
                            <span>Bound to Project</span>
                          </span>
                        } @else if (r.availabilityState === 'UNAUTHORIZED') {
                          <span class="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-md text-[10.5px] font-semibold bg-rose-50 text-rose-700 border border-rose-200">
                            <span class="w-1.5 h-1.5 rounded-xs bg-rose-600"></span>
                            <span>Unauthorized</span>
                          </span>
                        } @else if (r.availabilityState === 'UNAVAILABLE') {
                          <span class="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-md text-[10.5px] font-semibold bg-amber-50 text-amber-700 border border-amber-200">
                            <span class="w-1.5 h-1.5 rounded-xs bg-amber-500"></span>
                            <span>Unavailable</span>
                          </span>
                        } @else {
                          <span class="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-md text-[10.5px] font-semibold bg-slate-100 text-slate-600 border border-slate-200">
                            <span class="w-1.5 h-1.5 rounded-xs bg-slate-400"></span>
                            <span>Available in WS</span>
                          </span>
                        }
                      </td>

                      <!-- 5. Action: Text Only View Details / Manage -->
                      <td class="py-3.5 px-3 text-right whitespace-nowrap">
                        <button
                          type="button"
                          (click)="openDetail(r)"
                          class="h-7.5 px-2.5 rounded-md text-xs font-semibold text-slate-700 hover:text-blue-700 hover:bg-slate-100 border border-slate-200 transition-colors cursor-pointer shadow-2xs">
                          View Details
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

      <!-- Resource Safe Detail Modal (Zero Secret Leakage) -->
      @if (selectedResource(); as res) {
        <div
          class="fixed inset-0 bg-slate-900/40 backdrop-blur-xs flex items-center justify-center p-4 z-50 animate-in fade-in duration-150"
          (click)="closeDetail()">
          <div
            class="bg-white rounded-xl shadow-2xl border border-slate-200 max-w-lg w-full p-6 flex flex-col gap-5 select-none animate-in zoom-in-95 duration-150"
            (click)="$event.stopPropagation()">
            
            <div class="flex items-start justify-between pb-3 border-b border-slate-100">
              <div class="flex flex-col gap-1">
                <span class="text-[10px] font-bold uppercase tracking-wider text-slate-400">Connection Profile Details</span>
                <h3 class="text-base font-bold text-slate-900 font-heading">{{ res.connectionName }}</h3>
              </div>
              <button
                type="button"
                (click)="closeDetail()"
                class="w-7 h-7 rounded-md hover:bg-slate-100 text-slate-400 hover:text-slate-700 flex items-center justify-center font-bold cursor-pointer">
                &times;
              </button>
            </div>

            <div class="grid grid-cols-2 gap-3 text-xs">
              <div class="p-3 rounded-lg bg-slate-50 border border-slate-200 flex flex-col gap-0.5">
                <span class="text-[10px] font-semibold text-slate-400 uppercase">Provider Platform</span>
                <span class="font-bold text-slate-800">{{ res.provider }}</span>
              </div>
              <div class="p-3 rounded-lg bg-slate-50 border border-slate-200 flex flex-col gap-0.5">
                <span class="text-[10px] font-semibold text-slate-400 uppercase">Category</span>
                <span class="font-bold text-slate-800">{{ res.category }}</span>
              </div>
              <div class="p-3 rounded-lg bg-slate-50 border border-slate-200 flex flex-col gap-0.5 col-span-2">
                <span class="text-[10px] font-semibold text-slate-400 uppercase">Endpoint Host</span>
                <span class="font-mono font-medium text-slate-800 break-all">{{ res.host || 'Managed Platform Endpoint' }}</span>
              </div>
              <div class="p-3 rounded-lg bg-slate-50 border border-slate-200 flex flex-col gap-0.5 col-span-2">
                <span class="text-[10px] font-semibold text-slate-400 uppercase">Capability Notes</span>
                <span class="font-medium text-slate-700">{{ res.capabilityText || 'Standard Read/Write Pipeline Connection' }}</span>
              </div>
            </div>

            <div class="p-3 rounded-lg bg-amber-50/70 border border-amber-200 text-[11px] text-amber-900 leading-normal">
              <strong>Zero-Secret Boundary:</strong> Passwords, TLS keys, and token material are stored encrypted in HashiCorp Vault / Cloud KMS and are never transmitted to UI surfaces.
            </div>

            <div class="flex items-center justify-between pt-2 border-t border-slate-100">
              <button
                type="button"
                (click)="toggleBinding(res.connectionId)"
                class="h-8 px-3.5 rounded-md text-xs font-semibold transition-colors cursor-pointer shadow-2xs"
                [class.bg-blue-600]="!res.isBoundToProject"
                [class.hover:bg-blue-700]="!res.isBoundToProject"
                [class.text-white]="!res.isBoundToProject"
                [class.bg-white]="res.isBoundToProject"
                [class.hover:bg-slate-50]="res.isBoundToProject"
                [class.text-slate-700]="res.isBoundToProject"
                [class.border]="res.isBoundToProject"
                [class.border-slate-300]="res.isBoundToProject">
                {{ res.isBoundToProject ? 'Remove from Project' : 'Bind to Project Intent' }}
              </button>

              <button
                type="button"
                (click)="closeDetail()"
                class="h-8 px-3.5 rounded-md bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold cursor-pointer">
                Close
              </button>
            </div>

          </div>
        </div>
      }

    </div>
  `
})
export class ProjectResourcesComponent {
  public ps = inject(ProjectsService);

  public openDropdown = signal<'category' | 'association' | 'availability' | null>(null);
  public selectedResource = signal<ProjectResourceItem | null>(null);

  public categoryOptions: CategoryOption[] = [
    { label: 'All Categories', value: 'ALL' },
    { label: 'Relational DB', value: 'RELATIONAL' },
    { label: 'Data Warehouse', value: 'WAREHOUSE' },
    { label: 'Event Streaming', value: 'STREAMING' },
    { label: 'Object Storage', value: 'OBJECT_STORE' }
  ];

  public associationOptions: AssociationOption[] = [
    { label: 'All Resources', value: 'ALL' },
    { label: 'Bound to Project', value: 'BOUND' },
    { label: 'Available in Workspace', value: 'AVAILABLE' }
  ];

  public availabilityOptions: AvailabilityOption[] = [
    { label: 'All States', value: 'ALL' },
    { label: 'Available', value: 'AVAILABLE' },
    { label: 'Bound', value: 'BOUND' },
    { label: 'Unavailable', value: 'UNAVAILABLE' },
    { label: 'Unauthorized', value: 'UNAUTHORIZED' }
  ];

  @HostListener('document:click')
  public onDocumentClick(): void {
    this.openDropdown.set(null);
  }

  public toggleDropdown(dropdown: 'category' | 'association' | 'availability', event: Event): void {
    event.stopPropagation();
    if (this.openDropdown() === dropdown) {
      this.openDropdown.set(null);
    } else {
      this.openDropdown.set(dropdown);
    }
  }

  public selectCategoryFilter(value: string): void {
    this.ps.setResourceCategoryFilter(value);
    this.openDropdown.set(null);
  }

  public selectAssociationFilter(value: 'ALL' | 'BOUND' | 'AVAILABLE'): void {
    this.ps.setResourceAssociationFilter(value);
    this.openDropdown.set(null);
  }

  public selectAvailabilityFilter(value: string): void {
    this.ps.setResourceAvailabilityFilter(value);
    this.openDropdown.set(null);
  }

  public getCategoryFilterLabel(): string {
    const val = this.ps.resourceFilters().categoryFilter;
    const found = this.categoryOptions.find(o => o.value === val);
    return found ? found.label : 'All Categories';
  }

  public getAssociationFilterLabel(): string {
    const val = this.ps.resourceFilters().associationFilter;
    const found = this.associationOptions.find(o => o.value === val);
    return found ? found.label : 'All Resources';
  }

  public getAvailabilityFilterLabel(): string {
    const val = this.ps.resourceFilters().availabilityFilter;
    const found = this.availabilityOptions.find(o => o.value === val);
    return found ? found.label : 'All States';
  }

  public isFilterActive(): boolean {
    const f = this.ps.resourceFilters();
    return !!f.searchQuery || f.categoryFilter !== 'ALL' || f.associationFilter !== 'ALL' || f.availabilityFilter !== 'ALL';
  }

  public openDetail(res: ProjectResourceItem): void {
    this.selectedResource.set(res);
  }

  public closeDetail(): void {
    this.selectedResource.set(null);
  }

  public toggleBinding(connectionId: string): void {
    this.ps.toggleProjectResourceBinding(connectionId);
    // Update local modal state
    const updated = this.ps.activeProjectResources().find(r => r.connectionId === connectionId);
    if (updated) {
      this.selectedResource.set(updated);
    }
  }
}

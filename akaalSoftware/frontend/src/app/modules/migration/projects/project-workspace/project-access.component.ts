import { Component, inject, signal, HostListener } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ProjectsService } from '../projects.service';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';
import { ProjectsStateFallbackComponent } from '../components/projects-state-fallback.component';
import { ProjectAccessGrantItem, ProjectRoleType } from '../projects.models';

interface TypeOption {
  label: string;
  value: string;
}

interface RoleOption {
  label: string;
  value: string;
}

interface SourceOption {
  label: string;
  value: string;
}

@Component({
  selector: 'app-project-access',
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
      @if (ps.projectAccessAvailability() === 'UNAVAILABLE' || ps.projectAccessAvailability() === 'NOT_CONNECTED') {
        <app-projects-state-fallback
          [state]="ps.projectAccessAvailability()"
          entityName="access"
          [customErrorMessage]="ps.errorMessage() || 'Identity & access authority is currently unreachable or disconnected in this project context.'"
          (retry)="ps.retryConnection()">
        </app-projects-state-fallback>
      } @else if (ps.projectAccessAvailability() === 'UNAUTHORIZED') {
        <app-projects-state-fallback
          [state]="'UNAUTHORIZED'"
          entityName="access"
          customErrorMessage="You do not have administrative authorization to inspect security grants in this project boundary."
          (retry)="ps.retryConnection()">
        </app-projects-state-fallback>
      } @else if (ps.projectAccessAvailability() === 'ERROR') {
        <app-projects-state-fallback
          [state]="'ERROR'"
          entityName="access"
          [customErrorMessage]="ps.errorMessage() || 'Failed to load project access inventory.'"
          (retry)="ps.retryConnection()">
        </app-projects-state-fallback>
      } @else {
        
        <!-- Main Access Control Card -->
        <div class="p-6 sm:p-7 rounded-xl bg-white border border-slate-200 shadow-xs flex flex-col gap-5">
          
          <!-- Header Section: Title, Subtitle & Primary Action Button -->
          <div class="flex items-start justify-between pb-4 border-b border-slate-200 flex-wrap gap-4">
            <div class="flex flex-col gap-1 max-w-3xl">
              <div class="flex items-center gap-2.5">
                <h2 class="text-base font-bold text-slate-900 font-heading">
                  Project Access
                </h2>
                @if (ps.activeProjectAccessGrants().length > 0) {
                  <span class="px-2.5 py-0.5 rounded-md text-[11px] font-semibold bg-slate-100 text-slate-700 border border-slate-200 tabular-nums">
                    {{ ps.activeProjectAccessGrants().length }}
                  </span>
                }
              </div>
              <p class="text-xs text-slate-600 font-normal">
                Direct project-scoped role grants and inherited workspace authorizations applicable to this project boundary.
              </p>
            </div>

            <!-- Primary Action: Add Access (Text Only, No Lucide Icon, Restrained Rectangular) -->
            <button
              type="button"
              (click)="ps.openAddAccessModal()"
              class="h-8 px-3.5 rounded-md bg-blue-600 hover:bg-blue-700 active:bg-blue-800 text-white text-xs font-semibold transition-colors inline-flex items-center justify-center cursor-pointer shadow-2xs">
              Add Access
            </button>
          </div>

          <!-- Enterprise RBAC Law Banner (Access != Administration) -->
          <div class="p-3.5 rounded-lg bg-slate-50 border border-slate-200 text-slate-800 flex items-start gap-3">
            <app-lucide-icon name="shield-check" [size]="16" class="text-slate-600 shrink-0 mt-0.5"></app-lucide-icon>
            <div class="flex flex-col gap-0.5 text-xs">
              <span class="font-bold text-slate-900">Project Access &ne; Identity Administration</span>
              <p class="text-slate-600 text-[11px] leading-relaxed">
                Project Access assigns existing enterprise users, groups, and service accounts to project operational roles. Organization directories, SSO federation, and global role definitions are governed centrally by Platform Security Administrators.
              </p>
            </div>
          </div>

          <!-- Controls Bar: Search, Type Filter, Role Filter, Source Filter & Reset -->
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
                [ngModel]="ps.accessFilters().searchQuery"
                (ngModelChange)="ps.setAccessSearch($event)"
                placeholder="Search grants by principal name, email, or scope..."
                class="w-full h-9 pl-9 pr-8 rounded-md bg-slate-50 hover:bg-slate-100/70 focus:bg-white border border-slate-300 text-xs font-medium text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all shadow-2xs"
              />
              @if (ps.accessFilters().searchQuery) {
                <button
                  type="button"
                  (click)="ps.setAccessSearch('')"
                  class="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 text-xs font-bold cursor-pointer">
                  &times;
                </button>
              }
            </div>

            <!-- Filter Dropdowns Group -->
            <div class="flex items-center gap-2.5 flex-wrap">
              
              <!-- Role Filter Dropdown -->
              <div class="relative" (click)="$event.stopPropagation()">
                <button
                  type="button"
                  (click)="toggleDropdown('role', $event)"
                  class="h-8 px-2.5 rounded-md bg-white hover:bg-slate-50 border border-slate-300 flex items-center justify-between gap-2 text-xs font-semibold text-slate-700 cursor-pointer shadow-2xs focus:outline-none focus:ring-1 focus:ring-blue-500"
                  [class.bg-blue-50]="openDropdown() === 'role'"
                  [class.border-blue-400]="openDropdown() === 'role'">
                  <span>{{ getRoleFilterLabel() }}</span>
                  <app-lucide-icon name="chevron-down" [size]="12" class="text-slate-400 shrink-0"></app-lucide-icon>
                </button>

                @if (openDropdown() === 'role') {
                  <div class="absolute right-0 top-full mt-1 w-44 rounded-lg bg-white border border-slate-200 shadow-xl p-1 flex flex-col gap-0.5 z-50 animate-in fade-in zoom-in-95 duration-100">
                    @for (opt of roleOptions; track opt.value) {
                      <button
                        type="button"
                        (click)="selectRoleFilter(opt.value)"
                        class="w-full text-left px-2.5 py-1.5 rounded-md text-xs font-medium text-slate-700 hover:text-slate-900 hover:bg-slate-50 transition-colors flex items-center justify-between cursor-pointer"
                        [class.bg-blue-50]="ps.accessFilters().roleFilter === opt.value"
                        [class.text-blue-700]="ps.accessFilters().roleFilter === opt.value">
                        <span>{{ opt.label }}</span>
                        @if (ps.accessFilters().roleFilter === opt.value) {
                          <app-lucide-icon name="check" [size]="13" class="text-blue-600 shrink-0"></app-lucide-icon>
                        }
                      </button>
                    }
                  </div>
                }
              </div>

              <!-- Source Filter Dropdown -->
              <div class="relative" (click)="$event.stopPropagation()">
                <button
                  type="button"
                  (click)="toggleDropdown('source', $event)"
                  class="h-8 px-2.5 rounded-md bg-white hover:bg-slate-50 border border-slate-300 flex items-center justify-between gap-2 text-xs font-semibold text-slate-700 cursor-pointer shadow-2xs focus:outline-none focus:ring-1 focus:ring-blue-500"
                  [class.bg-blue-50]="openDropdown() === 'source'"
                  [class.border-blue-400]="openDropdown() === 'source'">
                  <span>{{ getSourceFilterLabel() }}</span>
                  <app-lucide-icon name="chevron-down" [size]="12" class="text-slate-400 shrink-0"></app-lucide-icon>
                </button>

                @if (openDropdown() === 'source') {
                  <div class="absolute right-0 top-full mt-1 w-52 rounded-lg bg-white border border-slate-200 shadow-xl p-1 flex flex-col gap-0.5 z-50 animate-in fade-in zoom-in-95 duration-100">
                    @for (opt of sourceOptions; track opt.value) {
                      <button
                        type="button"
                        (click)="selectSourceFilter(opt.value)"
                        class="w-full text-left px-2.5 py-1.5 rounded-md text-xs font-medium text-slate-700 hover:text-slate-900 hover:bg-slate-50 transition-colors flex items-center justify-between cursor-pointer"
                        [class.bg-blue-50]="ps.accessFilters().sourceFilter === opt.value"
                        [class.text-blue-700]="ps.accessFilters().sourceFilter === opt.value">
                        <span>{{ opt.label }}</span>
                        @if (ps.accessFilters().sourceFilter === opt.value) {
                          <app-lucide-icon name="check" [size]="13" class="text-blue-600 shrink-0"></app-lucide-icon>
                        }
                      </button>
                    }
                  </div>
                }
              </div>

              <!-- Type Filter Dropdown -->
              <div class="relative" (click)="$event.stopPropagation()">
                <button
                  type="button"
                  (click)="toggleDropdown('type', $event)"
                  class="h-8 px-2.5 rounded-md bg-white hover:bg-slate-50 border border-slate-300 flex items-center justify-between gap-2 text-xs font-semibold text-slate-700 cursor-pointer shadow-2xs focus:outline-none focus:ring-1 focus:ring-blue-500"
                  [class.bg-blue-50]="openDropdown() === 'type'"
                  [class.border-blue-400]="openDropdown() === 'type'">
                  <span>{{ getTypeFilterLabel() }}</span>
                  <app-lucide-icon name="chevron-down" [size]="12" class="text-slate-400 shrink-0"></app-lucide-icon>
                </button>

                @if (openDropdown() === 'type') {
                  <div class="absolute right-0 top-full mt-1 w-44 rounded-lg bg-white border border-slate-200 shadow-xl p-1 flex flex-col gap-0.5 z-50 animate-in fade-in zoom-in-95 duration-100">
                    @for (opt of typeOptions; track opt.value) {
                      <button
                        type="button"
                        (click)="selectTypeFilter(opt.value)"
                        class="w-full text-left px-2.5 py-1.5 rounded-md text-xs font-medium text-slate-700 hover:text-slate-900 hover:bg-slate-50 transition-colors flex items-center justify-between cursor-pointer"
                        [class.bg-blue-50]="ps.accessFilters().typeFilter === opt.value"
                        [class.text-blue-700]="ps.accessFilters().typeFilter === opt.value">
                        <span>{{ opt.label }}</span>
                        @if (ps.accessFilters().typeFilter === opt.value) {
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
                  (click)="ps.clearAccessFilters()"
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
                <span>Showing filtered access grants ({{ ps.filteredActiveProjectAccessGrants().length }} matching)</span>
              </div>
              <button
                type="button"
                (click)="ps.clearAccessFilters()"
                class="text-blue-700 hover:text-blue-900 font-bold px-2 py-0.5 rounded hover:bg-blue-100 cursor-pointer">
                Reset Filters
              </button>
            </div>
          }

          <!-- Access Table or Empty State -->
          @if (ps.filteredActiveProjectAccessGrants().length === 0) {
            
            <div class="py-14 rounded-xl border border-slate-200/80 bg-slate-50/50 flex flex-col items-center justify-center text-center gap-3">
              <div class="w-12 h-12 rounded-lg bg-white border border-slate-200 flex items-center justify-center text-slate-400 shadow-2xs">
                <app-lucide-icon name="shield" [size]="24"></app-lucide-icon>
              </div>
              <div class="flex flex-col gap-1 max-w-md">
                <h3 class="text-sm font-bold text-slate-800">
                  {{ isFilterActive() ? 'No access grants match your filter criteria' : 'No Access Grants Configured' }}
                </h3>
                <p class="text-xs text-slate-500 font-normal">
                  {{ isFilterActive() ? 'Try clearing your search terms or resetting role and source filters.' : 'Grant project-scoped roles to users, groups, or automated service accounts.' }}
                </p>
              </div>
              <div class="pt-2">
                @if (isFilterActive()) {
                  <button
                    type="button"
                    (click)="ps.clearAccessFilters()"
                    class="h-8 px-3.5 rounded-md bg-white hover:bg-slate-50 text-slate-700 border border-slate-300 text-xs font-semibold shadow-2xs transition-colors cursor-pointer">
                    Reset All Filters
                  </button>
                } @else {
                  <button
                    type="button"
                    (click)="ps.openAddAccessModal()"
                    class="h-8 px-3.5 rounded-md bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold shadow-2xs transition-colors cursor-pointer">
                    Add Access
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
                    <th class="py-3 px-4 w-[28%]">Principal / Identity</th>
                    <th class="py-3 px-4 w-[14%]">Type</th>
                    <th class="py-3 px-4 w-[16%]">Role</th>
                    <th class="py-3 px-4 w-[24%]">Access Source / Scope</th>
                    <th class="py-3 px-4 w-[18%] text-right">Action</th>
                  </tr>
                </thead>
                <tbody class="divide-y divide-slate-100 text-xs">
                  @for (g of ps.filteredActiveProjectAccessGrants(); track g.id) {
                    <tr class="hover:bg-blue-50/50 even:bg-slate-50/50 transition-colors select-none">
                      
                      <!-- 1. Principal Name & Email -->
                      <td class="py-3.5 px-4">
                        <div class="flex flex-col min-w-0">
                          <span class="font-bold text-slate-900 truncate">{{ g.principalName }}</span>
                          <span class="text-[11px] text-slate-500 font-mono truncate">{{ g.principalEmail }}</span>
                        </div>
                      </td>

                      <!-- 2. Principal Type -->
                      <td class="py-3.5 px-4">
                        <span class="px-2 py-0.5 rounded-md text-[10.5px] font-semibold bg-slate-100 text-slate-700 border border-slate-200 uppercase">
                          {{ g.principalType }}
                        </span>
                      </td>

                      <!-- 3. Role Badge -->
                      <td class="py-3.5 px-4">
                        <span
                          class="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-md text-[10.5px] font-semibold border select-none"
                          [class.bg-purple-50]="g.role === 'PROJECT_ADMIN'"
                          [class.text-purple-700]="g.role === 'PROJECT_ADMIN'"
                          [class.border-purple-200]="g.role === 'PROJECT_ADMIN'"
                          [class.bg-blue-50]="g.role === 'OPERATOR'"
                          [class.text-blue-700]="g.role === 'OPERATOR'"
                          [class.border-blue-200]="g.role === 'OPERATOR'"
                          [class.bg-slate-100]="g.role === 'VIEWER'"
                          [class.text-slate-700]="g.role === 'VIEWER'"
                          [class.border-slate-200]="g.role === 'VIEWER'">
                          <span>{{ getRoleDisplayLabel(g.role) }}</span>
                        </span>
                      </td>

                      <!-- 4. Source & Scope -->
                      <td class="py-3.5 px-4">
                        <div class="flex flex-col min-w-0">
                          <span class="font-semibold text-slate-800 text-[11px]">
                            {{ g.accessSource === 'DIRECT_PROJECT' ? 'Direct Project Grant' : 'Inherited from Workspace' }}
                          </span>
                          <span class="text-[10.5px] text-slate-500 truncate">
                            {{ g.scopeDescription }}
                          </span>
                        </div>
                      </td>

                      <!-- 5. Action: Revoke Access (Text Only, No Icon) -->
                      <td class="py-3.5 px-4 text-right whitespace-nowrap">
                        @if (g.accessSource === 'DIRECT_PROJECT') {
                          <button
                            type="button"
                            (click)="ps.openRevokeAccessModal(g)"
                            class="h-7.5 px-2.5 rounded-md text-xs font-semibold text-rose-700 hover:text-rose-800 hover:bg-rose-50 border border-rose-200 transition-colors cursor-pointer shadow-2xs">
                            Revoke Access
                          </button>
                        } @else {
                          <span class="text-[11px] text-slate-400 font-medium italic">Inherited Grant</span>
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

      <!-- Add Access Modal -->
      @if (ps.addAccessModalOpen()) {
        <div
          class="fixed inset-0 bg-slate-900/40 backdrop-blur-xs flex items-center justify-center p-4 z-50 animate-in fade-in duration-150"
          (click)="ps.closeAddAccessModal()">
          <div
            class="bg-white rounded-xl shadow-2xl border border-slate-200 max-w-lg w-full p-6 flex flex-col gap-5 select-none animate-in zoom-in-95 duration-150"
            (click)="$event.stopPropagation()">
            
            <div class="flex items-start justify-between pb-3 border-b border-slate-100">
              <div class="flex flex-col gap-1">
                <span class="text-[10px] font-bold uppercase tracking-wider text-slate-400">Security &amp; RBAC</span>
                <h3 class="text-base font-bold text-slate-900 font-heading">Add Project Access Role</h3>
              </div>
              <button
                type="button"
                (click)="ps.closeAddAccessModal()"
                class="w-7 h-7 rounded-md hover:bg-slate-100 text-slate-400 hover:text-slate-700 flex items-center justify-center font-bold cursor-pointer">
                &times;
              </button>
            </div>

            <!-- Principal Selection -->
            <div class="flex flex-col gap-1.5">
              <label class="text-xs font-bold text-slate-700">Select Identity (User, Group, Service Account)</label>
              <select
                [ngModel]="ps.selectedPrincipalForAdd()"
                (ngModelChange)="ps.setSelectedPrincipalForAdd($event)"
                class="w-full h-9 px-3 rounded-md bg-slate-50 border border-slate-300 text-xs font-medium text-slate-900 focus:bg-white focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 shadow-2xs">
                @for (p of ps.availablePrincipalsForAddAccess(); track p.id) {
                  <option [value]="p.id">{{ p.name }} ({{ p.type }} &bull; {{ p.email }})</option>
                }
              </select>
              <span class="text-[11px] text-slate-500 font-normal">Only authorized directory entities in this workspace may be assigned.</span>
            </div>

            <!-- Role Selection -->
            <div class="flex flex-col gap-1.5">
              <label class="text-xs font-bold text-slate-700">Project Role Assignment</label>
              <select
                [ngModel]="ps.selectedRoleForAdd()"
                (ngModelChange)="ps.setSelectedRoleForAdd($event)"
                class="w-full h-9 px-3 rounded-md bg-slate-50 border border-slate-300 text-xs font-medium text-slate-900 focus:bg-white focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 shadow-2xs">
                <option value="OPERATOR">Operator (Execute migrations, trigger validations)</option>
                <option value="PROJECT_ADMIN">Project Admin (Manage settings, association &amp; roles)</option>
                <option value="VIEWER">Viewer (Inspect logs, parity reports &amp; telemetry)</option>
              </select>
            </div>

            <div class="p-3 rounded-lg bg-blue-50/70 border border-blue-200 text-[11px] text-blue-900 leading-normal">
              <strong>Pre-P7D Authority Note:</strong> Project role grant intent will be compiled into the workspace security manifest. Production mutation occurs upon backend authority confirmation.
            </div>

            <div class="flex items-center justify-end gap-2.5 pt-2 border-t border-slate-100">
              <button
                type="button"
                (click)="ps.closeAddAccessModal()"
                class="h-8 px-3.5 rounded-md bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold cursor-pointer">
                Cancel
              </button>
              <button
                type="button"
                (click)="ps.submitAddAccessIntent()"
                class="h-8 px-3.5 rounded-md bg-blue-600 hover:bg-blue-700 active:bg-blue-800 text-white text-xs font-semibold shadow-2xs cursor-pointer">
                Save Grant Intent
              </button>
            </div>

          </div>
        </div>
      }

      <!-- Revoke Access Confirmation Modal -->
      @if (ps.revokeAccessModalItem(); as grant) {
        <div
          class="fixed inset-0 bg-slate-900/40 backdrop-blur-xs flex items-center justify-center p-4 z-50 animate-in fade-in duration-150"
          (click)="ps.closeRevokeAccessModal()">
          <div
            class="bg-white rounded-xl shadow-2xl border border-slate-200 max-w-md w-full p-6 flex flex-col gap-4 select-none animate-in zoom-in-95 duration-150"
            (click)="$event.stopPropagation()">
            
            <div class="flex items-start justify-between pb-2 border-b border-slate-100">
              <div class="flex flex-col gap-0.5">
                <span class="text-[10px] font-bold uppercase tracking-wider text-rose-600">Consequential Security Action</span>
                <h3 class="text-base font-bold text-slate-900 font-heading">Revoke Project Access</h3>
              </div>
              <button
                type="button"
                (click)="ps.closeRevokeAccessModal()"
                class="w-7 h-7 rounded-md hover:bg-slate-100 text-slate-400 hover:text-slate-700 flex items-center justify-center font-bold cursor-pointer">
                &times;
              </button>
            </div>

            <p class="text-xs text-slate-600 leading-relaxed">
              Are you sure you want to revoke <strong>{{ getRoleDisplayLabel(grant.role) }}</strong> access for <strong>{{ grant.principalName }}</strong> on this project?
            </p>

            <div class="p-3 rounded-lg bg-rose-50 border border-rose-200 text-xs text-rose-900">
              The principal will immediately lose operational permissions scoped directly to this project. Inherited workspace grants remain untouched.
            </div>

            <div class="flex items-center justify-end gap-2.5 pt-2 border-t border-slate-100">
              <button
                type="button"
                (click)="ps.closeRevokeAccessModal()"
                class="h-8 px-3.5 rounded-md bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold cursor-pointer">
                Cancel
              </button>
              <button
                type="button"
                (click)="ps.confirmRevokeAccess(grant.id)"
                class="h-8 px-3.5 rounded-md bg-rose-600 hover:bg-rose-700 active:bg-rose-800 text-white text-xs font-semibold shadow-2xs cursor-pointer">
                Revoke Access
              </button>
            </div>

          </div>
        </div>
      }

    </div>
  `
})
export class ProjectAccessComponent {
  public ps = inject(ProjectsService);

  public openDropdown = signal<'role' | 'source' | 'type' | null>(null);

  public roleOptions: RoleOption[] = [
    { label: 'All Roles', value: 'ALL' },
    { label: 'Project Admin', value: 'PROJECT_ADMIN' },
    { label: 'Operator', value: 'OPERATOR' },
    { label: 'Viewer', value: 'VIEWER' }
  ];

  public sourceOptions: SourceOption[] = [
    { label: 'All Sources', value: 'ALL' },
    { label: 'Direct Project Grant', value: 'DIRECT_PROJECT' },
    { label: 'Inherited from Workspace', value: 'INHERITED_WORKSPACE' }
  ];

  public typeOptions: TypeOption[] = [
    { label: 'All Types', value: 'ALL' },
    { label: 'User', value: 'USER' },
    { label: 'Group', value: 'GROUP' },
    { label: 'Service Account', value: 'SERVICE_ACCOUNT' }
  ];

  @HostListener('document:click')
  public onDocumentClick(): void {
    this.openDropdown.set(null);
  }

  public toggleDropdown(dropdown: 'role' | 'source' | 'type', event: Event): void {
    event.stopPropagation();
    if (this.openDropdown() === dropdown) {
      this.openDropdown.set(null);
    } else {
      this.openDropdown.set(dropdown);
    }
  }

  public selectRoleFilter(value: string): void {
    this.ps.setAccessRoleFilter(value);
    this.openDropdown.set(null);
  }

  public selectSourceFilter(value: string): void {
    this.ps.setAccessSourceFilter(value);
    this.openDropdown.set(null);
  }

  public selectTypeFilter(value: string): void {
    this.ps.setAccessTypeFilter(value);
    this.openDropdown.set(null);
  }

  public getRoleFilterLabel(): string {
    const val = this.ps.accessFilters().roleFilter;
    const found = this.roleOptions.find(o => o.value === val);
    return found ? found.label : 'All Roles';
  }

  public getSourceFilterLabel(): string {
    const val = this.ps.accessFilters().sourceFilter;
    const found = this.sourceOptions.find(o => o.value === val);
    return found ? found.label : 'All Sources';
  }

  public getTypeFilterLabel(): string {
    const val = this.ps.accessFilters().typeFilter;
    const found = this.typeOptions.find(o => o.value === val);
    return found ? found.label : 'All Types';
  }

  public getRoleDisplayLabel(role: string): string {
    switch (role) {
      case 'PROJECT_ADMIN': return 'Project Admin';
      case 'OPERATOR': return 'Operator';
      case 'VIEWER': return 'Viewer';
      default: return role;
    }
  }

  public isFilterActive(): boolean {
    const f = this.ps.accessFilters();
    return !!f.searchQuery || f.roleFilter !== 'ALL' || f.sourceFilter !== 'ALL' || f.typeFilter !== 'ALL';
  }
}

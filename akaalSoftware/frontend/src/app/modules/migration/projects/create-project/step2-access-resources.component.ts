import { Component, inject, signal, computed, HostListener } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ProjectsService } from '../projects.service';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';
import { ProjectPrincipal, ProjectRoleType } from '../projects.models';

export interface ProjectRoleOption {
  value: ProjectRoleType;
  label: string;
  icon: string;
  description: string;
}

@Component({
  selector: 'app-step2-access-resources',
  standalone: true,
  imports: [CommonModule, FormsModule, LucideIconComponent],
  template: `
    <div class="w-full max-w-4xl mx-auto flex flex-col gap-6 select-none animate-in fade-in duration-150">
      
      <!-- Top Title & Subtitle Card -->
      <div class="p-6 rounded-xl bg-white border border-slate-200 shadow-xs flex flex-col gap-1.5">
        <h2 class="text-base font-bold text-slate-900 font-heading">
          Initial Access &amp; Resource Associations
        </h2>
        <p class="text-xs text-slate-600 font-medium">
          Declare operational access intent and associate database connection resources with this project boundary.
        </p>
      </div>

      <!-- SECTION 1: INITIAL ACCESS INTENT -->
      <div class="p-6 rounded-xl bg-white border border-slate-200 shadow-xs flex flex-col gap-5">
        
        <div class="flex items-center justify-between pb-3 border-b border-slate-100 flex-wrap gap-3">
          <div class="flex flex-col gap-0.5">
            <span class="text-xs font-bold text-slate-900 uppercase tracking-wider font-heading flex items-center gap-2">
              <app-lucide-icon name="shield" [size]="14" class="text-blue-600"></app-lucide-icon>
              <span>Initial Access Intent</span>
            </span>
            <span class="text-[11px] text-slate-500">
              Assign initial project-level roles to operators, groups, or service accounts.
            </span>
          </div>

          <!-- Principal Search & Add Trigger with Increased Height -->
          <div class="relative w-80 max-w-full" (click)="$event.stopPropagation()">
            <div class="relative flex items-center">
              <app-lucide-icon
                name="search"
                [size]="14"
                class="absolute left-3 text-slate-400 pointer-events-none">
              </app-lucide-icon>
              <input
                type="text"
                [(ngModel)]="principalSearchQuery"
                placeholder="Search principal or group to add..."
                class="w-full h-10 pl-9 pr-3.5 rounded-md bg-slate-50 hover:bg-slate-100/80 border border-slate-300 text-xs font-medium text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all shadow-2xs"
              />
            </div>

            <!-- Auto-suggest Results Dropdown -->
            @if (filteredAvailablePrincipals().length > 0 && principalSearchQuery.trim()) {
              <div class="absolute right-0 left-0 mt-1.5 rounded-lg bg-white border border-slate-200 shadow-xl p-1.5 flex flex-col gap-1 z-50 animate-in fade-in zoom-in-95 duration-100 max-h-56 overflow-y-auto">
                @for (p of filteredAvailablePrincipals(); track p.id) {
                  <button
                    type="button"
                    (click)="addPrincipal(p)"
                    class="w-full text-left p-2.5 rounded-md hover:bg-slate-50 flex items-center justify-between gap-2.5 cursor-pointer transition-colors">
                    <div class="flex items-center gap-2.5 min-w-0">
                      <div class="w-7 h-7 rounded-md bg-slate-100 border border-slate-200 flex items-center justify-center text-slate-600 shrink-0">
                        <app-lucide-icon
                          [name]="p.type === 'GROUP' ? 'users' : p.type === 'SERVICE_ACCOUNT' ? 'bot' : 'user'"
                          [size]="14">
                        </app-lucide-icon>
                      </div>
                      <div class="flex flex-col min-w-0">
                        <span class="text-xs font-bold text-slate-900 truncate">{{ p.name }}</span>
                        <span class="text-[10.5px] text-slate-400 truncate">{{ p.email }}</span>
                      </div>
                    </div>
                    <span class="text-[11px] font-bold text-blue-600 shrink-0 bg-blue-50 px-2 py-0.5 rounded-md border border-blue-200">+ Add</span>
                  </button>
                }
              </div>
            }
          </div>
        </div>

        <!-- Assigned Principals Table -->
        <div class="overflow-x-auto rounded-lg border border-slate-200/80">
          <table class="w-full text-left border-collapse table-fixed">
            <thead>
              <tr class="bg-slate-50 text-[10px] font-bold uppercase tracking-wider text-slate-600 border-b border-slate-200 select-none">
                <th class="py-2.5 px-4 w-[42%]">Principal / Identity</th>
                <th class="py-2.5 px-4 w-[22%]">Identity Type</th>
                <th class="py-2.5 px-4 w-[26%]">Project Role</th>
                <th class="py-2.5 px-3 w-[10%] text-right">Action</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-100 text-xs">
              @for (p of ps.projectDraft().accessAssignments; track p.id) {
                <tr class="hover:bg-slate-50/70 transition-colors">
                  
                  <!-- Name & Email with Guaranteed Lucide Icon -->
                  <td class="py-3 px-4">
                    <div class="flex items-center gap-2.5 min-w-0">
                      <div class="w-7 h-7 rounded-md bg-blue-50 border border-blue-200/80 flex items-center justify-center text-blue-700 shrink-0">
                        <app-lucide-icon
                          [name]="p.type === 'GROUP' ? 'users' : p.type === 'SERVICE_ACCOUNT' ? 'bot' : 'user'"
                          [size]="14">
                        </app-lucide-icon>
                      </div>
                      <div class="flex flex-col min-w-0">
                        <span class="font-bold text-slate-900 truncate">{{ p.name }}</span>
                        <span class="text-[10.5px] text-slate-500 font-mono truncate">{{ p.email }}</span>
                      </div>
                    </div>
                  </td>

                  <!-- Type Badge -->
                  <td class="py-3 px-4">
                    <span class="px-2 py-0.5 rounded-md text-[10.5px] font-semibold bg-slate-100 text-slate-700 border border-slate-200">
                      {{ p.type }}
                    </span>
                  </td>

                  <!-- Custom GDS Project Role Selector (No raw browser select) -->
                  <td class="py-3 px-4 relative" (click)="$event.stopPropagation()">
                    <button
                      type="button"
                      (click)="toggleRoleDropdown(p.id, $event)"
                      class="h-8 px-2.5 rounded-md bg-white hover:bg-slate-50 border border-slate-300 flex items-center justify-between gap-1.5 text-xs font-semibold text-slate-800 cursor-pointer shadow-2xs focus:outline-none focus:ring-1 focus:ring-blue-500">
                      <div class="flex items-center gap-1.5">
                        <app-lucide-icon [name]="getRoleIcon(p.role)" [size]="13" class="text-blue-600 shrink-0"></app-lucide-icon>
                        <span>{{ getRoleLabel(p.role) }}</span>
                      </div>
                      <app-lucide-icon name="chevron-down" [size]="12" class="text-slate-400 shrink-0"></app-lucide-icon>
                    </button>

                    <!-- Role Dropdown Popover -->
                    @if (openRolePrincipalId() === p.id) {
                      <div class="absolute left-4 top-full mt-1 w-52 rounded-lg bg-white border border-slate-200 shadow-xl p-1 flex flex-col gap-0.5 z-50 animate-in fade-in zoom-in-95 duration-100">
                        @for (opt of roleOptions; track opt.value) {
                          <button
                            type="button"
                            (click)="selectRole(p.id, opt.value)"
                            class="w-full text-left px-2.5 py-1.5 rounded-md text-xs font-medium text-slate-700 hover:text-slate-900 hover:bg-slate-50 transition-colors flex items-center justify-between cursor-pointer"
                            [class.bg-blue-50]="p.role === opt.value"
                            [class.text-blue-700]="p.role === opt.value">
                            <div class="flex items-center gap-2">
                              <app-lucide-icon [name]="opt.icon" [size]="13" [class.text-blue-600]="p.role === opt.value" class="text-slate-500 shrink-0"></app-lucide-icon>
                              <span class="font-semibold">{{ opt.label }}</span>
                            </div>
                            @if (p.role === opt.value) {
                              <app-lucide-icon name="check" [size]="13" class="text-blue-600 shrink-0"></app-lucide-icon>
                            }
                          </button>
                        }
                      </div>
                    }
                  </td>

                  <!-- Remove Action -->
                  <td class="py-3 px-3 text-right">
                    <button
                      type="button"
                      (click)="removePrincipal(p.id)"
                      class="h-7 w-7 rounded-md hover:bg-red-50 text-slate-400 hover:text-red-600 inline-flex items-center justify-center transition-colors cursor-pointer"
                      title="Remove access assignment">
                      <app-lucide-icon name="trash-2" [size]="13"></app-lucide-icon>
                    </button>
                  </td>

                </tr>
              }
            </tbody>
          </table>
        </div>

        <div class="p-3 rounded-lg bg-slate-50 border border-slate-200 text-[11px] text-slate-600 leading-normal">
          <strong>Access Intent Notice:</strong> Access assignments define initial project operational roles. Actual runtime credential tokens and service account delegations are governed by akaalPipeline security orchestrators.
        </div>

      </div>

      <!-- SECTION 2: RESOURCE ASSOCIATION INTENT -->
      <div class="p-6 rounded-xl bg-white border border-slate-200 shadow-xs flex flex-col gap-5">
        
        <div class="flex items-center justify-between pb-3 border-b border-slate-100 flex-wrap gap-2">
          <div class="flex flex-col gap-0.5">
            <span class="text-xs font-bold text-slate-900 uppercase tracking-wider font-heading flex items-center gap-2">
              <app-lucide-icon name="database" [size]="14" class="text-blue-600"></app-lucide-icon>
              <span>Resource Association Intent</span>
            </span>
            <span class="text-[11px] text-slate-500">
              Select database, warehouse, and streaming connections available for migration workloads within this project.
            </span>
          </div>

          <span class="text-xs font-bold text-slate-700 bg-slate-100 px-2.5 py-1 rounded-md border border-slate-200">
            {{ ps.projectDraft().selectedResourceIds.length }} Selected
          </span>
        </div>

        <!-- Enterprise Disclaimer Banner (Required) -->
        <div class="p-3.5 rounded-lg bg-amber-50/80 border border-amber-200 text-amber-950 flex items-start gap-3">
          <app-lucide-icon name="shield-alert" [size]="16" class="text-amber-600 shrink-0 mt-0.5"></app-lucide-icon>
          <div class="flex flex-col gap-0.5 text-xs">
            <span class="font-bold text-amber-900">Resource Visibility &#8800; Resource Use Authorization</span>
            <p class="text-amber-800 text-[11px] leading-relaxed">
              Associating a connection profile declares operational intent for this project boundary. Database secrets and encryption keys remain sealed in enterprise vaults and are unlocked per migration run with cryptographic verification.
            </p>
          </div>
        </div>

        <!-- Connections Selection List -->
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
          @for (conn of ps.availableConnections(); track conn.connectionId) {
            <div
              (click)="ps.toggleProjectDraftResource(conn.connectionId)"
              class="p-3.5 rounded-lg border-2 transition-all cursor-pointer flex items-start gap-3 select-none"
              [class.border-blue-600]="isResourceSelected(conn.connectionId)"
              [class.bg-blue-50]="isResourceSelected(conn.connectionId)"
              [class.border-slate-200]="!isResourceSelected(conn.connectionId)"
              [class.bg-white]="!isResourceSelected(conn.connectionId)"
              [class.hover:border-slate-300]="!isResourceSelected(conn.connectionId)">
              
              <!-- Checkbox -->
              <div
                class="w-4 h-4 rounded-md border flex items-center justify-center shrink-0 mt-0.5 transition-colors"
                [class.bg-blue-600]="isResourceSelected(conn.connectionId)"
                [class.border-blue-600]="isResourceSelected(conn.connectionId)"
                [class.border-slate-300]="!isResourceSelected(conn.connectionId)"
                [class.bg-white]="!isResourceSelected(conn.connectionId)">
                @if (isResourceSelected(conn.connectionId)) {
                  <app-lucide-icon name="check" [size]="12" class="text-white"></app-lucide-icon>
                }
              </div>

              <!-- Connection Details -->
              <div class="flex flex-col gap-1 min-w-0">
                <div class="flex items-center gap-1.5">
                  <span class="px-1.5 py-0.2 rounded text-[9.5px] font-bold bg-slate-100 text-slate-700 border border-slate-200 uppercase">
                    {{ conn.provider }}
                  </span>
                  <span class="text-xs font-bold text-slate-900 truncate">{{ conn.connectionName }}</span>
                </div>
                @if (conn.host) {
                  <span class="text-[10.5px] text-slate-500 font-mono truncate">{{ conn.host }}</span>
                }
                <div class="flex items-center gap-2 text-[10px] text-slate-400 font-medium">
                  <span>{{ conn.category }}</span>
                  <span>&bull;</span>
                  <span>{{ conn.environment }}</span>
                </div>
              </div>

            </div>
          }
        </div>

      </div>

    </div>
  `
})
export class Step2AccessResourcesComponent {
  public ps = inject(ProjectsService);

  public principalSearchQuery = '';
  public openRolePrincipalId = signal<string | null>(null);

  public roleOptions: ProjectRoleOption[] = [
    { value: 'PROJECT_ADMIN', label: 'Project Admin', icon: 'shield', description: 'Full administrative control' },
    { value: 'OPERATOR', label: 'Operator', icon: 'play', description: 'Pipeline execution & maintenance' },
    { value: 'VIEWER', label: 'Viewer', icon: 'eye', description: 'Read-only monitoring' }
  ];

  public filteredAvailablePrincipals = computed(() => {
    const q = this.principalSearchQuery.trim().toLowerCase();
    if (!q) return [];
    const assignedIds = new Set(this.ps.projectDraft().accessAssignments.map(p => p.id));
    return this.ps.availablePrincipals()
      .filter(p => !assignedIds.has(p.id))
      .filter(p => p.name.toLowerCase().includes(q) || p.email.toLowerCase().includes(q));
  });

  @HostListener('document:click')
  public onDocumentClick(): void {
    this.openRolePrincipalId.set(null);
  }

  public toggleRoleDropdown(principalId: string, event: Event): void {
    event.stopPropagation();
    if (this.openRolePrincipalId() === principalId) {
      this.openRolePrincipalId.set(null);
    } else {
      this.openRolePrincipalId.set(principalId);
    }
  }

  public selectRole(principalId: string, role: ProjectRoleType): void {
    this.ps.updateProjectDraftPrincipalRole(principalId, role);
    this.openRolePrincipalId.set(null);
  }

  public getRoleLabel(role: ProjectRoleType): string {
    const found = this.roleOptions.find(o => o.value === role);
    return found ? found.label : role;
  }

  public getRoleIcon(role: ProjectRoleType): string {
    const found = this.roleOptions.find(o => o.value === role);
    return found ? found.icon : 'shield';
  }

  public isResourceSelected(connectionId: string): boolean {
    return this.ps.projectDraft().selectedResourceIds.includes(connectionId);
  }

  public addPrincipal(principal: ProjectPrincipal): void {
    this.ps.addProjectDraftPrincipal(principal);
    this.principalSearchQuery = '';
  }

  public removePrincipal(principalId: string): void {
    this.ps.removeProjectDraftPrincipal(principalId);
  }
}

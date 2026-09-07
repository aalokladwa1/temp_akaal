import { Component, inject, signal, OnInit, effect, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ProjectsService } from '../projects.service';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';
import { ProjectsStateFallbackComponent } from '../components/projects-state-fallback.component';
import { CustomSelectComponent, CustomSelectOption } from '../../../../shared/components/custom-select.component';

@Component({
  selector: 'app-project-settings',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    LucideIconComponent,
    ProjectsStateFallbackComponent,
    CustomSelectComponent
  ],
  template: `
    <div class="flex flex-col gap-6 select-none animate-in fade-in duration-150">
      
      <!-- Non-Ready State Fallback -->
      @if (ps.projectSettingsAvailability() === 'UNAVAILABLE' || ps.projectSettingsAvailability() === 'NOT_CONNECTED') {
        <app-projects-state-fallback
          [state]="ps.projectSettingsAvailability()"
          entityName="settings"
          [customErrorMessage]="ps.errorMessage() || 'Project settings authority is currently unreachable or disconnected in this project context.'"
          (retry)="ps.retryConnection()">
        </app-projects-state-fallback>
      } @else if (ps.projectSettingsAvailability() === 'UNAUTHORIZED') {
        <app-projects-state-fallback
          [state]="'UNAUTHORIZED'"
          entityName="settings"
          customErrorMessage="You do not have administrative authorization to modify settings for this project boundary."
          (retry)="ps.retryConnection()">
        </app-projects-state-fallback>
      } @else if (ps.projectSettingsAvailability() === 'ERROR') {
        <app-projects-state-fallback
          [state]="'ERROR'"
          entityName="settings"
          [customErrorMessage]="ps.errorMessage() || 'Failed to load project configuration.'"
          (retry)="ps.retryConnection()">
        </app-projects-state-fallback>
      } @else {
        
        @if (ps.activeProject(); as proj) {
          <!-- Main Settings Form Container (Centered with max-w-4xl mx-auto w-full) -->
          <div class="flex flex-col gap-6 max-w-4xl mx-auto w-full py-2">
            
            <!-- Section 1: General Identity & Scope -->
            <div class="p-6 sm:p-7 rounded-xl bg-white border border-slate-200 shadow-xs flex flex-col gap-5">
              
              <div class="flex items-start justify-between pb-3 border-b border-slate-200 flex-wrap gap-4">
                <div class="flex flex-col gap-0.5">
                  <h2 class="text-base font-bold text-slate-900 font-heading">
                    General Project Settings
                  </h2>
                  <p class="text-xs text-slate-600 font-normal">
                    Project identity, narrative scope, and strategic initiative alignment.
                  </p>
                </div>
                
                <span class="px-2.5 py-1 rounded-md text-xs font-bold font-mono bg-blue-50 text-blue-700 border border-blue-200/90 shrink-0">
                  {{ proj.key }}
                </span>
              </div>

              <!-- Form Fields -->
              <div class="flex flex-col gap-4">
                
                <!-- Project Name -->
                <div class="flex flex-col gap-1.5">
                  <label class="text-xs font-bold text-slate-800">Project Name</label>
                  <input
                    type="text"
                    [(ngModel)]="formName"
                    placeholder="Enter project name..."
                    class="w-full h-9 px-3 rounded-md bg-slate-50 hover:bg-slate-100/70 focus:bg-white border border-slate-300 text-xs font-medium text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all shadow-2xs"
                  />
                </div>

                <!-- Description -->
                <div class="flex flex-col gap-1.5">
                  <label class="text-xs font-bold text-slate-800">Scope Narrative &amp; Purpose</label>
                  <textarea
                    [(ngModel)]="formDescription"
                    rows="3"
                    placeholder="Describe the operational goals, source systems, and target architecture..."
                    class="w-full p-3 rounded-md bg-slate-50 hover:bg-slate-100/70 focus:bg-white border border-slate-300 text-xs font-medium text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all shadow-2xs resize-y">
                  </textarea>
                </div>

                <!-- Strategic Initiative Alignment (Global Design System Custom Select) -->
                <div class="flex flex-col gap-1.5">
                  <label class="text-xs font-bold text-slate-800">Strategic Initiative Alignment</label>
                  <app-custom-select
                    [options]="initiativeOptions()"
                    [value]="formInitiativeId"
                    (valueChange)="formInitiativeId = $event"
                    [size]="'md'"
                    placeholder="Standalone Project (No parent initiative)">
                  </app-custom-select>
                  <span class="text-[11px] text-slate-500 font-normal">
                    Reassociating an initiative organizes portfolio rollups. Workspace boundary remains immutable.
                  </span>
                </div>

              </div>

            </div>

            <!-- Section 2: Project Operational Defaults -->
            <div class="p-6 sm:p-7 rounded-xl bg-white border border-slate-200 shadow-xs flex flex-col gap-5">
              
              <div class="pb-3 border-b border-slate-200 flex flex-col gap-0.5">
                <h2 class="text-base font-bold text-slate-900 font-heading">
                  Operational Defaults &amp; Guidelines
                </h2>
                <p class="text-xs text-slate-600 font-normal">
                  Default pipeline execution modes and verification strategies pre-selected when authoring new workloads in this project.
                </p>
              </div>

              <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
                
                <!-- Default Migration Mode (Global Design System Custom Select) -->
                <div class="flex flex-col gap-1.5">
                  <label class="text-xs font-bold text-slate-800">Default Migration Execution Mode</label>
                  <app-custom-select
                    [options]="migrationModeOptions"
                    [value]="formDefaultMigrationMode"
                    (valueChange)="formDefaultMigrationMode = $event"
                    [size]="'md'">
                  </app-custom-select>
                </div>

                <!-- Default Validation Strategy (Global Design System Custom Select) -->
                <div class="flex flex-col gap-1.5">
                  <label class="text-xs font-bold text-slate-800">Default Validation Strategy</label>
                  <app-custom-select
                    [options]="validationStrategyOptions"
                    [value]="formDefaultValidationStrategy"
                    (valueChange)="formDefaultValidationStrategy = $event"
                    [size]="'md'">
                  </app-custom-select>
                </div>

              </div>

            </div>

            <!-- Section 3: Responsibility & Custodianship (Informational Context) -->
            <div class="p-6 sm:p-7 rounded-xl bg-white border border-slate-200 shadow-xs flex flex-col gap-5">
              
              <div class="pb-3 border-b border-slate-200 flex flex-col gap-0.5">
                <h2 class="text-base font-bold text-slate-900 font-heading">
                  Project Custodianship &amp; Contacts
                </h2>
                <p class="text-xs text-slate-600 font-normal">
                  Primary operational contacts for escalation and coordination. Designating a lead provides operational context and does not bypass RBAC or approval authority.
                </p>
              </div>

              <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div class="flex flex-col gap-1.5">
                  <label class="text-xs font-bold text-slate-800">Technical Lead</label>
                  <input
                    type="text"
                    [(ngModel)]="formLeadName"
                    placeholder="Enter lead name..."
                    class="w-full h-9 px-3 rounded-md bg-slate-50 hover:bg-slate-100/70 focus:bg-white border border-slate-300 text-xs font-medium text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 shadow-2xs"
                  />
                </div>
                <div class="flex flex-col gap-1.5">
                  <label class="text-xs font-bold text-slate-800">Technical Lead Email</label>
                  <input
                    type="email"
                    [(ngModel)]="formLeadEmail"
                    placeholder="lead@enterprise.corp..."
                    class="w-full h-9 px-3 rounded-md bg-slate-50 hover:bg-slate-100/70 focus:bg-white border border-slate-300 text-xs font-medium text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 shadow-2xs"
                  />
                </div>
              </div>

            </div>

            <!-- Save Action Bar -->
            <div class="flex items-center justify-between p-4 rounded-xl bg-white border border-slate-200 shadow-2xs">
              <div class="flex items-center gap-2 text-xs">
                @if (ps.settingsSaveStatus() === 'SAVED') {
                  <span class="text-emerald-700 font-semibold flex items-center gap-1.5">
                    <app-lucide-icon name="check" [size]="14" class="text-emerald-600"></app-lucide-icon>
                    <span>Project settings updated locally.</span>
                  </span>
                } @else {
                  <span class="text-slate-500">Unsaved configuration changes will not affect active pipelines until confirmed.</span>
                }
              </div>

              <!-- Primary Action: Save Changes (Text Only, No Icon, Restrained Rectangular) -->
              <button
                type="button"
                (click)="saveSettings()"
                class="h-8 px-4 rounded-md bg-blue-600 hover:bg-blue-700 active:bg-blue-800 text-white text-xs font-semibold shadow-2xs transition-colors cursor-pointer">
                Save Changes
              </button>
            </div>

            <!-- Section 4: Lifecycle & Danger Zone -->
            <div class="p-6 sm:p-7 rounded-xl bg-white border border-rose-200 shadow-xs flex flex-col gap-5">
              
              <div class="pb-3 border-b border-rose-100 flex flex-col gap-0.5">
                <h2 class="text-base font-bold text-rose-900 font-heading">
                  Project Lifecycle Actions
                </h2>
                <p class="text-xs text-rose-700 font-normal">
                  Consequential lifecycle transitions for this project boundary.
                </p>
              </div>

              <div class="flex items-center justify-between gap-4 flex-wrap">
                <div class="flex flex-col gap-0.5 max-w-xl">
                  <span class="text-xs font-bold text-slate-900">
                    {{ proj.status === 'ARCHIVED' ? 'Restore Archived Project' : 'Archive Project' }}
                  </span>
                  <p class="text-xs text-slate-500 font-normal leading-relaxed">
                    {{ proj.status === 'ARCHIVED'
                      ? 'Reactivating this project returns it to operational planning state and enables pipeline execution.'
                      : 'Archiving suspends active migration and validation workloads in this project boundary while preserving full audit history and data parity reports.' }}
                  </p>
                </div>

                @if (proj.status === 'ARCHIVED') {
                  <button
                    type="button"
                    (click)="restoreProject()"
                    class="h-8 px-3.5 rounded-md bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold shadow-2xs transition-colors cursor-pointer shrink-0">
                    Restore Project
                  </button>
                } @else {
                  <button
                    type="button"
                    (click)="openArchiveModal()"
                    class="h-8 px-3.5 rounded-md bg-rose-600 hover:bg-rose-700 active:bg-rose-800 text-white text-xs font-semibold shadow-2xs transition-colors cursor-pointer shrink-0">
                    Archive Project
                  </button>
                }
              </div>

            </div>

          </div>
        }

      }

      <!-- Archive Project Confirmation Modal -->
      @if (ps.archiveProjectModalOpen()) {
        <div
          class="fixed inset-0 bg-slate-900/40 backdrop-blur-xs flex items-center justify-center p-4 z-50 animate-in fade-in duration-150"
          (click)="closeArchiveModal()">
          <div
            class="bg-white rounded-xl shadow-2xl border border-slate-200 max-w-md w-full p-6 flex flex-col gap-4 select-none animate-in zoom-in-95 duration-150"
            (click)="$event.stopPropagation()">
            
            <div class="flex items-start justify-between pb-2 border-b border-slate-100">
              <div class="flex flex-col gap-0.5">
                <span class="text-[10px] font-bold uppercase tracking-wider text-rose-600">Consequential Lifecycle Action</span>
                <h3 class="text-base font-bold text-slate-900 font-heading">Archive Project</h3>
              </div>
              <button
                type="button"
                (click)="closeArchiveModal()"
                class="w-7 h-7 rounded-md hover:bg-slate-100 text-slate-400 hover:text-slate-700 flex items-center justify-center font-bold cursor-pointer">
                &times;
              </button>
            </div>

            <p class="text-xs text-slate-600 leading-relaxed">
              Are you sure you want to archive <strong>{{ ps.activeProject()?.name }}</strong>?
            </p>

            <div class="p-3 rounded-lg bg-rose-50 border border-rose-200 text-xs text-rose-900">
              Archiving will immediately pause active replication tasks and mark all associated validation missions as inactive. Project records remain inspectable in read-only mode.
            </div>

            <div class="flex items-center justify-end gap-2.5 pt-2 border-t border-slate-100">
              <button
                type="button"
                (click)="closeArchiveModal()"
                class="h-8 px-3.5 rounded-md bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold cursor-pointer">
                Cancel
              </button>
              <button
                type="button"
                (click)="confirmArchiveProject()"
                class="h-8 px-3.5 rounded-md bg-rose-600 hover:bg-rose-700 active:bg-rose-800 text-white text-xs font-semibold shadow-2xs cursor-pointer">
                Archive Project
              </button>
            </div>

          </div>
        </div>
      }

    </div>
  `
})
export class ProjectSettingsComponent implements OnInit {
  public ps = inject(ProjectsService);

  public formName: string = '';
  public formDescription: string = '';
  public formInitiativeId: string | null = null;
  public formDefaultMigrationMode: string = 'ONLINE_CDC';
  public formDefaultValidationStrategy: string = 'Structural';
  public formLeadName: string = 'Aalok Ladwa';
  public formLeadEmail: string = 'aalok.ladwa@enterprise.corp';

  public initiativeOptions = computed<CustomSelectOption[]>(() => {
    const list: CustomSelectOption[] = [
      {
        label: 'Standalone Project (No parent initiative)',
        value: null,
        desc: 'Project operates independently without rollups to a portfolio transformation program.'
      }
    ];
    for (const init of this.ps.initiatives()) {
      list.push({
        label: `${init.name} (${init.key})`,
        value: init.id,
        desc: init.objective || init.description,
        badge: init.status
      });
    }
    return list;
  });

  public migrationModeOptions: CustomSelectOption[] = [
    {
      label: 'Online CDC (Continuous stream replication)',
      value: 'ONLINE_CDC',
      desc: 'Real-time change data capture for minimal-downtime cutovers'
    },
    {
      label: 'Offline Bulk (High-throughput batch snapshot)',
      value: 'OFFLINE_BULK',
      desc: 'High-speed multi-threaded snapshot for batch workloads'
    },
    {
      label: 'Dual-Run Sync (Shadow live traffic)',
      value: 'DUAL_RUN',
      desc: 'Shadow mirror replication validating live read/write traffic'
    },
    {
      label: 'Schema Only (DDL generation without data movement)',
      value: 'SCHEMA_ONLY',
      desc: 'Generates and validates target DDL without moving table data'
    }
  ];

  public validationStrategyOptions: CustomSelectOption[] = [
    {
      label: 'Structural (Schema constraints, columns & indexes)',
      value: 'Structural',
      desc: 'Fast schema topology and column data type compatibility assertion'
    },
    {
      label: 'Cardinality (Row counts & partition sizes)',
      value: 'Cardinality',
      desc: 'Table and partition level row count parity verification'
    },
    {
      label: 'Partition Fingerprint (Sampling hash verification)',
      value: 'Partition Fingerprint',
      desc: 'Cryptographic hash checksums on representative data partitions'
    },
    {
      label: 'Complete Attribute (Cell-by-cell parity assertion)',
      value: 'Complete Attribute',
      desc: 'Exhaustive cell-by-cell data parity verification across entire table estate'
    }
  ];

  constructor() {
    effect(() => {
      const proj = this.ps.activeProject();
      if (proj) {
        this.formName = proj.name;
        this.formDescription = proj.description || '';
        this.formInitiativeId = proj.initiativeId || null;
      }
    });
  }

  ngOnInit(): void {
    const proj = this.ps.activeProject();
    if (proj) {
      this.formName = proj.name;
      this.formDescription = proj.description || '';
      this.formInitiativeId = proj.initiativeId || null;
    }
  }

  public saveSettings(): void {
    const proj = this.ps.activeProject();
    if (!proj) return;
    this.ps.updateProjectGeneral(proj.id, this.formName, this.formDescription, this.formInitiativeId);
  }

  public openArchiveModal(): void {
    this.ps.archiveProjectModalOpen.set(true);
  }

  public closeArchiveModal(): void {
    this.ps.archiveProjectModalOpen.set(false);
  }

  public confirmArchiveProject(): void {
    const proj = this.ps.activeProject();
    if (!proj) return;
    this.ps.archiveProject(proj.id);
  }

  public restoreProject(): void {
    const proj = this.ps.activeProject();
    if (!proj) return;
    this.ps.restoreProject(proj.id);
  }
}

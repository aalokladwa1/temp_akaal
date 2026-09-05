import { Component, inject, signal, computed, OnInit, HostListener } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MigrationUiService } from '../../../../core/services/migration-ui.service';
import { MigrationHomeService } from '../../../../core/services/migration-home.service';
import { MigrationMode } from '../../../../core/models/migration-view.models';
import { ProjectHomeRow } from '../../../../core/models/migration-home.models';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';

export interface CanonicalModeCard {
  mode: MigrationMode;
  title: string;
  subtitle: string;
}

export interface EnvironmentOption {
  id: string;
  name: string;
  color: string;
}

@Component({
  selector: 'app-step1-definition',
  standalone: true,
  imports: [CommonModule, FormsModule, LucideIconComponent],
  template: `
    <div class="w-full max-w-6xl mx-auto flex flex-col gap-4 font-sans select-none animate-in fade-in duration-150 text-xs">
      
      <!-- ========================================================================= -->
      <!-- 0. RESTRAINED PAGE INTRODUCTION                                           -->
      <!-- ========================================================================= -->
      <div class="flex flex-col gap-0.5 border-b border-slate-200/60 pb-1.5">
        <h1 class="text-base font-bold text-slate-900 tracking-tight">Define Migration</h1>
        <p class="text-xs text-slate-500 font-normal">Set the migration context and execution strategy.</p>
      </div>

      <!-- ========================================================================= -->
      <!-- 1. MIGRATION DEFINITION SECTION                                           -->
      <!-- ========================================================================= -->
      <section class="flex flex-col gap-2.5">
        <h2 class="text-[11px] font-bold uppercase tracking-wider text-slate-500 pb-0.5 border-b border-slate-200/60">
          Migration Definition
        </h2>

        <!-- Top Row: Migration Title (60%) & Binary Environment (40%) -->
        <div class="grid grid-cols-1 md:grid-cols-12 gap-4">
          
          <!-- Migration Title Input -->
          <div class="md:col-span-8 flex flex-col gap-1.5">
            <label for="step1-migration-title" class="text-xs font-semibold text-slate-700 flex items-center justify-between">
              <span>Migration Title <span class="text-rose-500">*</span></span>
            </label>
            <input
              id="step1-migration-title"
              type="text"
              [ngModel]="ms.wizardDraft().name"
              (ngModelChange)="onNameChange($event)"
              (blur)="nameTouched.set(true)"
              placeholder="e.g. Core Banking Oracle to Aurora Postgres"
              class="w-full h-9 px-3 text-xs bg-white border rounded-lg focus:outline-none transition-colors text-slate-900 placeholder:text-slate-400"
              [class.border-slate-200]="!isNameInvalid()"
              [class.focus:border-blue-600]="!isNameInvalid()"
              [class.border-rose-400]="isNameInvalid()"
              [class.bg-rose-50]="isNameInvalid()" />
            
            @if (isNameInvalid()) {
              <span class="text-[11px] text-rose-600 font-medium animate-in fade-in duration-100">
                Migration title is required.
              </span>
            }
          </div>

          <!-- Binary Environment Selector (Strictly Production & Non-Production) -->
          <div class="md:col-span-4 flex flex-col gap-1.5 relative" (click)="$event.stopPropagation()">
            <label class="text-xs font-semibold text-slate-700 block">
              Environment <span class="text-rose-500">*</span>
            </label>

            <button
              type="button"
              (click)="toggleDropdown('environment', $event)"
              class="w-full h-9 px-3 rounded-lg bg-white hover:bg-slate-50 border border-slate-200 flex items-center justify-between text-xs font-medium text-slate-800 cursor-pointer transition-colors focus:outline-none focus:border-blue-600">
              <div class="flex items-center gap-2 min-w-0">
                <span class="w-1.5 h-1.5 rounded-full shrink-0" [ngClass]="getEnvColor(ms.wizardDraft().environment)"></span>
                <span class="truncate">{{ ms.wizardDraft().environment || 'Production' }}</span>
              </div>
              <app-lucide-icon name="chevron-down" [size]="13" class="text-slate-400 shrink-0 ml-1"></app-lucide-icon>
            </button>

            @if (activeDropdown() === 'environment') {
              <div 
                class="absolute top-full left-0 right-0 mt-1.5 rounded-lg bg-white border border-slate-200 p-1 flex flex-col gap-0.5 z-50 animate-in fade-in duration-100">
                @for (env of environmentOptions; track env.id) {
                  <button
                    type="button"
                    (click)="selectEnvironment(env.id)"
                    class="w-full text-left px-2.5 py-1.5 rounded-md text-xs font-medium text-slate-700 hover:text-slate-900 hover:bg-slate-50 transition-colors flex items-center justify-between cursor-pointer"
                    [class.bg-blue-50]="ms.wizardDraft().environment === env.id"
                    [class.text-blue-700]="ms.wizardDraft().environment === env.id">
                    <div class="flex items-center gap-2">
                      <span class="w-1.5 h-1.5 rounded-full" [ngClass]="env.color"></span>
                      <span class="font-semibold text-slate-900">{{ env.name }}</span>
                    </div>
                    @if (ms.wizardDraft().environment === env.id) {
                      <app-lucide-icon name="check" [size]="13" class="text-blue-600 shrink-0"></app-lucide-icon>
                    }
                  </button>
                }
              </div>
            }
          </div>

        </div>

        <!-- Row 2: Project / Initiative (Single Logical Field) -->
        <div class="flex flex-col gap-1.5">
          <label class="text-xs font-semibold text-slate-700 block">
            Project / Initiative
          </label>
          
          <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
            
            <!-- Primary Choice: Independent vs Assign -->
            <div class="relative" (click)="$event.stopPropagation()">
              <button
                type="button"
                (click)="toggleDropdown('associationType', $event)"
                class="w-full h-9 px-3 rounded-lg bg-white hover:bg-slate-50 border border-slate-200 flex items-center justify-between text-xs font-medium text-slate-800 cursor-pointer transition-colors focus:outline-none focus:border-blue-600">
                <span class="truncate">{{ isAssignedToProject() ? 'Assign to Project / Initiative' : 'Independent Migration' }}</span>
                <app-lucide-icon name="chevron-down" [size]="13" class="text-slate-400 shrink-0 ml-1.5"></app-lucide-icon>
              </button>

              @if (activeDropdown() === 'associationType') {
                <div 
                  class="absolute top-full left-0 right-0 mt-1.5 rounded-lg bg-white border border-slate-200 p-1 flex flex-col gap-0.5 z-50 animate-in fade-in duration-100">
                  
                  <!-- Option 1: Independent Migration -->
                  <button
                    type="button"
                    (click)="setAssociationType('INDEPENDENT')"
                    class="w-full text-left px-2.5 py-2 rounded-md text-xs font-medium text-slate-700 hover:text-slate-900 hover:bg-slate-50 transition-colors flex items-center justify-between cursor-pointer"
                    [class.bg-blue-50]="!isAssignedToProject()"
                    [class.text-blue-700]="!isAssignedToProject()">
                    <div class="flex flex-col">
                      <span class="font-semibold text-slate-900">Independent Migration</span>
                      <span class="text-[11px] text-slate-500 font-normal">No project or initiative association</span>
                    </div>
                    @if (!isAssignedToProject()) {
                      <app-lucide-icon name="check" [size]="14" class="text-blue-600 shrink-0"></app-lucide-icon>
                    }
                  </button>

                  <div class="border-t border-slate-100 my-0.5"></div>

                  <!-- Option 2: Assign to Project / Initiative -->
                  <button
                    type="button"
                    (click)="setAssociationType('ASSIGN')"
                    class="w-full text-left px-2.5 py-2 rounded-md text-xs font-medium text-slate-700 hover:text-slate-900 hover:bg-slate-50 transition-colors flex items-center justify-between cursor-pointer"
                    [class.bg-blue-50]="isAssignedToProject()"
                    [class.text-blue-700]="isAssignedToProject()">
                    <div class="flex flex-col">
                      <span class="font-semibold text-slate-900">Assign to Project / Initiative</span>
                      <span class="text-[11px] text-slate-500 font-normal">Associate this migration with an existing project or initiative</span>
                    </div>
                    @if (isAssignedToProject()) {
                      <app-lucide-icon name="check" [size]="14" class="text-blue-600 shrink-0"></app-lucide-icon>
                    }
                  </button>

                </div>
              }
            </div>

            <!-- Conditional Project Selector (Revealed when Assigned) -->
            @if (isAssignedToProject()) {
              <div class="relative" (click)="$event.stopPropagation()">
                <button
                  type="button"
                  (click)="toggleDropdown('projectPicker', $event)"
                  class="w-full h-9 px-3 rounded-lg bg-slate-50 hover:bg-slate-100/80 border border-slate-200 flex items-center justify-between text-xs font-medium text-slate-800 cursor-pointer transition-colors focus:outline-none focus:border-blue-600">
                  <span class="truncate" [class.text-slate-400]="!selectedProject()">
                    {{ selectedProject()?.name || 'Search/select project or initiative…' }}
                  </span>
                  <app-lucide-icon name="chevron-down" [size]="13" class="text-slate-400 shrink-0 ml-1.5"></app-lucide-icon>
                </button>

                @if (activeDropdown() === 'projectPicker') {
                  <div 
                    class="absolute top-full left-0 right-0 mt-1.5 rounded-lg bg-white border border-slate-200 p-2 flex flex-col gap-1.5 z-50 animate-in fade-in duration-100 max-h-56 overflow-y-auto">
                    
                    <!-- Search input -->
                    <div class="relative">
                      <input
                        type="text"
                        [(ngModel)]="projectSearchQuery"
                        placeholder="Search projects..."
                        class="w-full h-7 pl-7 pr-2 text-xs bg-slate-50 border border-slate-200 rounded text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-blue-600" />
                      <app-lucide-icon name="search" [size]="12" class="absolute left-2 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none"></app-lucide-icon>
                    </div>

                    <div class="flex flex-col gap-0.5 mt-1">
                      @for (p of filteredProjects(); track p.id) {
                        <button
                          type="button"
                          (click)="selectProject(p.id)"
                          class="w-full text-left px-2.5 py-1.5 rounded-md text-xs font-medium text-slate-700 hover:text-slate-900 hover:bg-slate-50 transition-colors flex items-center justify-between cursor-pointer"
                          [class.bg-blue-50]="ms.wizardDraft().projectId === p.id"
                          [class.text-blue-700]="ms.wizardDraft().projectId === p.id">
                          <div class="flex flex-col min-w-0">
                            <span class="font-semibold text-slate-900 truncate">{{ p.name }}</span>
                            <span class="text-[10px] text-slate-500 truncate">{{ p.environment }} &middot; {{ p.migration_count }} migrations</span>
                          </div>
                          @if (ms.wizardDraft().projectId === p.id) {
                            <app-lucide-icon name="check" [size]="13" class="text-blue-600 shrink-0"></app-lucide-icon>
                          }
                        </button>
                      }
                      @if (filteredProjects().length === 0) {
                        <div class="py-3 text-center text-slate-400 text-xs">No matching projects found</div>
                      }
                    </div>

                  </div>
                }
              </div>
            }

          </div>

        </div>

      </section>

      <!-- ========================================================================= -->
      <!-- 2. EXECUTION STRATEGY SECTION (Balanced 2-Column Grid)                     -->
      <!-- ========================================================================= -->
      <section class="flex flex-col gap-3">
        <div class="flex items-center justify-between pb-1 border-b border-slate-200/60">
          <div class="flex items-center gap-2">
            <h2 class="text-[11px] font-bold uppercase tracking-wider text-slate-500">
              Execution Strategy <span class="text-rose-500">*</span>
            </h2>
            <span class="text-slate-300 font-light">&middot;</span>
            <span class="text-xs text-slate-400 font-normal">Choose how AKAAL should execute this migration.</span>
          </div>
          <span class="text-[11px] text-slate-400 font-normal">7 Canonical Creation Modes</span>
        </div>

        <!-- 2-Column Mode Tiles Grid (No "MX" Badges, Zero Shadow, Zero Hover Movement) -->
        <div class="grid grid-cols-1 md:grid-cols-2 gap-2.5 lg:gap-3">
          @for (card of canonicalModes; track card.mode) {
            <div
              (click)="selectMode(card.mode)"
              class="p-2.5 lg:p-3 border rounded-lg cursor-pointer bg-white transition-colors select-none flex flex-col justify-between gap-0.5 min-h-[58px]"
              [class.border-blue-600]="ms.wizardDraft().mode === card.mode"
              [class.ring-1]="ms.wizardDraft().mode === card.mode"
              [class.ring-blue-600]="ms.wizardDraft().mode === card.mode"
              [class.bg-blue-50]="ms.wizardDraft().mode === card.mode"
              [class.border-slate-200]="ms.wizardDraft().mode !== card.mode"
              [class.hover:border-slate-300]="ms.wizardDraft().mode !== card.mode"
              [class.hover:bg-slate-50]="ms.wizardDraft().mode !== card.mode">
              
              <div class="flex items-center justify-between">
                <span class="text-xs font-bold text-slate-900 truncate">{{ card.title }}</span>

                @if (ms.wizardDraft().mode === card.mode) {
                  <div class="w-4 h-4 rounded-full bg-blue-600 text-white flex items-center justify-center text-[10px] font-bold shrink-0">
                    ✓
                  </div>
                }
              </div>

              <p class="text-[11px] text-slate-500 leading-normal font-normal">
                {{ card.subtitle }}
              </p>

            </div>
          }
        </div>
      </section>

    </div>
  `
})
export class Step1DefinitionComponent implements OnInit {
  public ms = inject(MigrationUiService);
  public homeService = inject(MigrationHomeService);

  public activeDropdown = signal<string | null>(null);
  public isAssignedToProject = signal<boolean>(false);
  public projectSearchQuery = signal<string>('');
  public nameTouched = signal<boolean>(false);

  // 1. Canonical Project Options from MigrationHomeService
  public availableProjects = computed<ProjectHomeRow[]>(() => this.homeService.projects());

  public filteredProjects = computed(() => {
    const q = this.projectSearchQuery().trim().toLowerCase();
    const list = this.availableProjects();
    if (!q) return list;
    return list.filter(p => p.name.toLowerCase().includes(q) || p.environment.toLowerCase().includes(q));
  });

  public selectedProject = computed(() => {
    const pid = this.ms.wizardDraft().projectId;
    if (!pid) return undefined;
    return this.availableProjects().find(p => p.id === pid);
  });

  // 2. Strictly Two Environment Options: Production & Non-Production
  public readonly environmentOptions: EnvironmentOption[] = [
    { id: 'Production', name: 'Production', color: 'bg-rose-500' },
    { id: 'Non-Production', name: 'Non-Production', color: 'bg-emerald-500' }
  ];

  // 3. Exactly Seven Canonical Creation Modes (No MX badges, clean title + micro-phrase subtitle)
  public readonly canonicalModes: CanonicalModeCard[] = [
    {
      mode: 'M1_BULK',
      title: 'Bulk Migration',
      subtitle: 'One-time full snapshot'
    },
    {
      mode: 'M2_BULK_CDC',
      title: 'Bulk + CDC',
      subtitle: 'Full load with continuous sync'
    },
    {
      mode: 'M3_CDC',
      title: 'CDC Replication',
      subtitle: 'Log-based live streaming'
    },
    {
      mode: 'M4_INCREMENTAL',
      title: 'Incremental Polling',
      subtitle: 'Watermark and cursor polling'
    },
    {
      mode: 'M5_STATE_SYNC',
      title: 'State Synchronization',
      subtitle: 'Merkle-diff state comparison'
    },
    {
      mode: 'M6_SCHEMA_ONLY',
      title: 'Schema Only',
      subtitle: 'DDL, views, and routines only'
    },
    {
      mode: 'M7_DATA_ONLY',
      title: 'Data Only',
      subtitle: 'Transport into prepared schema'
    }
  ];

  public ngOnInit(): void {
    const draft = this.ms.wizardDraft();
    if (!draft.environment) {
      this.ms.updateDraft({ environment: 'Production' });
    }
    if (draft.projectId) {
      this.isAssignedToProject.set(true);
    }
  }

  @HostListener('document:click', ['$event'])
  public onDocClick(): void {
    this.activeDropdown.set(null);
  }

  public toggleDropdown(name: string, event: MouseEvent): void {
    event.stopPropagation();
    this.activeDropdown.update(curr => (curr === name ? null : name));
  }

  public onNameChange(name: string): void {
    this.nameTouched.set(true);
    this.ms.updateDraft({ name });
  }

  public setAssociationType(type: 'INDEPENDENT' | 'ASSIGN'): void {
    if (type === 'INDEPENDENT') {
      this.isAssignedToProject.set(false);
      this.ms.updateDraft({ projectId: undefined });
    } else {
      this.isAssignedToProject.set(true);
      const projects = this.availableProjects();
      if (projects.length > 0 && !this.ms.wizardDraft().projectId) {
        this.ms.updateDraft({ projectId: projects[0].id });
      }
    }
    this.activeDropdown.set(null);
  }

  public selectProject(projectId: string): void {
    this.ms.updateDraft({ projectId });
    this.activeDropdown.set(null);
  }

  public selectEnvironment(env: string): void {
    this.ms.updateDraft({ environment: env });
    this.activeDropdown.set(null);
  }

  public selectMode(mode: MigrationMode): void {
    this.ms.updateWizardMode(mode);
  }

  public getEnvColor(env: string): string {
    switch (env) {
      case 'Production': return 'bg-rose-500';
      case 'Non-Production': return 'bg-emerald-500';
      default: return 'bg-rose-500';
    }
  }

  public isNameInvalid(): boolean {
    return this.nameTouched() && !(this.ms.wizardDraft().name || '').trim();
  }
}

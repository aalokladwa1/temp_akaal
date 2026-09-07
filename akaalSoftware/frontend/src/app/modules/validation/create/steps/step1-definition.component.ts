import { Component, inject, signal, computed, OnInit, HostListener } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ValidationUiService, ValidationContextType } from '../../../../core/services/validation-ui.service';
import { MigrationHomeService } from '../../../../core/services/migration-home.service';
import { ProjectHomeRow } from '../../../../core/models/migration-home.models';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';

export interface EnvironmentOption {
  id: 'Production' | 'Non-Production';
  name: string;
  color: string;
}

@Component({
  selector: 'app-step1-definition',
  standalone: true,
  imports: [CommonModule, FormsModule, LucideIconComponent],
  template: `
    <div class="w-full max-w-6xl mx-auto flex flex-col gap-6 font-sans select-none animate-in fade-in duration-150 text-xs">
      
      <!-- ========================================================================= -->
      <!-- 0. RESTRAINED PAGE INTRODUCTION                                           -->
      <!-- ========================================================================= -->
      <div class="flex flex-col gap-0.5 border-b border-slate-200/60 pb-2">
        <h1 class="text-base font-bold text-slate-900 tracking-tight">Define Validation</h1>
        <p class="text-xs text-slate-500 font-normal">Establish validation identity, environment target, and project association context.</p>
      </div>

      <!-- ========================================================================= -->
      <!-- 1. VALIDATION DEFINITION SECTION                                          -->
      <!-- ========================================================================= -->
      <section class="flex flex-col gap-4">
        <h2 class="text-[11px] font-bold uppercase tracking-wider text-slate-500 pb-1 border-b border-slate-200/60">
          Validation Definition
        </h2>

        <!-- Top Row: Validation Title (60%) & Binary Environment (40%) -->
        <div class="grid grid-cols-1 md:grid-cols-12 gap-4">
          
          <!-- Validation Name Input -->
          <div class="md:col-span-8 flex flex-col gap-1.5">
            <label for="step1-validation-name" class="text-xs font-semibold text-slate-700 flex items-center justify-between">
              <span>Validation Name <span class="text-rose-500">*</span></span>
            </label>
            <input
              id="step1-validation-name"
              type="text"
              [ngModel]="vs.newValidationDraft().name"
              (ngModelChange)="onNameChange($event)"
              (blur)="nameTouched.set(true)"
              placeholder="Enter validation name"
              class="w-full h-9 px-3 text-xs bg-white border rounded-lg focus:outline-none transition-colors text-slate-900 placeholder:text-slate-400"
              [class.border-slate-200]="!isNameInvalid()"
              [class.focus:border-blue-600]="!isNameInvalid()"
              [class.border-rose-400]="isNameInvalid()"
              [class.bg-rose-50]="isNameInvalid()" />
            
            @if (isNameInvalid()) {
              <span class="text-[11px] text-rose-600 font-medium animate-in fade-in duration-100">
                Validation name is required.
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
                <span class="w-1.5 h-1.5 rounded-full shrink-0" [ngClass]="getEnvColor(vs.newValidationDraft().environment)"></span>
                <span class="truncate">{{ vs.newValidationDraft().environment || 'Production' }}</span>
              </div>
              <app-lucide-icon name="chevron-down" [size]="13" class="text-slate-400 shrink-0 ml-1"></app-lucide-icon>
            </button>

            @if (activeDropdown() === 'environment') {
              <div 
                class="absolute top-full left-0 right-0 mt-1.5 rounded-lg bg-white border border-slate-200 p-1 flex flex-col gap-0.5 z-50 shadow-md animate-in fade-in duration-100">
                @for (env of environmentOptions; track env.id) {
                  <button
                    type="button"
                    (click)="selectEnvironment(env.id)"
                    class="w-full text-left px-2.5 py-1.5 rounded-md text-xs font-medium text-slate-700 hover:text-slate-900 hover:bg-slate-50 transition-colors flex items-center justify-between cursor-pointer"
                    [class.bg-blue-50]="vs.newValidationDraft().environment === env.id"
                    [class.text-blue-700]="vs.newValidationDraft().environment === env.id">
                    <div class="flex items-center gap-2">
                      <span class="w-1.5 h-1.5 rounded-full" [ngClass]="env.color"></span>
                      <span class="font-semibold text-slate-900">{{ env.name }}</span>
                    </div>
                    @if (vs.newValidationDraft().environment === env.id) {
                      <app-lucide-icon name="check" [size]="13" class="text-blue-600 shrink-0"></app-lucide-icon>
                    }
                  </button>
                }
              </div>
            }
          </div>

        </div>

        <!-- Row 2: Project / Initiative Association -->
        <div class="flex flex-col gap-1.5">
          <label class="text-xs font-semibold text-slate-700 block">
            Project / Initiative <span class="text-rose-500">*</span>
          </label>
          
          <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
            
            <!-- Primary Choice: Independent vs Existing Project -->
            <div class="relative" (click)="$event.stopPropagation()">
              <button
                type="button"
                (click)="toggleDropdown('contextType', $event)"
                class="w-full h-9 px-3 rounded-lg bg-white hover:bg-slate-50 border border-slate-200 flex items-center justify-between text-xs font-medium text-slate-800 cursor-pointer transition-colors focus:outline-none focus:border-blue-600">
                <div class="flex items-center gap-2 min-w-0">
                  <app-lucide-icon [name]="isLinkedToProject() ? 'folder-kanban' : 'shield-check'" [size]="13" class="text-slate-500 shrink-0"></app-lucide-icon>
                  <span class="truncate">{{ isLinkedToProject() ? 'Existing AKAAL project' : 'Independent validation' }}</span>
                </div>
                <app-lucide-icon name="chevron-down" [size]="13" class="text-slate-400 shrink-0 ml-1.5"></app-lucide-icon>
              </button>

              @if (activeDropdown() === 'contextType') {
                <div 
                  class="absolute top-full left-0 right-0 mt-1.5 rounded-lg bg-white border border-slate-200 p-1 flex flex-col gap-0.5 z-50 shadow-md animate-in fade-in duration-100">
                  
                  <!-- Option 1: Independent validation -->
                  <button
                    type="button"
                    (click)="setContextType('INDEPENDENT')"
                    class="w-full text-left px-2.5 py-2 rounded-md text-xs font-medium text-slate-700 hover:text-slate-900 hover:bg-slate-50 transition-colors flex items-center justify-between cursor-pointer"
                    [class.bg-blue-50]="!isLinkedToProject()"
                    [class.text-blue-700]="!isLinkedToProject()">
                    <div class="flex flex-col">
                      <span class="font-semibold text-slate-900">Independent validation</span>
                      <span class="text-[11px] text-slate-500 font-normal">Validate data independently without project linkage</span>
                    </div>
                    @if (!isLinkedToProject()) {
                      <app-lucide-icon name="check" [size]="14" class="text-blue-600 shrink-0"></app-lucide-icon>
                    }
                  </button>

                  <div class="border-t border-slate-100 my-0.5"></div>

                  <!-- Option 2: Existing AKAAL project -->
                  <button
                    type="button"
                    (click)="setContextType('EXISTING_PROJECT')"
                    class="w-full text-left px-2.5 py-2 rounded-md text-xs font-medium text-slate-700 hover:text-slate-900 hover:bg-slate-50 transition-colors flex items-center justify-between cursor-pointer"
                    [class.bg-blue-50]="isLinkedToProject()"
                    [class.text-blue-700]="isLinkedToProject()">
                    <div class="flex flex-col">
                      <span class="font-semibold text-slate-900">Existing AKAAL project</span>
                      <span class="text-[11px] text-slate-500 font-normal">Associate this validation with an existing project or initiative</span>
                    </div>
                    @if (isLinkedToProject()) {
                      <app-lucide-icon name="check" [size]="14" class="text-blue-600 shrink-0"></app-lucide-icon>
                    }
                  </button>

                </div>
              }
            </div>

            <!-- Conditional Linked Project Selector (Revealed when Existing Project selected) -->
            @if (isLinkedToProject()) {
              <div class="relative flex flex-col gap-1" (click)="$event.stopPropagation()">
                <button
                  type="button"
                  (click)="toggleDropdown('projectPicker', $event)"
                  class="w-full h-9 px-3 rounded-lg bg-slate-50 hover:bg-slate-100/80 border flex items-center justify-between text-xs font-medium text-slate-800 cursor-pointer transition-colors focus:outline-none focus:border-blue-600"
                  [class.border-slate-200]="!isLinkedProjectInvalid()"
                  [class.border-rose-400]="isLinkedProjectInvalid()"
                  [class.bg-rose-50]="isLinkedProjectInvalid()">
                  <span class="truncate" [class.text-slate-400]="!selectedProject()">
                    {{ selectedProject()?.name || 'Search/select project or initiative…' }}
                  </span>
                  <app-lucide-icon name="chevron-down" [size]="13" class="text-slate-400 shrink-0 ml-1.5"></app-lucide-icon>
                </button>

                @if (isLinkedProjectInvalid()) {
                  <span class="text-[11px] text-rose-600 font-medium animate-in fade-in duration-100">
                    Please select a project to link.
                  </span>
                }

                @if (activeDropdown() === 'projectPicker') {
                  <div 
                    class="absolute top-full left-0 right-0 mt-1.5 rounded-lg bg-white border border-slate-200 p-2 flex flex-col gap-1.5 z-50 shadow-lg animate-in fade-in duration-100 max-h-56 overflow-y-auto">
                    
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
                          (click)="selectProject(p)"
                          class="w-full text-left px-2.5 py-1.5 rounded-md text-xs font-medium text-slate-700 hover:text-slate-900 hover:bg-slate-50 transition-colors flex items-center justify-between cursor-pointer"
                          [class.bg-blue-50]="vs.newValidationDraft().projectId === p.id"
                          [class.text-blue-700]="vs.newValidationDraft().projectId === p.id">
                          <div class="flex flex-col min-w-0">
                            <span class="font-semibold text-slate-900 truncate">{{ p.name }}</span>
                            <span class="text-[10px] text-slate-500 truncate">{{ p.environment }} &middot; {{ p.migration_count }} migrations</span>
                          </div>
                          @if (vs.newValidationDraft().projectId === p.id) {
                            <app-lucide-icon name="check" [size]="13" class="text-blue-600 shrink-0"></app-lucide-icon>
                          }
                        </button>
                      }
                      @if (filteredProjects().length === 0) {
                        <div class="py-3 text-center text-slate-400 text-xs font-medium">No projects available to link</div>
                      }
                    </div>

                  </div>
                }
              </div>
            }

          </div>

        </div>

      </section>

    </div>
  `
})
export class Step1DefinitionComponent implements OnInit {
  public vs: ValidationUiService;
  public homeService: MigrationHomeService;

  public activeDropdown = signal<string | null>(null);
  public projectSearchQuery = signal<string>('');
  public nameTouched = signal<boolean>(false);
  public projectPickerTouched = signal<boolean>(false);

  // Available Projects from MigrationHomeService
  public availableProjects = computed<ProjectHomeRow[]>(() => this.homeService.projects());

  public filteredProjects = computed(() => {
    const q = this.projectSearchQuery().trim().toLowerCase();
    const list = this.availableProjects();
    if (!q) return list;
    return list.filter(p => 
      p.name.toLowerCase().includes(q) || 
      p.environment.toLowerCase().includes(q)
    );
  });

  public isLinkedToProject = computed(() => this.vs.newValidationDraft().validationContext === 'EXISTING_PROJECT');

  public selectedProject = computed(() => {
    const id = this.vs.newValidationDraft().projectId;
    if (!id) return undefined;
    return this.availableProjects().find(p => p.id === id);
  });

  // Strictly Two Environment Options: Production (Red) & Non-Production (Green)
  public readonly environmentOptions: EnvironmentOption[] = [
    { id: 'Production', name: 'Production', color: 'bg-rose-500' },
    { id: 'Non-Production', name: 'Non-Production', color: 'bg-emerald-500' }
  ];

  constructor(vs?: ValidationUiService, homeService?: MigrationHomeService) {
    this.vs = vs || inject(ValidationUiService);
    this.homeService = homeService || inject(MigrationHomeService);
  }

  public ngOnInit(): void {
    const draft = this.vs.newValidationDraft();
    if (!draft.environment) {
      this.vs.updateDraft({ environment: 'Production' });
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
    this.vs.updateDraft({ name });
  }

  public setContextType(type: ValidationContextType): void {
    this.vs.setValidationContext(type);
    this.activeDropdown.set(null);
    if (type === 'EXISTING_PROJECT') {
      const projs = this.availableProjects();
      if (projs.length > 0 && !this.vs.newValidationDraft().projectId) {
        this.vs.updateDraft({
          projectId: projs[0].id,
          projectName: projs[0].name
        });
      }
    }
  }

  public selectProject(p: ProjectHomeRow): void {
    this.vs.updateDraft({
      projectId: p.id,
      projectName: p.name
    });
    this.activeDropdown.set(null);
  }

  public selectEnvironment(env: 'Production' | 'Non-Production'): void {
    this.vs.updateDraft({ environment: env });
    this.activeDropdown.set(null);
  }

  public getEnvColor(env: string): string {
    switch (env) {
      case 'Production': return 'bg-rose-500';
      case 'Non-Production': return 'bg-emerald-500';
      default: return 'bg-rose-500';
    }
  }

  public isNameInvalid(): boolean {
    return this.nameTouched() && !(this.vs.newValidationDraft().name || '').trim();
  }

  public isLinkedProjectInvalid(): boolean {
    return this.isLinkedToProject() && this.projectPickerTouched() && !this.vs.newValidationDraft().projectId;
  }
}

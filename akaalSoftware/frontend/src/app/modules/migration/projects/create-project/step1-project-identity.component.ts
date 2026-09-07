import { Component, inject, signal, computed, HostListener } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ProjectsService } from '../projects.service';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-step1-project-identity',
  standalone: true,
  imports: [CommonModule, FormsModule, LucideIconComponent],
  template: `
    <div class="w-full max-w-4xl mx-auto flex flex-col gap-6 select-none animate-in fade-in duration-150">
      
      <!-- Top Title & Subtitle Card -->
      <div class="p-6 rounded-xl bg-white border border-slate-200 shadow-xs flex flex-col gap-1.5">
        <h2 class="text-base font-bold text-slate-900 font-heading">
          Project Identity &amp; Scope
        </h2>
        <p class="text-xs text-slate-600 font-medium">
          Define the operational scope, identity key, and program alignment for this migration and validation project.
        </p>
      </div>

      <!-- Main Form Card -->
      <div class="p-6 rounded-xl bg-white border border-slate-200 shadow-xs flex flex-col gap-6">
        
        <!-- 1. Inherited Shell Context (Single Shell Authority) -->
        <div class="flex flex-col gap-2 p-4 rounded-lg bg-slate-50 border border-slate-200">
          <div class="flex items-center justify-between">
            <span class="text-[11px] font-bold uppercase tracking-wider text-slate-500 font-heading">
              Inherited Shell Context
            </span>
            <span class="text-[10.5px] font-semibold text-slate-500">Managed by Shell Context</span>
          </div>

          <div class="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-1">
            
            <!-- Organization -->
            <div class="flex items-center gap-2.5 p-2.5 rounded-md bg-white border border-slate-200 shadow-2xs">
              <div class="w-7 h-7 rounded-md bg-slate-100 flex items-center justify-center text-slate-600 shrink-0">
                <app-lucide-icon name="building-2" [size]="14"></app-lucide-icon>
              </div>
              <div class="flex flex-col min-w-0">
                <span class="text-[10px] font-semibold text-slate-400 uppercase">Organization</span>
                <span class="text-xs font-bold text-slate-800 truncate">{{ ps.cs.selectedOrg()?.name || 'Default Organization' }}</span>
              </div>
            </div>

            <!-- Workspace -->
            <div class="flex items-center gap-2.5 p-2.5 rounded-md bg-white border border-slate-200 shadow-2xs">
              <div class="w-7 h-7 rounded-md bg-slate-100 flex items-center justify-center text-slate-600 shrink-0">
                <app-lucide-icon name="panels-top-left" [size]="14"></app-lucide-icon>
              </div>
              <div class="flex flex-col min-w-0">
                <span class="text-[10px] font-semibold text-slate-400 uppercase">Workspace</span>
                <span class="text-xs font-bold text-slate-800 truncate">{{ ps.cs.selectedWorkspace()?.name || 'Default Workspace' }}</span>
              </div>
            </div>

            <!-- Environment -->
            <div class="flex items-center gap-2.5 p-2.5 rounded-md bg-white border border-slate-200 shadow-2xs">
              <div class="w-7 h-7 rounded-md bg-slate-100 flex items-center justify-center text-slate-600 shrink-0">
                <app-lucide-icon name="server" [size]="14"></app-lucide-icon>
              </div>
              <div class="flex flex-col min-w-0">
                <span class="text-[10px] font-semibold text-slate-400 uppercase">Environment</span>
                <div class="flex items-center gap-1.5">
                  <span class="text-xs font-bold text-slate-800 truncate">{{ ps.cs.selectedEnvironment()?.name || 'Production' }}</span>
                  @if (ps.cs.isProduction()) {
                    <span class="px-1 py-0.2 rounded text-[9px] font-bold bg-emerald-100 text-emerald-800 border border-emerald-300">PROD</span>
                  }
                </div>
              </div>
            </div>

          </div>
        </div>

        <!-- 2. Project Name & Key -->
        <div class="grid grid-cols-1 sm:grid-cols-3 gap-4">
          
          <!-- Name Input (2 cols) -->
          <div class="sm:col-span-2 flex flex-col gap-1.5">
            <label for="projectName" class="text-xs font-bold text-slate-800 flex items-center gap-1">
              <span>Project Name</span>
              <span class="text-red-500">*</span>
            </label>
            <input
              id="projectName"
              type="text"
              [ngModel]="ps.projectDraft().name"
              (ngModelChange)="ps.setProjectDraftName($event)"
              placeholder="e.g., Core Banking Ledger Modernization"
              class="w-full h-10 px-3.5 rounded-md bg-white border border-slate-300 text-xs font-medium text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all shadow-2xs"
            />
            <span class="text-[11px] text-slate-500">A clear operational descriptor for this project's workload group.</span>
          </div>

          <!-- Key Input (1 col) -->
          <div class="flex flex-col gap-1.5">
            <label for="projectKey" class="text-xs font-bold text-slate-800 flex items-center gap-1">
              <span>Project Key</span>
              <span class="text-slate-400 font-normal">(Auto)</span>
            </label>
            <input
              id="projectKey"
              type="text"
              [ngModel]="ps.projectDraft().key"
              (ngModelChange)="ps.setProjectDraftKey($event)"
              placeholder="e.g., CB-MOD"
              maxlength="10"
              class="w-full h-10 px-3.5 rounded-md bg-white border border-slate-300 font-mono text-xs font-bold text-blue-700 uppercase placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all shadow-2xs"
            />
            <span class="text-[11px] text-slate-500">Short unique prefix identifier.</span>
          </div>

        </div>

        <!-- 3. Purpose / Description -->
        <div class="flex flex-col gap-1.5">
          <label for="projectDescription" class="text-xs font-bold text-slate-800">
            Purpose &amp; Description
          </label>
          <textarea
            id="projectDescription"
            rows="3"
            [ngModel]="ps.projectDraft().description"
            (ngModelChange)="ps.setProjectDraftDescription($event)"
            placeholder="Explain the technical scope, target database platforms, and operational cutover objectives..."
            class="w-full p-3.5 rounded-md bg-white border border-slate-300 text-xs font-normal text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all shadow-2xs resize-none">
          </textarea>
          <span class="text-[11px] text-slate-500">Provide architecture context to assist operators and review gates.</span>
        </div>

        <!-- 4. Program / Initiative Association (Dual Dropdown pattern matching Migration Creation Step 1) -->
        <div class="flex flex-col gap-2 pt-2 border-t border-slate-100">
          <label class="text-xs font-bold text-slate-800 flex items-center justify-between">
            <span>Transformation Initiative Alignment</span>
            <span class="text-[11px] font-normal text-slate-500">Optional 0/1 Association</span>
          </label>
          <p class="text-[11.5px] text-slate-600 font-normal">
            Select whether this project is standalone or assigned to a broader transformation initiative.
          </p>

          <div class="grid grid-cols-1 md:grid-cols-2 gap-3 pt-1">
            
            <!-- Dropdown 1: Standalone vs Assign to Initiative -->
            <div class="relative" (click)="$event.stopPropagation()">
              <label class="text-[11px] font-semibold text-slate-600 mb-1 block">Project Scope Mode</label>
              <button
                type="button"
                (click)="toggleDropdown('associationMode', $event)"
                class="w-full h-10 px-3.5 rounded-md bg-white hover:bg-slate-50 border border-slate-300 flex items-center justify-between text-xs font-semibold text-slate-800 cursor-pointer transition-colors shadow-2xs focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500">
                <div class="flex items-center gap-2 min-w-0">
                  <app-lucide-icon
                    [name]="isAssignedToInitiative() ? 'target' : 'layers'"
                    [size]="14"
                    class="text-blue-600 shrink-0">
                  </app-lucide-icon>
                  <span class="truncate">{{ isAssignedToInitiative() ? 'Assign to Initiative' : 'Standalone Governed Project' }}</span>
                </div>
                <app-lucide-icon name="chevron-down" [size]="13" class="text-slate-400 shrink-0 ml-1.5"></app-lucide-icon>
              </button>

              @if (activeDropdown() === 'associationMode') {
                <div class="absolute top-full left-0 right-0 mt-1.5 rounded-lg bg-white border border-slate-200 shadow-xl p-1 flex flex-col gap-0.5 z-50 animate-in fade-in zoom-in-95 duration-100">
                  
                  <!-- Option 1: Standalone -->
                  <button
                    type="button"
                    (click)="selectAssociationMode('STANDALONE')"
                    class="w-full text-left px-3 py-2.5 rounded-md text-xs font-medium text-slate-700 hover:text-slate-900 hover:bg-slate-50 transition-colors flex items-center justify-between cursor-pointer"
                    [class.bg-blue-50]="!isAssignedToInitiative()"
                    [class.text-blue-700]="!isAssignedToInitiative()">
                    <div class="flex flex-col gap-0.5">
                      <span class="font-bold text-slate-900">Standalone Governed Project</span>
                      <span class="text-[11px] text-slate-500 font-normal">Governed independently without umbrella initiative</span>
                    </div>
                    @if (!isAssignedToInitiative()) {
                      <app-lucide-icon name="check" [size]="14" class="text-blue-600 shrink-0"></app-lucide-icon>
                    }
                  </button>

                  <div class="border-t border-slate-100 my-0.5"></div>

                  <!-- Option 2: Assign to Initiative -->
                  <button
                    type="button"
                    (click)="selectAssociationMode('ASSIGN')"
                    class="w-full text-left px-3 py-2.5 rounded-md text-xs font-medium text-slate-700 hover:text-slate-900 hover:bg-slate-50 transition-colors flex items-center justify-between cursor-pointer"
                    [class.bg-blue-50]="isAssignedToInitiative()"
                    [class.text-blue-700]="isAssignedToInitiative()">
                    <div class="flex flex-col gap-0.5">
                      <span class="font-bold text-slate-900">Assign to Initiative</span>
                      <span class="text-[11px] text-slate-500 font-normal">Associate with an existing transformation initiative</span>
                    </div>
                    @if (isAssignedToInitiative()) {
                      <app-lucide-icon name="check" [size]="14" class="text-blue-600 shrink-0"></app-lucide-icon>
                    }
                  </button>

                </div>
              }
            </div>

            <!-- Dropdown 2: Search & Select Initiative (Revealed when Assign is chosen) -->
            @if (isAssignedToInitiative()) {
              <div class="relative" (click)="$event.stopPropagation()">
                <label class="text-[11px] font-semibold text-slate-600 mb-1 block">Select Initiative</label>
                <button
                  type="button"
                  (click)="toggleDropdown('initiativePicker', $event)"
                  class="w-full h-10 px-3.5 rounded-md bg-white hover:bg-slate-50 border border-slate-300 flex items-center justify-between text-xs font-semibold text-slate-800 cursor-pointer transition-colors shadow-2xs focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500">
                  <div class="flex items-center gap-2 min-w-0">
                    @if (selectedInitiative(); as init) {
                      <span class="px-1.5 py-0.2 rounded text-[9.5px] font-bold font-mono bg-indigo-50 text-indigo-700 border border-indigo-200 shrink-0">
                        {{ init.key }}
                      </span>
                      <span class="truncate font-bold text-slate-900">{{ init.name }}</span>
                    } @else {
                      <span class="text-slate-400 font-normal">Search or select an initiative...</span>
                    }
                  </div>
                  <app-lucide-icon name="chevron-down" [size]="13" class="text-slate-400 shrink-0 ml-1.5"></app-lucide-icon>
                </button>

                @if (activeDropdown() === 'initiativePicker') {
                  <div class="absolute top-full left-0 right-0 mt-1.5 rounded-lg bg-white border border-slate-200 shadow-xl p-2 flex flex-col gap-1.5 z-50 animate-in fade-in zoom-in-95 duration-100 max-h-64 overflow-y-auto">
                    
                    <!-- Search Input in Dropdown -->
                    <div class="relative">
                      <input
                        type="text"
                        [(ngModel)]="initiativeSearchQuery"
                        placeholder="Search initiatives by name, key, objective..."
                        class="w-full h-9 pl-8 pr-3 text-xs bg-slate-50 border border-slate-200 rounded-md text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-1 focus:ring-blue-500"
                      />
                      <app-lucide-icon name="search" [size]="13" class="absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none"></app-lucide-icon>
                    </div>

                    <!-- Filtered List -->
                    <div class="flex flex-col gap-1 mt-1">
                      @for (init of filteredInitiatives(); track init.id) {
                        <button
                          type="button"
                          (click)="selectInitiative(init.id)"
                          class="w-full text-left p-2 rounded-md hover:bg-slate-50 transition-colors flex items-center justify-between gap-2 cursor-pointer"
                          [class.bg-blue-50]="ps.projectDraft().initiativeId === init.id"
                          [class.text-blue-700]="ps.projectDraft().initiativeId === init.id">
                          <div class="flex flex-col min-w-0">
                            <div class="flex items-center gap-1.5">
                              <span class="px-1.5 py-0.2 rounded text-[9.5px] font-bold font-mono bg-indigo-50 text-indigo-700 border border-indigo-200 shrink-0">
                                {{ init.key }}
                              </span>
                              <span class="font-bold text-slate-900 truncate text-xs">{{ init.name }}</span>
                            </div>
                            @if (init.objective) {
                              <span class="text-[10.5px] text-slate-500 line-clamp-1 mt-0.5">{{ init.objective }}</span>
                            }
                          </div>
                          @if (ps.projectDraft().initiativeId === init.id) {
                            <app-lucide-icon name="check" [size]="14" class="text-blue-600 shrink-0"></app-lucide-icon>
                          }
                        </button>
                      }

                      @if (filteredInitiatives().length === 0) {
                        <div class="py-4 text-center text-slate-400 text-xs">
                          No matching initiatives found
                        </div>
                      }
                    </div>

                  </div>
                }
              </div>
            }

          </div>
        </div>

      </div>

    </div>
  `
})
export class Step1ProjectIdentityComponent {
  public ps = inject(ProjectsService);

  public activeDropdown = signal<'associationMode' | 'initiativePicker' | null>(null);
  public initiativeSearchQuery = '';

  public isAssignedToInitiative = computed(() => {
    return this.ps.projectDraft().initiativeId !== null;
  });

  public selectedInitiative = computed(() => {
    const id = this.ps.projectDraft().initiativeId;
    if (!id) return null;
    return this.ps.initiatives().find(i => i.id === id) || null;
  });

  public filteredInitiatives = computed(() => {
    const q = this.initiativeSearchQuery.trim().toLowerCase();
    const list = this.ps.initiatives();
    if (!q) return list;
    return list.filter(i =>
      i.name.toLowerCase().includes(q) ||
      i.key.toLowerCase().includes(q) ||
      (i.objective && i.objective.toLowerCase().includes(q))
    );
  });

  @HostListener('document:click')
  public onDocumentClick(): void {
    this.activeDropdown.set(null);
  }

  public toggleDropdown(dropdown: 'associationMode' | 'initiativePicker', event: Event): void {
    event.stopPropagation();
    if (this.activeDropdown() === dropdown) {
      this.activeDropdown.set(null);
    } else {
      this.activeDropdown.set(dropdown);
    }
  }

  public selectAssociationMode(mode: 'STANDALONE' | 'ASSIGN'): void {
    if (mode === 'STANDALONE') {
      this.ps.setProjectDraftInitiative(null);
      this.activeDropdown.set(null);
    } else {
      // Default to first initiative if none selected
      if (!this.ps.projectDraft().initiativeId && this.ps.initiatives().length > 0) {
        this.ps.setProjectDraftInitiative(this.ps.initiatives()[0].id);
      }
      this.activeDropdown.set('initiativePicker');
    }
  }

  public selectInitiative(initiativeId: string): void {
    this.ps.setProjectDraftInitiative(initiativeId);
    this.activeDropdown.set(null);
  }
}

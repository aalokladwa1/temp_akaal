import { Component, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { DialogModule } from 'primeng/dialog';
import { ProjectsService } from '../projects.service';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-projects-header',
  standalone: true,
  imports: [CommonModule, RouterLink, DialogModule, LucideIconComponent],
  template: `
    <div class="flex items-start justify-between gap-6 pb-5 border-b border-slate-200 flex-wrap">
      
      <!-- Title, Shell Context & Purpose -->
      <div class="flex flex-col gap-1.5">
        
        <!-- Active Shell Context Breadcrumb / Pill -->
        <div class="flex items-center gap-2 text-xs text-slate-500 font-medium">
          <div class="flex items-center gap-1.5 px-2 py-0.5 rounded-md bg-slate-100 text-slate-700 border border-slate-200/80">
            <app-lucide-icon name="building-2" [size]="12" class="text-slate-500"></app-lucide-icon>
            <span>{{ ps.cs.selectedOrg()?.name || 'Organization' }}</span>
          </div>
          <span class="text-slate-300">&bull;</span>
          <div class="flex items-center gap-1.5 px-2 py-0.5 rounded-md bg-slate-100 text-slate-700 border border-slate-200/80">
            <app-lucide-icon name="panels-top-left" [size]="12" class="text-slate-500"></app-lucide-icon>
            <span>{{ ps.cs.selectedWorkspace()?.name || 'Workspace' }}</span>
          </div>
          <span class="text-slate-300">&bull;</span>
          <div class="flex items-center gap-1.5 px-2 py-0.5 rounded-md bg-slate-100 text-slate-700 border border-slate-200/80">
            <app-lucide-icon name="server" [size]="12" class="text-slate-500"></app-lucide-icon>
            <span>{{ ps.cs.selectedEnvironment()?.name || 'Environment' }}</span>
            @if (ps.cs.isProduction()) {
              <span class="px-1 py-0.2 rounded text-[9px] font-bold bg-emerald-100 text-emerald-800 border border-emerald-300">PROD</span>
            }
          </div>
        </div>

        <h1 class="text-2xl font-bold text-slate-900 tracking-tight font-heading">
          Projects &amp; Initiatives
        </h1>
        <p class="text-sm font-medium text-slate-600">
          Organize migration and validation work into governed Projects and broader transformation Initiatives.
        </p>
      </div>

      <!-- Action Buttons -->
      <div class="flex items-center gap-3 pt-1">
        
        <!-- New Initiative (3-Step Creation Wizard) -->
        <a
          routerLink="/migration/initiatives/new"
          class="h-9 px-3.5 rounded-md border border-slate-200/90 bg-white hover:bg-slate-50 active:bg-slate-100 text-slate-700 font-medium text-xs inline-flex items-center justify-center cursor-pointer transition-colors shadow-2xs">
          New Initiative
        </a>

        <!-- New Project (3-Step Creation Wizard) -->
        <a
          routerLink="/migration/projects/new"
          class="h-9 px-4 rounded-md bg-blue-600 hover:bg-blue-700 active:bg-blue-800 text-white font-semibold text-xs inline-flex items-center justify-center cursor-pointer transition-colors shadow-2xs">
          New Project
        </a>
      </div>

    </div>

    <!-- Truthful Creation Notice Modal (Zero Fake Persistence) -->
    <p-dialog
      [(visible)]="isModalOpen"
      [modal]="true"
      [closable]="true"
      [draggable]="false"
      [resizable]="false"
      [style]="{ width: '480px' }"
      styleClass="p-dialog-clean">
      <ng-template #header>
        <div class="flex items-center gap-2.5">
          <div class="w-8 h-8 rounded-md bg-blue-50 border border-blue-200 flex items-center justify-center text-blue-600">
            <app-lucide-icon [name]="modalType() === 'PROJECT' ? 'layers' : 'target'" [size]="16"></app-lucide-icon>
          </div>
          <h3 class="text-sm font-bold text-slate-900 font-heading">
            {{ modalType() === 'PROJECT' ? 'Create Governed Project' : 'Create Transformation Initiative' }}
          </h3>
        </div>
      </ng-template>

      <div class="flex flex-col gap-3.5 text-xs text-slate-600 font-medium leading-relaxed py-2">
        <div class="p-3.5 rounded-lg bg-blue-50/70 border border-blue-200/80 text-blue-900 flex items-start gap-2.5">
          <app-lucide-icon name="info" [size]="16" class="text-blue-600 shrink-0 mt-0.5"></app-lucide-icon>
          <div class="flex flex-col gap-1">
            <span class="font-bold text-blue-950">P7D Backend Authority Integration In-Flight</span>
            <p class="text-blue-800 text-[11px] leading-normal">
              {{ modalType() === 'PROJECT'
                ? 'Project creation and persistence will be connected in P7D to canonical akaalPipeline authorities.'
                : 'Initiative portfolio groupings are defined at the program level and will link directly to canonical project registries in P7D.' }}
            </p>
          </div>
        </div>

        <div class="flex flex-col gap-1 text-[11px] text-slate-500">
          <span>Active Context: <strong>{{ ps.cs.selectedWorkspace()?.name || 'Default Workspace' }}</strong> &bull; <strong>{{ ps.cs.selectedEnvironment()?.name || 'Default Environment' }}</strong></span>
        </div>
      </div>

      <ng-template #footer>
        <div class="flex justify-end gap-2">
          <button
            type="button"
            (click)="isModalOpen.set(false)"
            class="h-8 px-3.5 rounded-md border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 text-xs font-semibold cursor-pointer">
            Close
          </button>
        </div>
      </ng-template>
    </p-dialog>
  `
})
export class ProjectsHeaderComponent {
  public ps = inject(ProjectsService);
  public isModalOpen = signal<boolean>(false);
  public modalType = signal<'PROJECT' | 'INITIATIVE'>('PROJECT');

  public openProjectModal(): void {
    this.modalType.set('PROJECT');
    this.isModalOpen.set(true);
  }

  public openInitiativeModal(): void {
    this.modalType.set('INITIATIVE');
    this.isModalOpen.set(true);
  }
}

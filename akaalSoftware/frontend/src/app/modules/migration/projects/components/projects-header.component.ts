import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { ProjectsService } from '../projects.service';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-projects-header',
  standalone: true,
  imports: [CommonModule, RouterLink, LucideIconComponent],
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
  `
})
export class ProjectsHeaderComponent {
  public ps = inject(ProjectsService);
}


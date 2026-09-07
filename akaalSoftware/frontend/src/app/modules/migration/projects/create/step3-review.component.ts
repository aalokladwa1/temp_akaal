import { Component, inject, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ProjectsService } from '../projects.service';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';
import { ProjectDiscoveryItem } from '../projects.models';

@Component({
  selector: 'app-step3-review',
  standalone: true,
  imports: [CommonModule, LucideIconComponent],
  template: `
    <div class="flex flex-col gap-6 max-w-4xl mx-auto py-2">
      
      <!-- Section Header -->
      <div class="flex flex-col gap-1.5 pb-4 border-b border-slate-200">
        <h2 class="text-lg font-bold text-slate-900 tracking-tight font-heading">
          Review &amp; Create Initiative
        </h2>
        <p class="text-xs text-slate-600 font-normal leading-relaxed">
          Verify your initiative parameters and project associations before submitting intent.
        </p>
      </div>

      <!-- 1. Initiative Definition Summary Card -->
      <div class="p-6 rounded-xl bg-white border border-slate-200 shadow-xs flex flex-col gap-4">
        <div class="flex items-center justify-between pb-3 border-b border-slate-100">
          <div class="flex items-center gap-2">
            <app-lucide-icon name="target" [size]="16" class="text-blue-600"></app-lucide-icon>
            <span class="text-xs font-bold text-slate-900 uppercase tracking-wider font-heading">
              Initiative Scope
            </span>
          </div>
          <button
            type="button"
            (click)="ps.setCreateWizardStep(1)"
            class="text-xs font-semibold text-blue-600 hover:text-blue-700 cursor-pointer">
            Edit
          </button>
        </div>

        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
          <div class="flex flex-col gap-1">
            <span class="text-[11px] font-bold text-slate-500 uppercase tracking-wider">Initiative Name</span>
            <span class="font-bold text-slate-900 text-sm">
              {{ ps.initiativeDraft().name || 'Untitled Initiative' }}
            </span>
          </div>

          <div class="flex flex-col gap-1">
            <span class="text-[11px] font-bold text-slate-500 uppercase tracking-wider">Context Scope</span>
            <span class="font-semibold text-slate-800">
              {{ ps.cs.selectedOrg()?.name || 'Org' }} &bull; {{ ps.cs.selectedWorkspace()?.name || 'Workspace' }} ({{ ps.cs.selectedEnvironment()?.name || 'Environment' }})
            </span>
          </div>
        </div>

        @if (ps.initiativeDraft().objective) {
          <div class="flex flex-col gap-1 pt-2 border-t border-slate-100">
            <span class="text-[11px] font-bold text-slate-500 uppercase tracking-wider">Strategic Objective</span>
            <p class="text-xs text-slate-700 leading-relaxed font-normal">
              {{ ps.initiativeDraft().objective }}
            </p>
          </div>
        }
      </div>

      <!-- 2. Associated Projects Summary Card -->
      <div class="p-6 rounded-xl bg-white border border-slate-200 shadow-xs flex flex-col gap-4">
        <div class="flex items-center justify-between pb-3 border-b border-slate-100">
          <div class="flex items-center gap-2">
            <app-lucide-icon name="layers" [size]="16" class="text-blue-600"></app-lucide-icon>
            <span class="text-xs font-bold text-slate-900 uppercase tracking-wider font-heading">
              Associated Projects ({{ selectedProjects().length }})
            </span>
          </div>
          <button
            type="button"
            (click)="ps.setCreateWizardStep(2)"
            class="text-xs font-semibold text-blue-600 hover:text-blue-700 cursor-pointer">
            Edit Selection
          </button>
        </div>

        @if (selectedProjects().length === 0) {
          <div class="py-6 flex flex-col items-center justify-center text-center gap-1.5 text-slate-500">
            <app-lucide-icon name="folder-plus" [size]="22" class="text-slate-300"></app-lucide-icon>
            <span class="text-xs font-semibold text-slate-700">No projects currently associated</span>
            <p class="text-xs text-slate-500">
              This initiative will be created as a standalone strategic portfolio grouping. You can attach projects at any time.
            </p>
          </div>
        } @else {
          <div class="divide-y divide-slate-100">
            @for (p of selectedProjects(); track p.id) {
              <div class="py-3 first:pt-0 last:pb-0 flex items-center justify-between gap-4 text-xs">
                <div class="flex items-center gap-2.5 min-w-0">
                  <span class="px-2 py-0.5 rounded-md text-[10px] font-bold font-mono bg-blue-50 text-blue-700 border border-blue-200/80 shrink-0">
                    {{ p.key }}
                  </span>
                  <span class="font-bold text-slate-900 truncate">{{ p.name }}</span>
                </div>
                <div class="flex items-center gap-3 shrink-0 text-[11px] text-slate-500 font-medium">
                  <span>{{ p.migrationCount || 0 }} migrations</span>
                  <span>&bull;</span>
                  <span class="font-semibold text-slate-800">{{ p.status || 'Active' }}</span>
                </div>
              </div>
            }
          </div>
        }
      </div>

      <!-- 3. Truthful Pre-P7D Capability Notice -->
      <div class="p-5 rounded-xl bg-amber-50/70 border border-amber-200/90 text-amber-950 flex flex-col gap-2.5 shadow-2xs">
        <div class="flex items-center gap-2">
          <app-lucide-icon name="alert-circle" [size]="16" class="text-amber-600 shrink-0"></app-lucide-icon>
          <span class="text-xs font-bold text-amber-900 uppercase tracking-wider font-heading">
            Backend Persistence Authority: Pre-P7D Convergence Notice
          </span>
        </div>
        <p class="text-xs text-amber-900/90 font-medium leading-relaxed">
          Canonical Initiative database persistence and cross-project association authorities are scheduled for Pre-P7D backend convergence. 
          The creation interface records your drafting intent without simulating fake persisted records in the production runtime.
        </p>
      </div>

    </div>
  `
})
export class Step3ReviewComponent {
  public ps = inject(ProjectsService);

  public selectedProjects = computed<ProjectDiscoveryItem[]>(() => {
    const ids = new Set(this.ps.initiativeDraft().selectedProjectIds);
    return this.ps.projects().filter(p => ids.has(p.id));
  });
}

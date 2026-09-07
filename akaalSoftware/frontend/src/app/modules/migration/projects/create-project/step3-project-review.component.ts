import { Component, inject, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ProjectsService } from '../projects.service';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-step3-project-review',
  standalone: true,
  imports: [CommonModule, LucideIconComponent],
  template: `
    <div class="w-full max-w-4xl mx-auto flex flex-col gap-6 select-none animate-in fade-in duration-150">
      
      <!-- Top Title & Subtitle Card -->
      <div class="p-6 rounded-xl bg-white border border-slate-200 shadow-xs flex flex-col gap-1.5">
        <h2 class="text-base font-bold text-slate-900 font-heading">
          Review Project Specification
        </h2>
        <p class="text-xs text-slate-600 font-medium">
          Confirm the project parameters, governance intent, and resource boundaries before creating the workspace.
        </p>
      </div>

      <!-- Main Review Summary Grid -->
      <div class="grid grid-cols-1 md:grid-cols-2 gap-5">
        
        <!-- CARD 1: Identity & Scope -->
        <div class="p-5 rounded-xl bg-white border border-slate-200 shadow-xs flex flex-col gap-3">
          <div class="flex items-center justify-between pb-2 border-b border-slate-100">
            <span class="text-xs font-bold text-slate-900 uppercase tracking-wider font-heading flex items-center gap-1.5">
              <app-lucide-icon name="layers" [size]="14" class="text-blue-600"></app-lucide-icon>
              <span>Identity &amp; Scope</span>
            </span>
            <button
              type="button"
              (click)="ps.setProjectWizardStep(1)"
              class="text-[11px] font-semibold text-blue-600 hover:text-blue-800 cursor-pointer">
              Edit
            </button>
          </div>

          <div class="flex flex-col gap-2 text-xs">
            <div class="flex items-center gap-2">
              <span class="px-2 py-0.5 rounded-md text-[10px] font-bold font-mono bg-blue-50 text-blue-700 border border-blue-200/80 shrink-0">
                {{ ps.projectDraft().key || 'PRJ' }}
              </span>
              <span class="font-bold text-slate-900 text-sm truncate">{{ ps.projectDraft().name || 'Untitled Project' }}</span>
            </div>

            @if (ps.projectDraft().description) {
              <p class="text-slate-600 text-[11.5px] leading-relaxed pt-1">
                {{ ps.projectDraft().description }}
              </p>
            } @else {
              <span class="text-slate-400 italic text-[11px]">No description provided</span>
            }
          </div>
        </div>

        <!-- CARD 2: Shell Context & Initiative Alignment -->
        <div class="p-5 rounded-xl bg-white border border-slate-200 shadow-xs flex flex-col gap-3">
          <div class="flex items-center justify-between pb-2 border-b border-slate-100">
            <span class="text-xs font-bold text-slate-900 uppercase tracking-wider font-heading flex items-center gap-1.5">
              <app-lucide-icon name="building-2" [size]="14" class="text-blue-600"></app-lucide-icon>
              <span>Context &amp; Program</span>
            </span>
            <button
              type="button"
              (click)="ps.setProjectWizardStep(1)"
              class="text-[11px] font-semibold text-blue-600 hover:text-blue-800 cursor-pointer">
              Edit
            </button>
          </div>

          <div class="flex flex-col gap-2.5 text-xs">
            
            <!-- Shell Context -->
            <div class="flex flex-col gap-1">
              <span class="text-[10px] font-semibold text-slate-400 uppercase">Shell Context</span>
              <div class="flex items-center gap-1.5 text-xs text-slate-700 font-medium">
                <span>{{ ps.cs.selectedOrg()?.name || 'Org' }}</span>
                <span class="text-slate-300">&bull;</span>
                <span>{{ ps.cs.selectedWorkspace()?.name || 'Workspace' }}</span>
                <span class="text-slate-300">&bull;</span>
                <span class="font-bold text-slate-900">{{ ps.cs.selectedEnvironment()?.name || 'Production' }}</span>
                @if (ps.cs.isProduction()) {
                  <span class="px-1 py-0.2 rounded text-[9px] font-bold bg-emerald-100 text-emerald-800 border border-emerald-300">PROD</span>
                }
              </div>
            </div>

            <!-- Initiative Association -->
            <div class="flex flex-col gap-1 pt-1">
              <span class="text-[10px] font-semibold text-slate-400 uppercase">Initiative Alignment</span>
              @if (selectedInitiative(); as init) {
                <div class="flex items-center gap-2">
                  <span class="px-1.5 py-0.2 rounded text-[9.5px] font-bold font-mono bg-indigo-50 text-indigo-700 border border-indigo-200">
                    {{ init.key }}
                  </span>
                  <span class="font-semibold text-slate-800 truncate">{{ init.name }}</span>
                </div>
              } @else {
                <span class="font-medium text-slate-600">Standalone Project (No Initiative)</span>
              }
            </div>

          </div>
        </div>

        <!-- CARD 3: Access Intent -->
        <div class="p-5 rounded-xl bg-white border border-slate-200 shadow-xs flex flex-col gap-3">
          <div class="flex items-center justify-between pb-2 border-b border-slate-100">
            <span class="text-xs font-bold text-slate-900 uppercase tracking-wider font-heading flex items-center gap-1.5">
              <app-lucide-icon name="users" [size]="14" class="text-blue-600"></app-lucide-icon>
              <span>Access Intent ({{ ps.projectDraft().accessAssignments.length }})</span>
            </span>
            <button
              type="button"
              (click)="ps.setProjectWizardStep(2)"
              class="text-[11px] font-semibold text-blue-600 hover:text-blue-800 cursor-pointer">
              Edit
            </button>
          </div>

          <div class="flex flex-col gap-1.5">
            @for (p of ps.projectDraft().accessAssignments; track p.id) {
              <div class="flex items-center justify-between p-2 rounded-md bg-slate-50 border border-slate-200/80 text-xs">
                <div class="flex items-center gap-2 min-w-0">
                  <app-lucide-icon
                    [name]="p.type === 'GROUP' ? 'users' : p.type === 'SERVICE_ACCOUNT' ? 'bot' : 'user'"
                    [size]="13"
                    class="text-slate-500 shrink-0">
                  </app-lucide-icon>
                  <span class="font-semibold text-slate-800 truncate">{{ p.name }}</span>
                </div>
                <span class="px-2 py-0.5 rounded text-[10px] font-bold bg-blue-50 text-blue-700 border border-blue-200 shrink-0">
                  {{ p.role }}
                </span>
              </div>
            }
          </div>
        </div>

        <!-- CARD 4: Resource Associations -->
        <div class="p-5 rounded-xl bg-white border border-slate-200 shadow-xs flex flex-col gap-3">
          <div class="flex items-center justify-between pb-2 border-b border-slate-100">
            <span class="text-xs font-bold text-slate-900 uppercase tracking-wider font-heading flex items-center gap-1.5">
              <app-lucide-icon name="database" [size]="14" class="text-blue-600"></app-lucide-icon>
              <span>Resource Associations ({{ ps.projectDraft().selectedResourceIds.length }})</span>
            </span>
            <button
              type="button"
              (click)="ps.setProjectWizardStep(2)"
              class="text-[11px] font-semibold text-blue-600 hover:text-blue-800 cursor-pointer">
              Edit
            </button>
          </div>

          <div class="flex flex-col gap-1.5">
            @if (selectedResources().length > 0) {
              @for (res of selectedResources(); track res.connectionId) {
                <div class="flex items-center justify-between p-2 rounded-md bg-slate-50 border border-slate-200/80 text-xs">
                  <div class="flex items-center gap-2 min-w-0">
                    <span class="px-1.5 py-0.2 rounded text-[9.5px] font-bold bg-slate-200/80 text-slate-700 uppercase shrink-0">
                      {{ res.provider }}
                    </span>
                    <span class="font-semibold text-slate-800 truncate">{{ res.connectionName }}</span>
                  </div>
                  <span class="text-[10px] text-slate-400 font-mono shrink-0">{{ res.environment }}</span>
                </div>
              }
            } @else {
              <span class="text-slate-400 italic text-[11px]">No connections associated</span>
            }
          </div>
        </div>

      </div>

      <!-- Capability & Pre-P7D Persistence Notice -->
      <div class="p-4 rounded-xl bg-blue-50/70 border border-blue-200 text-blue-950 flex items-start gap-3">
        <app-lucide-icon name="info" [size]="16" class="text-blue-600 shrink-0 mt-0.5"></app-lucide-icon>
        <div class="flex flex-col gap-1 text-xs">
          <span class="font-bold text-blue-950">Pre-P7D Project Persistence Model</span>
          <p class="text-blue-800 text-[11px] leading-relaxed">
            This project specification will be registered in your active workspace runtime state. Full synchronization with distributed akaalPipeline cluster registries and execution daemons activates in P7D.
          </p>
        </div>
      </div>

    </div>
  `
})
export class Step3ProjectReviewComponent {
  public ps = inject(ProjectsService);

  public selectedInitiative = computed(() => {
    const id = this.ps.projectDraft().initiativeId;
    if (!id) return null;
    return this.ps.initiativeWorkspaces()[id] || this.ps.initiatives().find(i => i.id === id) || null;
  });

  public selectedResources = computed(() => {
    const ids = new Set(this.ps.projectDraft().selectedResourceIds);
    return this.ps.availableConnections().filter(c => ids.has(c.connectionId));
  });
}

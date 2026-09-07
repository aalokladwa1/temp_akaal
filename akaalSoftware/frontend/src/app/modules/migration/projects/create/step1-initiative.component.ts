import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ProjectsService } from '../projects.service';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-step1-initiative',
  standalone: true,
  imports: [CommonModule, FormsModule, LucideIconComponent],
  template: `
    <div class="flex flex-col gap-6 max-w-3xl mx-auto py-2">
      
      <!-- Section Header -->
      <div class="flex flex-col gap-1.5 pb-4 border-b border-slate-200">
        <h2 class="text-lg font-bold text-slate-900 tracking-tight font-heading">
          Initiative Identity &amp; Objective
        </h2>
        <p class="text-xs text-slate-600 font-normal leading-relaxed">
          An Initiative groups related migration projects contributing to a larger transformation program.
        </p>
      </div>

      <!-- Inherited Shell Context Notice -->
      <div class="p-4 rounded-xl bg-slate-50 border border-slate-200 flex items-center justify-between gap-4 flex-wrap">
        <div class="flex items-center gap-2.5 text-xs text-slate-700">
          <app-lucide-icon name="building-2" [size]="15" class="text-slate-500 shrink-0"></app-lucide-icon>
          <span class="font-medium">Active Context Scope:</span>
          <span class="font-bold text-slate-900">
            {{ ps.cs.selectedOrg()?.name || 'Organization' }}
          </span>
          <span class="text-slate-400">&bull;</span>
          <span class="font-bold text-slate-900">
            {{ ps.cs.selectedWorkspace()?.name || 'Workspace' }}
          </span>
          <span class="text-slate-400">&bull;</span>
          <span class="font-bold text-slate-900">
            {{ ps.cs.selectedEnvironment()?.name || 'Environment' }}
          </span>
        </div>
        <span class="px-2 py-0.5 rounded-md text-[10px] font-semibold bg-blue-50 text-blue-700 border border-blue-200">
          Inherited from Shell
        </span>
      </div>

      <!-- Form Inputs -->
      <div class="flex flex-col gap-5 bg-white p-6 rounded-xl border border-slate-200 shadow-xs">
        
        <!-- 1. Initiative Name (Required) -->
        <div class="flex flex-col gap-1.5">
          <label class="text-xs font-bold text-slate-800 flex items-center gap-1">
            <span>Initiative Name</span>
            <span class="text-rose-500 font-bold">*</span>
          </label>
          <input
            type="text"
            [ngModel]="ps.initiativeDraft().name"
            (ngModelChange)="ps.setDraftName($event)"
            placeholder="e.g. Data Center Exit & Modernization 2027"
            class="w-full h-9 px-3.5 text-xs bg-white border rounded-md text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all font-medium"
            [class.border-slate-300]="ps.initiativeDraft().name.trim().length > 0"
            [class.border-slate-200]="ps.initiativeDraft().name.trim().length === 0"
            autofocus
          />
          <span class="text-[11px] text-slate-500 font-normal">
            A clear, program-level title summarizing the strategic migration objective.
          </span>
        </div>

        <!-- 2. Objective / Description (Optional) -->
        <div class="flex flex-col gap-1.5">
          <label class="text-xs font-bold text-slate-800">
            <span>Strategic Objective &amp; Scope</span>
            <span class="text-slate-400 font-normal ml-1">(Optional)</span>
          </label>
          <textarea
            rows="4"
            [ngModel]="ps.initiativeDraft().objective"
            (ngModelChange)="ps.setDraftObjective($event)"
            placeholder="Describe the business rationale, migration boundaries, target platforms, or delivery timeline..."
            class="w-full p-3 text-xs bg-white border border-slate-300 rounded-md text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all font-normal leading-relaxed resize-y">
          </textarea>
          <span class="text-[11px] text-slate-500 font-normal">
            Provide strategic context for participating migration and validation teams.
          </span>
        </div>

      </div>

    </div>
  `
})
export class Step1InitiativeComponent {
  public ps = inject(ProjectsService);
}

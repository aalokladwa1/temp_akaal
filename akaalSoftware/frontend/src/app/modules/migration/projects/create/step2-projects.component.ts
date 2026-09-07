import { Component, inject, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ProjectsService } from '../projects.service';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';
import { ProjectDiscoveryItem } from '../projects.models';

@Component({
  selector: 'app-step2-projects',
  standalone: true,
  imports: [CommonModule, FormsModule, LucideIconComponent],
  template: `
    <div class="flex flex-col gap-6 max-w-4xl mx-auto py-2">
      
      <!-- Section Header -->
      <div class="flex flex-col gap-1.5 pb-4 border-b border-slate-200">
        <div class="flex items-center justify-between gap-4 flex-wrap">
          <div>
            <h2 class="text-lg font-bold text-slate-900 tracking-tight font-heading">
              Associate Projects
            </h2>
            <p class="text-xs text-slate-600 font-normal leading-relaxed">
              Optionally link existing migration projects to this initiative. Standalone initiatives with 0 projects are fully valid.
            </p>
          </div>
          <span class="px-3 py-1 rounded-md text-xs font-bold font-mono bg-blue-50 text-blue-700 border border-blue-200">
            {{ ps.initiativeDraft().selectedProjectIds.length }} Selected
          </span>
        </div>
      </div>

      <!-- Selected Projects Preview Chip List (if any selected) -->
      @if (selectedProjects().length > 0) {
        <div class="p-4 rounded-lg bg-blue-50/60 border border-blue-200 flex flex-col gap-2.5">
          <span class="text-[11px] font-bold text-blue-900 uppercase tracking-wider">
            Selected for Association ({{ selectedProjects().length }})
          </span>
          <div class="flex items-center gap-2 flex-wrap">
            @for (p of selectedProjects(); track p.id) {
              <div class="inline-flex items-center gap-2 px-3 py-1.5 rounded-md bg-white border border-blue-200 text-xs font-medium text-slate-800 shadow-2xs">
                <span class="font-mono text-[10px] font-bold text-blue-600 bg-blue-50 px-1.5 py-0.5 rounded border border-blue-100">{{ p.key }}</span>
                <span class="font-semibold text-slate-900">{{ p.name }}</span>
                <button
                  type="button"
                  (click)="ps.removeDraftProject(p.id)"
                  class="text-slate-400 hover:text-rose-600 ml-1 cursor-pointer transition-colors"
                  title="Remove selection">
                  <app-lucide-icon name="x" [size]="12"></app-lucide-icon>
                </button>
              </div>
            }
          </div>
        </div>
      }

      <!-- Search & Filter Bar -->
      <div class="p-4 rounded-xl bg-white border border-slate-200 shadow-xs flex items-center justify-between gap-4 flex-wrap">
        
        <!-- Search Input with Pure Inline Style Overlay -->
        <div style="position: relative; display: flex; align-items: center; width: 320px; max-width: 100%;">
          <app-lucide-icon
            name="search"
            [size]="14"
            style="position: absolute; left: 11px; top: 50%; transform: translateY(-50%); width: 14px; height: 14px; color: #94a3b8; pointer-events: none; z-index: 2;">
          </app-lucide-icon>
          <input
            type="text"
            [(ngModel)]="searchQuery"
            placeholder="Search available projects..."
            style="width: 100%; height: 36px; padding-left: 36px !important; padding-right: 28px; font-size: 12px; background-color: #ffffff; border: 1px solid #e2e8f0; border-radius: 6px; outline: none; color: #0f172a;"
          />
          @if (searchQuery) {
            <button
              type="button"
              (click)="searchQuery = ''"
              class="w-5 h-5 rounded-md hover:bg-slate-100 flex items-center justify-center text-slate-400 hover:text-slate-600 transition-colors cursor-pointer"
              style="position: absolute; right: 8px; top: 50%; transform: translateY(-50%);">
              <app-lucide-icon name="x" [size]="12"></app-lucide-icon>
            </button>
          }
        </div>

        <span class="text-xs text-slate-500 font-medium">
          Showing {{ filteredAvailableProjects().length }} projects in workspace
        </span>

      </div>

      <!-- Projects Selection List -->
      <div class="rounded-xl bg-white border border-slate-200 shadow-xs overflow-hidden">
        
        @if (filteredAvailableProjects().length === 0) {
          <div class="py-12 px-6 flex flex-col items-center justify-center text-center gap-2 text-slate-500">
            <app-lucide-icon name="folder-open" [size]="28" class="text-slate-300"></app-lucide-icon>
            <span class="text-xs font-semibold text-slate-700">No projects match your search query</span>
            <p class="text-xs text-slate-500">Try adjusting your search terms or continue with 0 associated projects.</p>
          </div>
        } @else {
          <div class="divide-y divide-slate-100">
            @for (p of filteredAvailableProjects(); track p.id) {
              <div
                (click)="ps.toggleDraftProject(p.id)"
                class="p-4 sm:px-5 sm:py-4 flex items-center justify-between gap-4 hover:bg-slate-50/80 transition-colors cursor-pointer select-none group"
                [class.bg-blue-50]="isSelected(p.id)">
                
                <!-- Left: Checkbox + Project Identity -->
                <div class="flex items-center gap-3.5 min-w-0">
                  <div
                    class="w-5 h-5 rounded border flex items-center justify-center transition-all shrink-0 cursor-pointer"
                    [class.bg-blue-600]="isSelected(p.id)"
                    [class.border-blue-600]="isSelected(p.id)"
                    [class.border-slate-300]="!isSelected(p.id)"
                    [class.bg-white]="!isSelected(p.id)">
                    @if (isSelected(p.id)) {
                      <app-lucide-icon name="check" [size]="13" class="text-white"></app-lucide-icon>
                    }
                  </div>

                  <div class="flex flex-col gap-1 min-w-0">
                    <div class="flex items-center gap-2">
                      <span class="px-2 py-0.5 rounded-md text-[10px] font-bold font-mono bg-blue-50 text-blue-700 border border-blue-200/80 shrink-0">
                        {{ p.key }}
                      </span>
                      <span class="font-bold text-slate-900 group-hover:text-blue-700 transition-colors truncate text-xs">
                        {{ p.name }}
                      </span>
                      @if (p.initiativeName) {
                        <span class="px-2 py-0.5 rounded-md text-[10px] font-medium bg-slate-100 text-slate-600 border border-slate-200 truncate max-w-[200px]" title="Currently associated with: {{ p.initiativeName }}">
                          Reassign from: {{ p.initiativeName }}
                        </span>
                      }
                    </div>
                    @if (p.description) {
                      <p class="text-[11.5px] text-slate-500 font-normal line-clamp-1">
                        {{ p.description }}
                      </p>
                    }
                  </div>
                </div>

                <!-- Right: Status Badge & Workload Meta -->
                <div class="flex items-center gap-4 shrink-0 text-xs">
                  <div class="hidden sm:flex flex-col text-right text-[11px] text-slate-500 font-medium">
                    <span class="tabular-nums font-semibold text-slate-800">{{ p.migrationCount || 0 }} migrations</span>
                    <span class="tabular-nums">{{ p.validationCount || 0 }} validations</span>
                  </div>

                  <span
                    class="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-md text-[11px] font-semibold border select-none"
                    [class.bg-emerald-50]="p.status === 'ACTIVE'"
                    [class.text-emerald-700]="p.status === 'ACTIVE'"
                    [class.border-emerald-200]="p.status === 'ACTIVE'"
                    [class.bg-blue-50]="p.status === 'PLANNING'"
                    [class.text-blue-700]="p.status === 'PLANNING'"
                    [class.border-blue-200]="p.status === 'PLANNING'"
                    [class.bg-slate-100]="p.status !== 'ACTIVE' && p.status !== 'PLANNING'"
                    [class.text-slate-700]="p.status !== 'ACTIVE' && p.status !== 'PLANNING'"
                    [class.border-slate-200]="p.status !== 'ACTIVE' && p.status !== 'PLANNING'">
                    <span
                      class="w-1.5 h-1.5 rounded-xs"
                      [class.bg-emerald-500]="p.status === 'ACTIVE'"
                      [class.bg-blue-500]="p.status === 'PLANNING'"
                      [class.bg-slate-400]="p.status !== 'ACTIVE' && p.status !== 'PLANNING'">
                    </span>
                    <span>{{ p.status || 'Active' }}</span>
                  </span>
                </div>

              </div>
            }
          </div>
        }

      </div>

    </div>
  `
})
export class Step2ProjectsComponent {
  public ps = inject(ProjectsService);
  public searchQuery = '';

  public isSelected(projectId: string): boolean {
    return this.ps.initiativeDraft().selectedProjectIds.includes(projectId);
  }

  public selectedProjects = computed<ProjectDiscoveryItem[]>(() => {
    const ids = new Set(this.ps.initiativeDraft().selectedProjectIds);
    return this.ps.projects().filter(p => ids.has(p.id));
  });

  public filteredAvailableProjects = computed<ProjectDiscoveryItem[]>(() => {
    const list = this.ps.projects();
    const q = this.searchQuery.trim().toLowerCase();
    if (!q) return list;
    return list.filter(p =>
      p.name.toLowerCase().includes(q) ||
      p.key.toLowerCase().includes(q) ||
      (p.description && p.description.toLowerCase().includes(q))
    );
  });
}

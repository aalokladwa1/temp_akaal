import { Component, inject, output, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { ProjectsService } from '../projects.service';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';
import { InitiativeTabType } from '../projects.models';

@Component({
  selector: 'app-initiative-overview',
  standalone: true,
  imports: [CommonModule, RouterLink, LucideIconComponent],
  template: `
    <div class="flex flex-col gap-6 lg:gap-7">
      
      @if (ps.activeInitiative(); as init) {
        
        <!-- =============================================================== -->
        <!-- 1. INITIATIVE OBJECTIVE & SUMMARY METRICS STRIP                 -->
        <!-- =============================================================== -->
        <div class="p-6 sm:p-7 rounded-xl bg-white border border-slate-200 shadow-xs flex flex-col gap-5">
          
          <!-- Narrative -->
          <div class="flex flex-col gap-2">
            <span class="text-[11px] font-bold text-slate-500 uppercase tracking-wider">Strategic Scope &amp; Objective</span>
            <p class="text-xs text-slate-700 font-normal leading-relaxed">
              {{ init.objective || init.description || 'No strategic objective defined for this initiative.' }}
            </p>
          </div>

          <!-- Key Metrics Grid -->
          <div class="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-4 border-t border-slate-100">
            
            <div class="p-4 rounded-lg bg-slate-50/80 border border-slate-200/80 flex flex-col gap-1">
              <span class="text-[10.5px] font-bold text-slate-500 uppercase tracking-wider">Associated Projects</span>
              <div class="flex items-baseline gap-2">
                <span class="text-2xl font-bold font-mono text-slate-900 tabular-nums">
                  {{ init.associatedProjectIds.length }}
                </span>
                <span class="text-[11px] text-slate-500 font-medium">in current scope</span>
              </div>
            </div>

            <div class="p-4 rounded-lg bg-slate-50/80 border border-slate-200/80 flex flex-col gap-1">
              <span class="text-[10.5px] font-bold text-slate-500 uppercase tracking-wider">Total Workloads</span>
              <div class="flex items-baseline gap-2">
                <span class="text-2xl font-bold font-mono text-slate-900 tabular-nums">
                  {{ totalWorkloads() }}
                </span>
                <span class="text-[11px] text-slate-500 font-medium">migrations active</span>
              </div>
            </div>

            <div class="p-4 rounded-lg bg-slate-50/80 border border-slate-200/80 flex flex-col gap-1">
              <span class="text-[10.5px] font-bold text-slate-500 uppercase tracking-wider">Last Activity</span>
              <div class="flex flex-col">
                <span class="text-sm font-bold text-slate-900 tabular-nums">
                  {{ init.lastActivityAt ? (init.lastActivityAt | date:'MMM d, yyyy') : 'Recent' }}
                </span>
                <span class="text-[10.5px] text-slate-400 font-mono">
                  {{ init.lastActivityAt ? (init.lastActivityAt | date:'HH:mm UTC') : '' }}
                </span>
              </div>
            </div>

          </div>

        </div>

        <!-- =============================================================== -->
        <!-- 2. ATTENTION / CURRENT WORK EVENT (If Any)                     -->
        <!-- =============================================================== -->
        @if (initiativeAttentionItems().length > 0) {
          <div class="p-5 rounded-xl bg-amber-50/70 border border-amber-200/90 text-amber-950 flex flex-col gap-3 shadow-2xs">
            <div class="flex items-center justify-between">
              <div class="flex items-center gap-2">
                <app-lucide-icon name="alert-triangle" [size]="16" class="text-amber-600 shrink-0"></app-lucide-icon>
                <span class="text-xs font-bold text-amber-900 uppercase tracking-wider font-heading">
                  Program Attention &bull; Active Finding
                </span>
              </div>
              <span class="px-2 py-0.5 rounded-md text-[11px] font-bold bg-amber-200/80 text-amber-900 border border-amber-300">
                {{ initiativeAttentionItems().length }} Actionable
              </span>
            </div>

            @for (att of initiativeAttentionItems(); track att.id) {
              <div class="p-4 rounded-lg bg-white border border-amber-200/80 shadow-2xs flex items-center justify-between gap-4 flex-wrap">
                <div class="flex flex-col gap-1 min-w-0">
                  <span class="text-xs font-bold text-slate-900">{{ att.title }}</span>
                  <p class="text-xs text-slate-600 font-normal leading-relaxed">{{ att.description }}</p>
                  <div class="flex items-center gap-2 text-[11px] text-slate-500 pt-1">
                    <span>Project: <strong class="text-slate-800">{{ att.projectName }}</strong></span>
                    <span>&bull;</span>
                    <span>Migration: <strong class="text-slate-800">{{ att.migrationName }}</strong></span>
                  </div>
                </div>

                @if (att.actionRoute && att.actionLabel) {
                  <a
                    [routerLink]="att.actionRoute"
                    class="h-8 px-3 rounded-md bg-amber-100 hover:bg-amber-200 text-amber-900 text-xs font-semibold inline-flex items-center justify-center transition-colors cursor-pointer shrink-0 shadow-2xs">
                    {{ att.actionLabel }}
                  </a>
                }
              </div>
            }
          </div>
        }

        <!-- =============================================================== -->
        <!-- 3. ASSOCIATED PROJECTS PREVIEW TABLE                            -->
        <!-- =============================================================== -->
        <div class="p-6 sm:p-7 rounded-xl bg-white border border-slate-200 shadow-xs flex flex-col gap-5">
          <div class="flex items-center justify-between pb-4 border-b border-slate-200 flex-wrap gap-3">
            <div class="flex items-center gap-2.5">
              <span class="text-xs font-bold text-slate-900 uppercase tracking-wider font-heading">
                Associated Projects
              </span>
              <span class="px-2.5 py-0.5 rounded-md text-[11px] font-semibold bg-slate-100 text-slate-700 border border-slate-200">
                {{ ps.activeInitiativeProjects().length }}
              </span>
            </div>

            <button
              type="button"
              (click)="navigateTab.emit('projects')"
              class="h-8.5 px-3.5 rounded-md bg-white hover:bg-slate-50 text-slate-700 hover:text-blue-700 border border-slate-200 text-xs font-semibold transition-all inline-flex items-center justify-center cursor-pointer shadow-2xs">
              View All Projects
            </button>
          </div>

          @if (ps.activeInitiativeProjects().length === 0) {
            <div class="py-10 flex flex-col items-center justify-center text-center gap-2 text-slate-500">
              <app-lucide-icon name="folder-plus" [size]="26" class="text-slate-300"></app-lucide-icon>
              <span class="text-xs font-semibold text-slate-700">No projects currently associated</span>
              <p class="text-xs text-slate-500 max-w-md">
                Attach existing database migration projects to track collective execution progress and validation health.
              </p>
              <button
                type="button"
                (click)="navigateTab.emit('projects')"
                class="mt-2 h-8.5 px-3.5 rounded-md bg-blue-50 text-blue-700 border border-blue-200 hover:bg-blue-100 text-xs font-semibold cursor-pointer transition-colors">
                Manage Project Associations
              </button>
            </div>
          } @else {
            <div class="overflow-x-auto rounded-xl border border-slate-200/70">
              <table class="w-full text-left border-collapse table-fixed">
                <thead>
                  <tr class="bg-slate-50 text-[10px] font-bold uppercase tracking-wider text-slate-600 border-b border-slate-200 select-none">
                    <th class="py-3 px-5 w-[46%]">Project</th>
                    <th class="py-3 px-5 w-[20%]">Status</th>
                    <th class="py-3 px-5 w-[20%]">Workloads</th>
                    <th class="py-3 px-4 w-[14%] text-right"></th>
                  </tr>
                </thead>
                <tbody class="divide-y divide-slate-100 text-xs">
                  @for (p of ps.activeInitiativeProjects().slice(0, 4); track p.id) {
                    <tr
                      [routerLink]="['/migration/projects', p.id]"
                      class="hover:bg-blue-50/50 even:bg-slate-50/50 transition-colors cursor-pointer group select-none">
                      
                      <td class="py-3.5 px-5">
                        <div class="flex items-center gap-2.5 min-w-0">
                          <span class="px-2 py-0.5 rounded-md text-[10px] font-bold font-mono bg-blue-50 text-blue-700 border border-blue-200/80 shrink-0">
                            {{ p.key }}
                          </span>
                          <span class="font-bold text-slate-900 group-hover:text-blue-700 transition-colors truncate">
                            {{ p.name }}
                          </span>
                        </div>
                      </td>

                      <td class="py-3.5 px-5">
                        <span
                          class="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-md text-[10.5px] font-semibold border select-none"
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
                      </td>

                      <td class="py-3.5 px-5">
                        <span class="text-xs font-semibold text-slate-700 tabular-nums">
                          {{ p.migrationCount || 0 }} migrations
                        </span>
                      </td>

                      <td class="py-3.5 px-4 text-right">
                        <app-lucide-icon
                          name="chevron-right"
                          [size]="15"
                          class="text-slate-400 group-hover:text-blue-600 group-hover:translate-x-0.5 transition-all inline-block">
                        </app-lucide-icon>
                      </td>

                    </tr>
                  }
                </tbody>
              </table>
            </div>
          }
        </div>

      }

    </div>
  `
})
export class InitiativeOverviewComponent {
  public ps = inject(ProjectsService);
  public navigateTab = output<InitiativeTabType>();

  public totalWorkloads = computed<number>(() => {
    return this.ps.activeInitiativeProjects().reduce((acc, p) => acc + (p.migrationCount || 0), 0);
  });

  public initiativeAttentionItems = computed(() => {
    const active = this.ps.activeInitiative();
    if (!active) return [];
    const associatedIds = new Set(active.associatedProjectIds);
    return this.ps.attentionItems().filter(att => att.projectId && associatedIds.has(att.projectId));
  });
}

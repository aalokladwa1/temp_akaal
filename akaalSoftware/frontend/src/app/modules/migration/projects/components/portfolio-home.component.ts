import { Component, inject, output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { ProjectsService } from '../projects.service';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';
import { ProjectsStateFallbackComponent } from './projects-state-fallback.component';
import { ProjectsTabType } from './projects-nav-bar.component';

@Component({
  selector: 'app-portfolio-home',
  standalone: true,
  imports: [CommonModule, RouterLink, ProjectsStateFallbackComponent],
  template: `
    <div class="flex flex-col gap-6 lg:gap-7">
      
      <!-- Non-Ready State Fallback -->
      @if (ps.isUnavailable() || ps.isUnauthorized() || ps.isError()) {
        <app-projects-state-fallback
          [state]="ps.projectsAvailability()"
          entityName="projects"
          [customErrorMessage]="ps.errorMessage()"
          (retry)="ps.retryConnection()">
        </app-projects-state-fallback>
      } @else if (ps.isEmpty()) {
        <app-projects-state-fallback
          [state]="'EMPTY'"
          entityName="projects"
          (retry)="ps.retryConnection()">
        </app-projects-state-fallback>
      } @else {
        
        <!-- ============================================================= -->
        <!-- 1. ACTIVE PROJECTS SNAPSHOT SECTION                          -->
        <!-- ============================================================= -->
        <div class="p-6 sm:p-7 rounded-xl bg-white border border-slate-200 shadow-xs flex flex-col gap-5">
          
          <div class="flex items-center justify-between pb-4 border-b border-slate-200 flex-wrap gap-3">
            <div class="flex items-center gap-2.5">
              <span class="text-xs font-bold text-slate-900 uppercase tracking-wider font-heading">
                Active Projects
              </span>
              @if (ps.projects().length > 0) {
                <span class="px-2.5 py-0.5 rounded-md text-[11px] font-semibold bg-slate-100 text-slate-700 border border-slate-200">
                  {{ ps.projects().length }}
                </span>
              }
            </div>

            <!-- Premium View All Button (No Capsule, Rectangular Framed) -->
            <button
              type="button"
              (click)="navigateTab.emit('projects')"
              class="h-8 px-3 rounded-md bg-white hover:bg-slate-50 text-slate-700 hover:text-blue-700 border border-slate-200 text-xs font-semibold transition-all inline-flex items-center justify-center cursor-pointer shadow-2xs">
              View all projects
            </button>
          </div>

          <!-- Compact Projects Preview Table -->
          <div class="overflow-x-auto rounded-xl border border-slate-200/70">
            <table class="w-full text-left border-collapse table-fixed">
              <thead>
                <tr class="bg-slate-50 text-[10px] font-bold uppercase tracking-wider text-slate-600 border-b border-slate-200 select-none">
                  <th class="py-3 px-5 w-[42%]">Project</th>
                  <th class="py-3 px-5 w-[24%]">Initiative</th>
                  <th class="py-3 px-5 w-[17%]">Status</th>
                  <th class="py-3 px-5 w-[17%]">Workloads</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-slate-100 text-xs">
                @for (p of ps.projects().slice(0, 4); track p.id) {
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
                      <span class="text-xs font-medium text-slate-600 truncate">
                        {{ p.initiativeName || '&mdash;' }}
                      </span>
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
                        {{ p.migrationCount !== null && p.migrationCount !== undefined ? (p.migrationCount + ' migrations') : '&mdash;' }}
                      </span>
                    </td>

                  </tr>
                }
              </tbody>
            </table>
          </div>

        </div>

        <!-- ============================================================= -->
        <!-- 2. TRANSFORMATION INITIATIVES SNAPSHOT SECTION               -->
        <!-- ============================================================= -->
        <div class="p-6 sm:p-7 rounded-xl bg-white border border-slate-200 shadow-xs flex flex-col gap-5">
          
          <div class="flex items-center justify-between pb-4 border-b border-slate-200 flex-wrap gap-3">
            <div class="flex items-center gap-2.5">
              <span class="text-xs font-bold text-slate-900 uppercase tracking-wider font-heading">
                Transformation Initiatives
              </span>
              @if (ps.initiatives().length > 0) {
                <span class="px-2.5 py-0.5 rounded-md text-[11px] font-semibold bg-slate-100 text-slate-700 border border-slate-200">
                  {{ ps.initiatives().length }}
                </span>
              }
            </div>

            <!-- Premium View All Button (No Capsule, Rectangular Framed) -->
            <button
              type="button"
              (click)="navigateTab.emit('initiatives')"
              class="h-8 px-3 rounded-md bg-white hover:bg-slate-50 text-slate-700 hover:text-blue-700 border border-slate-200 text-xs font-semibold transition-all inline-flex items-center justify-center cursor-pointer shadow-2xs">
              View all initiatives
            </button>
          </div>

          <!-- Initiatives Snapshot Grid with Generous Breathing Room -->
          <div class="grid grid-cols-1 md:grid-cols-3 gap-5">
            @for (init of ps.initiatives().slice(0, 3); track init.id) {
              <div
                class="p-5 sm:p-6 rounded-lg bg-white hover:bg-slate-50/60 border border-slate-200 hover:border-blue-300 transition-all flex flex-col justify-between gap-4 shadow-2xs group">
                
                <div class="flex flex-col gap-2">
                  <div class="flex items-center justify-between gap-2">
                    <span class="px-2.5 py-0.5 rounded-md text-[10.5px] font-bold font-mono bg-indigo-50 text-indigo-700 border border-indigo-200/80">
                      {{ init.key }}
                    </span>
                    <span class="px-2.5 py-0.5 rounded-md text-[10.5px] font-semibold bg-slate-100 text-slate-600 border border-slate-200 tabular-nums">
                      {{ init.associatedProjectCount }} {{ init.associatedProjectCount === 1 ? 'Project' : 'Projects' }}
                    </span>
                  </div>
                  
                  <h4 class="text-sm font-bold text-slate-900 group-hover:text-blue-700 transition-colors leading-snug pt-1">
                    {{ init.name }}
                  </h4>
                  
                  @if (init.objective) {
                    <p class="text-xs text-slate-600 font-normal leading-relaxed line-clamp-2">
                      {{ init.objective }}
                    </p>
                  }
                </div>

                <!-- Card Footer with Status Badge and Premium Enterprise Button -->
                <div class="pt-3.5 border-t border-slate-100 flex items-center justify-between mt-2">
                  <span
                    class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md text-[10.5px] font-semibold border select-none"
                    [class.bg-emerald-50]="init.status === 'ACTIVE'"
                    [class.text-emerald-700]="init.status === 'ACTIVE'"
                    [class.border-emerald-200]="init.status === 'ACTIVE'"
                    [class.bg-blue-50]="init.status === 'PLANNING'"
                    [class.text-blue-700]="init.status === 'PLANNING'"
                    [class.border-blue-200]="init.status === 'PLANNING'"
                    [class.bg-slate-100]="init.status !== 'ACTIVE' && init.status !== 'PLANNING'"
                    [class.text-slate-700]="init.status !== 'ACTIVE' && init.status !== 'PLANNING'"
                    [class.border-slate-200]="init.status !== 'ACTIVE' && init.status !== 'PLANNING'">
                    <span
                      class="w-1.5 h-1.5 rounded-xs"
                      [class.bg-emerald-500]="init.status === 'ACTIVE'"
                      [class.bg-blue-500]="init.status === 'PLANNING'"
                      [class.bg-slate-400]="init.status !== 'ACTIVE' && init.status !== 'PLANNING'">
                    </span>
                    <span>{{ init.status || 'Active' }}</span>
                  </span>

                  <!-- Premium Enterprise Explore Button -->
                  <button
                    type="button"
                    (click)="navigateTab.emit('initiatives')"
                    class="h-8 px-3 rounded-md bg-blue-50 hover:bg-blue-100 active:bg-blue-200/80 text-blue-700 text-xs font-semibold inline-flex items-center justify-center transition-colors border border-blue-200/70 cursor-pointer shadow-2xs">
                    Explore
                  </button>
                </div>

              </div>
            }
          </div>

        </div>

      }

    </div>
  `
})
export class PortfolioHomeComponent {
  public ps = inject(ProjectsService);
  public navigateTab = output<ProjectsTabType>();
}

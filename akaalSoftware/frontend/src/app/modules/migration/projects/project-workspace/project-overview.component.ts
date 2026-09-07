import { Component, inject, output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { ProjectsService } from '../projects.service';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';
import { ProjectWorkspaceTabType } from '../projects.models';

@Component({
  selector: 'app-project-overview',
  standalone: true,
  imports: [CommonModule, RouterLink, LucideIconComponent],
  template: `
    <div class="flex flex-col gap-6 select-none animate-in fade-in duration-150">
      
      @if (ps.activeProject(); as proj) {
        
        <!-- ============================================================= -->
        <!-- 1. IDENTITY & SCOPE NARRATIVE CARD                            -->
        <!-- ============================================================= -->
        <div class="p-6 sm:p-7 rounded-xl bg-white border border-slate-200 shadow-xs flex flex-col gap-5">
          
          <div class="flex items-start justify-between gap-4 pb-4 border-b border-slate-100 flex-wrap">
            <div class="flex flex-col gap-1 max-w-3xl">
              <span class="text-xs font-bold text-slate-500 uppercase tracking-wider font-heading">
                Operational Scope &amp; Architecture
              </span>
              <h2 class="text-lg font-bold text-slate-900 font-heading">
                {{ proj.name }}
              </h2>
              <p class="text-xs text-slate-600 font-normal leading-relaxed">
                {{ proj.description || 'No detailed architecture narrative specified for this project scope.' }}
              </p>
            </div>

              <!-- Program / Initiative Association Badge -->
            <div class="flex flex-col gap-1 items-end shrink-0">
              <span class="text-[10px] font-semibold text-slate-400 uppercase">Program Alignment</span>
              @if (proj.initiativeId) {
                <a
                  [routerLink]="['/migration/initiatives', proj.initiativeId, 'overview']"
                  class="p-2 rounded-md bg-indigo-50/70 hover:bg-indigo-100/70 border border-indigo-200 text-indigo-900 transition-colors inline-flex items-center justify-center cursor-pointer shadow-2xs">
                  <span class="text-xs font-bold">{{ proj.initiativeName || proj.initiativeKey || 'Transformation Initiative' }}</span>
                </a>
              } @else {
                <span class="px-2.5 py-1 rounded-md text-xs font-semibold bg-slate-100 text-slate-600 border border-slate-200">
                  Standalone Governed Project
                </span>
              }
            </div>
          </div>

          <!-- Metadata & Context Footer Row -->
          <div class="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-1 text-xs">
            
            <!-- Shell Authority Scope -->
            <div class="flex items-center gap-2.5 p-3 rounded-lg bg-slate-50 border border-slate-200/80">
              <app-lucide-icon name="panels-top-left" [size]="16" class="text-slate-500 shrink-0"></app-lucide-icon>
              <div class="flex flex-col min-w-0">
                <span class="text-[10px] font-semibold text-slate-400 uppercase">Context Authority</span>
                <span class="font-bold text-slate-800 truncate">
                  {{ ps.cs.selectedWorkspace()?.name || 'Workspace' }} &bull; {{ proj.environmentName }}
                </span>
              </div>
            </div>

            <!-- Creation Audit -->
            <div class="flex items-center gap-2.5 p-3 rounded-lg bg-slate-50 border border-slate-200/80">
              <app-lucide-icon name="calendar" [size]="16" class="text-slate-500 shrink-0"></app-lucide-icon>
              <div class="flex flex-col min-w-0">
                <span class="text-[10px] font-semibold text-slate-400 uppercase">Created Date</span>
                <span class="font-bold text-slate-800 truncate">
                  {{ proj.createdAt ? (proj.createdAt | date:'mediumDate') : 'Feb 2026' }}
                </span>
              </div>
            </div>

            <!-- Last Active -->
            <div class="flex items-center gap-2.5 p-3 rounded-lg bg-slate-50 border border-slate-200/80">
              <app-lucide-icon name="clock" [size]="16" class="text-slate-500 shrink-0"></app-lucide-icon>
              <div class="flex flex-col min-w-0">
                <span class="text-[10px] font-semibold text-slate-400 uppercase">Last Activity</span>
                <span class="font-bold text-slate-800 truncate">
                  {{ proj.lastActivityAt ? (proj.lastActivityAt | date:'MMM d, HH:mm UTC') : 'Recent' }}
                </span>
              </div>
            </div>

          </div>

        </div>

        <!-- ============================================================= -->
        <!-- 2. CURRENT WORK (MIGRATIONS & VALIDATIONS FACTUAL SUMMARY)    -->
        <!-- ============================================================= -->
        <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
          
          <!-- Migrations Workload Summary Card -->
          <div class="p-6 rounded-xl bg-white border border-slate-200 shadow-xs flex flex-col gap-4">
            
            <div class="flex items-center justify-between pb-3 border-b border-slate-100 flex-wrap gap-2">
              <div class="flex items-center gap-2">
                <div class="w-7 h-7 rounded-md bg-blue-50 text-blue-600 flex items-center justify-center border border-blue-200">
                  <app-lucide-icon name="arrow-left-right" [size]="14"></app-lucide-icon>
                </div>
                <span class="text-xs font-bold text-slate-900 uppercase tracking-wider font-heading">
                  Migrations Workloads
                </span>
              </div>

              <!-- New Migration Quick Action -->
              <a
                routerLink="/migration/create"
                [queryParams]="{ projectId: proj.id }"
                class="h-8 px-3 rounded-md bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold shadow-2xs inline-flex items-center justify-center transition-colors cursor-pointer">
                New Migration
              </a>
            </div>

            <!-- Factual Migrations Counters -->
            <div class="grid grid-cols-3 gap-3">
              
              <div class="p-3.5 rounded-lg bg-slate-50 border border-slate-200 flex flex-col gap-1">
                <span class="text-[10px] font-semibold text-slate-400 uppercase">Total Defined</span>
                <span class="text-xl font-bold text-slate-900 tabular-nums font-heading">
                  {{ proj.currentWork?.totalMigrations ?? 0 }}
                </span>
              </div>

              <div class="p-3.5 rounded-lg bg-blue-50/70 border border-blue-200/80 flex flex-col gap-1">
                <span class="text-[10px] font-semibold text-blue-600 uppercase">In-Flight / Active</span>
                <span class="text-xl font-bold text-blue-900 tabular-nums font-heading">
                  {{ proj.currentWork?.activeMigrations ?? 0 }}
                </span>
              </div>

              <div class="p-3.5 rounded-lg bg-emerald-50/70 border border-emerald-200/80 flex flex-col gap-1">
                <span class="text-[10px] font-semibold text-emerald-600 uppercase">Completed</span>
                <span class="text-xl font-bold text-emerald-900 tabular-nums font-heading">
                  {{ proj.currentWork?.completedMigrations ?? 0 }}
                </span>
              </div>

            </div>

            <!-- View Migrations Deep Link -->
            <button
              type="button"
              (click)="navigateTab.emit('migrations')"
              class="text-left text-xs font-semibold text-blue-600 hover:text-blue-800 transition-colors inline-flex items-center cursor-pointer pt-1">
              View all migration pipelines in this project
            </button>

          </div>

          <!-- Validations Assurance Summary Card -->
          <div class="p-6 rounded-xl bg-white border border-slate-200 shadow-xs flex flex-col gap-4">
            
            <div class="flex items-center justify-between pb-3 border-b border-slate-100 flex-wrap gap-2">
              <div class="flex items-center gap-2">
                <div class="w-7 h-7 rounded-md bg-emerald-50 text-emerald-600 flex items-center justify-center border border-emerald-200">
                  <app-lucide-icon name="check-circle-2" [size]="14"></app-lucide-icon>
                </div>
                <span class="text-xs font-bold text-slate-900 uppercase tracking-wider font-heading">
                  Validation Assurance
                </span>
              </div>

              <!-- New Validation Quick Action -->
              <a
                routerLink="/migration/validation/new"
                [queryParams]="{ projectId: proj.id }"
                class="h-8 px-3 rounded-md bg-white hover:bg-slate-50 text-slate-700 border border-slate-200 text-xs font-semibold shadow-2xs inline-flex items-center justify-center transition-colors cursor-pointer">
                New Validation
              </a>
            </div>

            <!-- Factual Validations Counters -->
            <div class="grid grid-cols-3 gap-3">
              
              <div class="p-3.5 rounded-lg bg-slate-50 border border-slate-200 flex flex-col gap-1">
                <span class="text-[10px] font-semibold text-slate-400 uppercase">Missions</span>
                <span class="text-xl font-bold text-slate-900 tabular-nums font-heading">
                  {{ proj.currentWork?.totalValidations ?? 0 }}
                </span>
              </div>

              <div class="p-3.5 rounded-lg bg-emerald-50/70 border border-emerald-200/80 flex flex-col gap-1">
                <span class="text-[10px] font-semibold text-emerald-600 uppercase">Passed</span>
                <span class="text-xl font-bold text-emerald-900 tabular-nums font-heading">
                  {{ proj.currentWork?.passedValidations ?? 0 }}
                </span>
              </div>

              <div class="p-3.5 rounded-lg bg-amber-50/70 border border-amber-200/80 flex flex-col gap-1">
                <span class="text-[10px] font-semibold text-amber-600 uppercase">Discrepancies</span>
                <span class="text-xl font-bold text-amber-900 tabular-nums font-heading">
                  {{ proj.currentWork?.discrepancyValidations ?? 0 }}
                </span>
              </div>

            </div>

            <!-- View Validations Deep Link -->
            <button
              type="button"
              (click)="navigateTab.emit('validations')"
              class="text-left text-xs font-semibold text-blue-600 hover:text-blue-800 transition-colors inline-flex items-center cursor-pointer pt-1">
              View validation missions and schema audits
            </button>

          </div>

        </div>

        <!-- ============================================================= -->
        <!-- 3. ATTENTION PROJECTION & UPCOMING EVENTS                      -->
        <!-- ============================================================= -->
        <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
          
          <!-- Attention Items Projection -->
          <div class="p-6 rounded-xl bg-white border border-slate-200 shadow-xs flex flex-col gap-4">
            
            <div class="flex items-center justify-between pb-3 border-b border-slate-100">
              <span class="text-xs font-bold text-slate-900 uppercase tracking-wider font-heading flex items-center gap-2">
                <app-lucide-icon name="alert-triangle" [size]="14" class="text-amber-500"></app-lucide-icon>
                <span>Attention Required</span>
              </span>

              @if (ps.activeProjectAttention().length > 0) {
                <span class="px-2 py-0.5 rounded-md text-[10.5px] font-bold bg-amber-100 text-amber-800 border border-amber-300">
                  {{ ps.activeProjectAttention().length }} Action Required
                </span>
              }
            </div>

            <div class="flex flex-col gap-2.5">
              @if (ps.activeProjectAttention().length > 0) {
                @for (item of ps.activeProjectAttention(); track item.id) {
                  <div class="p-3.5 rounded-lg bg-amber-50/60 border border-amber-200/80 flex flex-col gap-2">
                    <div class="flex items-start justify-between gap-2">
                      <div class="flex items-center gap-2">
                        <span class="w-2 h-2 rounded-xs bg-amber-500 shrink-0"></span>
                        <span class="text-xs font-bold text-slate-900">{{ item.title }}</span>
                      </div>
                      <span class="text-[10px] font-semibold text-slate-500 shrink-0">
                        {{ item.occurredAt | date:'MMM d, HH:mm' }}
                      </span>
                    </div>
                    <p class="text-[11.5px] text-slate-600 leading-relaxed pl-4">
                      {{ item.description }}
                    </p>
                    @if (item.actionRoute && item.actionLabel) {
                      <div class="pl-4 pt-1">
                        <a
                          [routerLink]="item.actionRoute"
                          class="h-8 px-3 rounded-md bg-amber-100 hover:bg-amber-200 text-amber-900 text-xs font-semibold inline-flex items-center justify-center transition-colors cursor-pointer shrink-0 shadow-2xs">
                          {{ item.actionLabel }}
                        </a>
                      </div>
                    }
                  </div>
                }
              } @else {
                <div class="p-6 rounded-lg bg-slate-50 border border-slate-200 text-center flex flex-col items-center justify-center gap-2">
                  <app-lucide-icon name="check" [size]="20" class="text-emerald-500"></app-lucide-icon>
                  <span class="text-xs font-semibold text-slate-700">No Actionable Attention Items</span>
                  <p class="text-[11px] text-slate-500">All migrations and validations in this project are operating nominally.</p>
                </div>
              }
            </div>

          </div>

          <!-- Upcoming Scheduled Events -->
          <div class="p-6 rounded-xl bg-white border border-slate-200 shadow-xs flex flex-col gap-4">
            
            <div class="flex items-center justify-between pb-3 border-b border-slate-100">
              <span class="text-xs font-bold text-slate-900 uppercase tracking-wider font-heading flex items-center gap-2">
                <app-lucide-icon name="calendar-clock" [size]="14" class="text-blue-600"></app-lucide-icon>
                <span>Upcoming Scheduled Events</span>
              </span>

              <span class="text-[11px] font-medium text-slate-500">
                {{ proj.upcomingEvents?.length ?? 0 }} scheduled
              </span>
            </div>

            <div class="flex flex-col gap-2.5">
              @if (proj.upcomingEvents && proj.upcomingEvents.length > 0) {
                @for (evt of proj.upcomingEvents; track evt.id) {
                  <div class="p-3.5 rounded-lg bg-slate-50 border border-slate-200 flex flex-col gap-1.5">
                    <div class="flex items-center justify-between gap-2">
                      <div class="flex items-center gap-2">
                        <span class="px-1.5 py-0.2 rounded text-[9.5px] font-bold uppercase bg-blue-50 text-blue-700 border border-blue-200">
                          {{ evt.type }}
                        </span>
                        <span class="text-xs font-bold text-slate-900">{{ evt.title }}</span>
                      </div>
                      <span class="text-[10.5px] font-mono font-semibold text-slate-600 shrink-0">
                        {{ evt.scheduledAt | date:'MMM d, yyyy HH:mm' }}
                      </span>
                    </div>
                    <p class="text-[11px] text-slate-500 leading-relaxed">
                      {{ evt.description }}
                    </p>
                  </div>
                }
              } @else {
                <div class="p-6 rounded-lg bg-slate-50 border border-slate-200 text-center flex flex-col items-center justify-center gap-2">
                  <app-lucide-icon name="calendar" [size]="20" class="text-slate-400"></app-lucide-icon>
                  <span class="text-xs font-semibold text-slate-700">No Scheduled Maintenance or Cutover Windows</span>
                  <p class="text-[11px] text-slate-500">Scheduled shadow replication and cutover gates will appear here.</p>
                </div>
              }
            </div>

          </div>

        </div>

        <!-- ============================================================= -->
        <!-- 4. RECENT ACTIVITY STREAM PREVIEW                             -->
        <!-- ============================================================= -->
        <div class="p-6 sm:p-7 rounded-xl bg-white border border-slate-200 shadow-xs flex flex-col gap-5">
          
          <div class="flex items-center justify-between pb-3 border-b border-slate-100 flex-wrap gap-2">
            <div class="flex items-center gap-2">
              <span class="text-xs font-bold text-slate-900 uppercase tracking-wider font-heading">
                Recent Operational Activity
              </span>
              <span class="px-2 py-0.5 rounded-md text-[10.5px] font-semibold bg-slate-100 text-slate-600 border border-slate-200">
                {{ ps.activeProjectActivities().length }} events
              </span>
            </div>

            <button
              type="button"
              (click)="navigateTab.emit('activity')"
              class="text-xs font-semibold text-blue-600 hover:text-blue-800 transition-colors inline-flex items-center cursor-pointer">
              View full audit stream
            </button>
          </div>

          <div class="flex flex-col gap-2.5">
            @if (ps.activeProjectActivities().length > 0) {
              @for (act of ps.activeProjectActivities(); track act.id) {
                <div class="p-3.5 rounded-lg bg-slate-50/70 border border-slate-200/80 flex items-start justify-between gap-3 text-xs">
                  
                  <div class="flex items-start gap-3 min-w-0">
                    <div
                      class="w-7 h-7 rounded-md flex items-center justify-center shrink-0 mt-0.5"
                      [class.bg-emerald-50]="act.severity === 'SUCCESS'"
                      [class.text-emerald-600]="act.severity === 'SUCCESS'"
                      [class.border]="true"
                      [class.border-emerald-200]="act.severity === 'SUCCESS'"
                      [class.bg-amber-50]="act.severity === 'WARNING'"
                      [class.text-amber-600]="act.severity === 'WARNING'"
                      [class.border-amber-200]="act.severity === 'WARNING'"
                      [class.bg-blue-50]="act.severity === 'INFO'"
                      [class.text-blue-600]="act.severity === 'INFO'"
                      [class.border-blue-200]="act.severity === 'INFO'">
                      <app-lucide-icon
                        [name]="act.category === 'VALIDATION' ? 'check-circle-2' : act.category === 'EXECUTION' ? 'play' : 'activity'"
                        [size]="14">
                      </app-lucide-icon>
                    </div>

                    <div class="flex flex-col gap-0.5 min-w-0">
                      <div class="flex items-center gap-2 flex-wrap">
                        <span class="font-bold text-slate-900">{{ act.title }}</span>
                        <span class="px-1.5 py-0.2 rounded text-[9.5px] font-bold bg-slate-200/80 text-slate-700 uppercase">
                          {{ act.category }}
                        </span>
                      </div>
                      <p class="text-[11.5px] text-slate-600 leading-relaxed">{{ act.description }}</p>
                      @if (act.actorName) {
                        <span class="text-[10.5px] text-slate-400">By <strong>{{ act.actorName }}</strong></span>
                      }
                    </div>
                  </div>

                  <span class="text-[10.5px] font-mono text-slate-500 whitespace-nowrap shrink-0">
                    {{ act.occurredAt | date:'MMM d, HH:mm' }}
                  </span>

                </div>
              }
            } @else {
              <div class="p-6 rounded-lg bg-slate-50 border border-slate-200 text-center text-xs text-slate-500">
                No recent activity recorded for this project scope.
              </div>
            }
          </div>

        </div>

      }

    </div>
  `
})
export class ProjectOverviewComponent {
  public ps = inject(ProjectsService);
  public navigateTab = output<ProjectWorkspaceTabType>();
}

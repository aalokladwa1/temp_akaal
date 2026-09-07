import { Component, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { ProjectsService } from '../projects.service';
import { LucideIconComponent } from '../../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-initiative-activity',
  standalone: true,
  imports: [CommonModule, RouterLink, LucideIconComponent],
  template: `
    <div class="flex flex-col gap-4">
      
      <!-- Activity Filter Toolbar -->
      <div class="p-4 sm:p-4.5 rounded-xl bg-white border border-slate-200 shadow-xs flex items-center justify-between gap-4 flex-wrap">
        <div class="flex items-center gap-2">
          <app-lucide-icon name="activity" [size]="16" class="text-blue-600"></app-lucide-icon>
          <span class="text-xs font-bold text-slate-900 uppercase tracking-wider font-heading">
            Operational Activity Timeline
          </span>
          <span class="px-2 py-0.5 rounded-md text-[11px] font-semibold bg-slate-100 text-slate-700 border border-slate-200">
            {{ ps.activeInitiativeActivities().length }} Events
          </span>
        </div>

        <!-- Category Filters -->
        <div class="flex items-center gap-1.5 flex-wrap">
          @for (cat of categoryOptions; track cat.value) {
            <button
              type="button"
              (click)="ps.setActivityCategoryFilter(cat.value)"
              class="h-8 px-3 rounded-md text-xs font-semibold transition-all cursor-pointer shadow-2xs border"
              [class.bg-blue-50]="ps.activityCategoryFilter() === cat.value"
              [class.text-blue-700]="ps.activityCategoryFilter() === cat.value"
              [class.border-blue-300]="ps.activityCategoryFilter() === cat.value"
              [class.bg-white]="ps.activityCategoryFilter() !== cat.value"
              [class.text-slate-700]="ps.activityCategoryFilter() !== cat.value"
              [class.border-slate-200]="ps.activityCategoryFilter() !== cat.value"
              [class.hover:bg-slate-50]="ps.activityCategoryFilter() !== cat.value">
              {{ cat.label }}
            </button>
          }
        </div>
      </div>

      <!-- Activity Timeline Stream -->
      <div class="p-6 rounded-xl bg-white border border-slate-200 shadow-xs flex flex-col gap-4">
        
        @if (ps.activeInitiativeActivities().length === 0) {
          <div class="py-12 flex flex-col items-center justify-center text-center gap-2 text-slate-500">
            <app-lucide-icon name="history" [size]="28" class="text-slate-300"></app-lucide-icon>
            <span class="text-xs font-semibold text-slate-700">No activity recorded for this category</span>
            <p class="text-xs text-slate-500">Operational events across associated projects will stream here automatically.</p>
          </div>
        } @else {
          <div class="flex flex-col divide-y divide-slate-100 font-normal">
            @for (act of ps.activeInitiativeActivities(); track act.id) {
              <div class="py-4 first:pt-0 last:pb-0 flex items-start justify-between gap-4 text-xs">
                
                <!-- Left: Severity Dot + Time + Content -->
                <div class="flex items-start gap-3.5 min-w-0">
                  
                  <!-- Severity Dot Indicator -->
                  <span
                    class="w-2.5 h-2.5 rounded-xs mt-1 shrink-0"
                    [class.bg-emerald-500]="act.severity === 'SUCCESS'"
                    [class.bg-amber-500]="act.severity === 'WARNING'"
                    [class.bg-blue-500]="act.severity === 'INFO'"
                    [class.bg-rose-500]="act.severity === 'ERROR'">
                  </span>

                  <!-- Timestamps -->
                  <div class="flex flex-col shrink-0 w-28">
                    <span class="font-bold text-slate-900 text-xs">
                      {{ act.occurredAt | date:'MMM d, yyyy' }}
                    </span>
                    <span class="text-[10.5px] text-slate-500 font-mono font-medium tabular-nums">
                      {{ act.occurredAt | date:'HH:mm:ss UTC' }}
                    </span>
                  </div>

                  <!-- Content Narrative -->
                  <div class="flex flex-col gap-1 min-w-0">
                    <div class="flex items-center gap-2 flex-wrap">
                      <span class="font-bold text-slate-900">{{ act.title }}</span>
                      @if (act.subjectName) {
                        <span class="text-slate-300">&bull;</span>
                        <span class="font-semibold text-blue-700 truncate">{{ act.subjectName }}</span>
                      }
                      @if (act.actorName) {
                        <span class="text-[11px] text-slate-500">by {{ act.actorName }}</span>
                      }
                    </div>
                    <p class="text-xs text-slate-600 font-normal leading-relaxed">
                      {{ act.description }}
                    </p>
                  </div>

                </div>

                <!-- Right: Action CTA if routed -->
                @if (act.actionRoute) {
                  <div class="shrink-0 mt-0.5">
                    <a
                      [routerLink]="act.actionRoute"
                      class="h-8 px-3.5 rounded-md border border-amber-200 bg-amber-50 text-amber-800 hover:bg-amber-100 hover:border-amber-300 text-xs font-semibold inline-flex items-center justify-center shadow-2xs transition-all cursor-pointer">
                      {{ act.actionType === 'REVIEW' ? 'Review' : 'View' }}
                    </a>
                  </div>
                }

              </div>
            }
          </div>
        }

      </div>

      <!-- Activity vs Audit Notice -->
      <div class="p-3.5 rounded-lg bg-slate-50 border border-slate-200 text-[11px] text-slate-500 flex items-center justify-between gap-4">
        <span>Activity displays operational context for participating teams. Immutable compliance records are governed in Reports &amp; Audits.</span>
        <a routerLink="/reports" class="font-semibold text-blue-600 hover:text-blue-700 shrink-0">Open Audit Log &rarr;</a>
      </div>

    </div>
  `
})
export class InitiativeActivityComponent {
  public ps = inject(ProjectsService);

  public categoryOptions = [
    { label: 'All Events', value: 'ALL' },
    { label: 'Milestones', value: 'MILESTONE' },
    { label: 'Associations', value: 'ASSOCIATION' },
    { label: 'Governance', value: 'GOVERNANCE' },
    { label: 'Metadata', value: 'METADATA' }
  ];
}

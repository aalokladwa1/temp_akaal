import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { MonitoringService } from '../services/monitoring.service';
import { LucideIconComponent } from '../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-monitoring-recent-events',
  standalone: true,
  imports: [CommonModule, RouterLink, LucideIconComponent],
  template: `
    <!-- Recent Operational Events (Section 8 - Bounded 5-8 Significant Events) -->
    <div class="p-6 rounded-2xl bg-white border border-slate-200 shadow-2xs flex flex-col gap-4 select-none">
      
      <!-- Header -->
      <div class="flex items-center justify-between pb-3 border-b border-slate-200 flex-wrap gap-2">
        <div class="flex items-center gap-2">
          <app-lucide-icon name="activity" [size]="16" class="text-blue-600"></app-lucide-icon>
          <span class="text-xs font-bold text-slate-900 uppercase tracking-wider font-heading">Recent Operational Events</span>
        </div>
        <span class="text-[11px] font-mono text-slate-500">
          Last {{ ms.recentEvents().length }} state transitions
        </span>
      </div>

      <!-- Events List or Empty State -->
      @if (ms.recentEvents().length === 0) {
        <div class="py-8 flex flex-col items-center justify-center text-center gap-1 text-slate-500">
          <span class="text-xs font-medium">No recent operational transitions recorded.</span>
        </div>
      } @else {
        <div class="flex flex-col divide-y divide-slate-100 font-normal">
          @for (evt of ms.recentEvents(); track evt.id) {
            <div class="py-3.5 first:pt-0 last:pb-0 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs">
              
              <!-- Left: Event Time & Description -->
              <div class="flex items-start gap-3 min-w-0">
                
                <!-- Category Severity Dot (Circular) -->
                <div 
                  class="w-2 h-2 rounded-full mt-1.5 shrink-0"
                  [ngClass]="{
                    'bg-rose-600': evt.severity === 'CRITICAL',
                    'bg-amber-500': evt.severity === 'WARNING',
                    'bg-blue-600': evt.severity === 'INFO',
                    'bg-emerald-600': evt.category === 'RECOVERY'
                  }">
                </div>

                <!-- Event Category Tag & Details -->
                <div class="flex flex-col min-w-0">
                  <div class="flex items-center gap-2 flex-wrap">
                    <span class="inline-flex items-center px-1.5 py-0.5 rounded-sm bg-slate-100 text-slate-700 border border-slate-200 text-[10px] font-mono font-semibold uppercase">
                      {{ ms.formatLabel(evt.category_label) }}
                    </span>
                    <span class="font-bold text-slate-900">{{ evt.entity_name }}</span>
                  </div>

                  <p class="text-xs text-slate-600 font-normal mt-0.5 leading-snug">
                    {{ ms.formatSentence(evt.summary) }}
                  </p>
                </div>

              </div>

              <!-- Right: Timestamp & Optional Drill-in -->
              <div class="flex items-center justify-between sm:justify-end gap-3 shrink-0 self-start sm:self-center">
                <span class="text-[11px] font-mono text-slate-500 tabular-nums">
                  {{ ms.formatObservationTime(evt.timestamp) }}
                </span>

                @if (evt.deep_link_route) {
                  <a
                    [routerLink]="evt.deep_link_route"
                    class="h-7 px-2.5 rounded-md bg-slate-50 hover:bg-blue-50 text-slate-700 hover:text-blue-700 border border-slate-200 hover:border-blue-200 text-[11px] font-semibold transition-all inline-flex items-center gap-1 cursor-pointer">
                    <span>Inspect</span>
                    <app-lucide-icon name="arrow-right" [size]="11" class="text-slate-400"></app-lucide-icon>
                  </a>
                }
              </div>

            </div>
          }
        </div>
      }

    </div>
  `
})
export class MonitoringRecentEventsComponent {
  public ms = inject(MonitoringService);
}

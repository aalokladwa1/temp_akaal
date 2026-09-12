import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { MonitoringService } from '../services/monitoring.service';
import { LucideIconComponent } from '../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-monitoring-alerts',
  standalone: true,
  imports: [CommonModule, RouterLink, LucideIconComponent],
  template: `
    <!-- Incidents & Alerts (Section 7) -->
    <div class="p-6 rounded-2xl bg-white border border-slate-200 shadow-2xs flex flex-col gap-4 select-none">
      
      <!-- Header -->
      <div class="flex items-center justify-between pb-3 border-b border-slate-200 flex-wrap gap-2">
        <div class="flex items-center gap-2">
          <app-lucide-icon name="bell-ring" [size]="16" class="text-blue-600"></app-lucide-icon>
          <span class="text-xs font-bold text-slate-900 uppercase tracking-wider font-heading">Active Incidents &amp; Alerts</span>
          <span 
            class="px-2 py-0.5 rounded-md text-[11px] font-semibold border"
            [ngClass]="ms.activeAlerts().length > 0 ? 'bg-amber-50 text-amber-700 border-amber-200' : 'bg-slate-100 text-slate-700 border-slate-200'">
            {{ ms.activeAlerts().length }}
          </span>
        </div>

        <a
          routerLink="/monitoring/alerts"
          class="h-7 px-2.5 rounded-lg bg-slate-50 hover:bg-blue-50 text-slate-700 hover:text-blue-700 border border-slate-200 hover:border-blue-200 text-xs font-semibold transition-all shadow-2xs inline-flex items-center gap-1.5 group cursor-pointer">
          <span>Alerts &amp; Incidents</span>
          <app-lucide-icon name="arrow-right" [size]="12" class="text-slate-400 group-hover:text-blue-600 group-hover:translate-x-0.5 transition-all"></app-lucide-icon>
        </a>
      </div>

      <!-- Active Alerts List or Calm Empty State -->
      @if (ms.activeAlerts().length === 0) {
        <div class="py-8 flex flex-col items-center justify-center text-center gap-1 text-slate-500">
          <app-lucide-icon name="check-circle-2" [size]="24" class="text-emerald-500"></app-lucide-icon>
          <span class="text-xs font-semibold text-slate-700">No firing alerts</span>
          <p class="text-[11px] text-slate-500">All threshold monitors and rule evaluations are clean.</p>
        </div>
      } @else {
        <div class="flex flex-col divide-y divide-slate-100">
          @for (alert of ms.activeAlerts(); track alert.id) {
            <div class="py-3.5 first:pt-0 last:pb-0 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
              
              <!-- Left: Alert Details -->
              <div class="flex items-start gap-3 min-w-0">
                <div 
                  class="w-2 h-2 rounded-full mt-1.5 shrink-0"
                  [ngClass]="alert.severity === 'CRITICAL' ? 'bg-rose-600' : 'bg-amber-500'">
                </div>

                <div class="flex flex-col min-w-0">
                  <div class="flex items-center gap-2 flex-wrap">
                    <span class="text-xs font-bold text-slate-900">{{ ms.formatLabel(alert.alert_rule_name) }}</span>
                    <span class="text-slate-300">&bull;</span>
                    <span class="text-xs font-semibold text-slate-700 truncate">{{ alert.affected_entity }}</span>
                  </div>
                  
                  <p class="text-xs text-slate-600 font-normal mt-0.5 leading-snug">
                    {{ alert.summary }}
                  </p>

                  <div class="flex items-center gap-3 mt-1 text-[11px] text-slate-500 font-mono">
                    <span>Status: <strong class="text-amber-800">{{ alert.status }}</strong></span>
                    <span>&bull;</span>
                    <span>Triggered: {{ ms.formatObservationTime(alert.triggered_at) }}</span>
                  </div>
                </div>
              </div>

              <!-- Right: Deep Link -->
              <div class="shrink-0 sm:self-center">
                <a
                  [routerLink]="alert.deep_link_route || '/monitoring/alerts'"
                  class="h-8 px-3 rounded-lg border border-slate-200 hover:border-blue-300 bg-slate-50 hover:bg-blue-50 text-slate-700 hover:text-blue-700 text-xs font-semibold transition-colors inline-flex items-center gap-1.5 cursor-pointer shadow-2xs group">
                  <span>View Alert</span>
                  <app-lucide-icon name="arrow-right" [size]="12" class="text-slate-400 group-hover:text-blue-600 group-hover:translate-x-0.5 transition-all"></app-lucide-icon>
                </a>
              </div>

            </div>
          }
        </div>
      }

    </div>
  `
})
export class MonitoringAlertsComponent {
  public ms = inject(MonitoringService);
}

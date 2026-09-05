import { Component, Input, HostBinding } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { AlertIncident } from '../../../core/models/dashboard.models';
import { LucideIconComponent } from '../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-alerts-incidents',
  standalone: true,
  imports: [CommonModule, LucideIconComponent],
  template: `
    <div class="p-7 rounded-2xl bg-white border border-slate-200 flex flex-col justify-between gap-6 shadow-xs h-full flex-1">
      
      <!-- Card Header -->
      <div class="flex items-center justify-between pb-4 border-b border-slate-200">
        <div class="flex items-center gap-2.5">
          <app-lucide-icon name="circle-x" [size]="20" class="text-rose-600"></app-lucide-icon>
          <h2 class="text-base font-bold text-slate-900 font-heading">Alerts / Incidents</h2>
        </div>
        <span class="text-xs text-slate-500 font-medium">{{ incidents.length }} incidents</span>
      </div>

      <!-- Incidents List / Empty State -->
      @if (incidents.length === 0) {
        <div class="py-8 flex flex-col items-center justify-center text-center gap-2 my-auto">
          <div class="w-9 h-9 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-600 flex items-center justify-center">
            <app-lucide-icon name="shield-check" [size]="18"></app-lucide-icon>
          </div>
          <span class="text-xs font-bold text-slate-800">No active incidents</span>
          <p class="text-[11px] text-slate-500 font-medium">Zero operational alerts or barrier warnings reported.</p>
        </div>
      } @else {
        <div class="flex flex-col divide-y divide-slate-200/80">
          @for (inc of incidents; track inc.id) {
            <div class="py-3 first:pt-0 last:pb-0 flex items-start justify-between gap-3 text-xs">
              <div class="flex items-start gap-2.5">
                <span 
                  class="w-2 h-2 rounded-full mt-1.5 shrink-0"
                  [class.bg-rose-500]="inc.severity === 'critical'"
                  [class.bg-amber-500]="inc.severity === 'warning'"
                  [class.bg-blue-500]="inc.severity === 'info'">
                </span>
                <div class="flex flex-col gap-0.5">
                  <span class="font-bold text-slate-900">{{ inc.subject }}</span>
                  <span class="text-[11px] text-slate-500 font-medium">{{ inc.context }}</span>
                </div>
              </div>

              <div class="flex items-center gap-2.5 shrink-0">
                <span class="text-[10px] font-mono text-slate-400 font-medium">{{ inc.age }}</span>
                <button
                  type="button"
                  (click)="goToMonitoring()"
                  class="h-8 px-3 rounded-lg bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold shadow-2xs transition-colors cursor-pointer select-none">
                  Investigate
                </button>
              </div>
            </div>
          }
        </div>
      }

      <div class="pt-3 border-t border-slate-200 flex items-center justify-between text-xs text-slate-500 font-medium">
        <span>Incident Engine: Real-time Sentry</span>
        <span class="inline-flex items-center gap-1.5 text-emerald-700 text-[11px] font-semibold">
          <span class="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
          <span>Nominal</span>
        </span>
      </div>

    </div>
  `
})
export class AlertsIncidentsComponent {
  @HostBinding('class') public hostClass = 'flex flex-col h-full flex-1';
  @Input() public incidents: AlertIncident[] = [];

  constructor(private router: Router) {}

  public goToMonitoring(): void {
    this.router.navigate(['/monitoring']);
  }
}

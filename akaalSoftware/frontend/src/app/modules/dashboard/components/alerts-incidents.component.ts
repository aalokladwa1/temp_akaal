import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { AlertIncident } from '../../../core/models/dashboard.models';
import { LucideIconComponent } from '../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-alerts-incidents',
  standalone: true,
  imports: [CommonModule, LucideIconComponent],
  template: `
    <div class="p-7 rounded-2xl bg-white border border-slate-200/90 flex flex-col gap-6 shadow-xs h-full">
      
      <!-- Card Header -->
      <div class="flex items-center justify-between pb-4 border-b border-slate-100">
        <div class="flex items-center gap-2.5">
          <app-lucide-icon name="circle-x" [size]="20" class="text-rose-600"></app-lucide-icon>
          <h2 class="text-base font-bold text-slate-900 font-heading">Alerts / Incidents</h2>
        </div>
        <span class="text-xs text-slate-600 font-semibold">{{ incidents.length }} incidents</span>
      </div>

      <!-- Incidents List -->
      @if (incidents.length === 0) {
        <div class="py-12 flex flex-col items-center justify-center text-center gap-2">
          <div class="w-10 h-10 rounded-xl bg-slate-50 flex items-center justify-center text-slate-500">
            <app-lucide-icon name="shield-check" [size]="20"></app-lucide-icon>
          </div>
          <span class="text-xs font-bold text-slate-800">No active incidents</span>
          <p class="text-[11px] text-slate-600 font-medium">Zero active operational alerts reported.</p>
        </div>
      } @else {
        <div class="flex flex-col divide-y divide-slate-100">
          @for (inc of incidents; track inc.id) {
            <div class="py-3.5 first:pt-0 last:pb-0 flex items-start justify-between gap-3 text-xs">
              <div class="flex items-start gap-2.5">
                <span 
                  class="w-2 h-2 rounded-full mt-1 shrink-0"
                  [class.bg-rose-500]="inc.severity === 'critical'"
                  [class.bg-amber-500]="inc.severity === 'warning'"
                  [class.bg-blue-500]="inc.severity === 'info'">
                </span>
                <div class="flex flex-col gap-0.5">
                  <span class="font-bold text-slate-900">{{ inc.subject }}</span>
                  <span class="text-[11px] text-slate-600 font-medium">{{ inc.context }}</span>
                </div>
              </div>

              <div class="flex items-center gap-3 shrink-0">
                <span class="text-[10px] text-slate-500 font-medium">{{ inc.age }}</span>
                <button
                  type="button"
                  (click)="goToMonitoring()"
                  class="px-3 py-1.5 rounded-xl bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold shadow-2xs transition-colors cursor-pointer">
                  Investigate
                </button>
              </div>
            </div>
          }
        </div>
      }

    </div>
  `
})
export class AlertsIncidentsComponent {
  @Input() public incidents: AlertIncident[] = [];

  constructor(private router: Router) {}

  public goToMonitoring(): void {
    this.router.navigate(['/monitoring']);
  }
}

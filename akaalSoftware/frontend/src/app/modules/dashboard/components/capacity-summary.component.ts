import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { CapacityMetric } from '../../../core/models/dashboard.models';
import { LucideIconComponent } from '../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-capacity-summary',
  standalone: true,
  imports: [CommonModule, LucideIconComponent],
  template: `
    <div class="p-7 rounded-2xl bg-white border border-slate-200/90 flex flex-col gap-6 shadow-xs h-full">
      
      <!-- Card Header -->
      <div class="flex items-center justify-between pb-4 border-b border-slate-100">
        <div class="flex items-center gap-2.5">
          <app-lucide-icon name="cpu" [size]="20" class="text-blue-600"></app-lucide-icon>
          <h2 class="text-base font-bold text-slate-900 font-heading">Capacity</h2>
        </div>
        <span class="text-xs text-slate-600 font-semibold">Resource Pressure</span>
      </div>

      <!-- Resource Gauges (Clean Modern Rows) -->
      <div class="flex flex-col divide-y divide-slate-100">
        @for (cap of metrics; track cap.resource) {
          <div class="py-3.5 first:pt-0 last:pb-0 flex flex-col gap-2">
            <div class="flex items-center justify-between text-xs">
              <span class="font-semibold text-slate-700">{{ cap.resource }}</span>
              <span class="text-slate-900 font-semibold">
                {{ cap.used !== null ? cap.used : '—' }} / {{ cap.total !== null ? cap.total : '—' }} {{ cap.unit }}
              </span>
            </div>

            <div class="w-full h-2 rounded-full bg-slate-100 overflow-hidden">
              <div 
                class="h-full rounded-full transition-all duration-300"
                [class.bg-blue-600]="(cap.percent ?? 0) < 80"
                [class.bg-amber-500]="(cap.percent ?? 0) >= 80 && (cap.percent ?? 0) < 90"
                [class.bg-rose-500]="(cap.percent ?? 0) >= 90"
                [style.width.%]="cap.percent ?? 0">
              </div>
            </div>

            <div class="flex justify-between text-[11px] text-slate-500">
              <span>Utilization</span>
              <span class="font-bold text-slate-800">{{ cap.percent !== null ? cap.percent + '%' : 'No runtime data' }}</span>
            </div>
          </div>
        }
      </div>

    </div>
  `
})
export class CapacitySummaryComponent {
  @Input() public metrics: CapacityMetric[] = [];
}

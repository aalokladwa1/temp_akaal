import { Component, Input, HostBinding } from '@angular/core';
import { CommonModule } from '@angular/common';
import { CapacityMetric } from '../../../core/models/dashboard.models';
import { LucideIconComponent } from '../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-capacity-summary',
  standalone: true,
  imports: [CommonModule, LucideIconComponent],
  template: `
    <div class="p-7 rounded-2xl bg-white border border-slate-200 flex flex-col justify-between gap-6 shadow-xs h-full flex-1">
      
      <!-- Card Header -->
      <div class="flex items-center justify-between pb-4 border-b border-slate-200">
        <div class="flex items-center gap-2.5">
          <app-lucide-icon name="cpu" [size]="20" class="text-blue-600"></app-lucide-icon>
          <h2 class="text-base font-bold text-slate-900 font-heading">Capacity</h2>
        </div>
        <span class="text-xs text-slate-500 font-medium">Resource Pressure</span>
      </div>

      <!-- Resource Gauges (Strict Tabular Right-Aligned Numerals) -->
      <div class="flex flex-col divide-y divide-slate-200/80">
        @for (cap of metrics; track cap.resource) {
          <div class="py-2.5 first:pt-0 last:pb-0 flex flex-col gap-1.5">
            <div class="flex items-baseline justify-between text-xs">
              <span class="font-medium text-slate-700">{{ cap.resource }}</span>
              <span class="font-mono text-slate-900 font-semibold tabular-nums text-right">
                {{ cap.used !== null ? cap.used : '0' }} / {{ cap.total !== null ? cap.total : '—' }} <span class="font-sans text-[11px] text-slate-500 font-normal">{{ cap.unit }}</span>
              </span>
            </div>

            <!-- Full Width Progress Bar Track -->
            <div class="w-full h-1.5 rounded-full bg-slate-100 overflow-hidden">
              <div 
                class="h-full rounded-full transition-all duration-300"
                [class.bg-blue-600]="(cap.percent ?? 0) < 80"
                [class.bg-amber-500]="(cap.percent ?? 0) >= 80 && (cap.percent ?? 0) < 90"
                [class.bg-rose-500]="(cap.percent ?? 0) >= 90"
                [style.width.%]="cap.percent ?? 0">
              </div>
            </div>

            <!-- Bottom Subtext Strictly Right-Aligned to Track Edge -->
            <div class="flex justify-between items-baseline text-[11px]">
              <span class="text-slate-400 font-medium">Utilization</span>
              <span class="font-mono font-bold text-slate-800 tabular-nums text-right">
                {{ cap.percent !== null ? cap.percent + '%' : '0%' }}
              </span>
            </div>
          </div>
        }
      </div>

    </div>
  `
})
export class CapacitySummaryComponent {
  @HostBinding('class') public hostClass = 'flex flex-col h-full flex-1';
  @Input() public metrics: CapacityMetric[] = [];
}

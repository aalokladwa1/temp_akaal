import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MonitoringService } from '../services/monitoring.service';
import { LucideIconComponent } from '../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-monitoring-operational-pressure',
  standalone: true,
  imports: [CommonModule, LucideIconComponent],
  template: `
    <!-- Operational Pressure (Section 6) -->
    <div class="p-6 rounded-2xl bg-white dark:bg-[#141517] border border-slate-200 dark:border-[#232428] shadow-2xs flex flex-col gap-4 select-none">
      
      <!-- Header -->
      <div class="flex items-center justify-between pb-3 border-b border-slate-200 dark:border-white/[0.08] flex-wrap gap-2">
        <div class="flex items-center gap-2">
          <app-lucide-icon name="gauge" [size]="16" class="text-blue-600 dark:text-blue-400"></app-lucide-icon>
          <span class="text-xs font-bold text-slate-900 dark:text-slate-100 uppercase tracking-wider font-heading">Operational Pressure &amp; Headroom</span>
        </div>
        <span class="text-[11px] font-mono text-slate-500 dark:text-slate-400">
          Thresholds: Warning &ge;70% &bull; Critical &ge;85%
        </span>
      </div>

      <!-- 5 Resource Meters Grid -->
      <div class="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-5 gap-3 lg:gap-4">
        @for (res of ms.operationalPressure(); track res.key) {
          <div class="p-4 rounded-xl bg-white dark:bg-[#1a1b1e] border border-slate-200 dark:border-[#26272b] flex flex-col justify-between gap-3 shadow-2xs">
            
            <!-- Resource Label & Trend Marker -->
            <div class="flex items-center justify-between">
              <span class="text-[11px] font-bold text-slate-700 dark:text-slate-300 uppercase tracking-wider truncate">
                {{ res.label }}
              </span>
              
              <div 
                class="flex items-center gap-1 text-[11px] font-semibold"
                [ngClass]="{
                  'text-emerald-700 dark:text-emerald-400': res.trend === 'improving',
                  'text-slate-600 dark:text-slate-400': res.trend === 'stable',
                  'text-rose-700 dark:text-rose-400': res.trend === 'worsening',
                  'text-slate-400 dark:text-slate-500': res.trend === 'unknown'
                }">
                @if (res.trend === 'improving') {
                  <app-lucide-icon name="trending-down" [size]="13"></app-lucide-icon>
                  <span class="capitalize text-[10px]">Cooling</span>
                } @else if (res.trend === 'worsening') {
                  <app-lucide-icon name="trending-up" [size]="13"></app-lucide-icon>
                  <span class="capitalize text-[10px]">Rising</span>
                } @else if (res.trend === 'stable') {
                  <app-lucide-icon name="minus" [size]="13"></app-lucide-icon>
                  <span class="capitalize text-[10px]">Stable</span>
                } @else {
                  <span class="capitalize text-[10px]">Unknown</span>
                }
              </div>
            </div>

            <!-- Current Value & Headroom Subtext -->
            <div class="flex flex-col gap-1.5">
              <div class="flex items-baseline justify-between gap-2">
                <span class="text-xl font-bold font-mono text-slate-900 dark:text-slate-100 tracking-tight tabular-nums">
                  {{ res.current_value_label }}
                </span>
                <span class="text-[11px] font-mono text-slate-500 dark:text-slate-400 tabular-nums truncate">
                  {{ res.headroom_label }}
                </span>
              </div>

              <!-- Meter Bar with Threshold Semantic Color -->
              <div class="w-full bg-slate-200 dark:bg-slate-700/60 rounded-full h-2 overflow-hidden">
                <div 
                  class="h-2 rounded-full transition-all duration-300"
                  [style.width.%]="res.utilization_percent"
                  [ngClass]="{
                    'bg-rose-600': res.utilization_percent >= res.threshold_critical_percent,
                    'bg-amber-500': res.utilization_percent >= res.threshold_warning_percent && res.utilization_percent < res.threshold_critical_percent,
                    'bg-blue-600': res.utilization_percent < res.threshold_warning_percent
                  }">
                </div>
              </div>
            </div>

            <!-- Status Indicator Text -->
            <div class="flex items-center justify-between text-[10px] font-semibold">
              <span class="text-slate-500 dark:text-slate-400 font-mono">Utilization</span>
              @if (res.utilization_percent >= res.threshold_critical_percent) {
                <span class="text-rose-700 dark:text-rose-400">CRITICAL PRESSURE</span>
              } @else if (res.utilization_percent >= res.threshold_warning_percent) {
                <span class="text-amber-700 dark:text-amber-400">ELEVATED</span>
              } @else {
                <span class="text-emerald-700 dark:text-emerald-400">NOMINAL</span>
              }
            </div>

          </div>
        }
      </div>

    </div>
  `
})
export class MonitoringOperationalPressureComponent {
  public ms = inject(MonitoringService);
}

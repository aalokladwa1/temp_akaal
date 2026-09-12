import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { MonitoringService } from '../services/monitoring.service';
import { PlatformHealthArea } from '../models/monitoring.models';
import { LucideIconComponent } from '../../../shared/components/lucide-icon.component';

@Component({
  selector: 'app-monitoring-platform-health',
  standalone: true,
  imports: [CommonModule, RouterLink, LucideIconComponent],
  template: `
    <!-- Platform & Data Path Health (Section 5) -->
    <div class="p-6 rounded-2xl bg-white border border-slate-200 shadow-2xs flex flex-col gap-4 select-none">
      
      <!-- Header -->
      <div class="flex items-center justify-between pb-3 border-b border-slate-200 flex-wrap gap-2">
        <div class="flex items-center gap-2">
          <app-lucide-icon name="server" [size]="16" class="text-blue-600"></app-lucide-icon>
          <span class="text-xs font-bold text-slate-900 uppercase tracking-wider font-heading">Platform &amp; Data Path Health</span>
        </div>
        <a
          routerLink="/monitoring/platform"
          class="h-7 px-2.5 rounded-lg bg-slate-50 hover:bg-blue-50 text-slate-700 hover:text-blue-700 border border-slate-200 hover:border-blue-200 text-xs font-semibold transition-all shadow-2xs inline-flex items-center gap-1.5 group cursor-pointer">
          <span>Platform Operations</span>
          <app-lucide-icon name="arrow-right" [size]="12" class="text-slate-400 group-hover:text-blue-600 group-hover:translate-x-0.5 transition-all"></app-lucide-icon>
        </a>
      </div>

      <!-- 6 Major Operational Areas Grid -->
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3.5">
        @for (area of ms.platformHealth(); track area.key) {
          <div 
            class="p-4 rounded-xl border transition-all flex flex-col justify-between gap-3 shadow-2xs hover:border-slate-300 hover:shadow-xs"
            [ngClass]="{
              'bg-white border-slate-200': area.health === 'HEALTHY',
              'bg-amber-50/40 border-amber-300': area.health === 'DEGRADED',
              'bg-rose-50/40 border-rose-300': area.health === 'UNHEALTHY',
              'bg-slate-50 border-slate-200': area.health === 'UNKNOWN'
            }">
            
            <!-- Top: Title & Status Badge -->
            <div class="flex items-center justify-between gap-2">
              <span class="text-xs font-bold text-slate-900 font-heading">{{ area.title }}</span>
              
              @if (area.health === 'HEALTHY') {
                <span class="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-md text-[11px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
                  <span class="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
                  <span>Healthy</span>
                </span>
              } @else if (area.health === 'DEGRADED') {
                <span class="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-md text-[11px] font-bold bg-amber-50 text-amber-800 border border-amber-300">
                  <span class="w-1.5 h-1.5 rounded-full bg-amber-600"></span>
                  <span>Degraded</span>
                </span>
              } @else if (area.health === 'UNHEALTHY') {
                <span class="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-md text-[11px] font-bold bg-rose-50 text-rose-800 border border-rose-300">
                  <span class="w-1.5 h-1.5 rounded-full bg-rose-600"></span>
                  <span>Unhealthy</span>
                </span>
              } @else {
                <span class="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-md text-[11px] font-semibold bg-slate-100 text-slate-700 border border-slate-200">
                  <span class="w-1.5 h-1.5 rounded-full bg-slate-400"></span>
                  <span>Unknown</span>
                </span>
              }
            </div>

            <!-- Bottom: Degraded Alert Warning (if abnormal) or Nominal Metric -->
            <div class="pt-2 border-t border-slate-100 flex items-center justify-between text-xs">
              @if (area.degraded_summary) {
                <div class="flex items-center gap-1.5 text-amber-800 font-semibold truncate">
                  <app-lucide-icon name="alert-circle" [size]="13" class="text-amber-600 shrink-0"></app-lucide-icon>
                  <span class="truncate">{{ area.degraded_summary }}</span>
                </div>
              } @else {
                <span class="text-slate-500 font-mono text-[11px]">
                  {{ area.active_count }} / {{ area.total_count }} active nodes
                </span>
                <span class="text-emerald-700 font-semibold text-[11px]">100% nominal</span>
              }
            </div>

          </div>
        }
      </div>

    </div>
  `
})
export class MonitoringPlatformHealthComponent {
  public ms = inject(MonitoringService);
}
